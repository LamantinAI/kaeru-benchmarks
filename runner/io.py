"""Host-side artifact utilities; never place grading inputs in actor workspaces."""

import hashlib
from datetime import date
import json
import os
from pathlib import Path
import subprocess


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    def encode(item):
        if isinstance(item, date):
            return item.isoformat()
        raise TypeError(f"unsupported artifact type: {type(item).__name__}")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=encode) + "\n")
    temporary.replace(path)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git_revision(path: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def clean_kaeru_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if not key.startswith("KAERU_")}


def snapshot(workspace: Path) -> list[dict]:
    result = []
    for path in sorted(workspace.rglob("*")):
        if path.is_symlink():
            result.append({"path": str(path.relative_to(workspace)), "symlink": os.readlink(path)})
        elif path.is_file():
            result.append({"path": str(path.relative_to(workspace)), "sha256": digest(path),
                           "bytes": path.stat().st_size})
    return result
