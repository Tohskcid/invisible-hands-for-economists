import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_manuscript_coverage", ROOT / "scripts/check_manuscript_coverage.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ManuscriptCoverageTests(unittest.TestCase):
    roles = ["introduction", "literature", "data", "identification", "results", "robustness", "conclusion", "appendix"]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "paper").mkdir()
        (self.root / "research/sections").mkdir(parents=True)
        self.manuscript = self.root / "paper/main.tex"
        self.manuscript.write_text("\n".join(f"\\section{{{role.title()}}}" for role in self.roles), encoding="utf-8")
        self.manifest = self.root / "research/manifest.jsonl"
        self.manifest.write_text("\n".join(json.dumps({"id": f"C{i}", "type": "claim"}) for i, _ in enumerate(self.roles)), encoding="utf-8")
        for name in ["packet.md", "data.md", "analyze.py", "result.json", "table.tex", "diagnostic.json", "appendix.md"]:
            (self.root / "research" / name).write_text(name, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, kind, name):
        path = self.root / "research" / name
        return {"kind": kind, "path": f"research/{name}", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def section(self, index, role):
        artifacts = [self.artifact("section_packet", "packet.md")]
        if role == "data":
            artifacts += [self.artifact("data_documentation", "data.md"), self.artifact("analysis_code", "analyze.py")]
        elif role == "identification":
            artifacts += [self.artifact("diagnostic", "diagnostic.json"), self.artifact("analysis_code", "analyze.py")]
        elif role in {"results", "robustness"}:
            artifacts += [
                self.artifact("analysis_code", "analyze.py"),
                self.artifact("result", "result.json"),
                self.artifact("table", "table.tex"),
            ]
        elif role == "appendix":
            artifacts.append(self.artifact("appendix", "appendix.md"))
        return {
            "id": role,
            "role": role,
            "status": "ready",
            "headings": [role.title()],
            "claim_ids": [f"C{index}"],
            "artifacts": artifacts,
        }

    def document(self):
        return {
            "schema_version": "1",
            "mode": "empirical",
            "manuscript_sha256": hashlib.sha256(self.manuscript.read_bytes()).hexdigest(),
            "sections": [self.section(i, role) for i, role in enumerate(self.roles)],
        }

    def test_complete_empirical_coverage_is_ready(self):
        report = MODULE.validate(self.document(), self.root, self.manuscript, self.manifest)
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["ready"])

    def test_descriptive_coverage_does_not_require_identification_section(self):
        roles = [role for role in self.roles if role != "identification"]
        self.manuscript.write_text("\n".join(f"\\section{{{role.title()}}}" for role in roles), encoding="utf-8")
        document = self.document()
        document["mode"] = "descriptive"
        document["sections"] = [self.section(i, role) for i, role in enumerate(roles)]
        report = MODULE.validate(document, self.root, self.manuscript, self.manifest)
        self.assertTrue(report["ready"], report["errors"])

    def test_quantitative_section_requires_code_result_and_exhibit(self):
        document = self.document()
        results = next(section for section in document["sections"] if section["role"] == "results")
        results["artifacts"] = [artifact for artifact in results["artifacts"] if artifact["kind"] != "result"]
        report = MODULE.validate(document, self.root, self.manuscript, self.manifest)
        self.assertTrue(any("role 'results' requires" in error for error in report["errors"]))

    def test_every_manuscript_section_must_be_covered(self):
        self.manuscript.write_text(self.manuscript.read_text(encoding="utf-8") + "\n\\section{Untracked}\n", encoding="utf-8")
        document = self.document()
        report = MODULE.validate(document, self.root, self.manuscript, self.manifest)
        self.assertTrue(any("Untracked" in error for error in report["errors"]))

    def test_tex_heading_with_nested_reference_is_recognized(self):
        self.manuscript.write_text(r"\section{Proof of Proposition~\ref{prop:one}}", encoding="utf-8")
        self.assertEqual(MODULE.manuscript_headings(self.manuscript),
                         {r"Proof of Proposition~\ref{prop:one}"})

    def test_blocked_section_is_valid_but_not_delivery_ready(self):
        document = self.document()
        robustness = next(section for section in document["sections"] if section["role"] == "robustness")
        robustness.update({"status": "blocked", "gap": "Placebo data unavailable", "claim_ids": [], "artifacts": []})
        report = MODULE.validate(document, self.root, self.manuscript, self.manifest)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["ready"])
        self.assertIn("robustness", report["required_roles_not_ready"])

    def test_malformed_enum_values_return_errors(self):
        document = self.document()
        document["mode"] = []
        document["sections"][0]["status"] = []
        document["sections"][0]["artifacts"][0]["kind"] = []
        report = MODULE.validate(document, self.root, self.manuscript, self.manifest)
        self.assertFalse(report["valid"])
        self.assertTrue(any("mode must be" in error for error in report["errors"]))

    def test_theory_results_require_proof_not_regression_artifacts(self):
        roles = ["introduction", "literature", "model", "results", "conclusion", "appendix"]
        self.manuscript.write_text("\n".join(f"\\section{{{role.title()}}}" for role in roles), encoding="utf-8")
        sections = []
        for index, role in enumerate(roles):
            artifacts = [self.artifact("section_packet", "packet.md")]
            if role == "model":
                artifacts.append(self.artifact("model", "data.md"))
            elif role == "results":
                artifacts.append(self.artifact("proof", "result.json"))
            elif role == "appendix":
                artifacts.append(self.artifact("appendix", "appendix.md"))
            sections.append({
                "id": role, "role": role, "status": "ready", "headings": [role.title()],
                "claim_ids": [f"C{index}"], "artifacts": artifacts,
            })
        document = {
            "schema_version": "1",
            "mode": "theory",
            "manuscript_sha256": hashlib.sha256(self.manuscript.read_bytes()).hexdigest(),
            "sections": sections,
        }
        report = MODULE.validate(document, self.root, self.manuscript, self.manifest)
        self.assertTrue(report["ready"], report["errors"])


if __name__ == "__main__":
    unittest.main()
