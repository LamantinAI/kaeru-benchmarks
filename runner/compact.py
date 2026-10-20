"""Compact an owned completed benchmark thread, preserving observable proof."""

import json
from pathlib import Path
import time

from .app_server import AppServer
from .io import write_json
from .policy import agent_options, config_arguments


def compact_thread(*, executable: str, thread: str, workspace: Path, output: Path,
                   previous_turn: Path, url: str, model: str, effort: str,
                   policy: str | None, timeout: float, isolation=None) -> dict:
    previous = json.loads(previous_turn.read_text())
    if previous.get("thread_id") != thread or previous.get("status") != "COMPLETED":
        raise ValueError("compaction requires a completed turn owned by this case")
    report = {"thread_id": thread, "request_method": "thread/compact/start",
              "real_compaction_event": False, "status": "STARTING"}
    write_json(output / "compaction-check.json", report)
    started = time.monotonic()
    deadline = started + timeout
    command = [executable, "app-server", "--listen", "stdio://"]
    options = agent_options(url, effort, policy, isolated=isolation is not None,
                            shell_path=str(workspace / "bin") + ":/usr/local/bin:/usr/bin:/bin")
    command.extend(config_arguments({"model": model, **options}))
    if isolation:
        command = isolation.command(command)
    connection = None
    compact_turn = None
    try:
        connection = AppServer(command, workspace, output)
        connection.request("initialize", {"clientInfo": {"name": "kaeru-benchmark-compaction", "version": "1"},
                                           "capabilities": {"experimentalApi": True}}, deadline)
        connection.send({"method": "initialized"})
        original = connection.request("thread/read", {"threadId": thread, "includeTurns": False}, deadline)
        metadata = original.get("thread", {})
        if (metadata.get("id") != thread or Path(metadata.get("cwd", "")).resolve() != workspace.resolve()
                or metadata.get("status", {}).get("type") not in {"idle", "notLoaded"}):
            raise ValueError("thread ownership, workspace or idle state does not match")
        write_json(output / "compaction-thread-before.json", original)
        resumed = connection.request("thread/resume", {
            "threadId": thread, "excludeTurns": True, "cwd": str(workspace),
            "model": model, "sandbox": options["sandbox_mode"], "approvalPolicy": "never",
            "config": options,
        }, deadline)
        write_json(output / "compaction-resume.json", resumed)
        if (resumed.get("thread", {}).get("id") != thread or resumed.get("model") != model
                or Path(resumed.get("cwd", "")).resolve() != workspace.resolve()
                or resumed.get("sandbox", {}).get("type") != ("dangerFullAccess" if isolation else "workspaceWrite")
                or resumed.get("approvalPolicy") != "never"):
            raise ValueError("resume changed the thread, model, workspace or permissions")
        # Discard notifications already observed during read/resume. Notifications
        # racing the compaction ack stay buffered by AppServer.request.
        connection.notifications.clear()
        connection.request("thread/compact/start", {"threadId": thread}, deadline)
        report["status"] = "ACKNOWLEDGED"
        write_json(output / "compaction-check.json", report)
        started_items = set()
        completed_items = set()
        successful_turns = set()
        while True:
            message = connection.notification(deadline)
            params = message.get("params", {})
            if params.get("threadId") != thread:
                continue
            method = message["method"]
            item = params.get("item", {})
            turn_id = params.get("turnId")
            if method == "turn/started":
                compact_turn = params.get("turn", {}).get("id")
            if item.get("type") == "contextCompaction" and item.get("id") and turn_id:
                compact_turn = turn_id
                key = (turn_id, item["id"])
                if method == "item/started":
                    started_items.add(key)
                elif method == "item/completed":
                    completed_items.add(key)
            if method == "turn/completed":
                turn = params.get("turn", {})
                if compact_turn and turn.get("id") == compact_turn and turn.get("status") != "completed":
                    raise RuntimeError("compaction turn failed or was interrupted")
                if turn.get("status") == "completed":
                    successful_turns.add(turn.get("id"))
            matched = started_items & completed_items
            confirmed = [key for key in matched if key[0] in successful_turns]
            if confirmed:
                turn_id, item_id = sorted(confirmed)[0]
                report.update(status="COMPLETED", real_compaction_event=True,
                              turn_id=turn_id, item_id=item_id)
                break
        after = connection.request("thread/read", {"threadId": thread, "includeTurns": False}, deadline)
        write_json(output / "compaction-thread-after.json", after)
        if after.get("thread", {}).get("id") != thread:
            raise RuntimeError("compaction returned a different thread")
        return report
    except Exception as exc:
        report.update(status="FAILED", real_compaction_event=False, error=f"{type(exc).__name__}: {exc}")
        if connection and compact_turn:
            try:
                connection.request("turn/interrupt", {"threadId": thread, "turnId": compact_turn},
                                   time.monotonic() + 3)
                report["interrupt_requested"] = True
            except Exception:
                report["interrupt_requested"] = False
        raise
    finally:
        if connection:
            connection.close()
        report["elapsed_seconds"] = time.monotonic() - started
        write_json(output / "compaction-check.json", report)
