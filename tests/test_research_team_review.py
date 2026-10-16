import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


team_checker = load("check_research_team")
review_checker = load("check_substantive_review")
data_checker = load("check_data_provenance")
package_checker = load("check_research_package")
coverage_checker = load("check_manuscript_coverage")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResearchTeamReviewTests(unittest.TestCase):
    def test_team_handoffs_are_hash_bound_and_review_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "research/result.txt"
            artifact.parent.mkdir()
            artifact.write_text("evidence", encoding="utf-8")
            roles = team_checker.ROLES["empirical"]
            report = {"coordinator_id": "pi", "tasks": [{
                "role": role, "agent_id": "reviewer" if role == "review" else "researcher-a" if role in {"literature", "planning"} else "researcher-b",
                "status": "accepted", "accepted_by": "pi",
                "artifacts": [{"path": "research/result.txt", "sha256": digest(artifact)}],
            } for role in sorted(roles)]}
            self.assertTrue(team_checker.validate(report, root, "empirical")["valid"])
            review_task = next(item for item in report["tasks"] if item["role"] == "review")
            review_task["agent_id"] = "researcher-b"
            self.assertFalse(team_checker.validate(report, root, "empirical")["valid"])
            review_task["agent_id"] = "reviewer"
            artifact.write_text("changed", encoding="utf-8")
            self.assertTrue(any("changed" in error for error in team_checker.validate(report, root, "empirical")["errors"]))

    def test_team_review_handoff_binds_review_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_path = root / "research/review.json"
            review_path.parent.mkdir()
            review_path.write_text('{"reviewer_id":"referee"}', encoding="utf-8")
            report = {"coordinator_id": "pi", "tasks": [{
                "role": role, "agent_id": "referee" if role == "review" else "author-a" if role in {"literature", "planning"} else "author-b",
                "status": "accepted", "accepted_by": "pi",
                "artifacts": [{"path": "research/review.json", "sha256": digest(review_path)}],
            } for role in sorted(team_checker.ROLES["theory"])]}
            self.assertTrue(team_checker.validate(report, root, "theory", review_path)["valid"])
            review_path.write_text('{"reviewer_id":"other"}', encoding="utf-8")
            self.assertFalse(team_checker.validate(report, root, "theory", review_path)["valid"])
            review_path.write_text('[]', encoding="utf-8")
            self.assertFalse(team_checker.validate(report, root, "theory", review_path)["valid"])

    def test_substantive_review_requires_limitations_and_current_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manuscript = root / "paper.tex"
            survey = root / "topic.json"
            manuscript.write_text("\\section{Limitations}\nThe source covers one period.", encoding="utf-8")
            survey.write_text("{}", encoding="utf-8")
            report = {
                "reviewer_id": "referee", "author_agent_ids": ["author"], "verdict": "pass",
                "manuscript_sha256": digest(manuscript), "topic_survey_sha256": digest(survey),
                "dimensions": {name: {"verdict": "pass", "reason": "Checked against the linked evidence.",
                                      "evidence": [{"path": "topic.json" if name in {"novelty", "overlap"} else "paper.tex",
                                                    "sha256": digest(survey if name in {"novelty", "overlap"} else manuscript)}]}
                               for name in review_checker.DIMENSIONS},
                "limitations": [{"text_anchor": "The source covers one period.", "effect_on_claim": "Short time scope", "boundary_or_mitigation": "No long-run claim"}],
                "open_critical_issues": [],
            }
            self.assertTrue(review_checker.validate(report, manuscript, survey, root)["valid"])
            report["dimensions"]["novelty"]["evidence"] = []
            self.assertFalse(review_checker.validate(report, manuscript, survey, root)["valid"])
            report["dimensions"]["novelty"]["evidence"] = [{"path": "topic.json", "sha256": digest(survey)}]
            manuscript.write_text("\\section{Limitations}\nChanged text.", encoding="utf-8")
            self.assertFalse(review_checker.validate(report, manuscript, survey, root)["valid"])

    def test_substantive_empirical_profile_requires_real_data_and_new_gates(self):
        required = package_checker.RESEARCH_PROFILES["empirical"]["manuscript"]
        self.assertTrue({"team_report", "substantive_review"}.issubset(required))
        for mode in package_checker.RESEARCH_PROFILES:
            if "manuscript" in package_checker.RESEARCH_PROFILES[mode]:
                self.assertIn("topic_survey", package_checker.RESEARCH_PROFILES[mode]["manuscript"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "research"
            research.mkdir()
            (research / "data.json").write_text("{}", encoding="utf-8")
            (research / "package.json").write_text(json.dumps({
                "mode": "empirical", "deliverable": "feasibility_report", "topic_survey": "research/data.json",
                "data_provenance": "research/data.json",
            }), encoding="utf-8")
            with patch.object(package_checker, "run", return_value={"passed": True}) as runner:
                package_checker.check(root, research / "package.json", ROOT / "scripts")
            self.assertIn("--require-real", next(call.args[0] for call in runner.call_args_list if "check_data_provenance.py" in call.args[0][1]))
            (research / "package.json").write_text(json.dumps({
                "mode": "empirical", "deliverable": "replication_package", "claim_scope": "research-only",
                "data_provenance": "research/data.json", "results": "research/data.json", "replication": "research/data.json",
            }), encoding="utf-8")
            with patch.object(package_checker, "run", return_value={"passed": True}) as runner:
                package_checker.check(root, research / "package.json", ROOT / "scripts")
            self.assertIn("--require-real", next(call.args[0] for call in runner.call_args_list if "check_data_provenance.py" in call.args[0][1]))
        proxy = {"schema_version": "1", "generated_at": "2026-10-17T00:00:00Z", "datasets": [{"id": "fixture", "kind": "proxy"}]}
        self.assertTrue(any("proxy data cannot" in error for error in data_checker.validate(proxy, require_real=True)["errors"]))

    def test_full_manuscript_package_runs_team_review_and_real_data_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            required = package_checker.RESEARCH_PROFILES["empirical"]["manuscript"]
            package = {"mode": "empirical", "deliverable": "manuscript", "claim_scope": "research-only", "mechanism_scope": "not-claimed", "latex_build_dir": "paper/build"}
            for field in required - {"latex_build_dir"}:
                name = "paper/main.tex" if field in {"manuscript", "latex_main"} else "paper/references.bib" if field == "bibliography" else "paper/release.pdf" if field == "release_pdf" else f"research/{field}.json"
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
                package[field] = name
            config = root / "research/package.json"
            config.write_text(json.dumps(package), encoding="utf-8")
            with patch.object(package_checker, "run", return_value={"passed": True}) as runner:
                self.assertTrue(package_checker.check(root, config, ROOT / "scripts")["valid"])
            commands = [call.args[0] for call in runner.call_args_list]
            data = next(command for command in commands if "check_data_provenance.py" in command[1])
            coverage = next(command for command in commands if "check_manuscript_coverage.py" in command[1])
            team = next(command for command in commands if "check_research_team.py" in command[1])
            self.assertIn("--require-real", data)
            self.assertIn("--require-limitations", coverage)
            self.assertIn("--review", team)
            self.assertTrue(any("check_substantive_review.py" in command[1] for command in commands))

    def test_coverage_requires_limitations_for_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manuscript = root / "paper.tex"
            manifest = root / "manifest.jsonl"
            manuscript.write_text("\\section{Introduction}\nText", encoding="utf-8")
            manifest.write_text('{"type":"claim","id":"c1"}\n', encoding="utf-8")
            report = {"schema_version": "1", "mode": "theory", "manuscript_sha256": digest(manuscript), "sections": [{
                "id": "intro", "role": "introduction", "status": "ready", "headings": ["Introduction"], "claim_ids": ["c1"], "artifacts": [],
            }]}
            result = coverage_checker.validate(report, root, manuscript, manifest, require_limitations=True)
            self.assertTrue(any("limitations" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
