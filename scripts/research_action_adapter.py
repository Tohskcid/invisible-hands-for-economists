#!/usr/bin/env python3
"""Execute one explicit Dream-RSI command action without invoking a shell."""

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath


def execute(request: dict) -> dict:
    action = request.get("action", {})
    payload = action.get("payload", {})
    command = payload.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("action payload.command must be a non-empty list of strings")
    root = Path(request.get("root", ".")).resolve()
    cwd_value = payload.get("cwd", ".")
    cwd_path = PurePosixPath(cwd_value) if isinstance(cwd_value, str) else None
    if cwd_path is None or cwd_path.is_absolute() or ".." in cwd_path.parts:
        raise ValueError("action payload.cwd must stay below the research root")
    completed = subprocess.run(
        command,
        cwd=root.joinpath(*cwd_path.parts),
        capture_output=True,
        text=True,
        timeout=int(payload.get("timeout", 3600)),
        check=False,
    )
    return {
        "status": "complete" if completed.returncode == 0 else "failed",
        "cost": action.get("estimated_cost", 0),
        "artifact": payload.get("artifact"),
        "next_actions": payload.get("next_actions", []),
        "referee_vulnerabilities": payload.get("referee_vulnerabilities", []),
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
    }


def main() -> int:
    try:
        result = execute(json.load(sys.stdin))
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        result = {"status": "failed", "cost": 0, "next_actions": [], "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
