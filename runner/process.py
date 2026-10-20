"""Owned child processes; timeout cleanup includes their subprocesses."""

import os
from pathlib import Path
import signal
import subprocess


def stop(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # The direct child can exit before its own children do.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def run_logged(command: list[str], directory: Path, name: str, *, timeout: float,
               cwd: Path | None = None, env: dict | None = None) -> dict:
    with (directory / f"{name}.stdout").open("w") as stdout, (directory / f"{name}.stderr").open("w") as stderr:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                   start_new_session=True)
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            stop(process)
    return {"returncode": process.returncode, "timed_out": timed_out}
