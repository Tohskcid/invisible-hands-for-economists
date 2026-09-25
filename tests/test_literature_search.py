import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("search_literature", ROOT / "scripts/search_literature.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LiteratureSearchTests(unittest.TestCase):
    def test_crossref_record_uses_canonical_doi_and_plain_abstract(self):
        record = MODULE.normalize({
            "DOI": "10.1234/example",
            "title": ["A paper"],
            "container-title": ["A Journal"],
            "author": [{"given": "Ada", "family": "Lovelace"}],
            "published-online": {"date-parts": [[2026, 9, 1]]},
            "abstract": "<jats:p>Evidence.</jats:p>",
            "type": "journal-article",
            "is-referenced-by-count": 3,
        })
        self.assertEqual(record["canonical_locator"], "https://doi.org/10.1234/example")
        self.assertEqual(record["authors"], ["Ada Lovelace"])
        self.assertEqual(record["abstract"], "Evidence.")
        self.assertEqual(record["year"], 2026)


if __name__ == "__main__":
    unittest.main()
