import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runner.fixtures import load_case
from runner.workspaces import prepare


class ExportWorkspaceTests(unittest.TestCase):
    def test_declared_exporter_supports_direct_and_verified_staging_and_blocks_corruption(self):
        case = Path(__file__).resolve().parents[1] / "tool-usage/cases/B2-constraint-after-compaction"
        _, fixture = load_case(case)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "actor"
            prepare(workspace, case, fixture)
            spec = importlib.util.spec_from_file_location("export_fixture", workspace / "jobs/runner.py")
            exporter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(exporter)
            source = workspace / "jobs/sample.csv"
            direct = {"name": "direct", "destination": "storage/direct"}
            self.assertEqual(exporter.export(workspace, direct, source).read_bytes(), source.read_bytes())
            staged = {"name": "staged", "destination": "storage/shared",
                      "staging_destination": "storage/staging", "verify_checksum": True}
            final = exporter.export(workspace, staged, source)
            self.assertEqual(final.read_bytes(), source.read_bytes())
            actions = [json.loads(line)["action"] for line in (workspace / "jobs/actions.jsonl").read_text().splitlines()]
            self.assertEqual(actions, ["written", "staged", "checksum_verified", "promoted"])
            final.unlink()
            with patch.object(exporter.shutil, "copyfile", side_effect=lambda src, dst: dst.write_bytes(b"corrupt")):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    exporter.export(workspace, staged, source)
            self.assertFalse(final.exists())
            self.assertIn('"action": "checksum_mismatch"', (workspace / "jobs/actions.jsonl").read_text())
            with self.assertRaisesRegex(ValueError, "inside the local workspace"):
                exporter.export(workspace, {"name": "escape", "destination": "../outside"}, source)


if __name__ == "__main__":
    unittest.main()
