#!/usr/bin/env python3
"""Bind manuscript numbers to a structured results file and its exact hash."""

import argparse
import hashlib
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath


KEY = r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
MARKDOWN_BINDING = re.compile(rf"(?P<value>{NUMBER})\s*\[result:(?P<key>{KEY})\]")
LATEX_BINDING = re.compile(rf"\\result\{{(?P<key>{KEY})\}}\{{(?P<value>{NUMBER})\}}")
HASH_MARKER = re.compile(r"\[results-sha256:([0-9a-f]{64})\]")
HASH = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: Path) -> dict:
    def reject_constant(value: str):
        raise ValueError(f"non-finite JSON number {value}")

    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError("results file must contain a JSON object")
    return value


def flatten_results(document: dict, root: Path | None = None) -> tuple[dict[str, float | int], list[str]]:
    errors: list[str] = []
    if document.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    if not isinstance(document.get("run_id"), str) or not document["run_id"].strip():
        errors.append("run_id must be a non-empty string")
    sources = document.get("source_sha256")
    if not isinstance(sources, dict) or not sources:
        errors.append("source_sha256 must be a non-empty object")
    else:
        for name, digest in sources.items():
            if not isinstance(name, str) or not name or not isinstance(digest, str) or not HASH.fullmatch(digest):
                errors.append("source_sha256 keys must be non-empty and values must be lowercase SHA-256 digests")
                break
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"source_sha256 has unsafe path {name!r}")
            elif root is not None:
                source = root.joinpath(*path.parts)
                if not source.is_file():
                    errors.append(f"hashed source does not exist: {name}")
                elif hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                    errors.append(f"hashed source changed: {name}")

    results = document.get("results")
    flat: dict[str, float | int] = {}
    if not isinstance(results, dict) or not results:
        return flat, errors + ["results must be a non-empty object"]
    for result_id, fields in results.items():
        if not isinstance(result_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", result_id):
            errors.append(f"invalid result id {result_id!r}")
            continue
        if not isinstance(fields, dict) or not fields:
            errors.append(f"result {result_id!r} must contain fields")
            continue
        numeric = 0
        for field, value in fields.items():
            if not isinstance(field, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", field):
                errors.append(f"result {result_id!r} has invalid field {field!r}")
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                continue
            flat[f"{result_id}.{field}"] = value
            numeric += 1
        if not numeric:
            errors.append(f"result {result_id!r} requires at least one finite numeric field")

    required = document.get("required_bindings", [])
    if not isinstance(required, list) or not all(isinstance(key, str) for key in required):
        errors.append("required_bindings must be a list of strings")
    else:
        for key in required:
            if key not in flat:
                errors.append(f"required binding {key!r} is not a numeric result field")
    return flat, errors


def displayed_matches(displayed: str, canonical: float | int) -> bool:
    try:
        shown = Decimal(displayed)
        truth = Decimal(str(canonical))
    except InvalidOperation:
        return False
    exponent = shown.as_tuple().exponent
    tolerance = Decimal("0.5") * (Decimal(10) ** exponent)
    return abs(shown - truth) <= tolerance + Decimal("1e-30")


def audit(results_path: Path, manuscript_path: Path, require_hash_marker: bool = True, root: Path | None = None) -> dict:
    document = load_json(results_path)
    flat, errors = flatten_results(document, root)
    manuscript = manuscript_path.read_text(encoding="utf-8")
    bindings = list(MARKDOWN_BINDING.finditer(manuscript)) + list(LATEX_BINDING.finditer(manuscript))
    seen: set[str] = set()
    for match in bindings:
        key, displayed = match.group("key"), match.group("value")
        seen.add(key)
        if key not in flat:
            errors.append(f"unknown result binding {key!r}")
        elif not displayed_matches(displayed, flat[key]):
            errors.append(f"binding {key!r} displays {displayed} but source value is {flat[key]}")

    for key in document.get("required_bindings", []) if isinstance(document.get("required_bindings", []), list) else []:
        if key not in seen:
            errors.append(f"required result binding {key!r} is missing from manuscript")

    digest = hashlib.sha256(results_path.read_bytes()).hexdigest()
    markers = HASH_MARKER.findall(manuscript)
    if require_hash_marker and digest not in markers:
        errors.append("manuscript is not bound to the current results SHA-256")
    for marker in markers:
        if marker != digest:
            errors.append(f"stale results SHA-256 marker {marker}")
    return {
        "valid": not errors,
        "results_sha256": digest,
        "bindings": len(bindings),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--root", type=Path, help="verify source_sha256 paths below this project root")
    parser.add_argument("--no-hash-marker", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.results.is_file() or not args.manuscript.is_file():
        print("[Error] Results and manuscript files must exist", file=sys.stderr)
        return 2
    try:
        report = audit(args.results, args.manuscript, not args.no_hash_marker, args.root.resolve() if args.root else None)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot check result bindings: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("valid" if report["valid"] else "invalid")
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
