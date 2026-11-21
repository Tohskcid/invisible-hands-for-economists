import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import collect_papers as collector


class PaperCollectionTests(unittest.TestCase):
    def test_resume_deduplicates_and_keeps_source_receipts(self):
        pages = [json.dumps({'message': {'items': [{'DOI': '10.1/A'}], 'next-cursor': 'next'}}).encode(),
                 json.dumps({'message': {'items': []}}).encode()]
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector, 'request', side_effect=pages) as fetch, patch.object(collector.time, 'sleep'):
            root = Path(tmp)
            collector.collect(root, ['aer'], 2024, 2024, 1, 1)
            collector.collect(root, ['aer'], 2024, 2024, 1, 1)
            result = collector.collect(root, ['aer'], 2024, 2024, 1, 1)
            self.assertEqual(fetch.call_count, 2)
            self.assertIn('cursor=next', fetch.call_args.args[0])
            self.assertEqual(result['papers'], 1)
            self.assertEqual(result['complete_queries'], 1)
            self.assertEqual(len(list((root / 'raw').glob('*.json'))), 2)

    def test_failure_preserves_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector, 'request', side_effect=OSError('secret remote message')):
            with self.assertRaises(OSError):
                collector.collect(Path(tmp), ['aer'], 2024, 2024, 1, 1)
            text = (Path(tmp) / 'catalog.json').read_text()
            self.assertNotIn('secret', text)
            self.assertEqual(json.loads(text)['queries']['aer:2024:1']['cursor'], '*')

    def test_pdf_cache_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector, 'request', return_value=b'%PDF-1.4\nfixture') as fetch:
            root = Path(tmp)
            result = collector.acquire(root, '10.1/test', 'https://example.org/a.pdf')
            self.assertEqual(collector.acquire(root, '10.1/test', 'https://example.org/a.pdf')['status'], 'cached')
            self.assertEqual(fetch.call_count, 1)
            Path(result['file']).write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                collector.acquire(root, '10.1/test', 'https://example.org/a.pdf')

    def test_login_html_is_not_fulltext(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector, 'request', return_value=b'<html>login</html>'):
            with self.assertRaises(ValueError):
                collector.acquire(Path(tmp), '10.1/test', 'https://example.org/a.pdf')
            self.assertFalse(list(Path(tmp).rglob('source.json')))
            self.assertTrue(list(Path(tmp).rglob('failure.json')))
