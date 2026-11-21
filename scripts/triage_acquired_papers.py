#!/usr/bin/env python3
"""Collect page evidence for curator review of a private bulk PDF cache."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import re
import subprocess

from collect_papers import digest, save
from curate_benchmarks import physical_pages, read_record, require, safe_path, sha
from reconcile_paper_sources import normalize


VERSION = re.compile(r'working paper|discussion paper|accepted manuscript|post.print|forthcoming|arxiv:', re.I)
APPENDIX = re.compile(r'\b(?:online |web |supplemental |technical )?append(?:ix|ices)\b', re.I)
INPUTS = re.compile(r'\b(?:replication (?:data|package|files)|data availability|restricted data|confidential (?:micro)?data)\b', re.I)
JOURNAL = re.compile(r'American Economic Review|Quarterly Journal of Economics|Journal of Political Economy|Review of Economic Studies|Econometrica', re.I)


def evidence(pages, paper, doi):
    total = len(pages)
    front = normalize(' '.join(pages[:3]))
    title = normalize(paper['title'])
    names = [normalize(v).split()[-1] for v in paper.get('authors', []) if normalize(v)]
    title_match = bool(title) and f' {title} ' in f' {front} '
    byline_match = bool(names) and all(f' {name} ' in f' {front} ' for name in names)
    text_pages = [i for i, p in enumerate(pages, 1) if len(normalize(p)) >= 120]
    version_lines = [line.strip()[:210] for p in pages[:3] for line in p.splitlines() if VERSION.search(line)]
    body_starts = [n for n, p in enumerate(pages[:3], 1) if JOURNAL.search(p[:800])
                   and doi.lower() in p[:1300].lower() and title in normalize(p[:2400])
                   and not re.search(r'repository|citation\s*\n|terms of use|how to cite|to cite this version|'
                                 r'hal[ -]id|submitted on|archive ouverte', p[:1500], re.I)]
    if len(text_pages) < max(1, total // 2):
        queue = 'visual-review'
    elif not (title_match and byline_match):
        queue = 'check-title-and-byline'
    elif body_starts:
        queue = 'check-journal-layout'
    elif version_lines:
        queue = 'compare-editions'
    else:
        queue = 'check-edition'
    sample = sorted({n for n in [1, 2, 3, (total+1)//2, total-1, total] if 1 <= n <= total})
    return {'queue': queue, 'physical_pages': total, 'text_pages_with_120_characters': len(text_pages),
            'title_on_opening_pages': title_match, 'all_author_surnames_on_opening_pages': byline_match,
            'journal_layout_pages': body_starts, 'opening_version_markers': version_lines[:8],
            'appendix_mentions_on_pages': [n for n, p in enumerate(pages, 1) if APPENDIX.search(p)],
            'data_access_mentions_on_pages': [n for n, p in enumerate(pages, 1) if INPUTS.search(p)],
            'sample_pages': {str(n): {'start': ' '.join(pages[n-1].split())[:210],
                                      'end': ' '.join(pages[n-1].split())[-160:]} for n in sample}}


def triage(root, catalog, previous):
    rows = []
    for receipt in sorted((root / 'papers').glob('*/source.json')):
        try:
            receipt = safe_path(root, receipt.relative_to(root).as_posix())
            rec = read_record(receipt)
            pdf = safe_path(receipt.parent, rec['file'])
            doi = rec['doi'].lower()
            require(pdf.is_file() and sha(pdf) == rec['sha256'], 'source receipt hash mismatch')
            identity = {'doi': doi, 'title': catalog[doi]['title'], 'file': pdf.relative_to(root).as_posix(),
                        'sha256': rec['sha256'], 'url': rec['url']}
            cached = previous.get(doi)
            if cached and all(cached.get(k) == v for k, v in identity.items()):
                rows.append(cached)
                continue
            raw = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', str(pdf), '-'],
                                 capture_output=True, timeout=120, check=True)
            pages = raw.stdout.decode().split('\f')
            if pages[-1] == '':
                pages.pop()
            require(len(pages) == physical_pages(pdf), 'PDF/text page count mismatch')
            rows.append({**identity, **evidence(pages, catalog[doi], doi)})
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            rows.append({'receipt': receipt.relative_to(root).as_posix(), 'queue': 'inspection-error', 'reason': str(exc)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, required=True, help='collector cache with papers/*/source.json')
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='private JSON snapshot (contains target identities)')
    args = parser.parse_args()
    require(args.collection.is_dir() and (args.collection / 'papers').is_dir(), 'collection needs a papers directory')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        catalog_raw = args.catalog.read_bytes()
        evidence_version = digest(Path(__file__).read_bytes() + catalog_raw)
        previous = read_record(args.out) if args.out.is_file() else {}
        cache = ({row.get('doi'): row for row in previous['rows']}
                 if previous.get('evidence_version') == evidence_version else {})
        rows = triage(args.collection.resolve(), json.loads(catalog_raw)['papers'], cache)
        result = {'evidence_version': evidence_version, 'captured_at': datetime.now(timezone.utc).isoformat(), 'source_receipts': len(rows),
                  'counts': dict(Counter(row['queue'] for row in rows)),
                  'scope': 'Review leads only. Check actual final version, supplements and input availability before nomination.',
                  'rows': rows}
        save(args.out, result)
    print(json.dumps({k: result[k] for k in ('captured_at', 'source_receipts', 'counts')}))
    return int(any(row['queue'] == 'inspection-error' for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
