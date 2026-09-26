import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_research_package", ROOT / "scripts/check_research_package.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ResearchPackageTests(unittest.TestCase):
    def test_quantitative_results_require_data_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            (root / "paper").mkdir()
            (root / "research/results.json").write_text("{}", encoding="utf-8")
            (root / "paper/main.tex").write_text("text", encoding="utf-8")
            config = root / "research/package.json"
            config.write_text(json.dumps({
                "results": "research/results.json",
                "manuscript": "paper/main.tex",
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "results requires data_provenance"):
                MODULE.check(root, config, ROOT / "scripts")

    def test_manuscript_requires_bibliography_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "paper").mkdir()
            (root / "paper/main.tex").write_text("text", encoding="utf-8")
            config = root / "package.json"
            config.write_text(json.dumps({"manuscript": "paper/main.tex"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires manifest, coverage, bibliography"):
                MODULE.check(root, config, ROOT / "scripts")

    def test_logic_review_is_part_of_manuscript_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "paper/main.tex": "text",
                "paper/references.bib": "",
                "research/manifest.jsonl": "",
                "research/coverage.json": "{}",
                "research/literature.json": "{}",
                "research/logic-review.json": "{}",
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            config = root / "research/package.json"
            package = {
                "manuscript": "paper/main.tex",
                "manifest": "research/manifest.jsonl",
                "coverage": "research/coverage.json",
                "bibliography": "paper/references.bib",
                "literature_archive": "research/literature.json",
                "logic_review": "research/logic-review.json",
            }
            config.write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires claim_scope"):
                MODULE.check(root, config, ROOT / "scripts")
            package["claim_scope"] = "research-only"
            package["mechanism_scope"] = "not-claimed"
            config.write_text(json.dumps(package), encoding="utf-8")
            with patch.object(MODULE, "run", return_value={"passed": True}) as run:
                MODULE.check(root, config, ROOT / "scripts")
            commands = [call.args[0] for call in run.call_args_list]
            self.assertTrue(any("check_project_layout.py" in command[1] for command in commands))
            logic_command = next(command for command in commands if "check_logic_review.py" in command[1])
            self.assertIn("--require-pass", logic_command)

    def test_latex_delivery_requires_and_runs_visual_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "paper").mkdir()
            (root / "research").mkdir()
            (root / "paper/main.tex").write_text("\\documentclass{article}", encoding="utf-8")
            (root / "research/visual-review.json").write_text("{}", encoding="utf-8")
            config = root / "research/package.json"
            config.write_text(json.dumps({"latex_main": "paper/main.tex"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires latex_visual_review"):
                MODULE.check(root, config, ROOT / "scripts")
            config.write_text(json.dumps({
                "latex_main": "paper/main.tex",
                "latex_visual_review": "research/visual-review.json",
            }), encoding="utf-8")
            with patch.object(MODULE, "run", return_value={"passed": True}) as run:
                MODULE.check(root, config, ROOT / "scripts")
            commands = [call.args[0] for call in run.call_args_list]
            self.assertIn("check_project_layout.py", commands[0][1])
            self.assertEqual([command[2] for command in commands[1:]], ["check", "finalize"])

    def test_structural_audit_is_run_as_a_hard_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            (root / "research/structural-audit.json").write_text("{}", encoding="utf-8")
            config = root / "research/package.json"
            config.write_text(json.dumps({
                "structural_audit": "research/structural-audit.json",
            }), encoding="utf-8")
            with patch.object(MODULE, "run", return_value={"passed": True}) as run:
                MODULE.check(root, config, ROOT / "scripts")
            command = run.call_args.args[0]
            self.assertIn("check_structural_audit.py", command[1])
            self.assertIn("--require-pass", command)

    def test_claimed_mechanism_requires_audit_and_independent_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            config = root / "research/package.json"
            config.write_text(json.dumps({"mechanism_scope": "claimed"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires mechanism_audit and mechanism_review"):
                MODULE.check(root, config, ROOT / "scripts")
            (root / "research/mechanism-audit.json").write_text("{}", encoding="utf-8")
            (root / "research/mechanism-review.json").write_text("{}", encoding="utf-8")
            config.write_text(json.dumps({
                "mechanism_scope": "claimed",
                "mechanism_audit": "research/mechanism-audit.json",
                "mechanism_review": "research/mechanism-review.json",
            }), encoding="utf-8")
            with patch.object(MODULE, "run", return_value={"passed": True}) as run:
                MODULE.check(root, config, ROOT / "scripts")
            command = run.call_args.args[0]
            self.assertIn("check_mechanism_audit.py", command[1])
            self.assertIn("--review", command)
            self.assertIn("--require-pass", command)

    def test_manuscript_must_declare_whether_it_claims_a_mechanism(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "paper/main.tex": "text",
                "paper/references.bib": "",
                "research/manifest.jsonl": "",
                "research/coverage.json": "{}",
                "research/literature.json": "{}",
                "research/logic-review.json": "{}",
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            config = root / "research/package.json"
            config.write_text(json.dumps({
                "manuscript": "paper/main.tex",
                "manifest": "research/manifest.jsonl",
                "coverage": "research/coverage.json",
                "bibliography": "paper/references.bib",
                "literature_archive": "research/literature.json",
                "logic_review": "research/logic-review.json",
                "claim_scope": "research-only",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires mechanism_scope"):
                MODULE.check(root, config, ROOT / "scripts")

    def test_real_world_claims_require_applicability_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            config = root / "research/package.json"
            config.write_text(json.dumps({"claim_scope": "marketing"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "claim_scope must be"):
                MODULE.check(root, config, ROOT / "scripts")
            config.write_text(json.dumps({"claim_scope": "real-world"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires real_world_audit"):
                MODULE.check(root, config, ROOT / "scripts")
            (root / "research/real-world-audit.json").write_text("{}", encoding="utf-8")
            config.write_text(json.dumps({
                "claim_scope": "real-world",
                "real_world_audit": "research/real-world-audit.json",
            }), encoding="utf-8")
            with patch.object(MODULE, "run", return_value={"passed": True}) as run:
                MODULE.check(root, config, ROOT / "scripts")
            command = run.call_args.args[0]
            self.assertIn("check_real_world_audit.py", command[1])
            self.assertIn("--require-applicable", command)

    def test_text_audit_is_run_as_a_hard_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            (root / "research/text-audit.json").write_text("{}", encoding="utf-8")
            config = root / "research/package.json"
            config.write_text(json.dumps({"text_audit": "research/text-audit.json"}), encoding="utf-8")
            with patch.object(MODULE, "run", return_value={"passed": True}) as run:
                MODULE.check(root, config, ROOT / "scripts")
            command = run.call_args.args[0]
            self.assertIn("check_text_audit.py", command[1])
            self.assertIn("--require-pass", command)

    def test_failed_gate_exposes_iteration_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            (root / "research/mechanism-audit.json").write_text("{}", encoding="utf-8")
            (root / "research/mechanism-review.json").write_text("{}", encoding="utf-8")
            config = root / "research/package.json"
            config.write_text(json.dumps({
                "mechanism_scope": "claimed",
                "mechanism_audit": "research/mechanism-audit.json",
                "mechanism_review": "research/mechanism-review.json",
            }), encoding="utf-8")
            failed = {
                "passed": False,
                "stdout": json.dumps({"return_to": "evidence_generation"}),
            }
            with patch.object(MODULE, "run", return_value=failed):
                report = MODULE.check(root, config, ROOT / "scripts")
            self.assertTrue(report["iteration_required"])
            self.assertEqual(report["return_to"], ["evidence_generation"])

    def test_coverage_cannot_run_without_manuscript_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "coverage.json").write_text("{}", encoding="utf-8")
            config = root / "package.json"
            config.write_text(json.dumps({"coverage": "coverage.json"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "coverage requires manuscript and manifest"):
                MODULE.check(root, config, ROOT / "scripts")


if __name__ == "__main__":
    unittest.main()
