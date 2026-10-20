import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runner.fixtures import load_case
from runner.workspaces import prepare


class BatchWorkspaceTests(unittest.TestCase):
    def test_both_datasets_support_setup_without_choosing_an_effort_policy(self):
        case = Path(__file__).resolve().parents[1] / "tool-usage/cases/B1-constraint-spoken"
        _, fixture = load_case(case)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "actor"
            prepare(workspace, case, fixture)
            path = workspace / "jobs/config.json"
            config = json.loads(path.read_text())
            spec = importlib.util.spec_from_file_location("batch_fixture", workspace / "jobs/runner.py")
            batch = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(batch)
            with self.assertRaisesRegex(ValueError, "dataset path"):
                batch.validate(workspace, config)
            config["dataset"] = "datasets/first.jsonl"
            with self.assertRaisesRegex(ValueError, "explicit supported effort"):
                batch.validate(workspace, config)
            for effort, dataset in [("medium", "first"), ("high", "second"), ("low", "second")]:
                config["dataset"] = f"datasets/{dataset}.jsonl"
                for job in config["jobs"]:
                    job["effort"] = effort
                path.write_text(json.dumps(config))
                result = subprocess.run([sys.executable, "jobs/runner.py", "--config", "jobs/config.json"],
                                        cwd=workspace, check=True, capture_output=True, text=True)
                prepared = json.loads(result.stdout)
                self.assertEqual(prepared["dataset"], config["dataset"])
                self.assertEqual(prepared["records"], 2)
                self.assertFalse(prepared["executed"])
                self.assertEqual(prepared["jobs"], config["jobs"])
            config["dataset"] = "../outside.jsonl"
            with self.assertRaisesRegex(ValueError, "inside the local workspace"):
                batch.validate(workspace, config)


if __name__ == "__main__":
    unittest.main()
