import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_exploration_ledger.py"
spec = importlib.util.spec_from_file_location("check_exploration_ledger", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExplorationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "research").mkdir()
        self.evidence = self.root / "research/test-result.txt"
        self.evidence.write_text("Rejected by a pre-specified placebo test.\n", encoding="utf-8")
        self.digest = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
        self.ledger = self.root / "research/experiments.tsv"
        self.write_ledger()

    def write_ledger(self, **overrides):
        row = {
            "iteration": "r01", "mode": "empirical", "hypothesis": "There is a stable shift.",
            "validation": "Placebo on pre-period.", "status": "discard",
            "artifact": "research/test-result.txt", "artifact_sha256": self.digest,
            "reason": "Pre-period shift is comparable.", "next_action": "Test a narrower claim.",
        }
        row.update(overrides)
        self.ledger.write_text("\t".join(module.FIELDS) + "\n" +
                               "\t".join(row[field] for field in module.FIELDS) + "\n",
                               encoding="utf-8")

    def test_valid_discarded_experiment(self):
        report = module.check(self.root, Path("research/experiments.tsv"))
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["rows"], 1)

    def test_evidence_tamper_rejected(self):
        self.evidence.write_text("Changed result", encoding="utf-8")
        report = module.check(self.root, self.ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("mismatch" in item for item in report["errors"]))

    def test_missing_next_action_rejected(self):
        self.write_ledger(next_action="")
        self.assertFalse(module.check(self.root, self.ledger)["valid"])

    def test_outside_artifact_rejected(self):
        self.write_ledger(artifact="../../outside.txt")
        report = module.check(self.root, self.ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("escapes" in item for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
