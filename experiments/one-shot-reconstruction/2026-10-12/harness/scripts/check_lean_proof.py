#!/usr/bin/env python3
"""Verify a Lean file or a locked theorem task without proof escapes."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ESCAPE_PATTERN = re.compile(r"\b(sorry|admit|sorryAx|axiom)\b")
LEAN_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")
LEAN_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'.]*$")
IMPORT_COMMAND = re.compile(r"(?m)^\s*import\b")
HASH_FIELDS = {"statement_sha256", "task_sha256"}
HARNESS_NAME = "EconResearchHarness.target"
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def strip_comments_and_strings(source: str) -> str:
    """Blank Lean strings and nested comments while retaining executable text."""
    output, index, block_depth = [], 0, 0
    while index < len(source):
        pair = source[index : index + 2]
        if block_depth:
            if pair == "/-":
                block_depth += 1
                index += 2
            elif pair == "-/":
                block_depth -= 1
                index += 2
            else:
                index += 1
            output.append(" ")
            continue
        if pair == "/-":
            block_depth = 1
            output.append(" ")
            index += 2
            continue
        if pair == "--":
            end = source.find("\n", index)
            if end == -1:
                break
            output.append("\n")
            index = end + 1
            continue
        if source[index] == '"':
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            output.append(" ")
            continue
        output.append(source[index])
        index += 1
    return "".join(output)


def proof_escapes(source: str) -> list[str]:
    return sorted(set(ESCAPE_PATTERN.findall(strip_comments_and_strings(source))))


def compiler_command(path: Path) -> list[str]:
    if shutil.which("lake"):
        return ["lake", "env", "lean", str(path)]
    if shutil.which("lean"):
        return ["lean", str(path)]
    raise FileNotFoundError("Lean 4 is unavailable; install Lean 4 + Mathlib before claiming a formal proof")


def digest(value: str) -> str:
    return hashlib.sha256(value.replace("\r\n", "\n").strip().encode()).hexdigest()


def task_digest(task: dict) -> str:
    payload = {key: value for key, value in task.items() if key not in HASH_FIELDS}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def load_task(path: Path) -> dict:
    task = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(task, dict):
        raise ValueError("task must be a JSON object")
    return task


def validate_task(task: dict) -> None:
    required = ("version", "theorem_name", "source_statement", "formalization_status", "assumptions", "statement", "imports", "allowed_axioms", "timeout_seconds", "statement_sha256", "task_sha256")
    missing = [field for field in required if field not in task]
    if missing:
        raise ValueError(f"task missing: {', '.join(missing)}")
    if task["version"] != 1:
        raise ValueError("unsupported task version")
    if not LEAN_NAME.fullmatch(task["theorem_name"]):
        raise ValueError("theorem_name must be a simple Lean identifier")
    if not isinstance(task["source_statement"], str) or not task["source_statement"].strip():
        raise ValueError("source_statement must be non-empty")
    if task["formalization_status"] != "approved":
        raise ValueError("formalization_status must be approved before proof search")
    if not isinstance(task["assumptions"], list) or not all(isinstance(item, str) for item in task["assumptions"]):
        raise ValueError("assumptions must be a list of strings")
    if not isinstance(task["statement"], str) or not task["statement"].strip():
        raise ValueError("statement must be a non-empty Lean type")
    if not isinstance(task["imports"], list) or not all(isinstance(item, str) and LEAN_MODULE.fullmatch(item) for item in task["imports"]):
        raise ValueError("imports must contain Lean module names")
    if not isinstance(task["allowed_axioms"], list) or not all(isinstance(item, str) and LEAN_MODULE.fullmatch(item) for item in task["allowed_axioms"]):
        raise ValueError("allowed_axioms must contain Lean declaration names")
    unsupported_axioms = sorted(set(task["allowed_axioms"]) - STANDARD_AXIOMS)
    if unsupported_axioms:
        raise ValueError(f"allowed_axioms contains nonstandard axioms: {', '.join(unsupported_axioms)}")
    if not isinstance(task.get("preamble", ""), str):
        raise ValueError("preamble must be a string")
    if IMPORT_COMMAND.search(task.get("preamble", "")):
        raise ValueError("put imports in the explicit imports list, not preamble")
    if isinstance(task["timeout_seconds"], bool) or not isinstance(task["timeout_seconds"], int) or not 1 <= task["timeout_seconds"] <= 600:
        raise ValueError("timeout_seconds must be an integer from 1 to 600")
    if proof_escapes(task.get("preamble", "")):
        raise ValueError("preamble contains a proof escape or axiom declaration")
    if task["statement_sha256"] != digest(task["statement"]):
        raise ValueError("statement hash mismatch")
    if task["task_sha256"] != task_digest(task):
        raise ValueError("task hash mismatch")


def lock_task(path: Path) -> dict:
    task = load_task(path)
    task["statement_sha256"] = digest(str(task.get("statement", "")))
    task["task_sha256"] = task_digest(task)
    validate_task(task)
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return task


def build_source(task: dict, proof: str) -> str:
    imports = "\n".join(f"import {module}" for module in task["imports"])
    preamble = task.get("preamble", "").strip()
    blocks = [block for block in (imports, preamble) if block]
    blocks.append(
        "namespace EconResearchHarness\n"
        f"theorem target : ({task['statement'].strip()}) := (\n{proof.strip()}\n)\n"
        f"#print axioms {HARNESS_NAME}\n"
        "end EconResearchHarness"
    )
    return "\n\n".join(blocks) + "\n"


def parse_axioms(output: str) -> list[str] | None:
    if re.search(r"EconResearchHarness\.target['\"]? does not depend on any axioms", output):
        return []
    match = re.search(r"EconResearchHarness\.target['\"]? depends on axioms:\s*\[([^]]*)\]", output)
    if not match:
        return None
    return sorted(item.strip() for item in match.group(1).split(",") if item.strip())


def blocked_result(message: str) -> dict:
    return {"status": "blocked", "formally_proved": False, "diagnostic": message}


def run_locked_task(task_path: Path, proof_path: Path) -> dict:
    try:
        task = load_task(task_path)
        validate_task(task)
        proof = proof_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "rejected", "formally_proved": False, "diagnostic": str(exc)}
    escapes = proof_escapes(proof)
    if escapes:
        return {"status": "rejected", "formally_proved": False, "diagnostic": f"proof escape(s): {', '.join(escapes)}"}

    project_dir = (task_path.resolve().parent / task.get("project_dir", ".")).resolve()
    if not project_dir.is_dir():
        return blocked_result(f"project directory not found: {project_dir}")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=".econ-proof-", dir=project_dir) as temporary:
        generated = Path(temporary) / "Candidate.lean"
        generated.write_text(build_source(task, proof), encoding="utf-8")
        try:
            command = compiler_command(generated)
        except FileNotFoundError as exc:
            return blocked_result(str(exc))
        try:
            completed = subprocess.run(
                command,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=task["timeout_seconds"],
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "status": "timeout",
                "formally_proved": False,
                "diagnostic": f"Lean exceeded {task['timeout_seconds']} seconds",
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
            }

    output = completed.stdout + "\n" + completed.stderr
    used_axioms = parse_axioms(output) if completed.returncode == 0 else None
    unexpected = sorted(set(used_axioms or []) - set(task["allowed_axioms"]))
    if completed.returncode != 0:
        status, diagnostic = "failed", "Lean rejected the candidate"
    elif used_axioms is None:
        status, diagnostic = "rejected", "axiom audit output was missing"
    elif unexpected:
        status, diagnostic = "rejected", f"unapproved axiom(s): {', '.join(unexpected)}"
    else:
        status, diagnostic = "formally_proved", "kernel accepted the locked statement and axiom audit"
    return {
        "status": status,
        "formally_proved": status == "formally_proved",
        "theorem_name": task["theorem_name"],
        "statement_sha256": task["statement_sha256"],
        "task_sha256": task["task_sha256"],
        "proof_sha256": digest(proof),
        "used_axioms": used_axioms,
        "unexpected_axioms": unexpected,
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "command": command,
        "diagnostic": diagnostic,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def emit(result: dict, as_json: bool, artifact: Path | None) -> int:
    if artifact:
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    visible = dict(result)
    for field in ("stdout", "stderr"):
        value = visible.get(field, "")
        if len(value) > 4000:
            visible[field] = value[:4000] + "\n[truncated; full output is in the artifact]"
    if as_json:
        print(json.dumps(visible, ensure_ascii=False, indent=2))
    else:
        print(f"[{result['status']}] {result['diagnostic']}")
        if result.get("stderr"):
            print(visible["stderr"], file=sys.stderr, end="")
    return 0 if result.get("formally_proved") or result["status"] == "locked" else 3 if result["status"] == "blocked" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, help="legacy full Lean source file")
    parser.add_argument("--task", type=Path, help="locked proof-task JSON")
    parser.add_argument("--proof", type=Path, help="candidate Lean proof term")
    parser.add_argument("--lock-task", type=Path, help="write hashes into a proof-task JSON, then exit")
    parser.add_argument("--artifact", type=Path, help="write the complete verification result as JSON")
    parser.add_argument("--json", action="store_true", help="print structured verification output")
    parser.add_argument("--timeout", type=int, default=60, help="legacy mode timeout in seconds")
    args = parser.parse_args()

    if args.lock_task:
        try:
            task = lock_task(args.lock_task)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return emit({"status": "rejected", "formally_proved": False, "diagnostic": str(exc)}, args.json, args.artifact)
        result = {"status": "locked", "formally_proved": False, "diagnostic": "proof task hashes written", "statement_sha256": task["statement_sha256"], "task_sha256": task["task_sha256"]}
        return emit(result, args.json, args.artifact)

    if args.task or args.proof:
        if not args.task or not args.proof:
            parser.error("--task and --proof must be used together")
        return emit(run_locked_task(args.task, args.proof), args.json, args.artifact)

    if not args.file:
        parser.error("provide FILE or use --task with --proof")
    if not args.file.is_file():
        print(f"[Error] File not found: {args.file}", file=sys.stderr)
        return 2
    escapes = proof_escapes(args.file.read_text(encoding="utf-8"))
    if escapes:
        print(f"[Error] Proof escape(s) found: {', '.join(escapes)}", file=sys.stderr)
        return 2
    try:
        completed = subprocess.run(compiler_command(args.file), timeout=args.timeout, check=False)
    except FileNotFoundError as exc:
        print(f"[Blocked] {exc}", file=sys.stderr)
        return 3
    except subprocess.TimeoutExpired:
        print(f"[Error] Lean exceeded {args.timeout} seconds", file=sys.stderr)
        return 2
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
