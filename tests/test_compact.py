"""Exercise the real stdio client against a deterministic no-model peer."""

import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from runner.compact import compact_thread
from runner.io import write_json
from runner.policy import MEMORY_POLICY, agent_options, config_arguments, memory_read_count


PEER = r'''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
mode=Path('.mode').read_text()
def send(value):
 print(json.dumps(value),flush=True)
def response(request,result):send({'id':request['id'],'result':result})
def event(method,**params):send({'method':method,'params':params})
for line in sys.stdin:
 request=json.loads(line);method=request.get('method')
 if method=='initialize':response(request,{'userAgent':'fake-test'})
 elif method=='thread/read':response(request,{'thread':{'id':request['params']['threadId'],'cwd':os.getcwd(),'status':{'type':'notLoaded'}}})
 elif method=='thread/resume':
  p=request['params'];response(request,{'thread':{'id':'wrong' if mode=='wrong-resume' else p['threadId']},'model':p['model'],'cwd':p['cwd'],'sandbox':{'type':'workspaceWrite'},'approvalPolicy':'never'})
 elif method=='thread/compact/start':
  thread=request['params']['threadId']
  if mode=='legacy-only':
   response(request,{});event('thread/compacted',threadId=thread);continue
  if mode=='ack-only':response(request,{});continue
  if mode!='early-events':response(request,{})
  tid='unrelated' if mode=='other-thread' else thread
  item={'type':'contextCompaction','id':'compact-item'}
  event('turn/started',threadId=tid,turn={'id':'compact-turn','status':'inProgress'})
  if mode!='missing-start':event('item/started',threadId=tid,turnId='compact-turn',item=item)
  event('item/completed',threadId=tid,turnId='compact-turn',item=item)
  event('turn/completed',threadId=tid,turn={'id':'compact-turn','status':'failed' if mode=='failed-turn' else 'completed'})
  if mode=='early-events':response(request,{})
 elif method=='turn/interrupt':response(request,{})
'''


class CompactionTests(unittest.TestCase):
    def run_compaction(self, root, mode):
        workspace, output = root / "workspace", root / "output"
        workspace.mkdir(); output.mkdir()
        (workspace / ".mode").write_text(mode)
        executable = root / "test-peer"
        executable.write_text(PEER); executable.chmod(0o700)
        previous = output / "turn-1.run.json"
        write_json(previous, {"thread_id": "owned-thread", "status": "COMPLETED"})
        return compact_thread(executable=str(executable), thread="owned-thread", workspace=workspace,
                              output=output, previous_turn=previous, url="http://127.0.0.1:1/mcp",
                              model="gpt-6-luna", effort="low", policy=MEMORY_POLICY, timeout=.6)

    def test_item_lifecycle_and_successful_turn_prove_compaction_in_both_ack_orders(self):
        for mode in ("normal", "early-events"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                report = self.run_compaction(root, mode)
                self.assertTrue(report["real_compaction_event"])
                self.assertEqual(report["thread_id"], "owned-thread")
                self.assertEqual(report["turn_id"], "compact-turn")
                events = [json.loads(line) for line in (root / "output/compaction-events.jsonl").read_text().splitlines()]
                resume = next(e["message"]["params"] for e in events if e["direction"] == "request"
                              and e["message"].get("method") == "thread/resume")
                self.assertEqual(resume["model"], "gpt-6-luna")
                self.assertEqual(resume["config"]["developer_instructions"], MEMORY_POLICY)
                self.assertFalse(any(e["message"].get("method") in {"thread/start", "thread/fork"} for e in events))

    def test_ack_legacy_wrong_thread_and_missing_start_are_not_success(self):
        for mode in ("ack-only", "legacy-only", "other-thread", "missing-start", "failed-turn", "wrong-resume"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises((RuntimeError, TimeoutError, ValueError)):
                    self.run_compaction(root, mode)
                report = json.loads((root / "output/compaction-check.json").read_text())
                self.assertFalse(report["real_compaction_event"])
                self.assertEqual(report["status"], "FAILED")
                if mode == "wrong-resume":
                    text = (root / "output/compaction-events.jsonl").read_text()
                    self.assertNotIn('"method": "thread/compact/start"', text)

    def test_foreign_or_unfinished_previous_turn_is_rejected_before_starting_a_peer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for previous in ({"thread_id": "foreign", "status": "COMPLETED"},
                             {"thread_id": "owned", "status": "TIMEOUT"}):
                path = root / "previous.json"; write_json(path, previous)
                with self.assertRaises(ValueError):
                    compact_thread(executable="does-not-exist", thread="owned", workspace=root,
                                   output=root, previous_turn=path, url="unused", model="gpt-6-luna",
                                   effort="low", policy=MEMORY_POLICY, timeout=1)
            self.assertFalse((root / "compaction-events.jsonl").exists())


class MemoryPolicyTests(unittest.TestCase):
    def test_cli_overrides_round_trip_nested_maps_as_toml(self):
        value = {"PATH": "/project/bin:/usr/bin", "nested": {"enabled": False}, "tags": ["a", "b"]}
        arguments = config_arguments({"setting": value})
        self.assertEqual(arguments[0], "-c")
        self.assertEqual(tomllib.loads(arguments[1])["setting"], value)

    def test_same_policy_is_injected_before_discovery_for_every_turn(self):
        self.assertEqual(agent_options("test-url", "low", MEMORY_POLICY)["developer_instructions"], MEMORY_POLICY)
        self.assertNotIn("developer_instructions", agent_options("test-url", "low", None))

    def test_isolated_shell_retains_explicit_tool_paths_without_inheriting_host_secrets(self):
        options = agent_options("test-url", "low", MEMORY_POLICY, isolated=True,
                                shell_path="/project/bin:/usr/bin:/bin")
        self.assertEqual(options["shell_environment_policy.inherit"], "none")
        self.assertEqual(options["shell_environment_policy.set"], {"PATH": "/project/bin:/usr/bin:/bin"})

    def test_only_successful_content_reads_count_as_memory_usage(self):
        good = {"server": "kaeru", "tool": "context", "status": "completed", "arguments": {},
                "result": {"content": [], "structured_content": {"state": "ok"}}}
        cases = [good, {**good, "tool": "initiatives"}, {**good, "tool": "note"},
                 {**good, "status": "failed"}, {**good, "error": {"message": "failed"}},
                 {**good, "result": {"structured_content": {"state": "rejected"}}},
                 {**good, "arguments": {"view": "diagnostics"}}, {**good, "server": "other"}]
        self.assertEqual(memory_read_count(cases), 1)


if __name__ == "__main__":
    unittest.main()
