from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
    def test_help_does_not_prepare_services_or_run_models(self):
        with patch("main.prepare_runtime") as prepare, redirect_stdout(StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                main.main(["--help"])
            self.assertEqual(stopped.exception.code, 0)
            prepare.assert_not_called()

    def test_main_runs_directly_without_a_subcommand(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            (source / "kaeru-core").mkdir(parents=True)
            (source / "kaeru-core/Cargo.toml").write_text("")
            with patch("main.prepare_runtime") as prepare, patch("main.launch") as launch:
                launch.return_value = {"status_counts": {"PREPARED": 1}}
                status = main.main(["--source", str(source), "--output", str(Path(directory) / "results"),
                                    "--case", "A2-unreachable-core", "--prepare-only"])
                self.assertEqual(status, 0)
                config, selected = prepare.call_args.args
                self.assertEqual(config.model, "gpt-6.1-sol")
                self.assertEqual(config.effort, "low")
                self.assertEqual([p.name for p in selected], ["A2-unreachable-core"])
                launch.assert_called_once_with(config)

    def test_invalid_arguments_stop_before_any_build(self):
        with patch("main.prepare_runtime") as prepare, redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                main.main(["--source", "/irrelevant", "--repetitions", "0"])
            prepare.assert_not_called()

    def test_explicit_guide_reaches_the_turn_policy_verbatim(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            (source / "kaeru-core").mkdir(parents=True)
            (source / "kaeru-core/Cargo.toml").write_text("")
            guide = Path(directory) / "guide.md"
            guide.write_text("# Tool guide\nFollow the returned continuation arguments.\n")
            with patch("main.prepare_runtime"), patch("main.launch") as launch:
                launch.return_value = {"status_counts": {"PREPARED": 1}}
                main.main(["--source", str(source), "--output", str(Path(directory) / "results"),
                           "--memory-guide", str(guide), "--prepare-only"])
                config = launch.call_args.args[0]
                self.assertEqual(config.memory_guide, guide.resolve())
                self.assertTrue(config.policy.startswith(main.MEMORY_POLICY))
                self.assertTrue(config.policy.endswith(guide.read_text()))

    def test_unreadable_or_disabled_guide_stops_before_build(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            (source / "kaeru-core").mkdir(parents=True)
            (source / "kaeru-core/Cargo.toml").write_text("")
            guide = Path(directory) / "missing.md"
            for extra in [[], ["--memory-policy", "none"]]:
                with patch("main.prepare_runtime") as prepare, redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit):
                        main.main(["--source", str(source), "--memory-guide", str(guide), *extra])
                    prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
