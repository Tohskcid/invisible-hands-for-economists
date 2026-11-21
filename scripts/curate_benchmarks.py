#!/usr/bin/env python3
"""Check, freeze and export independently reviewed blind benchmark packets, case by case."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
from urllib.parse import urlsplit

from check_historical_prior_art import evaluate as historical_review


CASE_ID = re.compile(r'(?:q|b|case|task|theory|empirical)-?[0-9]{1,12}')
INPUT = re.compile(r'inputs/input-[0-9]+\.(csv|tsv|txt|dat)')
PUBLIC_KEYS = {'id', 'mode', 'question', 'conditions', 'available_inputs', 'required_outputs',
               'source_restrictions', 'neutrality_obligation'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def words(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, *, empty=False):
    return isinstance(value, list) and (empty or bool(value)) and all(words(v) for v in value)


def safe_path(root, name):
    require(words(name), 'missing relative path')
    parts = name.split('/')
    require(not any(p in ('', '.', '..') or '\\' in p for p in parts), 'unsafe relative path')
    path = root
    for part in parts:
        path = path / part
        require(not path.is_symlink(), f'symlink in {name}')
    return path


def read_json(raw):
    def distinct(pairs):
        result = dict(pairs)
        require(len(result) == len(pairs), 'duplicate JSON field')
        return result
    record = json.loads(raw.decode('utf-8'), object_pairs_hook=distinct)
    require(isinstance(record, dict), 'expected a JSON object')
    return record


def file_bytes(path):
    require(path.is_file(), f'missing regular file: {path.name}')
    return path.read_bytes()


def read_record(path):
    return read_json(file_bytes(path))


def sha(path):
    require(path.is_file(), f'missing regular file: {path.name}')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def physical_pages(pdf):
    info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, timeout=90, env={**os.environ, 'LC_ALL': 'C'})
    count = re.search(rb'^Pages:\s+(\d+)\s*$', info.stdout, re.M)
    require(info.returncode == 0 and count and int(count[1]) > 0, 'cannot determine physical PDF page count')
    return int(count[1])


def page_span(span, total):
    require(isinstance(span, list) and len(span) == 2 and all(type(i) is int for i in span)
            and 1 <= span[0] <= span[1] <= total, f'invalid physical page range for {total}-page source')
    return span


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def scan(text, identifiers, name):
    text = normalize(text)
    require(not any(needle in text for needle in identifiers), f'target identifier in {name}')
    require(not re.search(r'https?://|\bdoi\s*:|\b10\.\d{4,9}/', text), f'external link or DOI in {name}')


def public_contract(public, case_id):
    require(PUBLIC_KEYS <= set(public) <= PUBLIC_KEYS | {'data_access_status'},
            'public-task.json has missing or unapproved fields')
    if 'data_access_status' in public:
        require(words(public['data_access_status']), 'empty public data access statement')
    require(public['id'] == case_id and public['mode'] in ('theory', 'empirical', 'structural', 'mixed'), 'invalid task id or mode')
    require(all(words(public[k]) for k in ['question', 'source_restrictions', 'neutrality_obligation'])
            and strings(public['required_outputs']), 'incomplete public task')
    conditions = public['conditions']
    require(isinstance(conditions, dict) and conditions and all(words(k) and words(v) for k, v in conditions.items()),
            'conditions must map names to concrete statements')
    inputs = public['available_inputs']
    require(strings(inputs, empty=True) and len(inputs) == len(set(inputs)) and all(INPUT.fullmatch(x) for x in inputs),
            'use distinct neutral filenames under inputs/ (input-N.csv, .tsv, .txt or .dat)')
    require(public['mode'] not in ('empirical', 'mixed') or inputs, 'empirical packet has no data inputs')
    return ['public-task.json', *inputs]


def inspect_case(root, case, case_id):
    public_raw = file_bytes(safe_path(case, 'public-task.json'))
    public = read_json(public_raw)
    public_names = public_contract(public, case_id)
    paths = {name: safe_path(case, name) for name in [*public_names, 'curation.json']}
    sealed_raw = file_bytes(paths['curation.json'])
    curation = read_json(sealed_raw)
    target = curation['target']
    require(isinstance(target, dict) and words(target.get('title')) and words(target.get('doi'))
            and strings(target.get('authors')), 'missing target title, DOI or authors')
    require(all(words(curation.get(k)) for k in ['curator', 'contamination', 'appendix_check'])
            and strings(curation.get('withheld'))
            and strings(curation.get('gaps'), empty=True), 'incomplete sealed curation record')
    rubric = curation.get('rubric')
    require(isinstance(rubric, list) and rubric, 'missing scoring rubric')
    for row in rubric:
        if words(row):
            continue
        require(isinstance(row, dict) and words(row.get('id')), 'missing rubric row id')
        if 'max_score' in row:
            valid = (words(row.get('criterion')) and type(row['max_score']) in (int, float)
                     and row['max_score'] > 0 and words(row.get('scoring')))
        else:
            criteria = row.get('criteria')
            valid = (words(row.get('title')) and type(row.get('max_points')) in (int, float)
                     and row['max_points'] > 0 and isinstance(criteria, list) and criteria
                     and all(isinstance(v, dict) and words(v.get('criterion')) and
                             type(v.get('points')) in (int, float) for v in criteria))
        require(valid, 'invalid scoring rubric row')
    identifiers = [normalize(s) for s in [target['title'], target['doi'], *target['authors']]]
    scan(json.dumps(public, ensure_ascii=False), identifiers, 'public-task.json')
    inputs = public_names[1:]
    input_checks = curation['input_checks']
    require(isinstance(input_checks, dict) and set(input_checks) == set(inputs)
            and all(words(v) for v in input_checks.values()), 'each delivered input needs private provenance')
    for name in inputs:
        require(paths[name].is_file(), f'missing regular input: {name}')
        with paths[name].open(encoding='utf-8') as stream:
            nonempty = False
            for line in stream:
                require('\0' not in line, f'binary content in {name}')
                scan(line, identifiers, name)
                nonempty |= bool(line.strip())
            require(nonempty, f'empty input: {name}')
    track = curation.get('track', 'strict-historical' if inputs else 'packet-only')
    require(track in ('strict-historical', 'packet-only', 'calibration'), 'unknown evaluation track')
    require(track != 'packet-only' or not inputs, 'packet-only track cannot include external data')
    if track == 'calibration':
        require(words(public.get('data_access_status')), 'calibration requires public data availability disclosure')
        if curation['gaps']:
            limits = curation['calibration']
            missing = limits['missing_blocks']
            rubric_ids = {r['id'] for r in rubric if isinstance(r, dict)}
            require(words(limits.get('feasible_scope')) and isinstance(missing, dict)
                    and set(missing) == set(curation['gaps']) and all(v in rubric_ids for v in missing.values()),
                    'calibration gaps must identify retained scoring rubric rows and feasible scope')
    if track == 'strict-historical' or 'timeline' in curation:
        timeline = curation['timeline']
        dates = historical_review(timeline)
        require(dates['valid'], f'invalid historical timeline: {dates["errors"]}')
        materials = [v['title'] for v in timeline['comparators'] if v.get('author_material')]
        require(track != 'strict-historical' or (sorted(materials) == sorted(inputs) and not dates['unsafe_author_material']),
                'delivered inputs must have pre-target, non-target-version provenance')

    sources = curation['sources']
    require(isinstance(sources, list) and sources, 'missing original sources')
    pages = {}
    source_files = set()
    roles = []
    embedded = False
    for source in sources:
        sid = source['id']
        require(words(sid) and re.fullmatch(r'[a-z0-9][a-z0-9_-]*', sid) and sid not in pages, 'invalid source id')
        role = source['role']
        require(role in ('main', 'appendix', 'documentation'), 'invalid source role')
        roles.append(role)
        url = urlsplit(source['url'])
        require(url.scheme == 'https' and url.hostname and not url.username and not url.password
                and words(source['version']) and words(source['identity_check']), f'{sid} lacks source verification')
        original = safe_path(root, source['file'])
        require(original.is_file() and original.suffix.lower() == '.pdf' and source['sha256'] not in source_files,
                f'{sid} must be a distinct original PDF')
        source_files.add(source['sha256'])
        with original.open('rb') as pdf:
            require(pdf.read(5) == b'%PDF-', f'{sid} is not a PDF')
        total = pages[sid] = physical_pages(original)
        require(isinstance(source['reading'], list), f'invalid reading log for {sid}')
        spans = []
        for entry in source['reading']:
            span = page_span(entry['pages'], total)
            require(words(entry.get('note')), f'missing reading note for {sid} pages {span}')
            spans.append(span)
            if entry.get('appendix') is True and role == 'main':
                embedded = True
        through = 0
        for start, end in sorted(spans):
            require(start <= through + 1, f'unlogged page {through + 1} in {sid}')
            through = max(through, end)
        require(through == total, f'unlogged pages after {through} in {sid}')
        paths[f'sources/{sid}'] = original
    require(roles.count('main') == 1, 'exactly one main original is required')
    external = 'appendix' in roles
    observed = ('both' if embedded else 'external') if external else ('embedded' if embedded else 'none')
    require(curation.get('appendix_status') == observed, 'appendix inventory disagrees with logged PDF pages')

    mappings = curation['field_sources']
    require(isinstance(mappings, dict) and all(field in mappings for field in [
        'question', *(f'conditions.{k}' for k in public['conditions'])]), 'missing question or condition page mapping')
    for field, mapping in mappings.items():
        require(mapping['source'] in pages and words(mapping['reason']), f'{field} lacks a verified source or necessity reason')
        page_span(mapping['pages'], pages[mapping['source']])
    primary = next(s['id'] for s in sources if s['role'] == 'main')
    for row in rubric:
        if isinstance(row, dict) and 'pages' in row:
            sid = row.get('source', primary)
            require(sid in pages, 'rubric references an unknown source')
            page_span(row['pages'], pages[sid])
    checked = {name: sha(path) for name, path in paths.items() if name not in ('public-task.json', 'curation.json')}
    checked['public-task.json'] = hashlib.sha256(public_raw).hexdigest()
    checked['curation.json'] = hashlib.sha256(sealed_raw).hexdigest()
    for source in sources:
        require(checked[f'sources/{source["id"]}'] == source['sha256'], f'{source["id"]} original SHA-256 changed')
    return curation, paths, checked, public_names


def review_case(case, curation, checked, public_names, *, allow_hold=False):
    path = safe_path(case, 'review.json')
    raw = file_bytes(path)
    review = read_json(raw)
    require(words(review.get('reviewer')) and normalize(review['reviewer']) != normalize(curation['curator']),
            'reviewer must be identified and independent of curator')
    held = allow_hold and review.get('decision') == 'hold'
    require(held or not curation['gaps'] or curation.get('track') == 'calibration', 'curation has unresolved gaps')
    require((held or review.get('decision') == 'pass') and all(words(review.get(k)) for k in ('sufficiency', 'leakage')),
            'packet lacks a passing independent sufficiency and leakage review')
    findings = review.get('input_findings')
    require(isinstance(findings, dict) and set(findings) == set(public_names) and all(words(v) for v in findings.values()),
            'review needs readiness findings for the public task and every delivered input')
    require(review.get('checked_sha256') == checked, 'review hashes differ from the current evidence or author packet')
    return path, hashlib.sha256(raw).hexdigest()


def inventory(directory, names):
    """Check exact membership (including empty or symlinked directories) and digest each file."""
    allowed_dirs = {str(p) for n in names for p in Path(n).parents if str(p) != '.'}
    found = {}
    for path in directory.rglob('*'):
        name = path.relative_to(directory).as_posix()
        require(not path.is_symlink(), f'symlink in published directory: {name}')
        if path.is_dir():
            require(name in allowed_dirs, f'unexpected directory: {name}')
        else:
            require(name in names and path.is_file(), f'unexpected file: {name}')
            found[name] = sha(path)
    require(set(found) == set(names), 'published directory has missing files')
    return found


def verify_freeze(frozen, case_id):
    require(frozen.is_dir(), 'case has not been frozen')
    receipt_path = safe_path(frozen, 'receipt.json')
    receipt = read_record(receipt_path)
    require(receipt['id'] == case_id and words(receipt['frozen_at']), 'invalid freeze receipt')
    public_names = public_contract(read_record(safe_path(frozen, 'public/public-task.json')), case_id)
    sealed = read_record(safe_path(frozen, 'sealed/curation.json'))
    names = {*(f'public/{n}' for n in public_names), 'sealed/curation.json', 'sealed/review.json',
             *(f'sealed/sources/{s["id"]}.pdf' for s in sealed['sources'])}
    require(set(receipt['files']) == names, 'freeze receipt has missing or unapproved files')
    actual = inventory(frozen, names | {'receipt.json'})
    commitment = actual.pop('receipt.json')
    require(receipt['files'] == actual, 'frozen case SHA-256 mismatch')
    checked = {name: actual['public/' + name] for name in public_names}
    checked['curation.json'] = actual['sealed/curation.json']
    for source in sealed['sources']:
        name = 'sources/' + source['id']
        checked[name] = actual['sealed/' + name + '.pdf']
        require(checked[name] == source['sha256'], 'frozen original differs from its source receipt')
    review_case(frozen / 'sealed', sealed, checked, public_names)
    return receipt, commitment, public_names


def publish(destination, files, expected, receipt=None):
    # Destination is absent and the batch lock serializes publication. Rename on the same filesystem.
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.staging-') as tmp:
        stage = Path(tmp) / 'case'
        stage.mkdir(mode=0o700)
        for name, source in files.items():
            out = safe_path(stage, name)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, out)
        require(inventory(stage, files) == expected, 'input changed while staging')
        if receipt is not None:
            (stage / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            for path in stage.rglob('*'):
                if path.is_file():
                    path.chmod(0o400)
        stage.rename(destination)


def freeze_case(root, case, case_id, frozen):
    curation, paths, checked, public_names = inspect_case(root, case, case_id)
    review, review_sha = review_case(case, curation, checked, public_names)
    files = {f'public/{n}': paths[n] for n in public_names}
    hashes = {f'public/{n}': checked[n] for n in public_names}
    for name in checked.keys() - set(public_names):
        dest = 'sealed/' + name + ('.pdf' if name.startswith('sources/') else '')
        files[dest], hashes[dest] = paths[name], checked[name]
    files['sealed/review.json'], hashes['sealed/review.json'] = review, review_sha
    if frozen.exists():
        receipt, commitment, _ = verify_freeze(frozen, case_id)
        require(hashes == receipt['files'], 'case already frozen with different bytes; assign a new id')
    else:
        receipt = {'id': case_id, 'frozen_at': datetime.now(timezone.utc).isoformat(), 'files': dict(sorted(hashes.items()))}
        publish(frozen, files, hashes, receipt)
        _, commitment, _ = verify_freeze(frozen, case_id)
    return {'status': 'frozen', 'frozen_at': receipt['frozen_at'], 'receipt_sha256': commitment}


def export_case(frozen, case_id, author_root):
    receipt, commitment, names = verify_freeze(frozen, case_id)
    files = {n: safe_path(frozen, 'public/' + n) for n in names}
    expected = {n: receipt['files']['public/' + n] for n in names}
    dest = safe_path(author_root, case_id)
    if dest.exists():
        require(dest.is_dir() and inventory(dest, names) == expected, 'existing author directory differs from frozen packet')
    else:
        publish(dest, files, expected)
    return {'status': 'exported', 'author_dir': str(dest), 'author_sha256': expected, 'receipt_sha256': commitment}


def batch(command, manifest, author_root=None):
    require(not manifest.is_symlink(), 'manifest cannot be a symlink')
    root = manifest.resolve().parent
    entries = read_record(manifest)['cases']
    require(strings(entries) and len(entries) == len(set(entries)), 'manifest needs distinct case paths')
    ids = [p.rsplit('/', 1)[-1] for p in entries]
    require(len(ids) == len(set(ids)) and all(CASE_ID.fullmatch(i) for i in ids), 'case IDs must be neutral and distinct')
    if command == 'export':
        require(author_root is not None and not author_root.is_symlink(), 'provide a separate author root')
        author_root = author_root.resolve()
        for private in [root, Path(__file__).resolve().parents[1]]:
            require(not author_root.is_relative_to(private) and not private.is_relative_to(author_root),
                    'author root must be outside both the curator workspace and checkout')
        author_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        require(all(not p.is_symlink() and p.is_dir() and p.name in ids for p in author_root.iterdir()),
                'author root must be fresh or contain only cases from this batch')
    results = {}
    with safe_path(root, '.curation.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if command == 'freeze':
            safe_path(root, 'frozen').mkdir(mode=0o700, exist_ok=True)
        for entry, case_id in zip(entries, ids):
            try:
                case = safe_path(root, entry)
                frozen = safe_path(root, f'frozen/{case_id}')
                if command == 'inspect':
                    curation, _, checked, names = inspect_case(root, case, case_id)
                    result = {'status': 'inspected', 'checked_sha256': checked, 'author_files': names, 'gaps': curation['gaps']}
                elif command == 'freeze':
                    result = freeze_case(root, case, case_id, frozen)
                else:
                    result = export_case(frozen, case_id, author_root)
            except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
                result = {'status': 'blocked', 'reason': str(exc)}
            results[case_id] = result
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'freeze', 'export'])
    parser.add_argument('manifest', type=Path, help='private batch.json with a cases array of relative case directories')
    parser.add_argument('--author-root', type=Path, help='dedicated directory outside both checkout and curator workspace')
    args = parser.parse_args()
    if (args.command == 'export') != (args.author_root is not None):
        parser.error('--author-root is required only for export')
    try:
        results = batch(args.command, args.manifest, args.author_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Batch blocked: {exc}\n')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return int(any(v['status'] == 'blocked' for v in results.values()))


if __name__ == '__main__':
    raise SystemExit(main())
