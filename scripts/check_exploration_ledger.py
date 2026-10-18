#!/usr/bin/env python3
"""Check that each research iteration has a decision and bound evidence."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


FIELDS = (
    "iteration", "mode", "hypothesis", "validation", "status", "artifact",
    "artifact_sha256", "reason", "next_action",
)
STATUSES = {"keep", "discard", "inconclusive", "blocked", "crash"}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def check(root: Path, ledger: Path) -> dict:
    root = root.resolve()
    ledger = (ledger if ledger.is_absolute() else root / ledger).resolve()
    errors: list[str] = []
    try:
        ledger.relative_to(root)
    except ValueError:
        return {"valid": False, "rows": 0, "errors": ["ledger escapes project root"]}
    if not ledger.is_file():
        return {"valid": False, "rows": 0, "errors": [f"ledger does not exist: {ledger}"]}
    with ledger.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return {"valid": False, "rows": 0, "errors": ["ledger is empty"]}
        missing = sorted(set(FIELDS) - set(reader.fieldnames))
        extra = sorted(set(reader.fieldnames) - set(FIELDS))
        if missing or extra:
            errors.append(f"ledger columns mismatch: missing={missing}, extra={extra}")
        rows = list(reader)
    if not rows:
        errors.append("ledger needs at least one recorded iteration")
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        label = f"row {index}"
        if None in row or any(value is None for value in row.values()):
            errors.append(f"{label}: malformed TSV row")
            continue
        for field in FIELDS:
            if not row.get(field, "").strip():
                errors.append(f"{label}: {field} is required")
        iteration = row.get("iteration", "").strip()
        if iteration in seen:
            errors.append(f"{label}: duplicate iteration {iteration!r}")
        seen.add(iteration)
        if row.get("status", "").strip() not in STATUSES:
            errors.append(f"{label}: status must be one of {sorted(STATUSES)}")
        artifact = row.get("artifact", "").strip()
        digest = row.get("artifact_sha256", "").strip()
        if not SHA256.fullmatch(digest):
            errors.append(f"{label}: artifact_sha256 must be lowercase SHA-256")
        if not artifact:
            continue
        target = (root / artifact).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"{label}: artifact escapes project root")
            continue
        if target == ledger:
            errors.append(f"{label}: ledger cannot be its own evidence artifact")
        elif not target.is_file():
            errors.append(f"{label}: artifact does not exist: {artifact}")
        elif SHA256.fullmatch(digest) and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            errors.append(f"{label}: artifact_sha256 mismatch: {artifact}")
    return {"valid": not errors, "rows": len(rows), "errors": errors,
            "evidence_note": "Hashes bind files; they do not establish scientific validity."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = check(args.root, args.ledger)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("PASS" if report["valid"] else "FAIL")
        for error in report["errors"]:
            print(error)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
