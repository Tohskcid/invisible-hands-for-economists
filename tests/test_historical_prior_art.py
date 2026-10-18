import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_historical_prior_art", ROOT / "scripts/check_historical_prior_art.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HistoricalPriorArtTests(unittest.TestCase):
    def record(self):
        return {
            "target": {
                "first_journal_public_at": "2025-10-22",
                "journal_date_source": "https://publisher.example/article",
                "first_target_public_at": "2024-04-15",
                "target_date_source": "https://archive.example/target",
            },
            "comparators": [
                {"title": "Old work", "first_public_at": "2024-03-31", "date_source": "https://archive.example/old", "is_target_version": False, "author_material": True},
                {"title": "Intermediate work", "first_public_at": "2025-01-01", "date_source": "https://archive.example/intermediate", "is_target_version": False, "author_material": True},
                {"title": "Same-day work", "first_public_at": "2025-10-22", "date_source": "https://archive.example/same", "is_target_version": False},
                {"title": "Later work", "first_public_at": "2025-10-23", "date_source": "https://archive.example/later", "is_target_version": False},
                {"title": "Target preprint", "first_public_at": "2024-04-15", "date_source": "https://archive.example/target", "is_target_version": True},
                {"title": "Old year only", "first_public_at": "2022", "date_source": "https://archive.example/old-year", "is_target_version": False},
                {"title": "Uncertain month", "first_public_at": "2025-10", "date_source": "https://archive.example/uncertain", "is_target_version": False},
                {"title": "Blind cutoff month", "first_public_at": "2024-04", "date_source": "https://archive.example/blind", "is_target_version": False},
            ],
        }

    def test_two_cutoffs_and_target_exclusion(self):
        result = MODULE.evaluate(self.record())
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual([item["historical_prior_art"] for item in result["comparators"]], [True, True, False, False, False, True, None, True])
        self.assertEqual([item["author_visible_for_strict_blind"] for item in result["comparators"]], [True, False, False, False, False, True, False, None])
        self.assertFalse(result["author_corpus_safe"])
        self.assertEqual(result["unsafe_author_material"], ["Intermediate work"])

    def test_safe_author_corpus(self):
        record = self.record()
        record["comparators"][1]["author_material"] = False
        result = MODULE.evaluate(record)
        self.assertTrue(result["author_corpus_safe"])

    def test_bad_or_unordered_dates_fail(self):
        record = self.record()
        record["target"]["first_target_public_at"] = "2026-01-01"
        record["comparators"][0]["first_public_at"] = "2025-02-30"
        result = MODULE.evaluate(record)
        self.assertFalse(result["valid"])
        self.assertTrue(any("cannot postdate" in error for error in result["errors"]))
        self.assertTrue(any("first_public_at" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
