#!/usr/bin/env python3
"""Resolve public attachment inventories for known licensed repository records."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
from html.parser import HTMLParser
from http.client import HTTPException
import json
from pathlib import Path
import re
from threading import Lock
import time
from urllib.error import HTTPError
from urllib.parse import unquote, urlencode, urljoin, urlsplit

from collect_papers import digest, request
from queue_open_papers import public_pdf_url, robots

PROVIDERS = {'econ-papers.upf.edu': 'upf', 'figshare.com': 'figshare',
             'zenodo.org': 'zenodo', 'dukespace.lib.duke.edu': 'duke'}


class UniversityPaperLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get('href') or ''
        if tag == 'a' and re.fullmatch(r'(?:https?://econ-papers\.upf\.edu)?/papers/[\w.-]+\.pdf', href, re.I):
            self.links.add(href)


class ZenodoFiles(HTMLParser):
    def __init__(self, landing, record):
        super().__init__()
        self.landing = landing
        self.prefix = '/records/' + record + '/files/'
        self.files = {}

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        href = dict(attrs).get('href') or ''
        u = urljoin(self.landing, href)
        p = urlsplit(u)
        if p.hostname == 'zenodo.org' and p.path.startswith(self.prefix):
            name = unquote(p.path.removeprefix(self.prefix))
            if name and '/' not in name:
                self.files[name] = 'https://zenodo.org' + p.path


def select_file(files, genre=''):
    if genre.lower() in ('dataset', 'software', 'figure', 'poster', 'presentation', 'other'):
        return dict(status='repository_non_article_record', resource_type=genre, file_count=len(files))
    links = {u for name, url in files if name.lower().endswith('.pdf')
             and not re.search(r'appendi[xc]|supplement|codebook|readme|documentation', name, re.I)
             and (u := public_pdf_url(url))}
    if len(links) == 1:
        return dict(status='pdf_link', pdf_url=links.pop(), resource_type=genre)
    return dict(status='repository_multiple_pdf_attachments' if links else 'no_primary_pdf_attachment',
                resource_type=genre, file_count=len(files))


def resolve(provider, url, read):
    p = urlsplit(url)
    if provider == 'upf':
        page = UniversityPaperLinks()
        page.feed(read(url).decode(errors='replace'))
        return select_file([(h, urljoin(url, h)) for h in page.links], 'working paper record')
    if provider == 'figshare':
        ids = re.findall(r'/(\d+)(?:/|$)', p.path + '/')
        if not ids:
            return dict(status='unknown_record_address')
        item = json.loads(read('https://api.figshare.com/v2/articles/' + ids[0]))
        if 'files' not in item:
            return dict(status='repository_attachments_unavailable', resource_type=item.get('defined_type_name', ''))
        return select_file([(f['name'], f.get('downloadUrl') or f.get('download_url')) for f in item['files']],
                           item.get('defined_type_name', ''))
    if provider == 'zenodo':
        match = re.search(r'/records?/(\d+)(?:/|$)', p.path)
        if not match:
            return dict(status='unknown_record_address')
        # The public record HTML explicitly names the attachments; its API path has different robots rules.
        landing = 'https://zenodo.org/records/' + match[1]
        page = ZenodoFiles(landing, match[1])
        page.feed(read(landing).decode(errors='replace'))
        result = select_file(page.files.items())
        if result['status'] == 'no_primary_pdf_attachment' and any(re.search(r'\.(dta|rds|csv|xlsx|parquet|sav)$', n, re.I) for n in page.files):
            result['status'] = 'repository_data_files_present'
        return result
    match = re.search(r'/handle/(\d+/\d+)$', p.path)
    if match:
        item = json.loads(read('https://dukespace.lib.duke.edu/server/api/pid/find?' + urlencode({'id': match[1]})))
        if item.get('handle') != match[1]:
            return dict(status='repository_handle_mismatch')
        uuid = item.get('uuid', '')
    else:
        uuid = p.path.rstrip('/').split('/')[-1]
    if not re.fullmatch(r'[a-f0-9-]{36}', uuid):
        return dict(status='unknown_record_address')
    args = urlencode([('embed', 'bundles'), ('embed', 'bundles/bitstreams')])
    item = json.loads(read('https://dukespace.lib.duke.edu/server/api/core/items/' + uuid + '?' + args))
    bundles = item.get('_embedded', {}).get('bundles', {}).get('_embedded', {}).get('bundles', [])
    originals = [b for b in bundles if b.get('name') == 'ORIGINAL']
    if len(originals) != 1:
        return dict(status='no_unique_original_bundle')
    listing = originals[0].get('_embedded', {}).get('bitstreams', {})
    if listing.get('page', {}).get('totalPages', 1) > 1:
        return dict(status='repository_multiple_attachment_pages')
    files = [(f['name'], f['_links']['content']['href']) for f in listing.get('_embedded', {}).get('bitstreams', [])]
    genre = next((v.get('value') for v in item.get('metadata', {}).get('dc.type', []) if v.get('value')), '')
    return select_file(files, genre)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition', type=Path, required=True)
    parser.add_argument('--providers', nargs='+', choices=sorted(PROVIDERS.values()), default=sorted(PROVIDERS.values()))
    args = parser.parse_args()
    d = args.acquisition / 'licensed-landings'
    cache = d / 'repository-cache'
    cache.mkdir(exist_ok=True)
    log = d / 'repository-records.jsonl'
    day = datetime.now(timezone.utc).date().isoformat()
    journal = [json.loads(l) for l in (d / 'resolution.jsonl').read_text().splitlines()]
    articles = [json.loads(l) for l in (args.acquisition / 'attempts.jsonl').read_text().splitlines()]
    with (d / '.repository.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        old = [json.loads(l) for l in log.read_text().splitlines()] if log.is_file() else []
        denied = {e.get('host') or e.get('http_host') or urlsplit(e['url']).hostname for e in journal + articles + old
                  if e['at'].startswith(day) and e.get('http_status') in (401, 403, 429, 503)}
        done = {e['url'] for e in old if not
                (e['provider'] == 'zenodo' and e['status'] == 'repository_robots_disallow' and not e.get('method'))
                and not (e['provider'] == 'figshare' and e.get('reason') == 'KeyError')}
        output = Lock()
        with log.open('a') as stream:
            def process(provider):
                current_host = None
                def read(url):
                    nonlocal current_host
                    current_host = urlsplit(url).hostname
                    cache_file = cache / digest(url.encode())
                    if cache_file.is_file():
                        return cache_file.read_bytes()
                    if current_host in denied:
                        raise PermissionError('deferred')
                    policy = robots(current_host)
                    if not policy.can_fetch('econ-benchmark-collector/1.0', url):
                        raise PermissionError('robots')
                    time.sleep(max(1, policy.crawl_delay('econ-benchmark-collector/1.0') or 0))
                    raw = request(url, max_bytes=3 * 1024**2, defer_denials=True,
                                  redirect_check=lambda dest: urlsplit(dest).hostname == current_host)
                    # Keep machine metadata; HTML download pages are not needed for future re-use.
                    if provider not in ('upf', 'zenodo'):
                        tmp = cache_file.with_suffix('.tmp')
                        tmp.write_bytes(raw)
                        tmp.replace(cache_file)
                    return raw
                for event in journal:
                    target = event.get('resolved_landing', '')
                    if (event['url'] in done or event['status'] not in ('no_advertised_pdf','landing_truncated')
                            or PROVIDERS.get(urlsplit(target).hostname) != provider):
                        continue
                    try:
                        result = resolve(provider, target, read)
                    except PermissionError as exc:
                        result = dict(status='repository_host_deferred' if str(exc)=='deferred' else 'repository_robots_disallow')
                    except HTTPError as exc:
                        current_host = urlsplit(exc.geturl()).hostname or current_host
                        result = dict(status='repository_http_error', http_status=exc.code)
                        if exc.code in (401, 403, 429, 503):
                            denied.add(current_host)
                        exc.close()
                    except (KeyError, TypeError, OSError, ValueError, HTTPException) as exc:
                        result = dict(status='repository_lookup_error', reason=type(exc).__name__)
                    row = dict(url=event['url'], resolved_landing=target, provider=provider, host=current_host,
                               at=datetime.now(timezone.utc).isoformat(), **result)
                    if provider == 'zenodo':
                        row['method'] = 'public_record_files'
                    with output:
                        print(json.dumps(row), file=stream, flush=True)
            with ThreadPoolExecutor(max_workers=len(set(args.providers))) as pool:
                list(pool.map(process, sorted(set(args.providers))))


if __name__ == '__main__':
    main()
