import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("research_action_adapter", ROOT / "scripts/research_action_adapter.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ResearchActionAdapterTests(unittest.TestCase):
    def test_executes_explicit_argv_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            request = {
                "root": directory,
                "action": {
                    "estimated_cost": 1,
                    "payload": {"command": [sys.executable, "-c", "print('ok')"]},
                },
            }
            result = MODULE.execute(request)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["stdout"].strip(), "ok")

    def test_rejects_cwd_escape(self):
        with self.assertRaisesRegex(ValueError, "stay below"):
            MODULE.execute({"root": ".", "action": {"payload": {"command": ["true"], "cwd": "../"}}})


if __name__ == "__main__":
    unittest.main()
