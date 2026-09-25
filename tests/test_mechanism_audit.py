import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_mechanism_audit", ROOT / "scripts/check_mechanism_audit.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MechanismAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "research").mkdir()
        self.artifact = self.root / "research/mechanism-test.txt"
        self.artifact.write_text("test result", encoding="utf-8")
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def tearDown(self):
        self.temporary.cleanup()

    def audit(self, status="distinguished"):
        alternatives = [
            {"id": f"A{number}", "statement": f"alternative {number}", "observable_implication": f"prediction {number}"}
            for number in range(1, 4)
        ]
        tests = [
            {
                "id": f"T{number}",
                "alternative_id": f"A{number}",
                "preferred_prediction": "preferred prediction",
                "alternative_prediction": f"alternative prediction {number}",
                "design": "pre-specified contrast",
                "decision_rule": "favor the prediction with lower out-of-sample error",
                "finding": "the preferred prediction fits better",
                "status": status,
                "artifact": "research/mechanism-test.txt",
                "artifact_sha256": self.digest,
            }
            for number in range(1, 4)
        ]
        unresolved = [] if status == "distinguished" else [item["id"] for item in alternatives]
        return {
            "schema_version": "1",
            "claim_id": "C1",
            "claim": "Treatment operates through the proposed channel.",
            "preferred_mechanism": {
                "id": "M0",
                "statement": "the proposed channel",
                "causal_chain": ["treatment changes mediator", "mediator changes outcome"],
                "distinctive_prediction": "the mediator moves before the outcome",
            },
            "alternatives": alternatives,
            "tests": tests,
            "overall_verdict": "pass" if status == "distinguished" else "revise",
            "claim_status": "mechanism-supported" if status == "distinguished" else "consistent-with",
            "bounded_conclusion": "Evidence distinguishes the proposed channel in this sample.",
            "unresolved_alternatives": unresolved,
        }

    def review(self, audit_path, verdict="pass"):
        return {
            "schema_version": "1",
            "reviewed_sha256": {"mechanism_audit": hashlib.sha256(audit_path.read_bytes()).hexdigest()},
            "independent_context": True,
            "verdict": verdict,
            "weakest_link": "measurement of the mediator",
            "observationally_equivalent_explanation": "none left among the enumerated alternatives",
            "discriminating_test_assessment": "tests have opposing observable predictions",
            "required_revision": "" if verdict == "pass" else "add a direct mediator test",
        }

    def test_passing_audit_requires_three_hash_bound_alternatives_and_review(self):
        audit = self.audit()
        audit_path = self.root / "research/mechanism-audit.json"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        report = MODULE.validate(audit, self.root, self.review(audit_path), audit_path, require_pass=True)
        self.assertTrue(report["gate_passed"], report["errors"])
        self.assertFalse(report["iteration_required"])

    def test_unresolved_alternative_returns_to_evidence_generation(self):
        report = MODULE.validate(self.audit("inconclusive"), self.root)
        self.assertTrue(report["valid"])
        self.assertFalse(report["gate_passed"])
        self.assertEqual(report["return_to"], "evidence_generation")

    def test_changed_artifact_invalidates_audit(self):
        audit = self.audit()
        self.artifact.write_text("changed", encoding="utf-8")
        report = MODULE.validate(audit, self.root)
        self.assertFalse(report["valid"])
        self.assertTrue(any("sha256" in error for error in report["errors"]))

    def test_generic_same_prediction_is_not_discriminating(self):
        audit = self.audit()
        audit["tests"][0]["alternative_prediction"] = audit["tests"][0]["preferred_prediction"]
        report = MODULE.validate(audit, self.root)
        self.assertFalse(report["valid"])
        self.assertTrue(any("opposing predictions" in error for error in report["errors"]))

    def test_stale_or_nonindependent_review_blocks_delivery(self):
        audit = self.audit()
        audit_path = self.root / "research/mechanism-audit.json"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        review = self.review(audit_path)
        review["independent_context"] = False
        report = MODULE.validate(audit, self.root, review, audit_path, require_pass=True)
        self.assertFalse(report["gate_passed"])
        self.assertEqual(report["return_to"], "independent_mechanism_review")


if __name__ == "__main__":
    unittest.main()
