"""Disposable actor filesystem shared only by this case's turns and compaction."""

import json
import os
import platform
from pathlib import Path
import shutil

from .io import write_json
from .process import run_logged


def find_native_binary(executable: str) -> Path:
    found = shutil.which(executable)
    path = Path(found or executable).resolve()
    if path.is_file():
        with path.open("rb") as stream:
            if stream.read(4) == b"\x7fELF":
                return path
    architecture = {"x86_64": "x64", "aarch64": "arm64"}.get(platform.machine())
    if architecture and path.is_file():
        package = path.parent.parent
        platform_package = "codex-linux-" + architecture
        roots = [package / "vendor", package / "node_modules/@openai" / platform_package / "vendor",
                 package.parent / platform_package / "vendor"]
        candidates = [candidate for root in roots for candidate in root.glob("*/bin/codex") if candidate.is_file()]
        if len(candidates) == 1:
            return candidates[0].resolve()
    raise ValueError("Cannot locate native Codex executable; pass --native-binary explicitly")


class Bubblewrap:
    def __init__(self, native: Path, workspace: Path, root: Path):
        if not shutil.which("bwrap"):
            raise RuntimeError("bubblewrap is not installed")
        if not native or not native.is_file() or native.name != "codex":
            raise ValueError("--native-binary must point to the native Codex executable")
        self.native, self.workspace, self.root = native.resolve(), workspace.resolve(), root
        self.home = root / "home"
        self.home.mkdir(parents=True)
        self.host_home = Path.home()
        codex_home = Path(os.environ.get("CODEX_HOME", str(self.host_home / ".codex")))
        if not codex_home.is_relative_to(self.host_home):
            raise ValueError("isolated CODEX_HOME must be under HOME")
        self.codex_home = self.home / codex_home.relative_to(self.host_home)
        self.codex_home.mkdir(parents=True, mode=0o700)
        auth = codex_home / "auth.json"
        if not auth.is_file():
            raise ValueError("isolated native runs require existing Codex auth.json")
        shutil.copyfile(auth, self.codex_home / "auth.json")
        (self.codex_home / "auth.json").chmod(0o600)
        self.answers = root / "answers"
        self.answers.mkdir()

    def command(self, arguments: list[str], *, answer: Path | None = None) -> list[str]:
        command = ["bwrap", "--die-with-parent", "--unshare-user", "--unshare-pid",
                   "--ro-bind", "/", "/", "--tmpfs", "/home", "--dir", str(self.host_home),
                   "--bind", str(self.home), str(self.host_home), "--tmpfs", "/tmp",
                   "--proc", "/proc", "--dev", "/dev"]
        for path in ("/mnt", "/media", "/opt", "/var/tmp", "/run/user"):
            if Path(path).exists():
                command.extend(["--tmpfs", path])
        command.extend(["--ro-bind", str(self.native.parent.parent), "/opt/kaeru-codex",
                        "--bind", str(self.workspace), str(self.workspace),
                        "--bind", str(self.answers), "/tmp/answers", "--chdir", str(self.workspace),
                        "--clearenv"])
        for key in ("HOME", "CODEX_HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TZ", "TERM",
                    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                    "http_proxy", "https_proxy", "all_proxy", "no_proxy"):
            if key in os.environ:
                command.extend(["--setenv", key, os.environ[key]])
        command.extend(["--setenv", "PATH", str(self.workspace / "bin") + ":/usr/local/bin:/usr/bin:/bin"])
        args = list(arguments)
        args[0] = "/opt/kaeru-codex/bin/codex"
        if answer:
            args[args.index("-o") + 1] = "/tmp/answers/" + answer.name
        return [*command, *args]

    def take_answer(self, destination: Path) -> None:
        source = self.answers / destination.name
        if source.is_symlink():
            raise RuntimeError("actor answer must be a regular file, not a symlink")
        if source.is_file():
            shutil.copyfile(source, destination)

    def preflight(self, output: Path, hidden: list[Path]) -> None:
        script = (
            "import json,pathlib; "
            "p=pathlib.Path('.sandbox-probe'); p.write_text('ok'); assert p.read_text()=='ok'; p.unlink(); "
            f"hidden={json.dumps([str(p) for p in hidden])}; "
            "assert not any(pathlib.Path(p).exists() for p in hidden), 'hidden input visible'; "
            "print(json.dumps({'workspace_write':True,'hidden_inputs_absent':True}))"
        )
        command = self.command([str(self.native), "--version"])
        # The same outer namespace as the native agent, without a model call.
        command = command[:-2] + ["/usr/bin/python3", "-c", script]
        result = run_logged(command, output, "isolation-probe", timeout=15)
        if result["returncode"] != 0:
            raise RuntimeError("actor filesystem isolation probe failed; see isolation-probe.stderr")
        write_json(output / "isolation-check.json", {
            "workspace_write": True, "hidden_inputs_absent": True,
            "home": "disposable, no inherited configuration or memory",
            "network": "shared for test MCP and model authentication",
            "command_sandbox": "danger-full-access inside the outer filesystem namespace",
        })

    def save_sessions(self, output: Path) -> None:
        # Exclude authentication, provider configuration and internal daemon logs.
        sessions = self.codex_home / "sessions"
        if sessions.is_dir():
            shutil.copytree(sessions, output / "native-sessions", symlinks=True)
