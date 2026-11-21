#!/usr/bin/env python3
"""Rebuild a submitted paper and replay its analysis against the frozen author inputs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from check_latex import engine_commands
from curate_benchmarks import read_record, require, sha, verify_freeze
from run_replication import run_replication


def verify(frozen, submission, output):
    _, commitment, names = verify_freeze(frozen, frozen.name)
    receipt = read_record(submission / 'receipt.json')
    require(receipt['release_receipt_sha256'] == commitment, 'wrong frozen packet')
    require('manuscript.tex' in receipt['output_sha256'], 'missing manuscript commitment')
    output.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, digest in receipt['output_sha256'].items():
            require(name in ('manuscript.tex', 'analysis.py', 'results.json') and sha(submission / name) == digest,
                    'unverified submission file')
            shutil.copyfile(submission / name, root / name)
        for name in names:
            dest = root / name
            dest.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(frozen / 'public' / name, dest)
        if 'analysis.py' in receipt['output_sha256']:
            replay = run_replication(root, [['codex', 'sandbox', '-P', ':workspace', '--',
                                            sys.executable, '-I', 'analysis.py']],
                                     names, ['results.json'], Path('results.json'), timeout=180)
            checked = {'clean_data_replay': replay['reproducible'], 'replay_errors': replay['errors']}
        else:
            checked = {'clean_data_replay': None, 'replay_errors': []}
        env = {**os.environ, 'openin_any': 'p', 'openout_any': 'p'}
        for command in engine_commands('pdflatex', root / 'manuscript.tex', root):
            try:
                result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=90)
                checked['tex_exit'] = result.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                checked['tex_error'] = type(exc).__name__
                break
            if result.returncode:
                break
        if checked.get('tex_exit') == 0 and (root / 'manuscript.pdf').is_file():
            shutil.copyfile(root / 'manuscript.pdf', output / 'manuscript.pdf')
            checked['pdf_sha256'] = sha(output / 'manuscript.pdf')
    (output / 'verification.json').write_text(json.dumps(checked, indent=2) + '\n')
    return checked


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('frozen', 'submission', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.frozen, args.submission, args.output)))
