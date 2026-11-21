import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import collect_papers
import collect_pmc_sources as pmc
import queue_open_papers as queue
import reconcile_paper_sources as reconcile
import resolve_licensed_landings as landing


class SourceInventoryTests(unittest.TestCase):
    def test_only_hash_bound_primary_reviews_promote_to_verified(self):
        d = '10.1234/example'
        wrong = '10.1234/wrong'
        paper = dict(title='Example Market Paper', authors=['A. Smith'], journal_id='qje', year=2000)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pdf = root / 'misleading-filename.pdf'
            pdf.write_bytes(b'%PDF-MOCK')
            sha = collect_papers.digest(pdf.read_bytes())
            rec = dict(doi=d, role='supplement', url='https://example.org/doc.pdf', version='appendix',
                       identity_check='appendix title/byline', body_check='appendix contents', end_check='proof ends')
            with patch.object(reconcile, 'opening_pages', return_value='example market paper a smith'):
                data, _ = reconcile.inventory(root, {d: paper}, {})
                self.assertEqual(data[0]['source_status'], 'local_candidate')
                data, _ = reconcile.inventory(root, {d: paper, wrong: paper}, {sha: rec})
                self.assertEqual([r['source_status'] for r in data], ['metadata_only', 'metadata_only'])
                rec['role'] = 'main'
                data, _ = reconcile.inventory(root, {d: paper}, {sha: rec})
                self.assertEqual(data[0]['source_status'], 'source_verified')
                pdf.write_bytes(b'%PDF-changed')
                data, summary = reconcile.inventory(root, {d: paper}, {sha: rec})
                self.assertEqual(data[0]['source_status'], 'local_candidate')
                self.assertEqual(summary['integrity_issues'][0]['issue'], 'reviewed_pdf_missing_or_changed')

    def test_collector_receipt_must_bind_present_local_bytes(self):
        d = '10.1234/test'
        with tempfile.TemporaryDirectory() as folder, patch.object(collect_papers, 'request', return_value=b'%PDF-MOCK'):
            root = Path(folder)
            pdf = Path(collect_papers.acquire(root, d, 'https://example.org/source.pdf')['file'])
            cat = {d: dict(title='Paper', authors=[], journal_id='qje', year=2021)}
            with patch.object(reconcile, 'opening_pages', return_value=''):
                rows, _ = reconcile.inventory(root, cat, {})
                self.assertEqual(rows[0]['source_status'], 'local_candidate')
                pdf.write_bytes(b'changed bytes')
                rows, summary = reconcile.inventory(root, cat, {})
                self.assertEqual(rows[0]['source_status'], 'metadata_only')
                self.assertTrue(summary['integrity_issues'])

    def test_pmc_requires_version_reuse_terms_and_checksum_bound_objects(self):
        self.assertEqual(pmc.eligible_license({'license_code': 'TDM', 'is_manuscript': True}), 'tdm')
        self.assertIsNone(pmc.eligible_license({'license_code': 'TDM', 'is_manuscript': False}))
        self.assertEqual(pmc.eligible_license({'license_code': 'CC BY-NC'}), 'cc-by-nc')
        self.assertIsNone(pmc.eligible_license({'license_code': 'unknown'}))
        self.assertEqual(pmc.eligible_license({'license_code': None, 'is_pmc_openaccess': True}), 'pmc-dataset-tdm')
        obj = 's3://pmc-oa-opendata/PMC123.2/PMC123.2.xml?md5=' + 'a' * 32
        url, checksum = pmc.object_location(obj, 'PMC123.2', 'xml')
        self.assertTrue(url.endswith('/PMC123.2/PMC123.2.xml'))
        self.assertEqual(checksum, 'a' * 32)
        for change in (obj.replace('PMC123.2.xml', 'PMC123.1.xml'), obj.split('?')[0]):
            with self.assertRaisesRegex(ValueError, 'Unexpected PMC'):
                pmc.object_location(change, 'PMC123.2', 'xml')

    def test_designated_supplement_cannot_become_primary_from_receipt(self):
        paper = dict(title='Econometrics Example Paper', authors=['A. Smith'], journal_id='econometrica', year=2020)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            doi = '10.1234/example'
            url = 'https://www.econometricsociety.org/example/supp/onlineappendix.pdf'
            with patch.object(collect_papers, 'request', return_value=b'%PDF-example'):
                collect_papers.acquire(root, doi, url)
            with patch.object(reconcile, 'opening_pages', return_value='econometrica supplementary material'):
                rows, summary = reconcile.inventory(root, {doi: paper}, {})
            self.assertEqual(rows[0]['source_status'], 'metadata_only')
            self.assertEqual(rows[0]['sources'][0]['role'], 'supplement')
            self.assertEqual(summary['source_status_counts'], {'metadata_only': 1})

    def test_terminal_location_states_include_unattempted_denied_host_and_mirrors(self):
        queue_map = {'a': [{'url': 'https://host/a'}, {'url': 'https://host/a'}, {'url': 'https://mirror/a'}],
                     'b': [{'url': 'https://host/b'}], 'c': [{'url': 'https://other/c'}]}
        attempts = {'a': [dict(doi='a', url='https://host/a', status='HTTPError', http_status=403, at='2026-01-01'),
                          dict(doi='a', url='https://mirror/a', status='downloaded-unread', sha256='f', at='2026-01-01')]}
        states = reconcile.location_outcomes(queue_map, attempts, '2026-01-01')
        self.assertEqual([[s['status'] for s in v] for v in states.values()],
                         [['http_403', 'pdf_acquired'], ['host_deferred_http_403'], ['pending']])
        self.assertEqual(reconcile.location_outcomes(queue_map, attempts, '2026-01-02')['b'][0]['status'], 'pending')

    def test_public_snapshot_omits_private_identity_and_locator(self):
        row = {'doi': '10.1234/test', 'journal': 'qje', 'year': 2000, 'source_status': 'source_verified',
               'provider_oa_location_count': 1, 'open_access_lead': 'licensed_pdf_route', 'crossref_reports_tdm_endpoint': False,
               'crossref_fulltext_link_count': 1, 'licensed_pdf_locations': [{'url': 'https://example.org/PDF'}],
               'case_disposition': {'status': 'nominated', 'case_id': 'private_case'},
               'sources': [{'file': '/private/home/document.pdf'}],
               'acquisition_attempts': [{'sha256': 'f' * 64, 'status': 'downloaded-unread'}]}
        summary = {'source_status_counts': {'source_verified': 1}, 'attempt_outcomes': {'downloaded-unread': 1},
                   'queue_downloaded_bytes': 42, 'queue_downloaded_urls': 1, 'eligible_location_outcomes': {'pdf_acquired': 1},
                   'pdf_files': 1, 'unique_pdf_hashes': 1}
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            reconcile.public_snapshot(out, [row], summary, {}, {})
            raw = gzip.decompress((out / 'source-status.tsv.gz').read_bytes()).decode()
            self.assertEqual(len(raw.splitlines()), 2)
            for private in ('private_case', '/private/home', 'https://'):
                self.assertNotIn(private, raw)
            self.assertEqual(json.loads((out / 'source-status-summary.json').read_text())['doi_rows'], 1)
            with self.assertRaisesRegex(ValueError, 'Duplicate DOI'):
                reconcile.public_snapshot(out, [row, row], summary, {}, {})


class OpenLocationTests(unittest.TestCase):
    def setUp(self):
        policy = queue.RobotFileParser()
        policy.allow_all = True
        mock = patch.object(queue, 'robots', return_value=policy)
        mock.start()
        self.addCleanup(mock.stop)

    def test_only_active_version_matched_license_is_eligible(self):
        cc = 'https://creativecommons.org/licenses/by/4.0/'
        lic = {'content-version': 'vor', 'start': {'date-time': '2001-01-01T00:00:00Z'}, 'URL': cc}
        pdf = {'content-version': 'vor', 'content-type': 'application/pdf', 'URL': 'https://example.org/p.pdf'}
        self.assertEqual(len(queue.crossref_locations({'licenses': [lic], 'fulltext_candidates': [pdf]})), 1)
        for key, change in [('content-version', 'am'), ('URL', 'https://example.org/license'), ('start', {'date-time': '2999-01-01'})]:
            self.assertFalse(queue.crossref_locations({'licenses': [{**lic, key: change}], 'fulltext_candidates': [pdf]}))

    def test_landing_discovery_uses_location_rights_and_advertised_links(self):
        source = dict(landing_page='https://host.org/article', pdf_url=None, license='cc-by', version='publishedVersion')
        self.assertEqual(list(landing.licensed_queue({'a': [source], 'b': [{**source, 'license': None}],
                                                   'c': [{**source, 'pdf_url': 'https://host.org/file'}]})), ['a'])
        parser = landing.PdfLinks()
        parser.feed('<a href="other.pdf">another article</a><meta name="citation_pdf_url" content="paper.pdf">')
        self.assertEqual(parser.links, {'paper.pdf'})
        resolver = landing.Resolver({'host.org': 403})
        with patch.object(resolver.opener, 'open') as fetch:
            self.assertEqual(resolver.resolve('https://host.org/article')['status'], 'host_deferred')
            fetch.assert_not_called()

    def test_open_locations_must_have_location_specific_open_license(self):
        loc = dict(is_oa=True, license='cc-by-nc-nd', version='acceptedVersion', pdf_url='http://example.org/file.pdf')
        self.assertEqual(queue.openalex_locations({'locations': [loc]})[0]['url'], 'https://example.org/file.pdf')
        self.assertEqual(queue.public_pdf_url('https://example.org/pd f.pdf'), 'https://example.org/pd%20f.pdf')
        for change in [{'is_oa': False}, {'license': None}, {'pdf_url': 'https://example.org/file?token=123'}]:
            self.assertFalse(queue.openalex_locations({'locations': [{**loc, **change}]}))

    def test_batch_resume_handles_failure_without_promoting_or_redownloading(self):
        urls = {'10.1/a': [{'url': 'https://example.org/a.pdf'}], '10.1/b': [{'url': 'https://example.org/b.pdf'}]}
        with tempfile.TemporaryDirectory() as folder, patch.object(queue.time, 'sleep'):
            root = Path(folder)
            (root / 'queue.json').write_text(json.dumps(urls))
            with patch.object(collect_papers, 'request', side_effect=[b'<html>', b'%PDF-b']) as get:
                result = queue.download(root, 10, 100, False)
                self.assertEqual((result['attempts'], result['downloaded']), (2, 1))
                self.assertEqual(queue.download(root, 10, 100, False)['attempts'], 0)
                self.assertEqual(get.call_count, 2)
            lines = [json.loads(l) for l in (root / 'attempts.jsonl').read_text().splitlines()]
            self.assertEqual([r['status'] for r in lines], ['non_pdf', 'downloaded-unread'])
            next(root.rglob('*.pdf')).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'missing or changed'):
                queue.download(root, 10, 100, False)

    def test_distinct_versions_and_recovery_share_a_doi(self):
        urls = {'10.1/a': [{'url': 'https://example.org/draft'}, {'url': 'https://example.org/final'}]}
        with tempfile.TemporaryDirectory() as folder, patch.object(queue.time, 'sleep'):
            root = Path(folder)
            (root / 'queue.json').write_text(json.dumps(urls))
            with patch.object(collect_papers, 'request', side_effect=[b'%PDF-draft', b'%PDF-final']) as get:
                self.assertEqual(queue.download(root, 10, 500, False)['downloaded'], 2)
                self.assertEqual(len(list(root.rglob('source.json'))), 2)
                log = root / 'attempts.jsonl'
                log.write_text(log.read_text().splitlines()[0] + '\n')
                self.assertEqual(queue.download(root, 10, 500, False)['attempts'], 0)
                self.assertEqual(get.call_count, 2)
                self.assertEqual(json.loads(log.read_text().splitlines()[1])['status'], 'recovered_receipt')

    def test_denied_host_falls_back_without_repeating_access_denials(self):
        urls = {'10.1/a': [{'url': 'https://denied.example/a'}, {'url': 'https://mirror.example/a'}],
                '10.1/b': [{'url': 'https://denied.example/b'}]}
        def fetch(url, max_bytes, **options):
            if 'denied' in url:
                raise HTTPError(url, 403, 'forbidden', {}, None)
            return b'%PDF-a'
        with tempfile.TemporaryDirectory() as folder, patch.object(queue.time, 'sleep'):
            root = Path(folder)
            (root / 'queue.json').write_text(json.dumps(urls))
            with patch.object(collect_papers, 'request', side_effect=fetch):
                first = queue.download(root, 10, 100 * 1024**2, False)
                self.assertEqual((first['attempts'], first['downloaded']), (2, 1))
                self.assertEqual(queue.download(root, 10, 100 * 1024**2, False)['attempts'], 0)

    def test_collector_honors_transfer_allowance_without_length_header(self):
        response = io.BytesIO(b'x' * 20)
        response.headers = {}
        with patch('urllib.request.urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                collect_papers.request('https://example.org/article.pdf', max_bytes=8)

    def test_long_retry_after_defers_instead_of_hitting_again(self):
        error = HTTPError('https://example.org/limit', 429, 'limited', {'Retry-After': '3600'}, io.BytesIO())
        with patch('urllib.request.urlopen', side_effect=error) as fetch:
            with self.assertRaises(HTTPError):
                collect_papers.request('https://example.org/limit')
        self.assertEqual(fetch.call_count, 1)
        error.close()
