#!/usr/bin/env python3
"""Find advertised PDF links on explicitly licensed OpenAlex landing pages."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from urllib.parse import urljoin, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

from collect_papers import save
from queue_open_papers import CC, public_pdf_url, robots

DENIAL_CODES = {401, 403, 429, 503}
PAGE_LIMIT = 2 * 1024 * 1024


class PdfLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and (attrs.get('name') or '').lower() == 'citation_pdf_url' and attrs.get('content'):
            self.links.add(attrs['content'])
        if (tag == 'link' and (attrs.get('type') or '').lower() == 'application/pdf'
                and 'alternate' in (attrs.get('rel') or '').lower().split() and attrs.get('href')):
            self.links.add(attrs['href'])


class ExplicitRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def licensed_queue(prospects):
    queue = {}
    for doi, locations in prospects.items():
        for loc in locations:
            if not loc.get('pdf_url') and loc.get('landing_page') and re.fullmatch(CC, loc.get('license') or ''):
                queue.setdefault(doi, []).append(dict(url=loc['landing_page'], license=loc['license'], version=loc.get('version')))
    return queue


class Resolver:
    def __init__(self, denied):
        self.denied = denied
        self.hosts = defaultdict(Lock)
        self.next_request = defaultdict(float)
        self.locks = Lock()
        self.opener = build_opener(ExplicitRedirect)

    def fetch(self, url):
        host = urlsplit(url).hostname
        with self.locks:
            lock = self.hosts[host]
        with lock:
            if host in self.denied:
                return dict(status='host_deferred', host=host, http_status=self.denied[host])
            try:
                policy = robots(urlsplit(url).netloc)
                if not policy.can_fetch('econ-benchmark-collector/1.0', url):
                    return dict(status='robots_disallow', host=host)
                time.sleep(max(0, self.next_request[host] - time.monotonic()))
                self.next_request[host] = time.monotonic() + max(1, policy.crawl_delay('econ-benchmark-collector/1.0') or 0)
                req = Request(url, headers={'User-Agent': 'econ-benchmark-collector/1.0'})
                with self.opener.open(req, timeout=12) as response:
                    content_type = response.headers.get_content_type()
                    if content_type == 'application/pdf':
                        return dict(status='pdf_link', pdf_url=url) if response.read(5) == b'%PDF-' else dict(status='invalid_pdf')
                    if content_type not in ('text/html', 'application/xhtml+xml'):
                        if content_type == 'application/octet-stream' and response.read(5) == b'%PDF-':
                            return dict(status='pdf_link', pdf_url=url)
                        return dict(status='other_media')
                    raw = response.read(PAGE_LIMIT)
                    parser = PdfLinks()
                    parser.feed(raw.decode(response.headers.get_content_charset() or 'utf-8', errors='replace'))
                    links = {public_pdf_url(urljoin(url, link)) for link in parser.links} - {None}
                    if len(links) == 1:
                        return dict(status='pdf_link', pdf_url=links.pop())
                    if links:
                        return dict(status='ambiguous_pdf_links')
                    return dict(status='landing_truncated' if len(raw) == PAGE_LIMIT else 'no_advertised_pdf')
            except HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308) and exc.headers.get('Location'):
                    result = dict(status='redirect', url=public_pdf_url(urljoin(url, exc.headers['Location'])))
                else:
                    if exc.code in DENIAL_CODES:
                        self.denied[host] = exc.code
                    result = dict(status='http_error', http_status=exc.code, host=host)
                exc.close()
                return result
            except (OSError, ValueError, HTTPException, LookupError) as exc:
                return dict(status='resolution_error', reason=type(exc).__name__, host=host)

    def resolve(self, start):
        url, seen = start, set()
        while url and url not in seen and len(seen) < 6:
            seen.add(url)
            result = self.fetch(url)
            if result['status'] != 'redirect':
                return {**result, 'resolved_landing': url}
            url = result['url']
        return dict(status='unusable_redirect')


def run(acquisition, workers, limit):
    out = acquisition / 'licensed-landings'
    out.mkdir(exist_ok=True)
    queue = licensed_queue(json.loads((acquisition / 'oa-prospects.json').read_text()))
    save(out / 'queue.json', queue)
    log = out / 'resolution.jsonl'
    old = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    today = datetime.now(timezone.utc).date().isoformat()
    denied = {}
    articles = [json.loads(line) for line in (acquisition / 'attempts.jsonl').read_text().splitlines()]
    for e in articles + old:
        if e['at'].startswith(today) and e.get('http_status') in DENIAL_CODES:
            denied[e.get('host') or e.get('http_host') or urlsplit(e['url']).hostname] = e['http_status']
    resolver = Resolver(denied)
    done = {e['url'] for e in old if e['status'] != 'host_deferred' or e['at'].startswith(today)}
    hosts = defaultdict(list)
    urls = {l['url'] for ls in queue.values() for l in ls}
    for url in sorted(urls - done):
        hosts[urlsplit(url).hostname].append(url)
    ordered = []
    for i in range(max(map(len, hosts.values()), default=0)):
        ordered.extend(group[i] for group in hosts.values() if len(group) > i)
    with log.open('a') as records, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(resolver.resolve, url): url for url in ordered[:limit]}
        for future in as_completed(futures):
            url = futures[future]
            e = dict(at=datetime.now(timezone.utc).isoformat(), url=url, **future.result())
            print(json.dumps(e), file=records, flush=True)
            old.append(e)
    latest = {e['url']: e for e in old}
    summary = dict(doi_count=len(queue), doi_url_pairs=sum(len({l['url'] for l in ls}) for ls in queue.values()),
                   distinct_landings=len(urls), processed=len(urls & latest.keys()),
                   outcomes=dict(Counter(latest[u]['status'] for u in urls & latest.keys())))
    save(out / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=5)
    parser.add_argument('--limit', type=int, default=10000)
    args = parser.parse_args()
    with (args.acquisition / '.landing-resolution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(run(args.acquisition, args.workers, args.limit), indent=2))


if __name__ == '__main__':
    main()
