import hashlib
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from triage_acquired_papers import evidence, triage


class IntakeTests(unittest.TestCase):
    def test_does_not_mistake_repository_cover_for_article_version(self):
        title, doi = 'Market Institutions', '10.1000/x'
        data = {'title': title, 'authors': ['Alexa Quinn']}
        cover = f'Citation\nAmerican Economic Review {doi}\n{title}. Alexa Quinn. Institutional repository.'
        body = 'Working paper: Market Institutions by Alexa Quinn. See the online appendix. ' + 'Body evidence ' * 10
        self.assertEqual(evidence([cover, '', ''], data, doi)['queue'], 'visual-review')
        record = evidence([cover, body, 'References ' * 20], data, doi)
        self.assertEqual(record['queue'], 'compare-editions')
        self.assertEqual(record['appendix_mentions_on_pages'], [2])
        self.assertTrue(record['all_author_surnames_on_opening_pages'])
        hal = f'{title}. Alexa Quinn. To cite this version: American Economic Review. {doi}. HAL Id: x'
        self.assertEqual(evidence([hal, body], data, doi)['queue'], 'compare-editions')
        final = f'American Economic Review 101: 1-3. {doi}. {title}. Alexa Quinn. ' + 'Model facts ' * 20
        self.assertEqual(evidence([final], data, doi)['queue'], 'check-journal-layout')

    def test_cache_rechecks_original_before_reusing_content_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'papers' / 'work'
            folder.mkdir(parents=True)
            data = b'%PDF-fixture'
            file = folder / 'original.pdf'
            file.write_bytes(data)
            receipt = {'doi': '10.1000/x', 'file': file.name, 'sha256': hashlib.sha256(data).hexdigest(),
                       'url': 'https://example.org/paper.pdf'}
            (folder / 'source.json').write_text(json.dumps(receipt))
            catalog = {receipt['doi']: {'title': 'Market Institutions', 'authors': ['Alexa Quinn']}}
            with patch('triage_acquired_papers.subprocess.run') as extract, patch('triage_acquired_papers.physical_pages', return_value=1):
                extract.return_value.stdout = ('Market Institutions. Alexa Quinn. ' + 'Evidence ' * 20 + '\f').encode()
                old = triage(root, catalog, {})[0]
                cached = {receipt['doi']: old}
                self.assertEqual(triage(root, catalog, cached), [old])
                self.assertEqual(extract.call_count, 1)
                file.write_bytes(b'corrupted')
                self.assertEqual(triage(root, catalog, cached)[0]['queue'], 'inspection-error')
