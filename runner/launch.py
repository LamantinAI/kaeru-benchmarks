"""Sequential case orchestration. Completion is never a correctness grade."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import uuid

from .agent import run_turn
from .audit import snapshot_api, validate_cloud, validate_search
from .client import R2Client
from .compact import compact_thread
from .environment import Environment
from .fixtures import InvalidFixture, input_files, load_case, normalize, select_cases, verify_seed
from .io import clean_kaeru_env, digest, git_revision, snapshot, write_json
from .isolation import Bubblewrap
from .process import run_logged
from .policy import MEMORY_POLICY
from .workspaces import prepare


def summary(records: list[dict]) -> dict:
    turns = [turn for case in records for turn in case["turns"]]
    usage = Counter()
    by_thread = {}
    for turn in turns:
        if turn.get("thread_id") and turn.get("usage") is not None:
            by_thread[turn["thread_id"]] = turn["usage"]
    for counters in by_thread.values():
        for key, value in counters.items():
            if isinstance(value, (float, int)):
                usage[key] += value
    return {"status_counts": dict(Counter(r["status"] for r in records)),
            "results": [{"case_id": r["case_id"], "repetition": r["repetition"],
                         "status": r["status"], "reason": r.get("reason"),
                         "turns": len(r["turns"])} for r in records],
            "usage": dict(usage), "kaeru_tool_calls": sum(t.get("kaeru_tool_calls", 0) for t in turns),
            "usage_basis": "last reported native cumulative counters per thread; no double-counting resumes",
            "compaction_cost": "unknown when the native compaction event does not report model usage",
            "turns_without_memory_read": sum(t.get("memory_policy") == "required"
                                            and not t.get("memory_read_observed") for t in turns),
            "elapsed_turn_seconds": sum(t["elapsed_seconds"] for t in turns), "grading": "NOT_GRADED"}


def helper_run(helper: Path, action: str, output: Path, name: str) -> dict:
    status = run_logged([str(helper), action, str(output / "fixture.json"),
                         str(output / "vault"), str(output / f"{name}.json")],
                        output, name, timeout=120, env=clean_kaeru_env())
    if status["returncode"] != 0:
        raise InvalidFixture(f"fixture helper failed during {action}; see {name}.stderr")
    return json.loads((output / f"{name}.json").read_text())


def run_case(config, case_dir: Path, output: Path) -> dict:
    case, fixture = load_case(case_dir)
    turns = case.get("turns", [{"id": "turn-1", "prompt": case.get("prompt")}])
    result = {"case_id": case["id"], "status": "PREPARING", "grading": "NOT_GRADED", "turns": []}
    write_json(output / "case.json", case)
    if fixture.get("cloud_nodes") and not config.cloud_binary:
        result.update(status="UNSUPPORTED_CLOUD", reason="Cloud fixture requires --cloud-binary")
        return result
    environment = None
    isolation = None
    seeded = False
    with tempfile.TemporaryDirectory(prefix="kb-") as temporary:
        workspace = Path(temporary) / ("w-" + uuid.uuid4().hex)
        try:
            manifest = normalize(case_dir, fixture, datetime.now(timezone.utc))
            write_json(output / "fixture.json", manifest)
            write_json(output / "workspace.json", prepare(workspace, case_dir, fixture))
            if not config.prepare_only and config.isolation == "bubblewrap":
                isolation = Bubblewrap(config.native_binary, workspace, Path(temporary) / "runtime")
                isolation.preflight(output, [case_dir, output / "fixture.json",
                                            Path.home() / ".agentmemo", Path.home() / ".codex/AGENTS.md"])
            before = helper_run(config.helper, "seed", output, "seed-state")
            seeded = True
            verify_seed(manifest, before)
            environment = Environment(config.binary, output / "vault", output,
                                      cloud_binary=config.cloud_binary)
            session = environment.start(manifest)
            client = R2Client(session.request)
            catalogue = client.discover()
            if not {"context", "read", "search", "note", "verdict", "trail"}.issubset(catalogue):
                raise InvalidFixture("tested binary does not expose the R2 API")
            write_json(output / "tools.json", catalogue)
            validate_search(client, manifest, output)
            validate_cloud(client, manifest, output)
            write_json(output / "fixture-validation.json", {"status": "VALID"})
            # A writable filesystem is proved before requesting any model work.
            probe = workspace / ".runner-write-probe"
            probe.write_text("writable")
            if probe.read_text() != "writable":
                raise RuntimeError("workspace write probe failed")
            probe.unlink()
            if config.prepare_only:
                result["status"] = "PREPARED"
            else:
                thread = None
                for index, turn in enumerate(turns, 1):
                    label = f"turn-{index}"
                    same = turn.get("session") == "same"
                    if same and not thread:
                        raise RuntimeError("same-session turn has no owned previous thread")
                    if turn.get("after") == "context-compaction":
                        if not same:
                            raise RuntimeError("compaction must preserve the same thread")
                        compact_thread(executable=config.agent, thread=thread, workspace=workspace,
                                       output=output, previous_turn=output / f"turn-{index-1}.run.json",
                                       url=environment.url, model=config.model, effort=config.effort,
                                       policy=config.policy, timeout=config.timeout, isolation=isolation)
                    snapshot_api(client, environment.artifact_root, label + "-before", output)
                    record = run_turn(executable=config.agent, model=config.model, effort=config.effort,
                                      url=environment.url, workspace=workspace, output=output,
                                      prompt=turn["prompt"], label=label, timeout=config.timeout,
                                      thread=thread if same else None, policy=config.policy, isolation=isolation)
                    previous_thread, thread = thread, record["thread_id"]
                    if (not same and previous_thread and thread == previous_thread):
                        record["status"] = "EXECUTION_ERROR"
                        record["reason"] = "fresh session reused the previous thread"
                    result["turns"].append(record)
                    write_json(output / "progress.json", result)
                    snapshot_api(client, environment.artifact_root, label + "-after", output)
                    if record["status"] != "COMPLETED":
                        result["status"] = record["status"]
                        break
                else:
                    result["status"] = "EXECUTED"
        except InvalidFixture as exc:
            result.update(status="INVALID_FIXTURE", reason=str(exc))
        except Exception as exc:
            result.update(status="ENVIRONMENT_ERROR", reason=f"{type(exc).__name__}: {exc}")
        finally:
            if environment:
                environment.close()
            if isolation:
                isolation.save_sessions(output)
            if seeded:
                try:
                    helper_run(config.helper, "snapshot", output, "final-state")
                except Exception as exc:
                    result["snapshot_error"] = str(exc)
                    result["status"] = "ENVIRONMENT_ERROR"
            if workspace.is_dir():
                # Actual files, not only checksums, are required for later grading.
                import shutil
                shutil.copytree(workspace, output / "workspace-final", symlinks=True)
                write_json(output / "workspace-final.json", snapshot(workspace))
    return result


def launch(config) -> dict:
    cases = select_cases(config.dataset, config.cases)
    config.output.mkdir(parents=True, exist_ok=False)
    config.output.chmod(0o700)
    info = {"dataset": git_revision(config.dataset), "source": git_revision(config.source),
            "binary_sha256": digest(config.binary), "helper_sha256": digest(config.helper),
            "cloud_binary_sha256": digest(config.cloud_binary) if config.cloud_binary else None,
            "native_binary_sha256": digest(config.native_binary) if config.native_binary else None,
            "runner": git_revision(Path(__file__).parent), "cases": [p.name for p in cases],
            "dataset_files_sha256": {str(path.relative_to(config.dataset.parent)): digest(path)
                                     for case in cases for path in sorted(input_files(case, load_case(case)[1]))},
            "runner_files_sha256": {str(path.relative_to(Path(__file__).parent.parent)): digest(path)
                                    for path in [*Path(__file__).parent.glob("*.py"),
                                                 *Path(__file__).parent.glob("*.rs"),
                                                 Path(__file__).parent.parent / "main.py",
                                                 Path(__file__).parent.parent / "pyproject.toml"]},
            "repetitions": config.repetitions, "prepare_only": config.prepare_only,
            "model": config.model, "reasoning_effort": config.effort,
            "memory_policy": {"condition": "required" if config.policy else "none",
                              "text": config.policy,
                              "guide": {"path": str(config.memory_guide),
                                        "sha256": digest(config.memory_guide)}
                                       if config.memory_guide else None},
            "isolation": {"workspace": "opaque temporary directory", "kind": config.isolation,
                          "sandbox": "outer bubblewrap filesystem" if config.isolation == "bubblewrap" else "workspace-write",
                          "user_config": "ignored", "project_docs": "disabled",
                          "remaining_limit": "Network shared for MCP/auth" if config.isolation == "bubblewrap"
                          else "Host filesystem reads are not fully isolated by workspace-write.",
                          "agent_events": "native MCP and shell events; observer calls kept separately"},
            "started_utc": datetime.now(timezone.utc).isoformat()}
    write_json(config.output / "run.json", info)
    if config.policy:
        (config.output / "memory-policy.txt").write_text(config.policy + "\n")
    records = []
    try:
        for repetition in range(1, config.repetitions + 1):
            for case in cases:
                output = config.output / f"repeat-{repetition:02d}" / case.name
                output.mkdir(parents=True)
                result = run_case(config, case, output)
                result["repetition"] = repetition
                write_json(output / "result.json", result)
                records.append(result)
                write_json(config.output / "summary.json", summary(records))
                print(json.dumps({"case_id": case.name, "repetition": repetition, "status": result["status"]}), flush=True)
    except BaseException:
        info["status"] = "INTERRUPTED"
        raise
    else:
        info["status"] = "FINISHED"
    finally:
        info["ended_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(config.output / "run.json", info)
    return {"status_counts": dict(Counter(r["status"] for r in records)), "results": records}
