#!/usr/bin/env python3
"""Resolve DOI batches to OA locations and acquire licensed PDFs into a private cache."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import date, datetime, timezone
import fcntl
from functools import lru_cache
from hashlib import md5
from http.client import HTTPException
import gzip
import json
from pathlib import Path
import re
import socket
import ssl
import time
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

from collect_papers import PDF_BYTE_LIMIT, acquire, digest, request, save


CC = r'(?:cc-by(?:-nc)?(?:-nd|-sa)?|cc0|public-domain)'
CC_URL = re.compile(r'https?://creativecommons\.org/(?:licenses/by(?:-nc)?(?:-nd|-sa)?|publicdomain/(?:zero|mark))/\d+\.\d+/?$')


def public_pdf_url(url):
    p = urlsplit(url or '')
    if (p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.fragment
            or any(re.search(r'token|key|signatur|credential|password|x-amz|expires', k, re.I)
                   for k, _ in parse_qsl(p.query))):
        return None
    return p._replace(scheme='https', path=quote(p.path, safe="/%:@!$&'()*+,;=-._~"),
                      query=quote(p.query, safe="%;/:@!$&'()*+,=-._~?")).geturl()


def crossref_locations(paper):
    locations = []
    for lic in paper.get('licenses', []):
        version = lic.get('content-version')
        start = lic.get('start', {}).get('date-time', '')[:10]
        if not CC_URL.fullmatch(lic.get('URL', '')) or not start or start > date.today().isoformat():
            continue
        for link in paper.get('fulltext_candidates', []):
            url = public_pdf_url(link.get('URL'))
            if (version in ('vor', 'am') and version == link.get('content-version')
                    and link.get('content-type') == 'application/pdf' and url):
                locations.append(dict(provider='Crossref', url=url, license=lic['URL'], version=version))
    return locations


def openalex_locations(paper):
    locations = []
    for loc in paper.get('locations', []):
        url = public_pdf_url(loc.get('pdf_url'))
        if loc.get('is_oa') and url and re.fullmatch(CC, loc.get('license') or ''):
            locations.append(dict(provider='OpenAlex', url=url, license=loc['license'],
                                  version=loc.get('version'), host_type=(loc.get('source') or {}).get('type')))
    return locations


def oa_report(paper):
    return [{'landing_page': public_pdf_url(l.get('landing_page_url')), 'pdf_url': public_pdf_url(l.get('pdf_url')),
             'license': l.get('license'), 'version': l.get('version')} for l in paper.get('locations', [])
            if l.get('is_oa')]


def cached_response(url, cache):
    path = cache / (digest(url.encode()) + '.json.gz')
    if path.is_file():
        with gzip.open(path, 'rb') as source:
            return json.load(source)
    try:
        raw = request(url)
    except HTTPError as exc:
        if exc.code not in (404, 410):
            raise
        raw = json.dumps({'http_status': exc.code}).encode()
        exc.close()
    response = json.loads(raw)
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(gzip.compress(raw, mtime=0))
    tmp.replace(path)
    time.sleep(0.2)
    return response


def index(catalog, out):
    cache = out / 'openalex'
    cache.mkdir(exist_ok=True)
    queue = {doi: crossref_locations(paper) for doi, paper in catalog.items()}
    ordered = sorted(catalog)
    matched = set()
    prospects = {}
    queried = set()
    error = None
    overflow = []
    for start in range(0, len(ordered), 100):
        chunk = ordered[start:start + 100]
        params = dict(filter='doi:' + '|'.join(chunk), select='doi,locations', per_page=100, cursor='*')
        url = 'https://api.openalex.org/works?' + urlencode(params)
        try:
            response = cached_response(url, cache)
        except OSError as exc:
            error = {'type': type(exc).__name__, 'first_doi': chunk[0], 'batch_size': len(chunk),
                     'http_status': getattr(exc, 'code', None)}
            break
        if not isinstance(response.get('results'), list):
            raise ValueError('OpenAlex returned an invalid page')
        for paper in response['results']:
            doi = (paper.get('doi') or '').lower().removeprefix('https://doi.org/')
            if doi not in chunk:
                continue
            matched.add(doi)
            if locations := oa_report(paper):
                prospects.setdefault(doi, []).extend(locations)
            queue[doi].extend(openalex_locations(paper))
        # Standalone DOI batches use the public first page. Record any duplicate-work
        # overflow explicitly; a missing DOI in such a page is an unresolved lookup.
        if response['meta']['count'] > len(response['results']):
            overflow.append({'first_doi': chunk[0], 'returned': len(response['results']),
                             'api_count': response['meta']['count'],
                             'unmatched': sorted(set(chunk) - matched)})
        queried.update(chunk)
    # Each exact-identifier lookup is independently available via the public Works endpoint.
    resolved_overflow = 0
    if not error:
        for batch in overflow:
            for doi in batch['unmatched']:
                exact_url = 'https://api.openalex.org/works/https://doi.org/' + quote(doi, safe='/') + '?select=doi,locations'
                try:
                    item = cached_response(exact_url, cache)
                except OSError as exc:
                    error = {'type': type(exc).__name__, 'single_doi': doi, 'http_status': getattr(exc, 'code', None)}
                    break
                if (item.get('doi') or '').lower() == 'https://doi.org/' + doi:
                    matched.add(doi)
                    resolved_overflow += 1
                    if locations := oa_report(item):
                        prospects.setdefault(doi, []).extend(locations)
                    queue[doi].extend(openalex_locations(item))
            if error:
                break
    landings = out / 'licensed-landings'
    landing_queue = json.loads((landings / 'queue.json').read_text()) if (landings / 'queue.json').is_file() else {}
    resolution_log = landings / 'resolution.jsonl'
    resolved = {e['url']: e for line in resolution_log.read_text().splitlines() if (e := json.loads(line))} if resolution_log.is_file() else {}
    for doi, locs in landing_queue.items():
        for loc in locs:
            result = resolved.get(loc['url'], {})
            if result.get('status') == 'pdf_link' and doi in queue:
                queue[doi].append(dict(provider='OpenAlex-landing', url=result['pdf_url'], license=loc['license'],
                                       version=loc['version'], from_landing=loc['url'], host_type='repository'))
    pmc_file = out / 'pmc/sources.json'
    pmc = json.loads(pmc_file.read_text())['entries'] if pmc_file.is_file() else []
    for item in pmc:
        if item['status'] == 'jats_candidate' and item.get('pdf_url') and item['doi'] in queue:
            queue[item['doi']].append(dict(provider='PMC', url=item['pdf_url'], license=item['license'],
                                           version=item['version'], md5=item['pdf_md5'], host_type='repository'))
    for doi, locations in queue.items():
        # Keep both providers' license evidence; each (DOI, URL) is downloaded at most once.
        locations.sort(key=lambda x: (x.get('host_type') != 'repository', x['provider'] != 'Crossref', x['url']))
    save(out / 'oa-prospects.json', prospects)
    save(out / 'queue.json', {d: locs for d, locs in queue.items() if locs})
    counts = {'catalog_dois': len(ordered), 'openalex_queried_dois': len(queried), 'openalex_error': error, 'overflow_batches': overflow, 'overflow_dois_resolved': resolved_overflow, 'openalex_matched_dois': len(matched), 'openalex_reported_oa_dois': len(prospects),
              'crossref_version_licensed_pdf_dois': sum(any(l['provider'] == 'Crossref' for l in q) for q in queue.values()),
              'openalex_location_licensed_pdf_dois': sum(any(l['provider'] == 'OpenAlex' for l in q) for q in queue.values()),
              'openalex_licensed_landing_dois': len(landing_queue),
              'openalex_licensed_landing_doi_urls': sum(len({l['url'] for l in q}) for q in landing_queue.values()),
              'openalex_landing_resolved_pdf_dois': sum(any(l['provider'] == 'OpenAlex-landing' for l in q) for q in queue.values()),
              'pmc_licensed_pdf_dois': sum(any(l['provider'] == 'PMC' for l in q) for q in queue.values()),
              'pmc_jats_dois': len({e['doi'] for e in pmc if e['status'] == 'jats_candidate'}),
              'eligible_dois': sum(bool(locs) for locs in queue.values()),
              'distinct_eligible_doi_urls': sum(len({l['url'] for l in q}) for q in queue.values()),
              'ordered_dois_sha256': digest(json.dumps(ordered).encode()), 'completed_at': datetime.now(timezone.utc).isoformat()}
    save(out / 'queue-summary.json', counts)
    return counts


@lru_cache(maxsize=None)
def robots(host):
    url = 'https://' + host + '/robots.txt'
    policy = RobotFileParser(url)
    try:
        raw = request(url, max_bytes=512 * 1024, defer_denials=True)
        policy.parse(raw.decode(errors='replace').splitlines())
    except HTTPError as exc:
        if exc.code in (404, 410):
            policy.allow_all = True
        else:
            raise
        exc.close()
    return policy


def download_one(out, doi, url, allowance, expected_md5=None, denied_hosts=None):
    record = dict(doi=doi, url=url, at=datetime.now(timezone.utc).isoformat())
    host = urlsplit(url).netloc
    delay = 1
    try:
        policy = robots(host)
        agent = 'econ-benchmark-collector/1.0'
        delay = max(delay, policy.crawl_delay(agent) or 0)
        if not policy.can_fetch(agent, url):
            record.update(status='robots_disallow', pdf_request_made=False)
            return record
        record['pdf_request_made'] = True
        receipt = out / 'papers' / digest(doi.encode()) / 'source.json'
        target = out
        if receipt.exists() and json.loads(receipt.read_text())['url'] != url:
            target = out / 'alternates' / digest(url.encode())
        def allow_redirect(destination):
            endpoint = urlsplit(destination)
            return (endpoint.hostname not in (denied_hosts or set())
                    and robots(endpoint.netloc).can_fetch(agent, destination))
        got = acquire(target, doi, url, max_bytes=allowance, defer_denials=True, expected_md5=expected_md5,
                      redirect_check=allow_redirect)
        pdf = Path(got['file'])
        record.update(status=got['status'], sha256=pdf.stem, bytes=pdf.stat().st_size, pdf_request_made=got['status'] != 'cached')
    except (OSError, ValueError, HTTPException) as exc:
        record.setdefault('pdf_request_made', False)
        record['status'] = type(exc).__name__
        reason = getattr(exc, 'reason', exc)
        if isinstance(reason, ssl.SSLCertVerificationError):
            record['failure_kind'] = 'certificate_validation'
        elif isinstance(reason, socket.gaierror):
            record['failure_kind'] = 'dns_resolution'
        elif isinstance(reason, OSError):
            record['failure_kind'] = type(reason).__name__
        if isinstance(exc, HTTPError):
            record.update(http_status=exc.code, http_host=urlsplit(exc.geturl()).hostname or urlsplit(url).hostname)
            exc.close()
        if str(exc) == 'Redirect disallowed by source access policy':
            record['status'] = 'redirect_disallowed'
        if str(exc).startswith('Source is not a PDF'):
            record['status'] = 'non_pdf'
        if str(exc) == 'Response exceeds byte limit':
            if record['pdf_request_made']:
                record.update(status='over_byte_limit', max_bytes=allowance)
            else:
                record['status'] = 'robots_size_limit'
    time.sleep(delay)
    return record


def download(out, attempts, byte_budget, retry, retry_transient=False):
    queue = json.loads((out / 'queue.json').read_text())
    checksums = {(d, l['url']): l['md5'] for d, locs in queue.items() for l in locs if l.get('md5')}
    attempts_path = out / 'attempts.jsonl'
    old = [json.loads(line) for line in attempts_path.read_text().splitlines()] if attempts_path.exists() else []
    logged = {(a['doi'], a['url']): a['sha256'] for a in old if a.get('sha256')}
    available = {}
    receipts = sorted((out / 'papers').glob('*/source.json')) + sorted((out / 'alternates').glob('*/papers/*/source.json'))
    with attempts_path.open('a', encoding='utf-8') as log:
        for receipt_path in receipts:
            receipt = json.loads(receipt_path.read_text())
            doi, url, sha = receipt['doi'], receipt['url'], receipt['sha256']
            if url not in {l['url'] for l in queue.get(doi, [])}:
                continue
            if receipt['file'] != sha + '.pdf' or not re.fullmatch(r'[0-9a-f]{64}', sha):
                raise ValueError(f'Invalid collector receipt for {doi}')
            pdf = receipt_path.with_name(receipt['file'])
            raw = pdf.read_bytes() if pdf.is_file() else b''
            checksum = checksums.get((doi, url))
            if digest(raw) != sha or (checksum and md5(raw).hexdigest() != checksum):
                raise ValueError(f'Downloaded PDF missing or changed for {doi}')
            available[(doi, url)] = sha
            if (doi, url) not in logged:
                recovered = dict(doi=doi, url=url, at=receipt['retrieved_at'], status='recovered_receipt',
                                 sha256=sha, bytes=pdf.stat().st_size, pdf_request_made=True)
                print(json.dumps(recovered, sort_keys=True), file=log, flush=True)
                old.append(recovered)
    if any(available.get(pair) != sha for pair, sha in logged.items()):
        raise ValueError('Downloaded PDF receipt missing or changed; restore or reverify the cache')
    today = datetime.now(timezone.utc).date().isoformat()
    visited = set(available)
    if not retry:
        for e in old:
            temporary_limit = e['status'] == 'over_byte_limit' and e.get('max_bytes') != PDF_BYTE_LIMIT
            transient = e['status'] in ('URLError', 'TimeoutError', 'RemoteDisconnected') or e.get('http_status') in (500, 502, 504)
            retried_today = e.get('transient_retry') and e['at'].startswith(today)
            if not temporary_limit and not (retry_transient and transient and not retried_today):
                visited.add((e['doi'], e['url']))
    denial_codes = {401, 403, 429, 503}
    landing_log = out / 'licensed-landings/resolution.jsonl'
    landing_denials = [json.loads(line) for line in landing_log.read_text().splitlines()] if landing_log.is_file() else []
    deferred = {e.get('http_host') or urlsplit(e['url']).hostname for e in old if e['at'].startswith(today)
                and e.get('http_status') in denial_codes}
    deferred.update(e['host'] for e in landing_denials if e.get('host') and e['at'].startswith(today)
                    and e.get('http_status') in denial_codes)
    candidates = [(doi, l['url'], urlsplit(l['url']).hostname) for doi, locs in queue.items() for l in locs]
    newly_downloaded = used = n = 0
    budget_full = False
    # Only one in-flight request per host and DOI. Reserve bytes before starting each transfer.
    active = {}
    with attempts_path.open('a', encoding='utf-8') as log, ThreadPoolExecutor(max_workers=3) as workers:
        while True:
            busy_dois = {d for d, _, _ in active.values()}
            busy_hosts = {h for _, h, _ in active.values()}
            available = byte_budget - used - sum(limit for _, _, limit in active.values())
            for doi, url, host in candidates:
                if len(active) == 3 or n >= attempts or available <= 0 or budget_full:
                    break
                if doi in busy_dois or host in deferred or host in busy_hosts or (doi, url) in visited:
                    continue
                max_bytes = min(PDF_BYTE_LIMIT, available)
                active[workers.submit(download_one, out, doi, url, max_bytes, checksums.get((doi, url)), deferred)] = doi, host, max_bytes
                visited.add((doi, url))
                busy_dois.add(doi)
                busy_hosts.add(host)
                available -= max_bytes
                n += 1
            if not active:
                break
            finished, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in finished:
                doi, host, allowance = active.pop(future)
                record = future.result()
                if retry_transient:
                    record['transient_retry'] = True
                if record.get('sha256'):
                    if record['status'] != 'cached':
                        newly_downloaded += 1
                        used += record['bytes']
                elif record['status'] == 'over_byte_limit' and allowance < PDF_BYTE_LIMIT:
                    # A candidate no longer fits the remaining batch budget; resume it in a fresh batch.
                    budget_full = True
                elif record.get('http_status') in denial_codes:
                    deferred.add(record.get('http_host') or host)
                print(json.dumps(record, sort_keys=True), file=log, flush=True)
    return dict(attempts=n, downloaded=newly_downloaded, bytes=used, byte_budget_reached=budget_full or used >= byte_budget, host_deferred=sorted(deferred))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='Private curator directory')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('index')
    sub.add_parser('crossref', help='Build the version-licensed Crossref queue offline')
    get = sub.add_parser('acquire')
    get.add_argument('--attempts', type=int, default=50)
    get.add_argument('--max-mib', type=int, default=128, help='Maximum new PDF bytes retained in this invocation (MiB)')
    get.add_argument('--retry-transient', action='store_true', help='Retry connection errors once per UTC day')
    get.add_argument('--retry', action='store_true', help='Retry previously failed URLs')
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())['papers']
    args.out.mkdir(parents=True, exist_ok=True)
    lock_name = '.collector.lock' if args.action == 'acquire' else '.queue.lock'
    with (args.out / lock_name).open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'index':
            result = index(catalog, args.out)
        elif args.action == 'crossref':
            queue = {doi: ls for doi, paper in sorted(catalog.items()) if (ls := crossref_locations(paper))}
            save(args.out / 'queue.json', queue)
            result = {'catalog_dois': len(catalog), 'eligible_dois': len(queue), 'source': 'Crossref'}
        else:
            if args.attempts < 1 or args.max_mib < 1:
                parser.error('Budgets must be positive')
            result = download(args.out, args.attempts, args.max_mib * 1024**2, args.retry, args.retry_transient)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
