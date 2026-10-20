"""Materialize declared dataset workspaces without branching on case identities."""

from pathlib import Path
import re
import shutil
import subprocess


def write_file(workspace: Path, relative: str, content: str) -> None:
    destination = (workspace / relative).resolve()
    if not destination.is_relative_to(workspace.resolve()):
        raise ValueError("artifact path escapes workspace")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content)


def workspace_files(case_dir: Path, fixture: dict) -> list[tuple[Path, Path]]:
    declared = fixture.get("workspace", {}).get("files")
    if declared is None:
        return []
    source_root = (case_dir / declared).resolve()
    if not source_root.is_relative_to(case_dir.resolve()) or not source_root.is_dir():
        raise ValueError("workspace files must be a directory inside the case")
    files = []
    for source in sorted(source_root.rglob("*")):
        if source.is_symlink():
            raise ValueError("workspace fixture cannot contain symlinks")
        if source.is_file():
            files.append((source, source.relative_to(source_root)))
    return files


def prepare_git_repositories(workspace: Path, names: list[str]) -> None:
    if len(names) != len(set(names)) or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name) for name in names):
        raise ValueError("invalid or duplicate local repository name")
    for name in names:
        bare = workspace / "repos/remotes" / f"{name}.git"
        clone = workspace / "repos" / name
        bare.parent.mkdir(parents=True, exist_ok=True)
        def git(*args):
            subprocess.run(["git", *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        git("init", "--bare", "--initial-branch=main", str(bare))
        git("clone", str(bare), str(clone))
        git("-C", str(clone), "config", "user.name", "Benchmark User")
        git("-C", str(clone), "config", "user.email", "bench@example.invalid")
        (clone / "README.md").write_text(f"Local {name} repository.\n")
        git("-C", str(clone), "add", "README.md")
        git("-C", str(clone), "-c", "commit.gpgsign=false", "commit", "-m", "initial local workspace")
        git("-C", str(clone), "push", "-u", "origin", "main")


def prepare(workspace: Path, case_dir: Path, fixture: dict) -> dict:
    workspace.mkdir(parents=True, exist_ok=False)
    artifacts = fixture.get("artifacts", [])
    for artifact in artifacts:
        write_file(workspace, artifact["path"], artifact["content"])
    files = workspace_files(case_dir, fixture)
    for source, relative in files:
        destination = workspace / relative
        if destination.exists():
            raise ValueError("declared workspace files conflict with an inline artifact")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if source.stat().st_mode & 0o111:
            destination.chmod(destination.stat().st_mode | 0o111)
    if not (workspace / "project-context.md").exists():
        write_file(workspace, "project-context.md", f"Initiative: {fixture['initiative']}.\n")
    repositories = fixture.get("workspace", {}).get("git_repositories", [])
    if repositories:
        prepare_git_repositories(workspace, repositories)
    return {"workspace": workspace.name, "workspace_files": [str(relative) for _, relative in files],
            "git_repositories": repositories, "artifacts": [a["path"] for a in artifacts]}
