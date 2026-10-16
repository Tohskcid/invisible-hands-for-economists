import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_data_provenance", ROOT / "scripts/check_data_provenance.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DataProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for path, text in {
            "scripts/fetch.py": "print('fetch')",
            "docs/schema.json": "{}",
            "docs/source-metadata.json": "{}",
            "data/raw.csv": "x\n1\n",
            "research/enclave-checksums.json": "{}",
        }.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def digest(self, path):
        return hashlib.sha256((self.root / path).read_bytes()).hexdigest()

    def real_dataset(self):
        return {
            "id": "official-data",
            "kind": "real",
            "name": "Official observations",
            "producer": "Statistical agency",
            "locator": "https://example.gov/data",
            "version": "2026-09",
            "retrieved_at": "2026-09-18T10:00:00+08:00",
            "license": "Government open-data terms",
            "license_locator": "https://example.gov/terms",
            "unit": "unit-day",
            "coverage": "2020-2025, national",
            "source_evidence_artifact": "docs/source-metadata.json",
            "source_evidence_sha256": self.digest("docs/source-metadata.json"),
            "schema_artifact": "docs/schema.json",
            "schema_sha256": self.digest("docs/schema.json"),
            "acquisition": {
                "method": "script",
                "artifact": "scripts/fetch.py",
                "artifact_sha256": self.digest("scripts/fetch.py"),
                "command": "python3 scripts/fetch.py",
                "executed_at": "2026-09-18T10:00:00+08:00",
            },
            "files": [{"path": "data/raw.csv", "sha256": self.digest("data/raw.csv"), "role": "raw"}],
        }

    def document(self, dataset=None):
        return {"schema_version": "1", "generated_at": "2026-09-18T10:05:00+08:00", "datasets": [dataset or self.real_dataset()]}

    def test_real_data_requires_and_verifies_full_lineage(self):
        document = self.document()
        report = MODULE.validate(document, self.root)
        self.assertTrue(report["valid"], report["errors"])
        (self.root / "data/raw.csv").write_text("changed", encoding="utf-8")
        report = MODULE.validate(document, self.root)
        self.assertTrue(any("checksum mismatch" in error for error in report["errors"]))

    def test_unknown_license_and_missing_acquisition_are_rejected(self):
        dataset = self.real_dataset()
        dataset["license"] = "unknown"
        dataset.pop("acquisition")
        report = MODULE.validate(self.document(dataset), self.root)
        self.assertFalse(report["valid"])
        self.assertTrue(any("license" in error for error in report["errors"]))
        self.assertTrue(any("acquisition" in error for error in report["errors"]))

    def test_source_verification_requires_evidence_and_license_locator(self):
        dataset = self.real_dataset()
        dataset.pop("source_evidence_artifact")
        dataset.pop("source_evidence_sha256")
        dataset.pop("license_locator")
        report = MODULE.validate(self.document(dataset), self.root)
        self.assertFalse(report["valid"])
        self.assertTrue(any("source_evidence" in error for error in report["errors"]))
        self.assertTrue(any("license_locator" in error for error in report["errors"]))

    def test_proxy_requires_seed_calibration_and_use_boundary(self):
        dataset = self.real_dataset()
        dataset["kind"] = "proxy"
        report = MODULE.validate(self.document(dataset), self.root)
        self.assertFalse(report["valid"])
        dataset.update({
            "seed": 42,
            "intended_use": "Pipeline validation only",
            "calibration_sources": ["https://example.gov/moments"],
        })
        self.assertTrue(MODULE.validate(self.document(dataset), self.root)["valid"])
        self.assertFalse(MODULE.validate(self.document(dataset), self.root, require_real=True)["valid"])
        self.assertTrue(MODULE.validate(self.document(), self.root, require_real=True)["valid"])

    def test_restricted_data_uses_exported_verification_artifact(self):
        dataset = self.real_dataset()
        dataset["kind"] = "restricted"
        dataset["files"] = [{"logical_path": "enclave/raw.csv", "sha256": "d" * 64, "role": "raw"}]
        dataset["access_boundary"] = "Approved secure enclave"
        dataset["verification_artifact"] = "research/enclave-checksums.json"
        dataset["verification_sha256"] = self.digest("research/enclave-checksums.json")
        report = MODULE.validate(self.document(dataset), self.root)
        self.assertTrue(report["valid"], report["errors"])


if __name__ == "__main__":
    unittest.main()
