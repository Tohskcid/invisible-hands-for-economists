import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "invisible-hands-for-economists"


class PluginPackagingTests(unittest.TestCase):
    def load(self, path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    def test_manifests_share_name_and_version(self):
        manifests = [
            self.load("plugin.json"),
            self.load(".codex-plugin/plugin.json"),
            self.load(".claude-plugin/plugin.json"),
        ]
        self.assertEqual({manifest["name"] for manifest in manifests}, {PLUGIN_NAME})
        self.assertEqual({manifest["version"] for manifest in manifests}, {"2.18.0"})

    def test_marketplaces_publish_the_same_plugin(self):
        for path in (
            ".agents/plugins/marketplace.json",
            ".claude-plugin/marketplace.json",
        ):
            marketplace = self.load(path)
            self.assertEqual(marketplace["name"], "invisible-hands")
            self.assertEqual([entry["name"] for entry in marketplace["plugins"]], [PLUGIN_NAME])

    def test_portable_skill_entrypoint_exists(self):
        self.assertTrue((ROOT / "skills/econ-research-lab/SKILL.md").is_file())
        self.assertTrue((ROOT / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
