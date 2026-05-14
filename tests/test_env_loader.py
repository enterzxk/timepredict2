from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from timepredict_agent.llm_summary import load_local_env


class EnvLoaderTest(unittest.TestCase):
    def test_load_local_env_does_not_override_existing_values(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text(
                "ANTHROPIC_MODEL=mimo-v2.5-pro\n"
                "ANTHROPIC_AUTH_TOKEN=local-token\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"ANTHROPIC_MODEL": "existing"}, clear=True):
                load_local_env(root)
                from os import environ

                self.assertEqual(environ["ANTHROPIC_MODEL"], "existing")
                self.assertEqual(environ["ANTHROPIC_AUTH_TOKEN"], "local-token")


if __name__ == "__main__":
    unittest.main()

