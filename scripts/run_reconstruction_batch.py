#!/usr/bin/env python3
"""Read, review, freeze, write and score each verified candidate independently."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import tempfile

from blind_agent_turn import PLAN_LIMIT
from collect_papers import save
from curate_benchmarks import CASE_ID, batch, read_record, require, safe_path, sha
from read_benchmarks import run as read_candidates
from score_reconstruction import score
from verify_reconstruction_output import verify
from write_from_packet import write


def process(root, candidate, folder, model):
    key = candidate['id']
    with tempfile.TemporaryDirectory() as export, tempfile.NamedTemporaryFile(
        mode='w+', dir=root, suffix='.json'
    ) as selected:
        single = Path(selected.name)
        json.dump({'cases': [candidate]}, selected)
        selected.flush()
        entry = read_candidates(single, model)[key]
        if entry['status'] != 'review-pass':
            return entry

        selected.seek(0)
        selected.truncate()
        json.dump({'cases': ['cases/' + key]}, selected)
        selected.flush()
        for action in ('freeze', 'export'):
            result = batch(action, single, Path(export) if action == 'export' else None)[key]
            require(result['status'] != 'blocked', result.get('reason', 'release failed'))

        frozen = root / 'frozen' / key
        submitted = safe_path(folder, 'author')
        if not (submitted / 'receipt.json').exists():
            if submitted.exists():
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                submitted.rename(folder / ('incomplete-' + timestamp))
            write(frozen, Path(export) / key, submitted, 'standard', model, 480)
        receipt = read_record(submitted / 'receipt.json')
        require(receipt['release_receipt_sha256'] == sha(frozen / 'receipt.json'),
                'existing submission used a different freeze')
        checks = verify(frozen, submitted, safe_path(folder, 'verification'))
        scores = score(frozen, submitted, safe_path(folder, 'review'), model=model)
        complete = (scores['met_frozen_rubric'] and bool(checks.get('pdf_sha256'))
                    and ('analysis.py' not in receipt['output_sha256'] or checks['clean_data_replay'] is True))
        return {'status': 'scored', 'scores': scores, 'verification': checks,
                'verified_full_rubric_and_artifacts': complete}


def run(manifest, results, model):
    root = manifest.resolve().parent
    candidates = read_record(manifest)['cases']
    ids = [candidate['id'] for candidate in candidates]
    require(ids and len(ids) == len(set(ids)) and all(CASE_ID.fullmatch(k) for k in ids), 'invalid case IDs')
    results.mkdir(mode=0o700, parents=True, exist_ok=True)
    statuses = {}
    for candidate in candidates:
        key = candidate['id']
        folder = safe_path(results, key)
        folder.mkdir(mode=0o700, exist_ok=True)
        with safe_path(folder, '.dispatch.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                statuses[key] = {'status': 'already_running'}
                continue
            try:
                status = process(root, candidate, folder, model)
            except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
                status = {'status': 'blocked', 'reason': str(exc)}
            save(safe_path(folder, 'status.json'), status)
            statuses[key] = status
            print(json.dumps({key: status}), flush=True)
            if status.get('reason') == PLAN_LIMIT:
                break
    return statuses


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, help='private verified candidate manifest')
    parser.add_argument('results', type=Path, help='private working directory')
    parser.add_argument('--model', default='gpt-6.2-astra')
    args = parser.parse_args()
    result = run(args.manifest, args.results, args.model)
    raise SystemExit(any(item['status'] != 'scored' for item in result.values()))
