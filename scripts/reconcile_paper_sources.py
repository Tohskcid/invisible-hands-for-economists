#!/usr/bin/env python3
"""Inventory every catalog DOI against repository PDF bytes and hash-bound identity reviews."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET

from urllib.parse import unquote, urlsplit

from collect_papers import PDF_BYTE_LIMIT, digest, save
from queue_open_papers import landing_evidence, public_pdf_url


def normalize(value):
    text = unicodedata.normalize('NFKD', html.unescape(re.sub('<[^>]+>', '', value))).lower()
    return ' '.join(re.findall(r'\w+', ''.join(c for c in text if not unicodedata.combining(c))))


def jats_evidence(raw, paper):
    article = ET.fromstring(raw)
    meta = article.find('./front/article-meta')
    if meta is None:
        raise ValueError('PMC article lacks front-matter metadata')
    title_node = meta.find('./title-group/article-title')
    title = normalize(''.join(title_node.itertext())) if title_node is not None else ''
    authors = []
    for byline in meta.findall('./contrib-group/contrib[@contrib-type="author"]'):
        for surname in byline.findall('./name/surname') + byline.findall('./string-name/surname'):
            authors.append(normalize(''.join(surname.itertext())))
    catalog_authors = Counter(parts[-1] for author in paper['authors'] if (parts := normalize(author).split()))
    title_matches = bool(title) and title == normalize(paper['title'])
    surnames_match = bool(catalog_authors) and catalog_authors == Counter(name.split()[-1] for name in authors if name)
    paragraphs = len(article.findall('./body//p'))
    references = len(article.findall('./back//ref'))
    return dict(title_matches=title_matches, byline_surname_multiset_matches=surnames_match,
                body_paragraphs=paragraphs, ending_references=references,
                matched=title_matches and surnames_match and paragraphs > 0 and references > 0)


def opening_pages(pdf):
    try:
        result = subprocess.run(['pdftotext', '-f', '1', '-l', '2', str(pdf), '-'],
                                capture_output=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ''
    if result.returncode:
        return ''
    return normalize(result.stdout.decode('utf-8', errors='replace'))[:3500]


def supplement_label(url, front):
    path = urlsplit(url).path.lower()
    publisher_designated = '/supp/' in path and urlsplit(url).hostname in ('econometricsociety.org', 'www.econometricsociety.org')
    explicit_url = bool(re.search(r'appendix|supplement|[/_-]supp[/_-]', path))
    heading = bool(re.search(r'supplementary material|supplement(?:ary appendix)? to|online appendix|supplemental appendix', front[:500]))
    if publisher_designated or (explicit_url and heading):
        return 'publisher-path-and-opening-heading' if heading else 'publisher-supplement-path'
    return None


def inventory(root, catalog, reviews):
    titles = defaultdict(list)
    for doi, paper in catalog.items():
        title = normalize(paper['title'])
        if title:
            titles[title.split()[0]].append((title, doi, [parts[-1] for name in paper['authors'] if (parts := normalize(name).split())]))
    pdfs = defaultdict(list)
    receipts = defaultdict(list)
    issues = []
    for dirname, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in {'.git', '.venv', 'node_modules', '__pycache__'})
        folder = Path(dirname)
        for name in sorted(files):
            path = folder / name
            if name.lower().endswith('.pdf'):
                pdfs[digest(path.read_bytes())].append(path.relative_to(root).as_posix())
            if name == 'source.json' and folder.parent.name == 'papers':
                rec = json.loads(path.read_text())
                if not isinstance(rec, dict) or not {'doi', 'sha256', 'file', 'url'} <= rec.keys():
                    continue
                receipt_path = path.relative_to(root).as_posix()
                if Path(rec['file']).name != rec['file']:
                    issues.append({'receipt': receipt_path, 'issue': 'invalid_file_name'})
                    continue
                file = (folder / rec['file']).relative_to(root).as_posix()
                receipts[rec['sha256']].append((rec['doi'].lower(), rec['url'], receipt_path, file))

    index = defaultdict(list)
    outside = []
    unmapped = []
    for sha, paths in sorted(pdfs.items()):
        paths.sort(key=lambda s: (len(s.split('/')), len(s), s))
        front = opening_pages(root / paths[0])
        found = {}
        for word in set(front.split()):
            for title, doi, surnames in titles.get(word, []):
                if len(title.split()) < 3 or ' ' + title + ' ' not in ' ' + front + ' ':
                    continue
                if any(' ' + name + ' ' in ' ' + front + ' ' for name in surnames):
                    found[doi] = {'basis': 'opening-pages-title-and-surname'}
        for doi, url, receipt, file in receipts.get(sha, []):
            if file not in paths:
                issues.append({'receipt': receipt, 'issue': 'receipt_file_missing_or_changed'})
            elif doi in catalog:
                found[doi] = {'basis': 'collector-receipt', 'receipt': receipt, 'url': url}
            else:
                outside.append({'doi': doi, 'sha256': sha, 'receipt': receipt})
        labels = [label for s in found.values() if s.get('url') and (label := supplement_label(s['url'], front))]
        if labels:
            for match in found.values():
                match.update(role='supplement', role_basis=labels[0])
        if any(re.search(r'read[ _-]?me|codebook', unquote(urlsplit(s.get('url', '')).path).split('/')[-1], re.I)
               for s in found.values()) and re.search(r'read\s?me|codebook|data files|replication', front[:650]):
            for match in found.values():
                match.update(role='documentation', role_basis='source-filename-and-document-heading')
        review = reviews.get(sha)
        if review:
            if review['doi'] not in catalog:
                raise ValueError(f"Identity review DOI absent from catalog: {review['doi']}")
            for field in ('version', 'identity_check', 'body_check', 'end_check', 'url', 'role'):
                if not isinstance(review.get(field), str) or not review[field].strip():
                    raise ValueError(f'Identity review {sha} missing {field}')
            if review['role'] not in ('main', 'supplement'):
                raise ValueError(f'Unknown document role for {sha}')
            # An identified document cannot also be the primary article for a cited DOI.
            found = {review['doi']: {**found.get(review['doi'], {}), **review, 'basis': 'hash-bound-content-review'}}
        if not found:
            unmapped.append({'sha256': sha, 'file': paths[0], 'copy_count': len(paths),
                             'opening_page_words_extracted': len(front.split())})
        for doi, match in sorted(found.items()):
            index[doi].append(dict(sha256=sha, file=paths[0], copies=paths, **match))
    for sha in sorted(set(receipts) - set(pdfs)):
        for _, _, receipt, _ in receipts[sha]:
            issues.append({'receipt': receipt, 'issue': 'receipt_file_missing_or_changed'})
    for sha in sorted(set(reviews) - set(pdfs)):
        issues.append({'sha256': sha, 'issue': 'reviewed_pdf_missing_or_changed'})
    rows = []
    for doi, paper in sorted(catalog.items()):
        sources = index.get(doi, [])
        has_main = any(s.get('role') == 'main' and s['basis'] == 'hash-bound-content-review' for s in sources)
        pending = any(s['basis'] != 'hash-bound-content-review' and s.get('role') not in ('supplement', 'documentation') for s in sources)
        status = 'source_verified' if has_main else 'local_candidate' if pending else 'metadata_only'
        rows.append(dict(doi=doi, journal=paper['journal_id'], year=paper['year'], title=paper['title'],
                         source_status=status, sources=sources))
    summary = dict(catalog_dois=len(rows), pdf_files=sum(map(len, pdfs.values())), unique_pdf_hashes=len(pdfs),
                   scanned_pdf_hash_set_sha256=digest(('\n'.join(sorted(pdfs)) + '\n').encode()),
                   opening_pdf_text_extractor_available=bool(shutil.which('pdftotext')),
                   source_status_counts=dict(Counter(r['source_status'] for r in rows)), outside_catalog_receipts=outside,
                   integrity_issues=issues, unmapped_pdfs=unmapped,
                   meaning='Source identity and version only. No status certifies complete reading, appendices, access to research inputs, or reconstruction.')
    return rows, summary


def location_outcomes(queue, attempts, today, landing_events=()):
    """Classify every distinct eligible pair, including hosts whose refusal stopped later requests."""
    events = [e for history in attempts.values() for e in history]
    denied = {e.get('http_host') or urlsplit(e['url']).hostname: e['http_status'] for e in events
              if e['at'].startswith(today) and e.get('http_status') in (401, 403, 429, 503)}
    denied.update({e['host']: e['http_status'] for e in landing_events if e.get('host') and e['at'].startswith(today)
                   and e.get('http_status') in (401, 403, 429, 503)})
    history_by_pair = defaultdict(list)
    for e in events:
        history_by_pair[e['doi'], e['url']].append(e)
    by_doi = defaultdict(list)
    for doi, options in sorted(queue.items()):
        for url in sorted({option['url'] for option in options}):
            history = history_by_pair[doi, url]
            host = urlsplit(url).hostname
            if any(e.get('sha256') for e in history):
                state = 'pdf_acquired'
            elif history:
                last = history[-1]
                if last['status'] == 'over_byte_limit':
                    state = 'file_size_limit' if last.get('max_bytes') == PDF_BYTE_LIMIT else 'batch_size_limit'
                elif last.get('http_status'):
                    state = 'http_' + str(last['http_status'])
                else:
                    state = last.get('failure_kind', last['status']) if last['status'] == 'URLError' else last['status']
            elif host in denied:
                state = 'host_deferred_http_' + str(denied[host])
            else:
                state = 'pending'
            item = dict(url=url, status=state, events=len(history))
            if history and history[-1].get('http_host'):
                item['reported_http_host'] = history[-1]['http_host']
            by_doi[doi].append(item)
    return by_doi


def import_checked_manifests(root, manifests, reviews):
    root = root.resolve()
    targets = set()
    versions = {}
    added = {}
    cohorts = {}
    for manifest in manifests:
        cohort = set()
        cohorts[manifest.name] = cohort
        for case in json.loads(manifest.read_text())['cases']:
            doi = case['target']['doi'].lower()
            for source in case['sources']:
                if source['role'] not in ('main', 'appendix', 'supplement'):
                    continue
                role = 'main' if source['role'] == 'main' else 'supplement'
                file = (manifest.parent / source['file']).resolve()
                sha = source['sha256']
                if not file.is_relative_to(root) or not file.is_file() or digest(file.read_bytes()) != sha:
                    raise ValueError(f'Checked source file missing or changed for {doi}')
                if role == 'main':
                    targets.add(doi)
                    cohort.add(doi)
                if sha in reviews:
                    if (reviews[sha]['doi'], reviews[sha]['role']) != (doi, role):
                        raise ValueError(f'Conflicting source role or DOI in checked manifest for {sha}')
                    continue
                identity = source['identity_check'].strip()
                if not identity or not source['version'].strip():
                    raise ValueError(f'Missing source inspection evidence for {doi}')
                info = subprocess.run(['pdfinfo', str(file)], check=True, capture_output=True, timeout=30)
                pages = int(re.search(rb'(?m)^Pages:\s+(\d+)', info.stdout).group(1))
                evidence = []
                for page in ((pages + 1) // 2, pages):
                    result = subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), str(file), '-'],
                                            check=True, capture_output=True, timeout=30)
                    content = ' '.join(result.stdout.decode(errors='replace').split())
                    if len(content) < 25:
                        raise ValueError(f'Physical page {page} needs a visual content check for {sha}')
                    evidence.append(f'Physical page {page} of {pages}; verified extract SHA-256 {digest(content.encode())}.')
                record = dict(doi=doi, role=role, url=source['url'], version=source['version'], identity_check=identity,
                              body_check=evidence[0], end_check=evidence[1])
                added[sha] = record
                reviews[sha] = record
                issue = re.match(r'(?:published (?:econometrica|aer|qje)|econometrica, vol\.|the quarterly journal of economics \(|review of economic studies \(|american economic review (?:19|20)\d\d)', source['version'], re.I)
                if role == 'main' and issue:
                    versions[sha] = 'published_journal'
    return targets, versions, added, {name: len(dois) for name, dois in cohorts.items()}


def public_snapshot(out, rows, summary, discovery, hashes):
    """Publish only fixed, answer-free columns; private PDF paths and case IDs stay local."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter='\t', lineterminator='\n')
    writer.writerow(['doi', 'journal', 'year', 'reported_oa_locations', 'licensed_pdf_urls', 'source_status',
                     'acquisition_status', 'case_readiness', 'data_reason', 'local_pdf_status', 'pmc_jats_versions', 'local_supplement_pdfs', 'publisher_pair_status', 'open_access_lead', 'reviewed_pdf_versions', 'local_documentation_pdfs', 'licensed_landing_pages', 'resolved_landing_pdf_urls', 'pmc_jats_content_matches', 'location_status_by_sha256'])
    doi_set = set()
    statuses = Counter()
    for row in rows:
        doi = row['doi'].lower()
        if doi in doi_set:
            raise ValueError(f'Duplicate DOI in snapshot: {doi}')
        doi_set.add(doi)
        attempts = row['acquisition_attempts']
        options = len({s['url'] for s in row['licensed_pdf_locations']})
        if any(e.get('sha256') for e in attempts):
            state = 'pdf_acquired'
        elif attempts and all(e['status'] == 'over_byte_limit' for e in attempts):
            state = 'deferred_by_byte_limit'
        elif any(e.get('pdf_request_made', True) for e in attempts):
            state = 'attempted_without_pdf'
        elif attempts:
            state = 'host_access_deferred'
        elif options and all(l['status'].startswith('host_deferred_') for l in row['location_outcomes']):
            state = 'host_access_deferred'
        else:
            state = 'queued' if options else 'no_licensed_pdf_in_queue'
        statuses[state] += 1
        case = row.get('case_disposition', {})
        for code in (case.get('status', 'unassessed'), case.get('data_reason', 'unassessed')):
            if not re.fullmatch('[a-z][a-z0-9_-]*', code):
                raise ValueError('Public snapshot disposition must be a short reason code')
        location_tokens = {}
        for kind, field in (('pdf', 'location_outcomes'), ('landing', 'licensed_landing_outcomes')):
            for loc in row.get(field, []):
                location_tokens[(kind, loc['url'])] = loc['status']
        for kind, url in row.get('crossref_endpoint_uris', []):
            state = location_tokens.get(('pdf', url), 'provider_rights_or_entitlement_unverified')
            location_tokens[(kind, url)] = state
        for kind, url in row.get('reported_oa_uris', []):
            location_tokens.setdefault((kind, url), 'reported_outside_eligible_queue')
        coded_locations = '|'.join('/'.join((kind, digest(url.encode()), state)) for (kind, url), state in sorted(location_tokens.items()))
        writer.writerow([doi, row['journal'], row['year'], row['provider_oa_location_count'], options,
                         row['source_status'], state, case.get('status', 'unassessed'),
                         case.get('data_reason', 'unassessed'), row.get('local_pdf_status', row['source_status']),
                         len(row.get('pmc_jats_sources', [])), sum(s.get('role') == 'supplement' for s in row.get('sources', [])),
                         row.get('publisher_pair_status', 'not_in_pair_queue'), row['open_access_lead'],
                         ','.join(row.get('reviewed_pdf_versions', [])) or 'none',
                         sum(s.get('role') == 'documentation' for s in row.get('sources', [])),
                         len(row.get('licensed_landing_outcomes', [])),
                         len({l['url'] for l in row['licensed_pdf_locations'] if l.get('provider') == 'OpenAlex-landing'}),
                         sum(j['document_evidence']['matched'] for j in row.get('pmc_jats_sources', [])), coded_locations])
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / 'source-status.tsv.gz'
    packed = gzip.compress(buffer.getvalue().encode(), mtime=0)
    tmp = snapshot.with_suffix('.tmp')
    tmp.write_bytes(packed)
    tmp.replace(snapshot)
    evidence = {
        'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'doi_rows': len(doi_set),
        'inventory': snapshot.name, 'inventory_sha256': digest(packed), 'input_sha256': hashes,
        'checked_manifest_dois': summary.get('checked_manifest_dois', 0),
        'checked_manifest_cohorts': summary.get('checked_manifest_cohorts', {}),
        'source_status_counts': summary['source_status_counts'], 'acquisition_status_counts': dict(statuses),
        'source_status_by_journal': {j: dict(Counter(r['source_status'] for r in rows if r['journal'] == j))
                                     for j in sorted({r['journal'] for r in rows})},
        'case_readiness_counts': dict(Counter(r.get('case_disposition', {}).get('status', 'unassessed') for r in rows)),
        'open_access_discovery': {k: discovery.get(k) for k in (
            'openalex_queried_dois', 'openalex_matched_dois', 'openalex_reported_oa_dois',
            'crossref_version_licensed_pdf_dois', 'openalex_location_licensed_pdf_dois',
            'eligible_dois', 'distinct_eligible_doi_urls', 'pmc_licensed_pdf_dois', 'pmc_jats_dois',
            'openalex_licensed_landing_dois', 'openalex_licensed_landing_doi_urls', 'openalex_landing_resolved_pdf_dois')},
        'pdf_transfer_events': sum(e.get('pdf_request_made', True) for r in rows for e in r['acquisition_attempts']),
        'workspace_pdf_files': summary['pdf_files'], 'workspace_distinct_pdf_hashes': summary['unique_pdf_hashes'],
        'queue_events': sum(len(r['acquisition_attempts']) for r in rows),
        'catalog_with_tdm_endpoint': sum(r['crossref_reports_tdm_endpoint'] for r in rows),
        'catalog_with_any_crossref_fulltext_link': sum(bool(r['crossref_fulltext_link_count']) for r in rows),
        'attempt_outcomes': summary['attempt_outcomes'], 'retained_pdf_bytes': summary['queue_downloaded_bytes'],
        'distinct_downloaded_locations': summary['queue_downloaded_urls'],
        'dois_with_queue_pdf_bytes': statuses['pdf_acquired'],
        'licensed_landing_pair_outcomes': dict(Counter(l['status'] for r in rows for l in r.get('licensed_landing_outcomes', []))),
        'open_access_lead_counts': dict(Counter(r['open_access_lead'] for r in rows)),
        'publisher_pair_outcomes': dict(Counter(r['publisher_pair_status'] for r in rows if 'publisher_pair_status' in r)),
        'local_supplement_only_pdf_dois': sum(r.get('local_pdf_status') == 'metadata_only' and any(s.get('role') == 'supplement' for s in r['sources']) for r in rows),
        'local_pdf_status_counts': dict(Counter(r.get('local_pdf_status', r['source_status']) for r in rows)),
        'reviewed_pdf_version_dois': dict(Counter(v for r in rows for v in r.get('reviewed_pdf_versions', []))),
        'pmc_jats_automated_content_matches': sum(j['document_evidence']['matched'] for r in rows for j in r.get('pmc_jats_sources', [])),
        'pmc_provider_resolution': summary.get('pmc_provider_resolution', {}),
        'pmc_jats_version_counts': dict(Counter(j['version'] for r in rows for j in r.get('pmc_jats_sources', []))),
        'pmc_jats_only_candidate_dois': sum(bool(r.get('pmc_jats_sources')) and r.get('local_pdf_status') == 'metadata_only' for r in rows),
        'eligible_location_outcomes': summary['eligible_location_outcomes'],
        'deferred_locations_by_host': summary.get('deferred_locations_by_host', {}),
        'provider_documentation': {
            'Crossref': 'https://www.crossref.org/documentation/retrieve-metadata/text-and-data-mining/',
            'OpenAlex': 'https://help.openalex.org/data/works/attributes/',
            'NIH NLM NCBI PubMed Central Article Datasets': 'https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/',
            'PMC dataset access and terms': 'https://pmc-oa-opendata.s3.amazonaws.com/README.txt'},
        'definitions': {
            'metadata_only': 'No primary PDF matched in the scanned repository and no PMC JATS source was retained. Remote availability can be unknown.',
            'local_candidate': 'Matching opening text, a collector receipt, or NIH JATS with an exact DOI and article body. A curator still needs to inspect the content and version.',
            'source_verified': 'A curator inspected the title/byline, version, article body and ending of the exact hashed local bytes. Full reading, readiness, and reconstruction have separate records.',
            'licensed_pdf_urls': 'Distinct direct locations carrying active version-matched Crossref CC metadata an OA location-specific recognized license in OpenAlex, or NIH PubMed Central version-level CC/TDM or explicit dataset TDM access. NIH/NLM PubMed Central supplied the versioned research-dataset sources. A link alone does not establish identity.',
            'reported_oa_locations': 'Number of provider location records; a location may be a landing page without a PDF. Counts can include multiple copies.',
            'location_status_by_sha256': 'Every distinct reported URL is represented per DOI and role as role/SHA-256(normalized exact URL)/status, separated by vertical bars. This allows verification against a known URL without publishing query parameters. The outside-queue state indicates a lead whose terms or available file need separate review.',
            'resolved_landing_pdf_urls': 'Distinct PDF links found by inspecting explicitly licensed OpenAlex landing pages or their official repository file listings. A link can duplicate an earlier discovery.',
            'reviewed_pdf_versions': 'Versions of hash-bound primary PDFs recorded in the curator assessment. Multiple kinds can coexist for a DOI.',
            'open_access_lead': 'Discovery status. A reported direct PDF outside the eligible queue or an OA landing page remains a source-review lead.',
            'publisher_pair_status': 'Separate official journal main-article acquisition from a supplement landing page. A collected PDF still needs independent inspection.',
            'acquisition_status': 'Outcome for the explicit licensed PDF queue. Other primary PDFs and NIH XML also contribute to source_status.',
            'deferred_locations_by_host': 'A host returned an access or rate-limit response to a document, redirect check, or robots request. Untried locations on that host were held. This records an access condition at this checkpoint, not a licensing ruling.',
            'pdf_transfer_events': 'Recorded acquisition attempts that reached a PDF URL. A response can be HTML or a supplement; internal transport retries are not separately logged.',
            'local_documentation_pdfs': 'PDFs identified as data documentation or readme files using their supplied path and opening content. These do not count as primary articles.',
            'local_supplement_pdfs': 'Number of distinct local PDF hashes identified as supplementary by curator review or an explicit supplier path and opening heading. The publisher-designated Econometric Society supplement directory is also sufficient to exclude a file from the primary-article count.',
            'local_pdf_status': 'Source status from the PDF inventory alone.',
            'pmc_jats_content_matches': 'Automatic comparison of the actual JATS file: normalized article title and author surname counts match the catalog, and the body and ending reference list are present. This records a stricter candidate signal and does not substitute for independent content review.',
            'pmc_jats_versions': 'Locally stored NIH full-article XML versions with provider checksum, matching front-matter DOI and body. A paper can also have a local PDF.',
            'case_readiness': 'Source-intake disposition at this checkpoint; downstream review and execution are recorded in individual case packages.',
            'data_reason': 'Known reason for limited input access or readiness. Unassessed means no specific input finding was recorded.'}}
    phase = summary.get('checkpoint', {}).get('phase', 'observed')
    captured = summary.get('checkpoint', {}).get('captured_at_utc', evidence['observed_at_utc'])
    evidence['source_checkpoint'] = {'phase': phase, 'captured_at_utc': captured}
    save(out / 'source-status-summary.json', evidence)
    counts = evidence['source_status_counts']
    oa = evidence['open_access_discovery']
    pairs = evidence['publisher_pair_outcomes']
    pair_note = ''
    if pairs:
        pair_note = (f"另從 {sum(pairs.values()):,} 個期刊補充資料頁追查正文，"
                     f"已由期刊直接取得 {pairs.get('downloaded-unread', 0):,} 篇，由作者或機構補得 "
                     f"{pairs.get('alternate_published_copy_acquired', 0):,} 篇。此批來源可與授權佇列重疊。")
    languages = {'interim': '查找進行中的快照', 'operational': '本輪操作檢查點', 'final': '本輪查找完成的快照', 'observed': '來源快照'}
    lines = [
        '# 期刊論文來源與資料可用性', '',
        f"外部查找紀錄封存於 {captured}，本地檔案清查完成於 {evidence['observed_at_utc']}。這份{languages.get(phase, '來源快照')}涵蓋目錄內全部 {len(rows):,} 個相異 DOI。"
        '每列對應一篇目錄紀錄。檔案身分、實驗所需資料與重建結果分開記錄。', '',
        '| 來源狀態 | DOI 數 | 判定依據 |', '| --- | ---: | --- |',
        f"| 已辨識文章版本 | {counts.get('source_verified', 0):,} | 已逐檔核對雜湊、標題、作者、正文與末頁。出版版、接受稿及工作論文的分類另見 reviewed_pdf_versions。 |",
        f"| 有待辨識的本地全文候選 | {counts.get('local_candidate', 0):,} | 已有 PDF 線索或含 DOI 與正文的 NIH 文章 XML，仍待完整來源核對。 |",
        f"| 尚無匹配的本地主要全文 | {counts.get('metadata_only', 0):,} | 此時只見書目、附件或尚待處理的外部線索。 |", '',
        f"OpenAlex 查詢了 {oa.get('openalex_queried_dois') or 0:,} 個 DOI，精確匹配 {oa.get('openalex_matched_dois') or 0:,} 個，"
        f"其中 {oa.get('openalex_reported_oa_dois') or 0:,} 個帶有開放取用線索。"
        f"Crossref、OpenAlex 與 PMC 的授權和版本資料目前支持 {oa.get('eligible_dois') or 0:,} 個 DOI 的 "
        f"{oa.get('distinct_eligible_doi_urls') or 0:,} 個 PDF 位置。已從 {evidence['distinct_downloaded_locations']:,} 個位置取得 PDF，關聯 {evidence['dois_with_queue_pdf_bytes']:,} 個 DOI。"
        '同篇文章可以有多個位置，取得的檔案也可能是附錄或資料說明。' + pair_note, '',
        f"NIH/NLM/NCBI PubMed Central Article Datasets 提供 {oa.get('pmc_jats_dois') or 0:,} 篇有本地 JATS 全文的文章，"
        f"其中 {evidence['pmc_jats_version_counts'].get('author-manuscript', 0):,} 份為作者稿，"
        f"{evidence['pmc_jats_version_counts'].get('published-article', 0):,} 份為出版版。研究檔保存來源授權、提供者校驗碼與本地 SHA-256。"
        '原始資料供應者為美國國家衛生研究院、國家醫學圖書館暨國家生物技術資訊中心。'
        ' [PMC 官方資料說明](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/) · [資料條款](https://pmc-oa-opendata.s3.amazonaws.com/README.txt)', '',
        '逐篇檢索時，可用 local_pdf_status 和 pmc_jats_versions 查找不同格式，'
        '用 local_supplement_pdfs 和 local_documentation_pdfs 辨別附件，用 case_readiness 和 data_reason 檢查已知的研究前提。'
        'location_status_by_sha256 逐一記錄已發現網址的用途、雜湊與狀態。實驗判定以各案的盲測與獨立評閱紀錄為準。未評估的資料可用性保留為 unassessed。', '',
        '[下載完整 DOI 表](source-status.tsv.gz) · [統計、主機回應與來源雜湊](source-status-summary.json)', '']
    tmp = out / 'source-status.md.tmp'
    tmp.write_text('\n'.join(lines), encoding='utf-8')
    tmp.replace(out / 'source-status.md')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, help='Private JSON object keyed by reviewed PDF SHA-256')
    parser.add_argument('--acquisition', type=Path, help='Private licensed-PDF queue directory')
    parser.add_argument('--checked-manifest', type=Path, action='append', default=[],
                        help='Curated source manifest with DOI, relative file, SHA, role, version and content inspection')
    parser.add_argument('--version-classes', type=Path, help='Private classified version labels keyed by reviewed primary PDF SHA-256')
    parser.add_argument('--publisher-pairs', type=Path, help='Private supplemental landing page / main article acquisition report')
    parser.add_argument('--dispositions', type=Path, help='Private case and input assessments keyed by DOI')
    parser.add_argument('--public-snapshot', type=Path, help='Write DOI-only compressed TSV and summary')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    catalog_bytes = args.catalog.read_bytes()
    reviews = json.loads(args.reviews.read_text()) if args.reviews else {}
    target_manifest_dois, inferred_versions, added_reviews, checked_cohorts = import_checked_manifests(args.root.resolve(), args.checked_manifest, reviews)
    catalog = json.loads(catalog_bytes)['papers']
    rows, summary = inventory(args.root.resolve(), catalog, reviews)
    if args.acquisition:
        queue = json.loads((args.acquisition / 'queue.json').read_text())
        stamp = args.acquisition / 'checkpoint.json'
        if stamp.is_file():
            summary['checkpoint'] = json.loads(stamp.read_text())
        location_file = args.acquisition / 'oa-prospects.json'
        prospects = json.loads(location_file.read_text()) if location_file.is_file() else {}
        attempts = defaultdict(list)
        log = args.acquisition / 'attempts.jsonl'
        if log.is_file():
            for line in log.read_text().splitlines():
                event = json.loads(line)
                attempts[event['doi']].append(event)
        landing_dir = args.acquisition / 'licensed-landings'
        landing_log = landing_dir / 'resolution.jsonl'
        landing_events = landing_evidence(args.acquisition)
        landing_queue = json.loads((landing_dir / 'queue.json').read_text()) if (landing_dir / 'queue.json').is_file() else {}
        latest_landing = {e['url']: e for e in landing_events}
        outcomes = location_outcomes(queue, attempts, datetime.now(timezone.utc).date().isoformat(), landing_events)
        save(args.acquisition / 'location-status.json', outcomes)
        pmc_manifest = args.acquisition / 'pmc/sources.json'
        pmc = defaultdict(list)
        if pmc_manifest.is_file():
            provenance = json.loads(pmc_manifest.read_text())
            summary['pmc_provider_resolution'] = {
                'journal_search_records': provenance['journal_search_records'], 'pmc_ids_checked': provenance['pmcids_checked'],
                'outcomes': dict(Counter(item['status'] for item in provenance['entries'])),
                'retained_jats_bytes': sum(item['bytes'] for item in provenance['entries'] if item['status'] == 'jats_candidate')}
            for item in provenance['entries']:
                if item['status'] != 'jats_candidate':
                    continue
                file = pmc_manifest.parent / item['file']
                raw = file.read_bytes() if file.is_file() else b''
                if item['doi'] not in catalog or digest(raw) != item['sha256']:
                    raise ValueError('PMC source DOI or local article checksum mismatch')
                item['document_evidence'] = jats_evidence(raw, catalog[item['doi']])
                pmc[item['doi']].append(item)
        for row in rows:
            doi = row['doi']
            row['local_pdf_status'] = row['source_status']
            row['pmc_jats_sources'] = pmc.get(doi, [])
            if doi in pmc and row['source_status'] == 'metadata_only':
                row['source_status'] = 'local_candidate'
            row['location_outcomes'] = outcomes.get(doi, [])
            links = catalog[doi].get('fulltext_candidates', [])
            row['crossref_fulltext_link_count'] = len(links)
            row['crossref_endpoint_uris'] = sorted({('crossref_tdm' if item.get('intended-application') == 'text-mining' else 'crossref_fulltext', url)
                                                  for item in links if (url := public_pdf_url(item.get('URL')))})
            row['crossref_reports_tdm_endpoint'] = any(link.get('intended-application') == 'text-mining' for link in links)
            row['provider_oa_location_count'] = len(prospects.get(doi, []))
            row['reported_oa_uris'] = sorted({(kind, item[key]) for item in prospects.get(doi, [])
                                             for kind, key in (('pdf', 'pdf_url'), ('landing', 'landing_page')) if item.get(key)})
            row['licensed_pdf_locations'] = queue.get(doi, [])
            row['licensed_landing_outcomes'] = [latest_landing.get(url, {'url': url, 'status': 'pending'})
                                              for url in sorted({l['url'] for l in landing_queue.get(doi, [])})]
            if doi in queue:
                row['open_access_lead'] = 'licensed_pdf_route'
            elif any(p.get('pdf_url') for p in prospects.get(doi, [])):
                row['open_access_lead'] = 'reported_pdf_requires_source_review'
            elif doi in prospects:
                row['open_access_lead'] = 'reported_oa_location_without_direct_pdf'
            else:
                row['open_access_lead'] = 'no_reported_oa_location'
            row['acquisition_attempts'] = attempts.get(doi, [])
        summary['source_status_counts'] = dict(Counter(r['source_status'] for r in rows))
        summary['licensed_queue_dois'] = len(queue)
        summary['attempted_queue_dois'] = len(attempts)
        events = [e for history in attempts.values() for e in history]
        downloaded = {(e['doi'], e['url']): e for e in events if 'sha256' in e}
        downloaded_dois = {doi for doi, _ in downloaded}
        summary['eligible_location_outcomes'] = dict(Counter(l['status'] for ls in outcomes.values() for l in ls))
        deferrals = defaultdict(Counter)
        for locations in outcomes.values():
            for loc in locations:
                if loc['status'].startswith('host_deferred_') or loc['status'] in ('http_401', 'http_403', 'http_429', 'http_503'):
                    deferrals[loc.get('reported_http_host') or urlsplit(loc['url']).hostname][loc['status']] += 1
        summary['deferred_locations_by_host'] = dict(sorted(deferrals.items()))
        summary['queue_not_yet_attempted_dois'] = len(set(queue) - attempts.keys())
        summary['queue_attempts_with_no_download_dois'] = len(attempts.keys() - downloaded_dois)
        summary['queue_downloaded_dois'] = len(downloaded_dois)
        summary['queue_downloaded_urls'] = len(downloaded)
        summary['queue_downloaded_bytes'] = sum(e['bytes'] for e in downloaded.values())
        summary['attempt_outcomes'] = dict(Counter(str(e.get('http_status', e['status'])) for e in events))
    version_classes = json.loads(args.version_classes.read_text()) if args.version_classes else {}
    version_classes = {**inferred_versions, **version_classes}
    valid_versions = {'published_journal', 'publisher_advance', 'accepted_manuscript', 'author_manuscript', 'working_paper', 'alternative_reprint'}
    if any(h not in reviews or reviews[h]['role'] != 'main' or kind not in valid_versions for h, kind in version_classes.items()):
        raise ValueError('Classified version requires a reviewed primary PDF and a recognized version label')
    for row in rows:
        row['reviewed_pdf_versions'] = sorted({version_classes.get(s['sha256'], 'reviewed_unclassified')
                                               for s in row['sources'] if s.get('role') == 'main'})
    if args.publisher_pairs:
        outcomes = {}
        for item in json.loads(args.publisher_pairs.read_text())['rows']:
            doi, state = item['doi'], item['status']
            if doi not in catalog or doi in outcomes or not re.fullmatch(r'[a-z][a-z0-9_-]*', state):
                raise ValueError('Invalid publisher main article outcome')
            outcomes[doi] = state
        alternate_file = args.publisher_pairs.with_name('alternate-retrieval.json')
        if alternate_file.is_file():
            for item in json.loads(alternate_file.read_text())['rows']:
                if item['doi'] not in outcomes:
                    raise ValueError('Publisher alternate absent from the reported landing-page cohort')
                if item['status'] == 'downloaded-published-layout':
                    outcomes[item['doi']] = 'alternate_published_copy_acquired'
        for row in rows:
            if row['doi'] in outcomes:
                row['publisher_pair_status'] = outcomes[row['doi']]
    if args.dispositions:
        dispositions = json.loads(args.dispositions.read_text())
        if not set(dispositions) <= {r['doi'] for r in rows}:
            raise ValueError('Case disposition refers to a DOI outside catalog')
        for row in rows:
            if row['doi'] in dispositions:
                row['case_disposition'] = dispositions[row['doi']]
    for row in rows:
        if row['doi'] in target_manifest_dois and 'case_disposition' not in row:
            row['case_disposition'] = {'status': 'source_checked_readiness_pending'}
    summary['checked_manifest_dois'] = len(target_manifest_dois)
    summary['checked_manifest_cohorts'] = checked_cohorts
    summary['catalog_sha256'] = digest(catalog_bytes)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.checked_manifest:
        save(args.out / 'checked-manifest-reviews.json', added_reviews)
    tmp = args.out / 'inventory.jsonl.tmp'
    with tmp.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    tmp.replace(args.out / 'inventory.jsonl')
    save(args.out / 'summary.json', summary)
    if args.public_snapshot:
        if not args.acquisition:
            parser.error('--public-snapshot requires --acquisition')
        sources = {'catalog': args.catalog, 'queue': args.acquisition / 'queue.json',
                   'attempts': args.acquisition / 'attempts.jsonl', 'oa_locations': args.acquisition / 'oa-prospects.json',
                   'queue_summary': args.acquisition / 'queue-summary.json', 'reviews': args.reviews,
                   'location_status': args.acquisition / 'location-status.json', 'case_dispositions': args.dispositions,
                   'publisher_pairs': args.publisher_pairs, 'classified_versions': args.version_classes}
        for i, manifest in enumerate(args.checked_manifest, 1):
            sources[f'checked_manifest_{i}'] = manifest
        if args.publisher_pairs and alternate_file.is_file():
            sources['publisher_alternates'] = alternate_file
        if pmc_manifest.is_file():
            sources['pmc'] = pmc_manifest
        if stamp.is_file():
            sources['checkpoint'] = stamp
        if landing_log.is_file():
            sources.update(licensed_landing_queue=landing_dir / 'queue.json', landing_resolution=landing_log)
        repository_log = landing_dir / 'repository-records.jsonl'
        if repository_log.is_file():
            sources['repository_record_resolution'] = repository_log
        hashes = {k: digest(p.read_bytes()) for k, p in sources.items() if p}
        hashes['scanned_pdf_hash_set'] = summary['scanned_pdf_hash_set_sha256']
        associations = sorted((r['doi'], s['sha256'], s.get('role') or 'unknown', s['basis'])
                              for r in rows for s in r['sources'])
        hashes['matched_pdf_evidence'] = digest(json.dumps(associations, separators=(',', ':')).encode())
        public_snapshot(args.public_snapshot, rows, summary, json.loads(sources['queue_summary'].read_text()), hashes)
    print(json.dumps({k: summary[k] for k in ('catalog_dois', 'pdf_files', 'unique_pdf_hashes', 'source_status_counts')}))
    return int(bool(summary['integrity_issues']))


if __name__ == '__main__':
    raise SystemExit(main())
