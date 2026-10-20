"""Native Codex turns; the runner does not imitate the model's tool decisions."""

import hashlib
import json
import os
from pathlib import Path
import time

from .io import clean_kaeru_env, snapshot, write_json
from .process import run_logged
from .policy import MEMORY_POLICY, agent_options, config_arguments, memory_read_count


def parse_events(path: Path) -> dict:
    thread, usage, calls, errors, malformed = None, None, [], [], 0
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if event.get("type") == "thread.started":
            thread = event.get("thread_id")
        if event.get("type") == "turn.completed":
            usage = event.get("usage")
        if event.get("type") in {"turn.failed", "error"}:
            errors.append(event)
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "mcp_tool_call":
            calls.append(item)
    return {"thread_id": thread, "usage": usage, "tool_calls": calls,
            "errors": errors, "malformed_trace_lines": malformed}


def run_turn(*, executable: str, model: str, effort: str, url: str, workspace: Path,
             output: Path, prompt: str, label: str, timeout: float, thread: str | None,
             policy: str | None = MEMORY_POLICY, isolation=None) -> dict:
    write_json(output / f"{label}.workspace-before.json", snapshot(workspace))
    common = ["--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--json",
              "-m", model, "-o", str(output / f"{label}.answer.txt")]
    options = agent_options(url, effort, policy, isolated=isolation is not None,
                            shell_path=str(workspace / "bin") + ":/usr/local/bin:/usr/bin:/bin")
    common.extend(config_arguments(options))
    command = [executable, "exec"]
    if thread:
        command.extend(["resume", thread])
    else:
        command.extend(["--sandbox", options["sandbox_mode"], "-C", str(workspace)])
    command.extend([*common, prompt])
    if isolation:
        command = isolation.command(command, answer=output / f"{label}.answer.txt")
    env = clean_kaeru_env()
    env["PATH"] = str(workspace / "bin") + os.pathsep + env.get("PATH", "")
    started = time.monotonic()
    status = run_logged(command, output, label, timeout=timeout, cwd=workspace, env=env)
    if isolation:
        isolation.take_answer(output / f"{label}.answer.txt")
    evidence = parse_events(output / f"{label}.stdout")
    evidence["thread_id"] = evidence["thread_id"] or thread
    complete = evidence["usage"] is not None
    result = {**status, **evidence, "elapsed_seconds": time.monotonic() - started,
              "usage_scope": "native_thread_cumulative",
              "kaeru_tool_calls": sum(call.get("server") == "kaeru" for call in evidence["tool_calls"]),
              "kaeru_read_calls": memory_read_count(evidence["tool_calls"]),
              "memory_policy": "required" if policy else "none",
              "memory_read_observed": memory_read_count(evidence["tool_calls"]) > 0,
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "status": "TIMEOUT" if status["timed_out"] else (
                  "COMPLETED" if status["returncode"] == 0 and complete and not evidence["errors"]
                  and evidence["thread_id"] else "EXECUTION_ERROR")}
    write_json(output / f"{label}.workspace-after.json", snapshot(workspace))
    write_json(output / f"{label}.run.json", result)
    return result
