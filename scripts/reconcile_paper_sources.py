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

from urllib.parse import urlsplit

from collect_papers import PDF_BYTE_LIMIT, digest, save


def normalize(value):
    text = unicodedata.normalize('NFKD', html.unescape(re.sub('<[^>]+>', '', value))).lower()
    return ' '.join(re.findall(r'\w+', ''.join(c for c in text if not unicodedata.combining(c))))


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
        pending = any(s['basis'] != 'hash-bound-content-review' and s.get('role') != 'supplement' for s in sources)
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
            by_doi[doi].append(dict(url=url, status=state, events=len(history)))
    return by_doi


def public_snapshot(out, rows, summary, discovery, hashes):
    """Publish only fixed, answer-free columns; private PDF paths and case IDs stay local."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter='\t', lineterminator='\n')
    writer.writerow(['doi', 'journal', 'year', 'reported_oa_locations', 'licensed_pdf_urls', 'source_status',
                     'acquisition_status', 'case_readiness', 'data_reason', 'local_pdf_status', 'pmc_jats_versions', 'local_supplement_pdfs', 'publisher_pair_status', 'open_access_lead'])
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
        writer.writerow([doi, row['journal'], row['year'], row['provider_oa_location_count'], options,
                         row['source_status'], state, case.get('status', 'unassessed'),
                         case.get('data_reason', 'unassessed'), row.get('local_pdf_status', row['source_status']),
                         len(row.get('pmc_jats_sources', [])), sum(s.get('role') == 'supplement' for s in row.get('sources', [])),
                         row.get('publisher_pair_status', 'not_in_pair_queue'), row['open_access_lead']])
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / 'source-status.tsv.gz'
    packed = gzip.compress(buffer.getvalue().encode(), mtime=0)
    tmp = snapshot.with_suffix('.tmp')
    tmp.write_bytes(packed)
    tmp.replace(snapshot)
    evidence = {
        'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'doi_rows': len(doi_set),
        'inventory': snapshot.name, 'inventory_sha256': digest(packed), 'input_sha256': hashes,
        'source_status_counts': summary['source_status_counts'], 'acquisition_status_counts': dict(statuses),
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
        'licensed_landing_pair_outcomes': dict(Counter(l['status'] for r in rows for l in r.get('licensed_landing_outcomes', []))),
        'open_access_lead_counts': dict(Counter(r['open_access_lead'] for r in rows)),
        'publisher_pair_outcomes': dict(Counter(r['publisher_pair_status'] for r in rows if 'publisher_pair_status' in r)),
        'local_supplement_only_pdf_dois': sum(r.get('local_pdf_status') == 'metadata_only' and any(s.get('role') == 'supplement' for s in r['sources']) for r in rows),
        'local_pdf_status_counts': dict(Counter(r.get('local_pdf_status', r['source_status']) for r in rows)),
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
            'open_access_lead': 'Discovery status. A reported direct PDF outside the eligible queue or an OA landing page remains a source-review lead.',
            'publisher_pair_status': 'Separate official journal main-article acquisition from a supplement landing page. A collected PDF still needs independent inspection.',
            'acquisition_status': 'Outcome for the explicit licensed PDF queue. Other primary PDFs and NIH XML also contribute to source_status.',
            'pdf_transfer_events': 'Recorded acquisition attempts that reached a PDF URL. A response can be HTML or a supplement; internal transport retries are not separately logged.',
            'local_supplement_pdfs': 'Number of distinct local PDF hashes identified as supplementary by curator review or an explicit supplier path and opening heading. The publisher-designated Econometric Society supplement directory is also sufficient to exclude a file from the primary-article count.',
            'local_pdf_status': 'Source status from the PDF inventory alone.',
            'pmc_jats_versions': 'Locally stored NIH full-article XML versions with provider checksum, matching front-matter DOI and body. A paper can also have a local PDF.',
            'case_readiness': 'Source-intake disposition at this checkpoint; downstream review and execution are recorded in individual case packages.',
            'data_reason': 'Known reason for limited input access or readiness. Unassessed means no specific input finding was recorded.'}}
    save(out / 'source-status-summary.json', evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, help='Private JSON object keyed by reviewed PDF SHA-256')
    parser.add_argument('--acquisition', type=Path, help='Private licensed-PDF queue directory')
    parser.add_argument('--publisher-pairs', type=Path, help='Private supplemental landing page / main article acquisition report')
    parser.add_argument('--dispositions', type=Path, help='Private case and input assessments keyed by DOI')
    parser.add_argument('--public-snapshot', type=Path, help='Write DOI-only compressed TSV and summary')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    catalog_bytes = args.catalog.read_bytes()
    reviews = json.loads(args.reviews.read_text()) if args.reviews else {}
    catalog = json.loads(catalog_bytes)['papers']
    rows, summary = inventory(args.root.resolve(), catalog, reviews)
    if args.acquisition:
        queue = json.loads((args.acquisition / 'queue.json').read_text())
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
        landing_events = [json.loads(line) for line in landing_log.read_text().splitlines()] if landing_log.is_file() else []
        landing_queue = json.loads((landing_dir / 'queue.json').read_text()) if (landing_dir / 'queue.json').is_file() else {}
        latest_landing = {e['url']: e for e in landing_events}
        outcomes = location_outcomes(queue, attempts, datetime.now(timezone.utc).date().isoformat(), landing_events)
        save(args.acquisition / 'location-status.json', outcomes)
        pmc_manifest = args.acquisition / 'pmc/sources.json'
        pmc = defaultdict(list)
        if pmc_manifest.is_file():
            for item in json.loads(pmc_manifest.read_text())['entries']:
                if item['status'] != 'jats_candidate':
                    continue
                file = pmc_manifest.parent / item['file']
                if item['doi'] not in catalog or not file.is_file() or digest(file.read_bytes()) != item['sha256']:
                    raise ValueError('PMC source DOI or local article checksum mismatch')
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
            row['crossref_reports_tdm_endpoint'] = any(link.get('intended-application') == 'text-mining' for link in links)
            row['provider_oa_location_count'] = len(prospects.get(doi, []))
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
                    deferrals[urlsplit(loc['url']).hostname][loc['status']] += 1
        summary['deferred_locations_by_host'] = dict(sorted(deferrals.items()))
        summary['queue_not_yet_attempted_dois'] = len(set(queue) - attempts.keys())
        summary['queue_attempts_with_no_download_dois'] = len(attempts.keys() - downloaded_dois)
        summary['queue_downloaded_dois'] = len(downloaded_dois)
        summary['queue_downloaded_urls'] = len(downloaded)
        summary['queue_downloaded_bytes'] = sum(e['bytes'] for e in downloaded.values())
        summary['attempt_outcomes'] = dict(Counter(str(e.get('http_status', e['status'])) for e in events))
    if args.publisher_pairs:
        outcomes = {}
        for item in json.loads(args.publisher_pairs.read_text())['rows']:
            doi, state = item['doi'], item['status']
            if doi not in catalog or doi in outcomes or not re.fullmatch(r'[a-z][a-z0-9_-]*', state):
                raise ValueError('Invalid publisher main article outcome')
            outcomes[doi] = state
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
    summary['catalog_sha256'] = digest(catalog_bytes)
    args.out.mkdir(parents=True, exist_ok=True)
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
                   'publisher_pairs': args.publisher_pairs}
        if pmc_manifest.is_file():
            sources['pmc'] = pmc_manifest
        if landing_log.is_file():
            sources.update(licensed_landing_queue=landing_dir / 'queue.json', landing_resolution=landing_log)
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
