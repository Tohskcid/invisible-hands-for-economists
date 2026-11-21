#!/usr/bin/env python3
"""Write one manuscript from an independently frozen, exported task."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from blind_agent_turn import account_environment, check_completion, run_turn
from curate_benchmarks import inventory, require, sha, verify_freeze


GUIDANCE = Path(__file__).resolve().parents[1] / 'references/reconstruction_coverage.md'
COMMON = """Write a complete, self-contained economics working paper in English addressing the released task. Include substantive arguments and derivations, assumptions and boundaries, and an honest statement of missing components. Put a brief disclosure of recognition or recollection at the top as a LaTeX comment, and do not use recollection of the target as evidence. Use only the supplied task and permitted inputs. No external literature, network, additional agents or search for a target. Do not mention a treatment assignment. Return one compilable LaTeX article delimited by \\documentclass and \\end{document}, without Markdown. Place the recognition comment immediately after the documentclass line."""


def data_turn(prompt, work, model, timeout):
    """Data authors use a fresh writable directory and the existing research CLI sandbox."""
    args = ['codex', 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check', '--json',
            '-s', 'workspace-write', '--disable', 'multi_agent', '-m', model, '-C', str(work),
            '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="medium"', '-']
    start = datetime.now(timezone.utc)
    result = subprocess.run(args, cwd=work, input=prompt, text=True, capture_output=True, timeout=timeout, env=account_environment())
    check_completion(result)
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    done = [e for e in events if e['type'] == 'turn.completed']
    sessions = [e['thread_id'] for e in events if e['type'] == 'thread.started']
    require(len(done) == len(sessions) == 1, 'missing completed data author session')
    calls = [e['item']['type'] for e in events if e['type'] == 'item.completed']
    require(set(calls) <= {'command_execution', 'file_change', 'agent_message', 'reasoning'},
            'unexpected author tool; review data exposure before using manuscript')
    finish = datetime.now(timezone.utc)
    return {'model': model, 'reasoning': 'medium', 'start_utc': start.isoformat(), 'end_utc': finish.isoformat(),
            'elapsed_seconds': (finish-start).total_seconds(), 'deadline_seconds': timeout, 'usage': done[0]['usage'],
            'tool_calls': sum(c not in ('agent_message','reasoning') for c in calls),
            'events_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(),
            'session_sha256': hashlib.sha256(sessions[0].encode()).hexdigest(),
            'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()}, result.stdout


def write(frozen, packet, output, condition, model, timeout):
    receipt, commitment, files = verify_freeze(frozen, packet.name)
    expected = {n:receipt['files']['public/' + n] for n in files}
    require(not packet.is_symlink() and inventory(packet, files) == expected, 'export differs from freeze')
    require(not output.exists() and not output.is_symlink(), 'use a fresh output directory')
    task = (packet/'public-task.json').read_text()
    guide = GUIDANCE.read_text() if condition == 'coverage' else ''
    prompt = COMMON + '\n\n' + guide + '\n\nReleased task:\n' + task
    output.parent.mkdir(exist_ok=True, parents=True)
    output.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix='research-author-') as tmp:
        work = Path(tmp)
        if len(files) == 1:
            text, run = run_turn(prompt + '\nNo tools. Return your manuscript as your final response.',
                                 work, model=model, timeout=timeout)
            if text.startswith('```') and text.endswith('```'):
                text = '\n'.join(text.splitlines()[1:-1])
            require(text.lstrip().startswith(r'\documentclass') and text.rstrip().endswith(r'\end{document}'),
                    'author did not return a complete LaTeX file')
            (output/'manuscript.tex').write_text(text.strip()+'\n')
        else:
            for name in files:
                dest = work/name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(packet/name, dest)
            prompt += ('\nRead and write only inside this directory. Reconstruct the analysis from inputs, run it, '
                       'save self-contained Python analysis.py and numeric results.json, and write the final paper '
                       'to manuscript.tex. Use the provided filenames and assemble all publishable tables in the TeX.')
            try:
                run, trace = data_turn(prompt, work, model, timeout)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                partial = output / 'incomplete'
                partial.mkdir(mode=0o700)
                for name in ('manuscript.tex', 'analysis.py', 'results.json'):
                    path = work / name
                    if path.is_file() and not path.is_symlink():
                        shutil.copyfile(path, partial / name)
                raise
            (output/'events.private.jsonl').write_text(trace)
            require(all(not (work/n).is_symlink() and sha(work/n)==v for n,v in expected.items()), 'input changed')
            for name in ['manuscript.tex','analysis.py','results.json']:
                path = work/name
                require(path.is_file() and not path.is_symlink() and path.stat().st_size, f'missing {name}')
                shutil.copyfile(path, output/name)
            json.loads((output/'results.json').read_text())
    run.update({'condition':condition, 'release_receipt_sha256':commitment, 'author_input_sha256':expected,
                'guidance_sha256':hashlib.sha256(guide.encode()).hexdigest() if guide else None,
                'output_sha256':{p.name:sha(p) for p in sorted(output.iterdir()) if p.name!='events.private.jsonl'}})
    (output/'receipt.json').write_text(json.dumps(run,indent=2)+'\n')
    return run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('frozen','packet','output'):
        p.add_argument(n,type=Path)
    p.add_argument('--condition',choices=('standard','coverage'),default='standard')
    p.add_argument('--model',default='gpt-6.2-astra')
    p.add_argument('--timeout',type=int,default=480)
    a=p.parse_args()
    try:
        r=write(a.frozen,a.packet,a.output,a.condition,a.model,a.timeout)
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        p.exit(1,f'Author incomplete: {exc}\n')
    print(json.dumps({'status':'submitted','outputs':r['output_sha256']}))


if __name__=='__main__':
    main()
