#!/usr/bin/env python3
"""Collect journal metadata and explicitly selected public PDFs for benchmark curation."""
import argparse
import datetime as dt
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from search_literature import normalize

JOURNALS = {'aer': '0002-8282', 'econometrica': '0012-9682', 'jpe': '0022-3808',
            'qje': '0033-5533', 'restud': '0034-6527'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(temporary, path)


PDF_BYTE_LIMIT = 50 * 1024 * 1024


def public_host(hostname):
    host = (hostname or '').lower().rstrip('.')
    if not host or host in ('localhost', 'localhost.localdomain') or host.endswith(('.localhost', '.local', '.localdomain', '.internal')):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return '.' in host and not all(part.isdigit() for part in host.split('.'))


def request(url, max_bytes=PDF_BYTE_LIMIT, *, defer_denials=False, redirect_check=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not public_host(parsed.hostname) or parsed.username or parsed.password:
        raise ValueError('Only public HTTPS URLs without credentials are supported')
    req = urllib.request.Request(url, headers={'User-Agent': 'econ-benchmark-collector/1.0'})
    open_url = urllib.request.urlopen
    if redirect_check is not None:
        class CheckedRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                target = urllib.parse.urlsplit(newurl)
                if target.scheme != 'https' or not public_host(target.hostname) or target.username or target.password or not redirect_check(newurl):
                    fp.close()
                    raise ValueError('Redirect disallowed by source access policy')
                return super().redirect_request(req, fp, code, msg, headers, newurl)
        open_url = urllib.request.build_opener(CheckedRedirect).open
    for attempt in range(3):
        try:
            with open_url(req, timeout=30) as response:
                if int(response.headers.get('Content-Length') or 0) > max_bytes:
                    raise ValueError('Response exceeds byte limit')
                raw = response.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise ValueError('Response exceeds byte limit')
                return raw
        except urllib.error.HTTPError as exc:
            if (defer_denials and exc.code in (429, 503)) or exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            delay = 2 ** (attempt + 1)
            retry_after = exc.headers.get('Retry-After')
            if retry_after:
                try:
                    delay = max(delay, int(retry_after))
                except ValueError:
                    try:
                        delay = max(delay, parsedate_to_datetime(retry_after).timestamp() - time.time())
                    except (TypeError, ValueError, OverflowError):
                        pass
            if delay > 30:
                raise
            exc.close()
            time.sleep(delay)


def collect(root, journals, first, last, pages, rows):
    path = root / 'catalog.json'
    state = json.loads(path.read_text()) if path.exists() else {'papers': {}, 'queries': {}}
    raw_dir = root / 'raw'
    raw_dir.mkdir(exist_ok=True)
    for journal in journals:
        # Year-sized queries bound restart work when the remote cursor expires.
        for year in range(first, last + 1):
            key = f'{journal}:{year}:{rows}'
            query = state['queries'].setdefault(key, {'cursor': '*', 'complete': False, 'receipts': []})
            for _ in range(pages):
                if query['complete']:
                    break
                params = urllib.parse.urlencode({'filter': f'type:journal-article,from-pub-date:{year}-01-01,until-pub-date:{year}-12-31',
                                                'rows': rows, 'cursor': query['cursor']})
                url = f'https://api.crossref.org/journals/{JOURNALS[journal]}/works?{params}'
                try:
                    raw = request(url)
                    message = json.loads(raw)['message']
                    items = message['items']
                    if not isinstance(items, list):
                        raise ValueError('Crossref items is not a list')
                    next_cursor = message.get('next-cursor')
                    if len(items) >= rows and not next_cursor:
                        raise ValueError('Full page lacks next cursor')
                    records = [normalize(item) for item in items]
                    if any(not record['doi'] for record in records):
                        raise ValueError('Crossref record lacks DOI')
                except (OSError, ValueError, KeyError) as exc:
                    query['error'] = type(exc).__name__
                    save(path, state)
                    raise
                sha = digest(raw)
                (raw_dir / f'{sha}.json').write_bytes(raw)
                timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
                for item, record in zip(items, records):
                    doi = record['doi'].lower()
                    record.update({'journal_id': journal, 'raw_sha256': sha, 'retrieved_at': timestamp,
                                   'fulltext_candidates': item.get('link', []), 'licenses': item.get('license', []),
                                   'curation_status': 'unread', 'publication_status': 'metadata-only'})
                    state['papers'][doi] = record
                query['receipts'].append({'url': url, 'sha256': sha, 'retrieved_at': timestamp, 'count': len(items)})
                query.update(cursor=next_cursor, complete=len(items) < rows)
                query.pop('error', None)
                save(path, state)
                time.sleep(1)
    return {'papers': len(state['papers']), 'complete_queries': sum(q['complete'] for q in state['queries'].values()),
            'queries': len(state['queries'])}


def acquire(root, doi, url, max_bytes=PDF_BYTE_LIMIT, *, defer_denials=False, expected_md5=None, redirect_check=None):
    """An explicit source URL is not a license or an identity verification."""
    folder = root / 'papers' / digest(doi.lower().encode())
    folder.mkdir(parents=True, exist_ok=True)
    receipt_path = folder / 'source.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        pdf = folder / receipt['file']
        if receipt['url'] != url:
            raise ValueError('Source already recorded; use a separate collection for another version')
        cached = pdf.read_bytes()
        if digest(cached) != receipt['sha256'] or (expected_md5 and hashlib.md5(cached).hexdigest() != expected_md5):
            raise ValueError('Cached PDF hash mismatch')
        return {'status': 'cached', 'file': str(pdf)}
    try:
        raw = request(url, max_bytes=max_bytes, defer_denials=defer_denials, redirect_check=redirect_check)
        if expected_md5 and hashlib.md5(raw).hexdigest() != expected_md5:
            raise ValueError('PDF differs from provider checksum')
        if not raw.startswith(b'%PDF-'):
            raise ValueError('Source is not a PDF (possibly a login or access-denied page)')
    except (OSError, ValueError) as exc:
        save(folder / 'failure.json', {'status': 'unavailable', 'error': type(exc).__name__})
        raise
    sha = digest(raw)
    pdf = folder / f'{sha}.pdf'
    pdf.write_bytes(raw)
    save(receipt_path, {'doi': doi.lower(), 'url': url, 'sha256': sha, 'file': pdf.name,
                        'retrieved_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                        'status': 'downloaded-unread', 'identity_verified': False,
                        'redistribution_license': 'not-established', 'appendices_checked': False})
    (folder / 'failure.json').unlink(missing_ok=True)
    return {'status': 'downloaded-unread', 'file': str(pdf)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Private curator workspace, never author input')
    sub = parser.add_subparsers(dest='command', required=True)
    discover = sub.add_parser('discover')
    discover.add_argument('--journals', nargs='+', choices=JOURNALS, default=list(JOURNALS))
    discover.add_argument('--from-year', type=int, required=True)
    discover.add_argument('--to-year', type=int, required=True)
    discover.add_argument('--pages', type=int, default=1, help='Maximum new pages per journal/year this invocation')
    discover.add_argument('--rows', type=int, default=100)
    download = sub.add_parser('acquire')
    download.add_argument('--doi', required=True)
    download.add_argument('--url', required=True, help='Explicitly selected public PDF URL; no access tokens')
    args = parser.parse_args()
    if args.command == 'discover' and not (1500 <= args.from_year <= args.to_year <= 2100 and args.pages > 0 and 1 <= args.rows <= 1000):
        parser.error('Invalid year range, page budget, or rows (1..1000)')
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        with (args.out / '.collector.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = (collect(args.out, args.journals, args.from_year, args.to_year, args.pages, args.rows)
                      if args.command == 'discover' else acquire(args.out, args.doi, args.url))
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        # Do not echo remote responses, authentication pages, or credential-bearing URLs.
        print(json.dumps({'status': 'stopped', 'error': type(exc).__name__, 'checkpoint': str(args.out)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
