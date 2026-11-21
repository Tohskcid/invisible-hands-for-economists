"""Run one answer-only Codex turn for a reconstruction experiment."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

PLAN_LIMIT = 'existing account usage limit reached; preserve progress without purchasing credits'


def account_environment():
    """Use the existing plan for this workflow; do not fall back to a metered API key."""
    env = os.environ.copy()
    for name in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
        env.pop(name, None)
    status = subprocess.run(['codex', 'login', 'status'], env=env, capture_output=True, text=True, timeout=20)
    if status.returncode or 'chatgpt' not in (status.stdout + status.stderr).lower():
        raise RuntimeError('existing ChatGPT plan required; preserve progress until it is available')
    return env


def check_completion(result):
    if result.returncode:
        failure = (result.stdout + result.stderr).lower()
        if any(token in failure for token in ('usage limit', 'insufficient_quota', 'usage_limit_reached')):
            raise RuntimeError(PLAN_LIMIT)
        if any(token in failure for token in ('context_length_exceeded', 'maximum context length', 'context window exceeded')):
            raise RuntimeError('source evidence exceeded the installed model context; split the review and retain page receipts')
        raise RuntimeError(f'Codex exited {result.returncode}; no usable submission')


def run_turn(prompt, cwd, *, images=(), model='gpt-6.2-astra', timeout=480):
    """Return the final text and a receipt. Reject tool activity or incomplete turns."""
    cwd = Path(cwd).resolve()
    if any(cwd.iterdir()):
        raise ValueError('expected an empty, dedicated working directory')
    args = ['codex', 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check',
            '--json', '-s', 'read-only', '--disable', 'shell_tool', '--disable', 'unified_exec',
            '--disable', 'multi_agent', '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="medium"',
            '-m', model, '-C', str(cwd)]
    for source in images:
        args.extend(['-i', str(Path(source).resolve())])
    started = datetime.now(timezone.utc).isoformat()
    initial = time.monotonic()
    result = subprocess.run([*args, '-'], input=prompt, cwd=cwd, capture_output=True,
                            text=True, timeout=timeout, env=account_environment())
    check_completion(result)
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    messages = []
    usage = session = None
    for event in events:
        typ = event['type']
        if typ in ('turn.failed', 'error'):
            raise ValueError('agent turn failed')
        if typ == 'thread.started':
            session = event['thread_id']
        if typ == 'turn.completed':
            usage = event['usage']
        item = event.get('item')
        if item and item['type'] not in ('reasoning', 'agent_message'):
            raise ValueError('unexpected tool activity in blind turn')
        if typ == 'item.completed' and item['type'] == 'agent_message':
            messages.append(item['text'])
    if not session or usage is None or not messages or not messages[-1].strip():
        raise ValueError('missing completed turn or final text')
    receipt = {'start_utc': started, 'end_utc': datetime.now(timezone.utc).isoformat(),
               'elapsed_seconds': round(time.monotonic() - initial, 2), 'deadline_seconds': timeout,
               'model': model, 'reasoning': 'medium', 'tool_calls': 0, 'usage': usage,
               'session_sha256': hashlib.sha256(session.encode()).hexdigest(),
               'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'events_sha256': hashlib.sha256(result.stdout.encode()).hexdigest()}
    return messages[-1].strip(), receipt
