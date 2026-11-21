#!/usr/bin/env python3
"""Collect exact catalog matches from NIH's free, versioned PMC research dataset."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import md5
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
import xml.etree.ElementTree as ET

from collect_papers import JOURNALS, digest, request, save
from queue_open_papers import CC

BUCKET = 'https://pmc-oa-opendata.s3.amazonaws.com/'
EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
JOURNAL_NAMES = ['Am Econ Rev', 'Econometrica', 'J Polit Econ', 'Q J Econ', 'Rev Econ Stud']


def cached(out, url):
    path = out / 'cache' / digest(url.encode())
    if path.is_file():
        return path.read_bytes()
    raw = request(url, defer_denials=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(raw)
    tmp.replace(path)
    time.sleep(0.4 if url.startswith(EUTILS) else 0.12)
    return raw


def identify(out, catalog, prospects):
    journals = ['"' + n + '"[jour]' for n in JOURNAL_NAMES] + ['"' + n + '"' for n in JOURNALS.values()]
    term = '(' + ' OR '.join(journals) + ') AND (open_access[filter] OR author_manuscript[filter]) NOT pmc embargo[filter]'
    args = dict(db='pmc', term=term, retmode='json', retmax=10000)
    result = json.loads(cached(out, EUTILS + 'esearch.fcgi?' + urlencode(args)))['esearchresult']
    ids = result['idlist']
    if len(ids) != int(result['count']):
        raise ValueError('Incomplete PMC journal search')
    matches = {}
    for start in range(0, len(ids), 100):
        args = dict(db='pmc', id=','.join(ids[start:start + 100]), retmode='json')
        records = json.loads(cached(out, EUTILS + 'esummary.fcgi?' + urlencode(args)))['result']
        if set(records['uids']) != set(ids[start:start + 100]):
            raise ValueError('Incomplete PMC summary response')
        for uid in records['uids']:
            for item in records[uid].get('articleids', []):
                doi = item['value'].lower()
                if item['idtype'] == 'doi' and doi in catalog:
                    matches['PMC' + uid] = doi
    for doi, locs in prospects.items():
        for loc in locs:
            for key in ('pdf_url', 'landing_page'):
                p = urlsplit(loc.get(key) or '')
                if p.hostname in ('pmc.ncbi.nlm.nih.gov', 'www.ncbi.nlm.nih.gov') and (m := re.search(r'/articles/(PMC\d+)(?:/|$)', p.path)):
                    matches.setdefault(m[1], doi)
    return matches, len(ids)


def object_location(value, version_id, extension):
    p = urlsplit(value or '')
    expected = '/' + version_id + '/' + version_id + '.' + extension
    checksum = parse_qs(p.query).get('md5', [])
    if p.scheme != 's3' or p.netloc != 'pmc-oa-opendata' or p.path != expected or len(checksum) != 1 or not re.fullmatch('[0-9a-f]{32}', checksum[0]):
        raise ValueError('Unexpected PMC versioned object or checksum')
    return BUCKET.rstrip('/') + p.path, checksum[0]


def eligible_license(item):
    license_code = (item.get('license_code') or '').lower().replace(' ', '-')
    if re.fullmatch(CC, license_code) or license_code == 'tdm' and item.get('is_manuscript') is True:
        return license_code
    # The official PMC bulk dataset explicitly licenses TDM. This does not establish CC or redistribution rights.
    if not license_code and item.get('is_pmc_openaccess') is True:
        return 'pmc-dataset-tdm'
    return None


def collect_version(out, doi, version_id):
    url = BUCKET + 'metadata/' + version_id + '.json'
    item = json.loads(cached(out, url))
    res = dict(doi=doi, version_id=version_id, metadata_url=url)
    if str(item.get('doi') or '').lower() != doi or version_id != f"{item['pmcid']}.{item['version']}":
        return {**res, 'status': 'version_doi_mismatch'}
    license_code = eligible_license(item)
    if item.get('is_retracted') or not license_code:
        return {**res, 'status': 'retracted_or_no_recognized_license'}
    res.update(license=license_code, version='author-manuscript' if item['is_manuscript'] else 'published-article')
    if item.get('pdf_url'):
        res['pdf_url'], res['pdf_md5'] = object_location(item['pdf_url'], version_id, 'pdf')
    url, checksum = object_location(item['xml_url'], version_id, 'xml')
    file = out / 'articles' / (version_id + '.xml')
    raw = file.read_bytes() if file.is_file() else request(url, defer_denials=True)
    if md5(raw).hexdigest() != checksum:
        raise ValueError('PMC article XML checksum mismatch')
    article = ET.fromstring(raw)
    dois = {i.text.lower().strip() for i in article.findall('./front/article-meta/article-id') if i.get('pub-id-type') == 'doi' and i.text}
    if doi not in dois or article.find('body') is None:
        return {**res, 'status': 'jats_front_doi_or_body_unmatched'}
    if not file.is_file():
        tmp = file.with_suffix('.tmp')
        tmp.write_bytes(raw)
        tmp.replace(file)
    res.update(status='jats_candidate', file='articles/' + file.name, sha256=digest(raw), bytes=len(raw), xml_url=url)
    return res


def versions(out, pmcid, doi):
    url = BUCKET + '?' + urlencode({'list-type': 2, 'prefix': pmcid + '.', 'delimiter': '/'})
    doc = ET.fromstring(cached(out, url))
    if doc.findtext('{*}IsTruncated') != 'false':
        raise ValueError('Incomplete PMC version listing')
    ids = [p.text.rstrip('/') for p in doc.findall('{*}CommonPrefixes/{*}Prefix')]
    if any(not re.fullmatch(re.escape(pmcid) + r'\.\d+', v) for v in ids):
        raise ValueError('Invalid PMC version listing')
    return [collect_version(out, doi, v) for v in ids] or [dict(doi=doi, pmcid=pmcid, status='no_distributed_version')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--acquisition', type=Path, required=True)
    args = parser.parse_args()
    out = args.acquisition / 'pmc'
    for subdir in ('cache', 'articles'):
        (out / subdir).mkdir(exist_ok=True, parents=True)
    catalog = json.loads(args.catalog.read_text())['papers']
    prospects = json.loads((args.acquisition / 'oa-prospects.json').read_text())
    matches, search_count = identify(out, catalog, prospects)
    entries = []
    def fetch(pair):
        pmcid, doi = pair
        try:
            return versions(out, pmcid, doi)
        except HTTPError as exc:
            if exc.code not in (404, 410):
                raise
            exc.close()
            return [dict(doi=doi, pmcid=pmcid, status='missing_provider_object', http_status=exc.code)]
    with ThreadPoolExecutor(max_workers=2) as workers:
        for records in workers.map(fetch, sorted(matches.items())):
            entries.extend(records)
    summary = dict(journal_search_records=search_count, pmcids_checked=len(matches), entries=entries)
    save(out / 'sources.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'entries'}))
    print(json.dumps({'jats_acquired': sum(e['status'] == 'jats_candidate' for e in entries),
                      'pdf_locations': sum('pdf_url' in e for e in entries)}))


if __name__ == '__main__':
    main()
