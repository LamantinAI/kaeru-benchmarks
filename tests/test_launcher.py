"""No-model checks of fixture fidelity, session ownership and failure evidence."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from runner.agent import parse_events, run_turn
from runner.fixtures import InvalidFixture, load_case, normalize, verify_seed
from runner.launch import run_case, summary
from runner.process import run_logged
from runner.workspaces import prepare, write_file


DATASET = Path(__file__).resolve().parents[1] / "tool-usage/cases"
CLOCK = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


class FixtureTests(unittest.TestCase):
    def test_all_current_cases_normalize_and_ids_are_reproducible(self):
        cases = sorted(DATASET.glob("*/case.yaml"))
        self.assertEqual(len(cases), 27)
        for case_file in cases:
            with self.subTest(case=case_file.parent.name):
                _, fixture = load_case(case_file.parent)
                first = normalize(case_file.parent, fixture, CLOCK)
                self.assertEqual(first, normalize(case_file.parent, fixture, CLOCK))
                self.assertEqual(len({n["id"] for n in first["nodes"]}), len(first["nodes"]))
                self.assertEqual(sum(n["noise"] for n in first["nodes"]), fixture["noise"]["count"])

    def test_status_deadlines_sibling_scope_and_cloud_separation_survive(self):
        def manifest(name):
            path = DATASET / name
            return normalize(path, load_case(path)[1], CLOCK)
        hypothesis = next(n for n in manifest("D2-partial-verdict")["nodes"] if n["type"] == "hypothesis")
        self.assertIn("status:open", hypothesis["tags"])
        task = next(n for n in manifest("C1-reentry-cold")["nodes"] if n["type"] == "task")
        self.assertIn("due:2026-10-11", task["tags"])
        sibling = next(n for n in manifest("A3-fragmented-project")["nodes"] if n["name"] == "invoice-rounding-decision")
        self.assertEqual(sibling["initiative"], "billing-legacy")
        cloud = manifest("E5-team-tier")
        self.assertTrue(cloud["cloud_nodes"])
        self.assertFalse({n["name"] for n in cloud["nodes"]} & {n["name"] for n in cloud["cloud_nodes"]})

    def test_exact_readback_rejects_scope_body_time_and_edges_drift(self):
        manifest = {"nodes": [{"id": "one", "name": "one", "body": "first\nsecond 'quoted'",
                               "type": "episode", "tier": "operational", "layer": "warm",
                               "tags": [], "initiative": "scope", "recorded_epoch": 100}], "edges": []}
        expected = manifest["nodes"][0]
        def state():
            return {"graph": {"nodes": [{**expected, "initiatives": ["scope"], "created_secs": 100,
                                          "visibility": "local"}], "edges": []}}
        verify_seed(manifest, state())
        for key, value in (("body", "first\\nsecond 'quoted'"), ("initiatives", ["other"]),
                           ("created_secs", 101)):
            wrong = state()
            wrong["graph"]["nodes"][0][key] = value
            with self.subTest(field=key), self.assertRaises(InvalidFixture):
                verify_seed(manifest, wrong)

    def test_opaque_workspace_contains_artifacts_but_not_memory_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "w-opaque"
            _, fixture = load_case(DATASET / "A2-unreachable-core")
            prepare(workspace, DATASET / "A2-unreachable-core", fixture)
            self.assertNotIn("TSV", (workspace / "project-context.md").read_text())
            self.assertFalse((workspace / "case.yaml").exists())
            self.assertFalse((workspace / "fixture.yaml").exists())
            with self.assertRaises(ValueError):
                write_file(workspace, "../escape", "bad")
            with self.assertRaises(FileExistsError):
                prepare(workspace, DATASET / "A2-unreachable-core", fixture)

    def test_b2_workspace_has_the_declared_three_jobs_and_two_future_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "w-opaque"
            _, fixture = load_case(DATASET / "B2-constraint-after-compaction")
            prepare(workspace, DATASET / "B2-constraint-after-compaction", fixture)
            jobs = json.loads((workspace / "jobs/config.json").read_text())["jobs"]
            self.assertEqual(sum(j["kind"] == "scheduled" for j in jobs), 3)
            self.assertEqual(sum(j["kind"] == "ad-hoc" for j in jobs), 2)
            self.assertTrue(all(j["destination"] is None for j in jobs))


class AgentTests(unittest.TestCase):
    def test_summary_counts_cumulative_thread_usage_once_across_resumes(self):
        turns = [{"thread_id": "same", "usage": {"input_tokens": 100, "output_tokens": 10}, "elapsed_seconds": 1},
                 {"thread_id": "same", "usage": {"input_tokens": 250, "output_tokens": 25}, "elapsed_seconds": 2},
                 {"thread_id": "fresh", "usage": {"input_tokens": 80, "output_tokens": 8}, "elapsed_seconds": 1}]
        report = summary([{"case_id": "test", "repetition": 1, "status": "EXECUTED", "turns": turns}])
        self.assertEqual(report["usage"], {"input_tokens": 330, "output_tokens": 33})

    def test_missing_usage_errors_and_native_tools_are_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace"
            path.write_text('\n'.join(json.dumps(e) for e in [
                {"type": "thread.started", "thread_id": "owned"},
                {"type": "item.completed", "item": {"type": "mcp_tool_call", "tool": "read", "result": {"data": "raw"}}},
                {"type": "turn.failed", "error": "failure"},
            ]) + '\nnot-json\n')
            parsed = parse_events(path)
            self.assertIsNone(parsed["usage"])
            self.assertEqual(parsed["thread_id"], "owned")
            self.assertEqual(parsed["tool_calls"][0]["result"], {"data": "raw"})
            self.assertEqual(parsed["malformed_trace_lines"], 1)
            self.assertTrue(parsed["errors"])

    def test_fresh_and_resume_commands_preserve_the_expected_thread(self):
        commands = []
        def fake(command, output, name, **kwargs):
            commands.append(command)
            thread = "owned" if "resume" not in command else command[3]
            (output / f"{name}.stdout").write_text('\n'.join(json.dumps(e) for e in [
                {"type": "thread.started", "thread_id": thread},
                {"type": "turn.completed", "usage": {"input_tokens": 23, "output_tokens": 7}},
            ]))
            return {"returncode": 0, "timed_out": False}
        with tempfile.TemporaryDirectory() as directory, patch("runner.agent.run_logged", fake):
            root = Path(directory)
            for thread in (None, "owned"):
                result = run_turn(executable="codex", model="test-model", effort="low", url="http://127.0.0.1:1/mcp",
                                  workspace=root, output=root, prompt="Do ordinary work.", label="turn",
                                  timeout=2, thread=thread)
                self.assertEqual(result["status"], "COMPLETED")
                self.assertEqual(result["thread_id"], "owned")
            self.assertNotIn("resume", commands[0])
            self.assertEqual(commands[1][2:4], ["resume", "owned"])

    def test_timeout_retains_partial_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_logged([sys.executable, "-u", "-c", "import time;print('partial');time.sleep(30)"],
                                root, "timeout", timeout=.2)
            self.assertTrue(result["timed_out"])
            self.assertIn("partial", (root / "timeout.stdout").read_text())

    def test_e5_missing_cloud_stops_before_agent_calls(self):
        with tempfile.TemporaryDirectory() as directory, patch("runner.launch.run_turn") as agent:
            config = SimpleNamespace(prepare_only=False, compactor=None, cloud_binary=None)
            for case, status in (("E5-team-tier", "UNSUPPORTED_CLOUD"),):
                output = Path(directory) / case
                output.mkdir()
                result = run_case(config, DATASET / case, output)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["grading"], "NOT_GRADED")
            agent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
