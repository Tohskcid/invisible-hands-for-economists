import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_project_layout", ROOT / "scripts/check_project_layout.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProjectLayoutTests(unittest.TestCase):
    def test_accepts_canonical_and_equivalent_category_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = [
                "paper/main.tex",
                "output/tables/estimates.csv",
                "figure/event-study.png",
                "Final Project/docs/thesis.pdf",
                "Final Project/src/estimate.py",
                "tmp/main.aux",
            ]
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            self.assertTrue(MODULE.scan(root)["valid"])

    def test_rejects_root_artifacts_and_leaked_latex_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "thesis.pdf").write_text("x", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs/main.aux").write_text("x", encoding="utf-8")
            report = MODULE.scan(root)
            self.assertFalse(report["valid"])
            self.assertEqual(report["return_to"], ["artifact_organization"])
            self.assertEqual(
                {item["kind"] for item in report["violations"]},
                {"uncategorized-artifact", "latex-build-artifact"},
            )


if __name__ == "__main__":
    unittest.main()
