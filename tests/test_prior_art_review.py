import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_prior_art_review", ROOT / "scripts/check_prior_art_review.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def small_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


class PriorArtReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        full_text = self.root / "literature/closest.pdf"
        full_text.parent.mkdir()
        full_text.write_bytes(small_pdf("Loose bound under condition X."))
        self.digest = hashlib.sha256(full_text.read_bytes()).hexdigest()
        self.survey = {
            "cutoff": "2026-10-17", "decision": "proceed",
            "nearest_works": [{"citation_key": "closest2025", "title": "Closest paper",
                               "locator": "https://example.org/closest", "first_public_at": "2025-03",
                               "full_text_status": "checked"}],
        }
        self.survey_bytes = json.dumps(self.survey).encode()

    def review(self):
        return {
            "schema_version": "1", "author_id": "writer",
            "topic_survey_sha256": hashlib.sha256(self.survey_bytes).hexdigest(),
            "proposed_claims": [{"id": "C1", "statement": "A tighter bound is possible."}],
            "works": [{"citation_key": "closest2025", "title": "Closest paper",
                       "locator": "https://example.org/closest", "date_source": "https://example.org/date",
                       "first_public_at": "2025-03", "full_text_status": "checked",
                       "full_text_locator": "https://example.org/closest.pdf", "full_text_retrieved_at": "2026-10-17",
                       "full_text_artifact": "literature/closest.pdf", "full_text_sha256": self.digest}],
            "comparisons": [{"claim_id": "C1", "citation_key": "closest2025",
                             "prior_claim": "Loose bound", "source_pointer": "page 1",
                             "source_excerpt": "Loose bound under condition X.",
                             "difference": "Proposed bound is strict under condition X.", "overlap": "partial"}],
            "independent_review": {"reviewer_id": "referee", "independent_of_author": True,
                                   "source_passages_verified": True, "source_dates_verified": True,
                                   "reviewed_at": "2026-10-17", "decision": "proceed",
                                   "rationale": "Checked theorem and bound; partial overlap remains."},
        }

    def check(self, review):
        return MODULE.validate(review, self.survey, self.survey_bytes, self.root)

    def test_complete_evidence_passes_without_certifying_novelty(self):
        report = self.check(self.review())
        self.assertTrue(report["gate_passed"], report["errors"])
        self.assertFalse(report["novelty_certified"])

    def test_abstract_only_b04_style_source_blocks(self):
        review = self.review()
        review["works"][0]["full_text_status"] = "abstract-only"
        self.survey["nearest_works"][0]["full_text_status"] = "abstract-only"
        self.survey_bytes = json.dumps(self.survey).encode()
        review["topic_survey_sha256"] = hashlib.sha256(self.survey_bytes).hexdigest()
        report = self.check(review)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("abstracts cannot" in item for item in report["errors"]))

    def test_missing_claim_work_pair_blocks(self):
        review = self.review()
        review["proposed_claims"].append({"id": "C2", "statement": "Additional result"})
        report = self.check(review)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("every proposed claim" in item for item in report["errors"]))

    def test_changed_full_text_and_survey_block(self):
        review = self.review()
        (self.root / "literature/closest.pdf").write_bytes(b"changed")
        report = self.check(review)
        self.assertTrue(any("checksum mismatch" in item for item in report["errors"]))
        review = self.review()
        self.survey_bytes = b"changed"
        report = self.check(review)
        self.assertTrue(any("does not bind" in item for item in report["errors"]))

    def test_unreadable_document_or_unfound_excerpt_blocks(self):
        review = self.review()
        (self.root / "literature/closest.pdf").write_text("only an abstract", encoding="utf-8")
        review["works"][0]["full_text_sha256"] = hashlib.sha256((self.root / "literature/closest.pdf").read_bytes()).hexdigest()
        report = self.check(review)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("not a PDF" in item for item in report["errors"]))
        (self.root / "literature/closest.pdf").write_bytes(small_pdf("Another claim."))
        review["works"][0]["full_text_sha256"] = hashlib.sha256((self.root / "literature/closest.pdf").read_bytes()).hexdigest()
        report = self.check(review)
        self.assertTrue(any("source_excerpt is not found" in item for item in report["errors"]))

    def test_fabricated_page_number_blocks(self):
        review = self.review()
        review["comparisons"][0]["source_pointer"] = "page 99"
        report = self.check(review)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("outside the retained PDF" in item for item in report["errors"]))

    def test_final_central_claims_must_match_reviewed_claims(self):
        manifest = [{"type": "claim", "id": "C1", "statement": "A tighter bound is possible.", "central": True},
                    {"type": "claim", "id": "C2", "statement": "A new conclusion.", "central": True}]
        report = MODULE.validate(self.review(), self.survey, self.survey_bytes, self.root, manifest)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("central manifest claim" in item for item in report["errors"]))

    def test_self_review_or_unresolved_overlap_blocks(self):
        review = self.review()
        review["independent_review"]["reviewer_id"] = "writer"
        review["comparisons"][0]["overlap"] = "uncertain"
        report = self.check(review)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("distinct from the author" in item for item in report["errors"]))
        self.assertTrue(any("same or uncertain" in item for item in report["errors"]))

    def test_known_overlap_is_allowed_only_for_explicit_replication(self):
        review = self.review()
        review["comparisons"][0]["overlap"] = "same"
        self.survey["decision"] = "replicate"
        self.survey_bytes = json.dumps(self.survey).encode()
        review["topic_survey_sha256"] = hashlib.sha256(self.survey_bytes).hexdigest()
        review["independent_review"]["decision"] = "replicate"
        report = self.check(review)
        self.assertTrue(report["gate_passed"], report["errors"])
        self.assertFalse(report["novelty_certified"])

    def test_historical_cutoff_is_strict_and_month_precision_conservative(self):
        review = self.review()
        review["historical_author_cutoff_exclusive"] = "2025-03-31"
        report = self.check(review)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("author cutoff" in item for item in report["errors"]))

    def test_impossible_year_and_source_date_mismatch_block(self):
        review = self.review()
        review["works"][0]["first_public_at"] = "0000"
        report = self.check(review)
        self.assertFalse(report["gate_passed"])
        self.assertTrue(any("first_public_at requires" in item for item in report["errors"]))
        self.assertTrue(any("differs from the survey" in item for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
