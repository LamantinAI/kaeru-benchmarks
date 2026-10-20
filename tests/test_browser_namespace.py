import tempfile
from pathlib import Path
import unittest

from runner.environment import Environment


class BrowserConfigurationIsolation(unittest.TestCase):
    def test_disposable_mcp_uses_its_own_missing_account_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            env = Environment(Path("/not-started"), output / "vault", output)
            self.assertEqual(env.env["KAERU_MCP_WEB_CONFIG_FILE"], str(output / "browser-account.toml"))
            self.assertFalse((output / "browser-account.toml").exists())
            self.assertEqual(env.env["KAERU_MCP_UI_ENABLE"], "0")
            env.close()
