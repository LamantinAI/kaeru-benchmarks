"""Validate a local batch configuration without executing model calls."""

import argparse
import json
from pathlib import Path


def confined(workspace: Path, value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("configure a dataset path")
    path = (workspace / value).resolve()
    if not path.is_relative_to(workspace.resolve()):
        raise ValueError("paths must remain inside the local workspace")
    return path


def validate(workspace: Path, config: dict) -> dict:
    dataset = confined(workspace, config.get("dataset"))
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    if not records or any(not isinstance(row, dict) for row in records):
        raise ValueError("dataset must contain JSON objects")
    jobs = config.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("configure at least one job")
    names = set()
    for job in jobs:
        name = job.get("name")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("job names must be nonempty and unique")
        names.add(name)
        if job.get("effort") not in {"low", "medium", "high"}:
            raise ValueError("configure an explicit supported effort")
    return {"dataset": str(dataset.relative_to(workspace.resolve())),
            "records": len(records), "jobs": jobs, "executed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="jobs/config.json")
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    config = json.loads(confined(workspace, args.config).read_text())
    print(json.dumps(validate(workspace, config)))


if __name__ == "__main__":
    main()
