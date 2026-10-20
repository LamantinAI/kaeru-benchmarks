"""Disposable local file exporter; job configuration selects its behavior."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def confined(workspace: Path, value: str) -> Path:
    path = (workspace / value).resolve()
    if not path.is_relative_to(workspace.resolve()):
        raise ValueError("export paths must remain inside the local workspace")
    return path


def export(workspace: Path, job: dict, source: Path) -> Path:
    destination = job.get("destination")
    if not destination:
        raise ValueError("configure the job destination first")
    final = confined(workspace, destination) / source.name
    staging = job.get("staging_destination")
    target = confined(workspace, staging) / source.name if staging else final
    source = confined(workspace, str(source))
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    target.parent.mkdir(parents=True, exist_ok=True)

    def record(action: str) -> None:
        with (workspace / "jobs/actions.jsonl").open("a") as stream:
            stream.write(json.dumps({"job": job["name"], "action": action,
                                     "path": str(target.relative_to(workspace))}) + "\n")

    shutil.copyfile(source, target)
    record("staged" if staging else "written")
    if job.get("verify_checksum", False):
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            record("checksum_mismatch")
            raise ValueError("checksum mismatch; output was not promoted")
        record("checksum_verified")
    if staging:
        final.parent.mkdir(parents=True, exist_ok=True)
        target.replace(final)
        target = final
        record("promoted")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    config = json.loads((workspace / "jobs/config.json").read_text())
    job = next(item for item in config["jobs"] if item["name"] == args.job)
    print(export(workspace, job, confined(workspace, args.input)))


if __name__ == "__main__":
    main()
