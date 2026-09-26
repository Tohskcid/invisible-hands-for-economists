import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manifest_tool = load_module("manifest_tool", "scripts/validate_research_manifest.py")
claim_tool = load_module("claim_tool", "scripts/audit_claims.py")


class ResearchManifestTests(unittest.TestCase):
    def test_valid_graph(self):
        records = [
            {"id": "H1", "type": "hypothesis", "statement": "x", "falsifier": "y", "_line": 1},
            {"id": "E1", "type": "experiment", "hypothesis_id": "H1", "validation": "v", "_line": 2},
            {"id": "D1", "type": "dataset", "name": "data", "source": "agency", "locator": "https://example.test", "verified_at": "2026-09-16", "access_status": "public", "license": "CC0", "_line": 3},
            {"id": "R1", "type": "run", "experiment_id": "E1", "harness_version": "1", "status": "keep", "artifact": "a", "data_ids": ["D1"], "_line": 4},
            {"id": "F1", "type": "finding", "statement": "z", "run_ids": ["R1"], "status": "supported", "_line": 5},
            {"id": "S1", "type": "evidence", "source": "doi:x", "locator": "p. 1", "verified_at": "2026-09-15", "_line": 6},
            {"id": "C1", "type": "claim", "statement": "z", "evidence_ids": ["S1"], "finding_ids": ["F1"], "_line": 7},
        ]
        self.assertEqual(manifest_tool.validate(records), [])

    def test_dangling_run_is_rejected(self):
        records = [{"id": "F1", "type": "finding", "statement": "z", "run_ids": ["missing"], "status": "supported", "_line": 1}]
        self.assertTrue(any("must reference a run" in error for error in manifest_tool.validate(records)))

    def test_claim_requires_evidence_or_finding(self):
        records = [{"id": "C1", "type": "claim", "statement": "z", "_line": 1}]
        self.assertTrue(any("requires evidence_ids, finding_ids, or premise_ids" in error for error in manifest_tool.validate(records)))

    def test_argument_graph_accepts_grounded_conclusion(self):
        records = [
            {"id": "S1", "type": "evidence", "source": "doi:x", "locator": "p. 1", "verified_at": "2026-09-16", "_line": 1},
            {"id": "C1", "type": "claim", "statement": "result", "evidence_ids": ["S1"], "central": True, "role": "premise", "status": "supported", "scope": "sample-a", "uncertainty": "sampling error", "_line": 2},
            {"id": "C2", "type": "claim", "statement": "conclusion", "premise_ids": ["C1"], "central": True, "role": "conclusion", "status": "supported", "scope": "sample-a", "uncertainty": "external validity", "_line": 3},
        ]
        self.assertEqual(manifest_tool.validate(records), [])
        self.assertEqual(manifest_tool.validate_argument(records), [])

    def test_argument_graph_rejects_cycle_and_ungrounded_conclusion(self):
        records = [
            {"id": "C1", "type": "claim", "statement": "a", "premise_ids": ["C2"], "_line": 1},
            {"id": "C2", "type": "claim", "statement": "b", "premise_ids": ["C1"], "central": True, "role": "conclusion", "status": "supported", "scope": "s", "uncertainty": "u", "_line": 2},
        ]
        self.assertTrue(any("cycle" in error for error in manifest_tool.validate(records)))
        self.assertTrue(any("no path" in error for error in manifest_tool.validate_argument(records)))

    def test_supported_conclusion_rejects_bad_premise(self):
        records = [
            {"id": "S1", "type": "evidence", "source": "doi:x", "locator": "p. 1", "verified_at": "2026-09-16", "_line": 1},
            {"id": "C1", "type": "claim", "statement": "result", "evidence_ids": ["S1"], "status": "contradicted", "_line": 2},
            {"id": "C2", "type": "claim", "statement": "conclusion", "premise_ids": ["C1"], "central": True, "role": "conclusion", "status": "supported", "scope": "s", "uncertainty": "u", "_line": 3},
        ]
        self.assertTrue(any("contradicted" in error for error in manifest_tool.validate_argument(records)))

    def test_proxy_taint_flows_through_claim_premises(self):
        records = [
            {"id": "P1", "type": "proxy", "name": "synthetic", "reason": "no source", "generator": "make.py", "seed": 7, "schema": "schema.json", "intended_use": "test", "_line": 1},
            {"id": "S1", "type": "evidence", "source": "spec", "locator": "p. 1", "verified_at": "2026-09-16", "_line": 2},
            {"id": "C1", "type": "claim", "statement": "synthetic result", "evidence_ids": ["S1"], "data_ids": ["P1"], "scope": "proxy_only", "_line": 3},
            {"id": "C2", "type": "claim", "statement": "derived result", "premise_ids": ["C1"], "scope": "real_population", "_line": 4},
        ]
        self.assertTrue(any("proxy_only" in error for error in manifest_tool.validate(records)))

    def test_proxy_data_cannot_support_unscoped_claim(self):
        records = [
            {"id": "P1", "type": "proxy", "name": "synthetic", "reason": "no source", "generator": "make.py", "seed": 7, "schema": "schema.json", "intended_use": "pipeline test", "_line": 1},
            {"id": "S1", "type": "evidence", "source": "spec", "locator": "p. 1", "verified_at": "2026-09-16", "_line": 2},
            {"id": "C1", "type": "claim", "statement": "simulation works", "evidence_ids": ["S1"], "data_ids": ["P1"], "_line": 3},
        ]
        self.assertTrue(any("proxy_only" in error for error in manifest_tool.validate(records)))
        records[-1]["scope"] = "proxy_only"
        self.assertEqual(manifest_tool.validate(records), [])

    def test_proxy_scope_check_follows_finding_and_run_links(self):
        records = [
            {"id": "P1", "type": "proxy", "name": "synthetic", "reason": "no source", "generator": "make.py", "seed": 7, "schema": "schema.json", "intended_use": "pipeline test", "_line": 1},
            {"id": "H1", "type": "hypothesis", "statement": "x", "falsifier": "y", "_line": 2},
            {"id": "E1", "type": "experiment", "hypothesis_id": "H1", "validation": "v", "_line": 3},
            {"id": "R1", "type": "run", "experiment_id": "E1", "harness_version": "1", "status": "keep", "artifact": "a", "data_ids": ["P1"], "_line": 4},
            {"id": "F1", "type": "finding", "statement": "z", "run_ids": ["R1"], "status": "supported", "_line": 5},
            {"id": "C1", "type": "claim", "statement": "z", "finding_ids": ["F1"], "_line": 6},
        ]
        self.assertTrue(any("proxy_only" in error for error in manifest_tool.validate(records)))


class ClaimAuditTests(unittest.TestCase):
    def test_unknown_marker_and_unmarked_number(self):
        text = "The estimate is 12%.\n\nA supported claim. [claim:C2]"
        errors = claim_tool.audit(text, {"C1"}, strict_numbers=True)
        self.assertTrue(any("unknown claim marker" in error for error in errors))
        self.assertTrue(any("quantitative paragraph" in error for error in errors))

    def test_known_marker_passes(self):
        self.assertEqual(claim_tool.audit("The estimate is 12%. [claim:C1]", {"C1"}, True), [])

    def test_unknown_data_marker_is_rejected(self):
        errors = claim_tool.audit("The sample uses [data:D2].", set(), False, {"D1"})
        self.assertIn("unknown data marker 'D2'", errors)

    def test_data_manuscript_requires_a_data_marker(self):
        errors = claim_tool.audit("No provenance marker.", set(), False, {"D1"}, True)
        self.assertIn("manuscript requires at least one [data:ID] marker", errors)

    def test_manuscript_requires_every_central_claim_marker(self):
        errors = claim_tool.audit("A result. [claim:C1]", {"C1", "C2"}, False, required_claims={"C1", "C2"})
        self.assertIn("central claim marker 'C2' is missing from manuscript", errors)


if __name__ == "__main__":
    unittest.main()
