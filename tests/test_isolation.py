"""Filesystem-boundary checks do not need credentials or a model."""

from pathlib import Path
import tempfile
import unittest

from runner.isolation import Bubblewrap


class IsolationTests(unittest.TestCase):
    def test_actor_cannot_make_the_host_copy_an_answer_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            isolation = object.__new__(Bubblewrap)
            isolation.answers = root / "answers"
            isolation.answers.mkdir()
            (root / "hidden").write_text("not an actor answer")
            (isolation.answers / "reply").symlink_to(root / "hidden")
            with self.assertRaises(RuntimeError):
                isolation.take_answer(root / "reply")
            self.assertFalse((root / "reply").exists())

    def test_command_rewrites_only_the_answer_path_and_keeps_caller_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            isolation = object.__new__(Bubblewrap)
            isolation.native = root / "native/bin/codex"
            isolation.workspace = root / "opaque-project"
            isolation.host_home = root / "host-home"
            isolation.home = root / "actor-home"
            isolation.answers = root / "answers"
            arguments = ["codex", "exec", "-o", str(root / "hidden/reply"), "ordinary prompt"]
            command = isolation.command(arguments, answer=root / "hidden/reply")
            self.assertEqual(arguments[0], "codex")
            self.assertEqual(arguments[3], str(root / "hidden/reply"))
            self.assertEqual(command[-5:], ["/opt/kaeru-codex/bin/codex", "exec", "-o", "/tmp/answers/reply", "ordinary prompt"])
            self.assertIn("--clearenv", command)
            self.assertIn("--unshare-pid", command)


if __name__ == "__main__":
    unittest.main()
