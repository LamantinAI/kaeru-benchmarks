"""Build the tiny fixture writer without changing the tested source checkout."""

import json
import logging
from pathlib import Path
import shutil
import subprocess
import tomllib

from .io import clean_kaeru_env, digest, git_revision, write_json


def build_helper(source: Path, output: Path) -> Path:
    source, output = source.resolve(), output.resolve()
    if not (source / "kaeru-core/Cargo.toml").is_file():
        raise ValueError("--source must contain kaeru-core")
    output.mkdir(parents=True, exist_ok=True)
    (output / "src").mkdir(exist_ok=True)
    shutil.copyfile(Path(__file__).with_name("fixture_helper.rs"), output / "src/main.rs")
    manifest = (
        '[package]\nname="kaeru-bench-fixture"\nversion="0.1.0"\nedition="2024"\n'
        '[workspace]\n[dependencies]\nserde_json="1"\n'
        f'kaeru-core={{path={json.dumps(str(source / "kaeru-core"))}}}\n'
    )
    source_manifest = tomllib.loads((source / "Cargo.toml").read_text())
    for registry, patches in source_manifest.get("patch", {}).items():
        manifest += f"\n[patch.{json.dumps(registry)}]\n"
        for package, settings in patches.items():
            settings = dict(settings)
            if "path" in settings:
                settings["path"] = str((source / settings["path"]).resolve())
            entries = ", ".join(f"{json.dumps(key)}={json.dumps(value)}" for key, value in settings.items())
            manifest += f"{json.dumps(package)}={{ {entries} }}\n"
    (output / "Cargo.toml").write_text(manifest)
    # Reuse the tested revision's dependency versions rather than resolving a
    # newer dependency stack for the fixture writer.
    shutil.copyfile(source / "Cargo.lock", output / "Cargo.lock")
    env = clean_kaeru_env()
    env.setdefault("CARGO_TARGET_DIR", str(source / "target"))
    with (output / "build.log").open("w") as log:
        subprocess.run(["cargo", "build", "--manifest-path", str(output / "Cargo.toml")],
                       env=env, stdout=log, stderr=log, check=True)
    # Cargo may use a host-configured shared target directory.
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--no-deps", "--format-version", "1", "--manifest-path",
         str(output / "Cargo.toml")], env=env, text=True))
    binary = Path(metadata["target_directory"]) / "debug/kaeru-bench-fixture"
    destination = output / "fixture-helper"
    shutil.copy2(binary, destination)
    write_json(output / "build-info.json", {
        "source": git_revision(source), "binary_sha256": digest(destination),
        "helper_source_sha256": digest(output / "src/main.rs"),
        "lockfile_sha256": digest(output / "Cargo.lock"),
    })
    return destination


def prepare_runtime(config, cases: list[Path]) -> None:
    from .fixtures import load_case
    cloud_needed = any(load_case(case)[1].get("cloud_nodes") for case in cases)
    packages = []
    if config.binary is None:
        packages.append("kaeru-mcp")
    if cloud_needed and config.cloud_binary is None:
        packages.append("kaeru-cloud")
    if not packages and config.helper is not None:
        return
    env = clean_kaeru_env()
    if packages:
        command = ["cargo", "build", "--locked"]
        for package in packages:
            command.extend(["-p", package])
        logging.info("Building %s", ", ".join(packages))
        subprocess.run(command, cwd=config.source, env=env, check=True)
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--no-deps", "--format-version", "1"], cwd=config.source, env=env, text=True))
    target = Path(metadata["target_directory"])
    config.binary = config.binary or target / "debug/kaeru-mcp"
    if cloud_needed:
        config.cloud_binary = config.cloud_binary or target / "debug/kaeru-cloud"
    if config.helper is None:
        logging.info("Building fixture helper")
        config.helper = build_helper(config.source, target / "kaeru-bench-helper")
