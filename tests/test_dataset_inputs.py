from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import yaml

from runner.audit import validate_search
from runner.fixtures import input_files, load_case, normalize
from runner.workspaces import prepare


class DatasetInputsTests(unittest.TestCase):
    def test_a_new_case_uses_its_declared_assets_timestamps_and_search_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case_dir = root / "tool-usage/cases/brand-new-case"
            (case_dir / "assets").mkdir(parents=True)
            bank = root / "tool-usage/noise/bank.yaml"
            bank.parent.mkdir()
            bank.write_text(yaml.safe_dump({"nodes": [{"name": "noise-1"}, {"name": "noise-2"}]}))
            (case_dir / "case.yaml").write_text(yaml.safe_dump({"id": case_dir.name, "prompt": "Do work."}))
            (case_dir / "assets/config.json").write_text('{"setting": null}\n')
            fixture = {"initiative": "new-project", "workspace": {"files": "assets"},
                       "noise": {"library": "../../noise/bank.yaml", "count": 2,
                                 "recorded_start": "2020-01-02T12:00:00Z", "target": "wanted",
                                 "target_rank_at_least": 2, "newer_noise_min": 2,
                                 "rank_probe": {"text": "term", "limit": 2}},
                       "nodes": [{"name": "wanted", "recorded": "2020-01-01"}]}
            (case_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture))
            _, loaded = load_case(case_dir)
            manifest = normalize(case_dir, loaded, datetime(2026, 10, 18, tzinfo=timezone.utc))
            workspace = root / "actor"
            prepare(workspace, case_dir, loaded)
            self.assertEqual((workspace / "config.json").read_bytes(), (case_dir / "assets/config.json").read_bytes())
            self.assertEqual(len(input_files(case_dir, loaded)), 4)
            output = root / "observations"; output.mkdir()
            calls = []
            class Client:
                def read_pages(self, operation, arguments):
                    calls.append((operation, arguments))
                    return [SimpleNamespace(raw={}, envelope={"data": {"hits": [{"name": "noise-1"}, {"name": "wanted"}]},
                                                               "coverage": {"complete": True}})]
            validate_search(Client(), manifest, output)
            self.assertEqual(calls[0], ("search", {"text": "term", "limit": 2, "initiatives": ["new-project"]}))
            self.assertTrue((output / "search-preflight.json").is_file())

    def test_declared_workspace_files_cannot_escape_the_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / "case"; case.mkdir()
            other = root / "other"; other.mkdir()
            with self.assertRaises(ValueError):
                prepare(root / "actor", case, {"initiative": "project", "workspace": {"files": "../other"}})


if __name__ == "__main__":
    unittest.main()
