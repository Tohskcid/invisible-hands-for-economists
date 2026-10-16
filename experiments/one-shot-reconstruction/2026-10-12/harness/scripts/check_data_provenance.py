#!/usr/bin/env python3
"""Validate source, acquisition, schema, and checksum records for research data."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
HASH = re.compile(r"^[0-9a-f]{64}$")
KINDS = {"real", "restricted", "proxy"}
METHODS = {"api", "script", "database-export", "manual-download", "provided-file"}
INVALID_LICENSES = {"", "unknown", "n/a", "none", "unspecified"}


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def relative(value: object) -> PurePosixPath | None:
    if not nonempty(value):
        return None
    path = PurePosixPath(value)
    return None if path.is_absolute() or ".." in path.parts else path


def verify_file(root: Path | None, value: object, digest: object, label: str, errors: list[str]) -> None:
    path = relative(value)
    if path is None:
        errors.append(f"{label} must be a safe relative path")
        return
    if not isinstance(digest, str) or not HASH.fullmatch(digest):
        errors.append(f"{label}_sha256 must be a lowercase SHA-256 digest")
        return
    if root is None:
        return
    root = root.resolve()
    target = root.joinpath(*path.parts).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        errors.append(f"{label} resolves outside the project root: {value}")
        return
    if not target.is_file():
        errors.append(f"{label} does not exist: {value}")
    elif hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        errors.append(f"{label} checksum mismatch: {value}")


def valid_locator(value: object) -> bool:
    if not nonempty(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate(document: object, root: Path | None = None) -> dict:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "datasets": 0, "errors": ["provenance must be a JSON object"]}
    if document.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    generated_at = document.get("generated_at")
    if not isinstance(generated_at, str) or not DATE_TIME.fullmatch(generated_at):
        errors.append("generated_at must be an ISO-8601 timestamp with timezone")
    datasets = document.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        return {"valid": False, "datasets": 0, "errors": errors + ["datasets must be a non-empty list"]}

    ids: set[str] = set()
    for index, dataset in enumerate(datasets, 1):
        prefix = f"dataset {index}"
        if not isinstance(dataset, dict):
            errors.append(f"{prefix} must be an object")
            continue
        dataset_id = dataset.get("id")
        if not nonempty(dataset_id):
            errors.append(f"{prefix} requires id")
        elif dataset_id in ids:
            errors.append(f"duplicate dataset id {dataset_id!r}")
        else:
            ids.add(dataset_id)
        prefix = f"dataset {dataset_id!r}"
        kind = dataset.get("kind")
        if kind not in KINDS:
            errors.append(f"{prefix} kind must be one of {sorted(KINDS)}")
        for field in ("name", "producer", "version", "unit", "coverage"):
            if not nonempty(dataset.get(field)):
                errors.append(f"{prefix} requires {field}")
        if not valid_locator(dataset.get("locator")):
            errors.append(f"{prefix} locator must be a canonical HTTPS URL")
        if not valid_locator(dataset.get("license_locator")):
            errors.append(f"{prefix} license_locator must be a canonical HTTPS URL")
        retrieved_at = dataset.get("retrieved_at")
        if not isinstance(retrieved_at, str) or not DATE_TIME.fullmatch(retrieved_at):
            errors.append(f"{prefix} retrieved_at must be an ISO-8601 timestamp with timezone")
        license_value = dataset.get("license")
        if not nonempty(license_value) or license_value.strip().casefold() in INVALID_LICENSES:
            errors.append(f"{prefix} requires a verified license or terms-of-use statement")

        verify_file(root, dataset.get("source_evidence_artifact"), dataset.get("source_evidence_sha256"), f"{prefix} source_evidence_artifact", errors)
        verify_file(root, dataset.get("schema_artifact"), dataset.get("schema_sha256"), f"{prefix} schema_artifact", errors)
        acquisition = dataset.get("acquisition")
        if not isinstance(acquisition, dict):
            errors.append(f"{prefix} acquisition must be an object")
        else:
            if acquisition.get("method") not in METHODS:
                errors.append(f"{prefix} acquisition method must be one of {sorted(METHODS)}")
            if not nonempty(acquisition.get("command")):
                errors.append(f"{prefix} acquisition requires command or recorded manual action")
            executed_at = acquisition.get("executed_at")
            if not isinstance(executed_at, str) or not DATE_TIME.fullmatch(executed_at):
                errors.append(f"{prefix} acquisition executed_at must be an ISO-8601 timestamp with timezone")
            verify_file(root, acquisition.get("artifact"), acquisition.get("artifact_sha256"), f"{prefix} acquisition artifact", errors)

        files = dataset.get("files")
        if not isinstance(files, list) or not files:
            errors.append(f"{prefix} files must be a non-empty list")
            files = []
        for file_index, file_record in enumerate(files, 1):
            if not isinstance(file_record, dict):
                errors.append(f"{prefix} file {file_index} must be an object")
                continue
            if file_record.get("role") not in {"raw", "intermediate", "analysis"}:
                errors.append(f"{prefix} file {file_index} requires role raw, intermediate, or analysis")
            if kind == "restricted":
                if not nonempty(file_record.get("logical_path")):
                    errors.append(f"{prefix} restricted file {file_index} requires logical_path")
                if not isinstance(file_record.get("sha256"), str) or not HASH.fullmatch(file_record["sha256"]):
                    errors.append(f"{prefix} restricted file {file_index} requires SHA-256")
            else:
                verify_file(root, file_record.get("path"), file_record.get("sha256"), f"{prefix} file {file_index}", errors)

        if kind == "restricted":
            if not nonempty(dataset.get("access_boundary")):
                errors.append(f"{prefix} restricted data requires access_boundary")
            verify_file(root, dataset.get("verification_artifact"), dataset.get("verification_sha256"), f"{prefix} verification_artifact", errors)
        if kind == "proxy":
            if isinstance(dataset.get("seed"), bool) or not isinstance(dataset.get("seed"), (int, str)):
                errors.append(f"{prefix} proxy requires deterministic seed")
            if not nonempty(dataset.get("intended_use")):
                errors.append(f"{prefix} proxy requires intended_use")
            calibration = dataset.get("calibration_sources")
            if not isinstance(calibration, list) or not calibration or not all(valid_locator(item) for item in calibration):
                errors.append(f"{prefix} proxy requires canonical HTTPS calibration_sources")
    return {"valid": not errors, "datasets": len(datasets), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provenance", type=Path)
    parser.add_argument("--root", type=Path, help="verify artifacts and data files below this project root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.provenance.is_file():
        print(f"[Error] File not found: {args.provenance}", file=sys.stderr)
        return 2
    try:
        document = json.loads(args.provenance.read_text(encoding="utf-8"))
        report = validate(document, args.root.resolve() if args.root else None)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot read data provenance: {exc}", file=sys.stderr)
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
