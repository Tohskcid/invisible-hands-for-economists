import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_literature_archive", ROOT / "scripts/check_literature_archive.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LiteratureArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "paper").mkdir()
        (self.root / "literature/papers").mkdir(parents=True)
        self.bibliography = self.root / "paper/references.bib"
        self.bibliography.write_text("@article{Smith2020, title={A Test}}", encoding="utf-8")
        self.filename = MODULE.expected_filename("Smith2020", "A Test")
        self.pdf = self.root / "literature/papers" / self.filename
        self.pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

    def tearDown(self):
        self.temp.cleanup()

    def record(self, status="downloaded"):
        record = {
            "citekey": "Smith2020",
            "title": "A Test",
            "authors": ["Alex Smith"],
            "year": 2020,
            "canonical_locator": "https://doi.org/10.1000/test",
            "verified_at": "2026-09-18T12:00:00+08:00",
            "access_basis": "Publisher open-access copy",
            "access_status": status,
        }
        if status == "downloaded":
            record.update({
                "download_locator": "https://example.org/test.pdf",
                "retrieved_at": "2026-09-18T12:01:00+08:00",
                "file": f"literature/papers/{self.filename}",
                "sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
            })
        else:
            record["reason"] = "No lawful full text found after repository search"
        return record

    def document(self, papers=None):
        return {
            "schema_version": "1",
            "generated_at": "2026-09-18T12:05:00+08:00",
            "papers": papers if papers is not None else [self.record()],
        }

    def test_downloaded_pdf_passes_and_is_complete(self):
        report = MODULE.validate(self.document(), self.root, self.bibliography)
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["complete"])

    def test_filename_and_pdf_signature_are_checked(self):
        record = self.record()
        bad = self.root / "literature/papers/wrong.pdf"
        bad.write_text("not a pdf", encoding="utf-8")
        record["file"] = "literature/papers/wrong.pdf"
        record["sha256"] = hashlib.sha256(bad.read_bytes()).hexdigest()
        report = MODULE.validate(self.document([record]), self.root, self.bibliography)
        self.assertTrue(any("filename must be" in error for error in report["errors"]))
        self.assertTrue(any("not a PDF" in error for error in report["errors"]))

    def test_every_bibliography_key_must_be_accounted_for(self):
        report = MODULE.validate(self.document([]), self.root, self.bibliography)
        self.assertFalse(report["valid"])
        self.assertTrue(any("missing from archive" in error for error in report["errors"]))

    def test_documented_access_gap_is_valid_but_incomplete(self):
        report = MODULE.validate(self.document([self.record("unavailable")]), self.root, self.bibliography)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["complete"])

    def test_official_html_page_can_be_retained_without_fabricating_pdf(self):
        folder = self.root / "literature/pages"
        folder.mkdir()
        name = MODULE.expected_html_filename("Smith2020", "A Test")
        page = folder / name
        page.write_text("<!doctype html><html><body>Official research documentation.</body></html>", encoding="utf-8")
        record = self.record()
        record.update({"source_kind": "official-webpage", "file": f"literature/pages/{name}",
                       "download_locator": "https://example.org/test.html",
                       "sha256": hashlib.sha256(page.read_bytes()).hexdigest()})
        report = MODULE.validate(self.document([record]), self.root, self.bibliography)
        self.assertTrue(report["complete"], report["errors"])
        page.write_text("just an abstract", encoding="utf-8")
        record["sha256"] = hashlib.sha256(page.read_bytes()).hexdigest()
        report = MODULE.validate(self.document([record]), self.root, self.bibliography)
        self.assertTrue(any("not an HTML page" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
