#!/usr/bin/env python3
"""Validate a compact, hash-bound blind review of a manuscript's central claims."""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> list[dict]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid manifest JSON on line {number}: {exc.msg}") from exc
    return records


def central_claims(manifest: list[dict]) -> set[str]:
    return {
        record["id"]
        for record in manifest
        if record.get("type") == "claim" and record.get("central") is True and isinstance(record.get("id"), str)
    }


def validate(
    review: dict,
    manuscript: Path,
    manifest_path: Path,
    manifest: list[dict],
    require_pass: bool = False,
) -> list[str]:
    errors = []
    hashes = review.get("reviewed_sha256")
    expected_hashes = {"manuscript": file_hash(manuscript), "manifest": file_hash(manifest_path)}
    if hashes != expected_hashes:
        errors.append("reviewed_sha256 must match the current manuscript and manifest")

    overall = review.get("overall_verdict")
    if overall not in {"pass", "revise", "reject"}:
        errors.append("overall_verdict must be pass, revise, or reject")
    elif require_pass and overall != "pass":
        errors.append("overall_verdict must be pass for delivery")
    gaps = review.get("global_gaps")
    if not isinstance(gaps, list) or any(not isinstance(gap, str) for gap in gaps):
        errors.append("global_gaps must be a list of strings")
    if not isinstance(review.get("uncertainty"), str):
        errors.append("uncertainty must be a string")

    entries = review.get("claim_reviews")
    if not isinstance(entries, list):
        return errors + ["claim_reviews must be a list"]
    seen = []
    allowed = {"coherent", "revise", "unsupported", "uncertain"}
    string_fields = ("weakest_link", "scope_or_number_mismatch", "competing_explanation", "required_revision")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"claim_reviews[{index}] must be an object")
            continue
        claim_id = entry.get("claim_id")
        if not isinstance(claim_id, str):
            errors.append(f"claim_reviews[{index}].claim_id must be a string")
        else:
            seen.append(claim_id)
        if entry.get("verdict") not in allowed:
            errors.append(f"claim_reviews[{index}].verdict is invalid")
        for field in string_fields:
            if not isinstance(entry.get(field), str):
                errors.append(f"claim_reviews[{index}].{field} must be a string")

    expected = central_claims(manifest)
    if not expected:
        errors.append("manifest contains no central claims to review")
    if set(seen) != expected or len(seen) != len(expected):
        errors.append("claim_reviews must cover every central claim exactly once")
    if overall == "pass":
        if any(entry.get("verdict") != "coherent" for entry in entries if isinstance(entry, dict)):
            errors.append("a passing review requires every central claim to be coherent")
        if any(entry.get("required_revision") for entry in entries if isinstance(entry, dict)):
            errors.append("a passing review cannot contain required revisions")
        if isinstance(gaps, list) and gaps:
            errors.append("a passing review cannot contain global gaps")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        review = json.loads(args.review.read_text(encoding="utf-8"))
        errors = validate(review, args.manuscript, args.manifest, manifest, args.require_pass)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    result = {"passed": not errors, "errors": errors}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif errors:
        for error in errors:
            print(f"[Error] {error}", file=sys.stderr)
    else:
        print("Logic review passed.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
