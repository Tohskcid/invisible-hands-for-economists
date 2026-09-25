import hashlib
import importlib.util
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_topic_survey", ROOT / "scripts/check_topic_survey.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TopicSurveyTests(unittest.TestCase):
    def survey(self):
        return {
            "schema_version": "2",
            "question": "Does a policy affect employment?",
            "scope": "Applied microeconomics through 2026-09-17",
            "cutoff": "2026-09-17",
            "refresh_after_days": 30,
            "frontier_window_years": 3,
            "citation_policy": "never-exclude",
            "searches": [
                {"axis": "question", "lane": "baseline", "channel": "journal-index", "source": "EconLit", "query": "policy employment", "searched_at": "2026-09-17", "retrieval_tool": "database", "source_evidence_artifact": "research/source.json", "source_evidence_sha256": "a" * 64},
                {"axis": "mechanism", "lane": "frontier", "channel": "working-paper-series", "source": "NBER", "query": "policy labor demand", "searched_at": "2026-09-17", "retrieval_tool": "browser", "source_evidence_artifact": "research/source.json", "source_evidence_sha256": "a" * 64},
                {"axis": "method", "lane": "frontier", "channel": "journal-advance", "source": "Journal advance articles", "query": "new policy design", "searched_at": "2026-09-17", "retrieval_tool": "publisher-search", "source_evidence_artifact": "research/source.json", "source_evidence_sha256": "a" * 64},
            ],
            "nearest_works": [{
                "title": "Closest paper",
                "locator": "https://example.org/paper",
                "source_evidence_artifact": "research/source.json",
                "source_evidence_sha256": "a" * 64,
                "verified_at": "2026-09-17",
                "question": "Related policy question",
                "estimand_or_theorem": "ATT",
                "method_or_proof": "DiD",
                "difference": "Different assignment mechanism",
                "prior_bottleneck": "Old data could not distinguish assignment.",
                "innovation": "Uses a new assignment discontinuity.",
                "why_field_cares": "Changes the causal interpretation.",
                "validation": "Placebos and balance tests.",
                "influence_or_reuse": "Reusable design in related policies.",
                "relation": "extension",
                "nearest": True,
                "discovery_lane": "frontier",
                "first_public_at": "2026-08-01",
                "citation_key": "closest2026",
                "quality_signals": ["credible-design-or-proof", "discriminating-result"],
                "frontier_case": "The design separates the mechanism from selection.",
                "manuscript_action": "cite",
                "selection_reason": "Closest current design and a live duplicate risk.",
                "full_text_status": "checked",
                "backward_checked": True,
                "forward_checked": True,
            }],
            "contribution_class": "extension",
            "contribution_statement": "Tests a different assignment mechanism.",
            "decision": "proceed",
            "researcher_checkpoints": [
                {"id": "scope-lock", "question": "Use this scope?", "response": "Yes", "decided_at": "2026-09-17", "status": "accepted"},
                {"id": "contribution-lock", "question": "Pursue this gap?", "response": "Yes", "decided_at": "2026-09-17", "status": "accepted"},
            ],
            "limitations": ["Coverage excludes inaccessible dissertations."],
        }

    def test_valid_bounded_extension(self):
        report = MODULE.validate(self.survey())
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["gate_passed"])

    def test_blocked_record_is_valid_but_cannot_enter_design(self):
        survey = self.survey()
        survey["decision"] = "blocked"
        survey["researcher_checkpoints"][0]["status"] = "blocked"
        report = MODULE.validate(survey)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["gate_passed"])

    def test_duplicate_cannot_proceed_unchanged(self):
        survey = self.survey()
        survey["nearest_works"][0]["relation"] = "duplicate"
        survey["contribution_class"] = "duplicate"
        report = MODULE.validate(survey)
        self.assertFalse(report["valid"])
        self.assertTrue(any("duplicate" in error for error in report["errors"]))

    def test_no_verified_work_cannot_be_called_novel(self):
        survey = self.survey()
        survey["nearest_works"] = []
        report = MODULE.validate(survey)
        self.assertFalse(report["valid"])
        self.assertTrue(any("blocked/unresolved" in error for error in report["errors"]))

    def test_locator_must_be_canonical_https_url(self):
        survey = self.survey()
        survey["nearest_works"][0]["locator"] = "Journal Name 1(2): 3-4"
        report = MODULE.validate(survey)
        self.assertFalse(report["valid"])
        self.assertTrue(any("canonical HTTPS URL" in error for error in report["errors"]))

    def test_source_evidence_requires_safe_path_and_sha256(self):
        survey = self.survey()
        survey["nearest_works"][0]["source_evidence_artifact"] = "../source.json"
        survey["nearest_works"][0]["source_evidence_sha256"] = "not-a-hash"
        report = MODULE.validate(survey)
        self.assertFalse(report["valid"])
        self.assertTrue(any("safe source_evidence_artifact" in error for error in report["errors"]))
        self.assertTrue(any("source_evidence_sha256" in error for error in report["errors"]))

    def test_source_evidence_checksum_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "research/source.json"
            evidence.parent.mkdir()
            survey = self.survey()
            work = survey["nearest_works"][0]
            evidence.write_text(json.dumps({"sources": [{
                "title": work["title"],
                "canonical_locator": work["locator"],
                "retrieval_tool": "browser",
                "retrieved_at": work["verified_at"],
            }], "searches": [
                {"source": item["source"], "query": item["query"], "retrieved_at": item["searched_at"], "retrieval_tool": item["retrieval_tool"]}
                for item in survey["searches"]
            ]}), encoding="utf-8")
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            survey["nearest_works"][0]["source_evidence_sha256"] = digest
            for search in survey["searches"]:
                search["source_evidence_sha256"] = digest
            self.assertTrue(MODULE.validate(survey, root)["valid"])
            evidence.write_text("changed", encoding="utf-8")
            report = MODULE.validate(survey, root)
        self.assertTrue(any("checksum mismatch" in error for error in report["errors"]))

    def test_model_memory_and_stale_search_are_rejected(self):
        survey = self.survey()
        survey["searches"][0]["retrieval_tool"] = "model-memory"
        report = MODULE.validate(survey, as_of=dt.date(2026, 11, 1))
        self.assertTrue(any("non-model retrieval tool" in error for error in report["errors"]))
        self.assertTrue(any("stale" in error for error in report["errors"]))

    def test_proceed_requires_researcher_locks(self):
        survey = self.survey()
        survey["researcher_checkpoints"] = []
        report = MODULE.validate(survey)
        self.assertTrue(any("scope-lock" in error and "contribution-lock" in error for error in report["errors"]))

    def test_breakthrough_decomposition_is_required(self):
        survey = self.survey()
        del survey["nearest_works"][0]["prior_bottleneck"]
        report = MODULE.validate(survey)
        self.assertTrue(any("prior_bottleneck" in error for error in report["errors"]))

    def test_frontier_requires_two_channels_and_never_excludes_by_citations(self):
        survey = self.survey()
        survey["searches"] = [item for item in survey["searches"] if item["channel"] != "journal-advance"]
        survey["citation_policy"] = "rank-by-citations"
        report = MODULE.validate(survey)
        self.assertTrue(any("two distinct frontier" in error for error in report["errors"]))
        self.assertTrue(any("never-exclude" in error for error in report["errors"]))

    def test_selected_frontier_work_must_be_bound_to_manuscript(self):
        survey = self.survey()
        missing = MODULE.audit_frontier_bindings(survey, "No citation here.", "")
        self.assertTrue(any("bibliography" in error for error in missing))
        self.assertTrue(any("manuscript" in error for error in missing))
        manuscript = r"Current work matters \cite{closest2026}."
        bibliography = "@article{closest2026, title={Closest paper}}"
        self.assertEqual(MODULE.audit_frontier_bindings(survey, manuscript, bibliography), [])


if __name__ == "__main__":
    unittest.main()
