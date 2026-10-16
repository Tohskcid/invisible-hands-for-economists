#!/usr/bin/env python3
"""Validate bibliography coverage, lawful download records, PDF files, and names."""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
HASH = re.compile(r"^[0-9a-f]{64}$")
STATUSES = {"downloaded", "unavailable", "restricted"}


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def https_url(value: object) -> bool:
    if not nonempty(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def slug(value: str, limit: int) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    result = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-").lower()
    return result[:limit].rstrip("-") or "paper"


def expected_filename(citekey: str, title: str) -> str:
    return f"{slug(citekey, 60)}--{slug(title, 80)}.pdf"


def bibliography_keys(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.casefold() == ".bib":
        return set(re.findall(r"@\w+\s*[{(]\s*([^,\s]+)\s*,", text))
    return set(re.findall(r"\\bibitem(?:\[[^]]*\])?\s*{([^}]+)}", text))


def safe_file(root: Path, value: object, label: str, errors: list[str]) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label} requires a relative path")
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} must stay below the project root")
        return None
    target = root.joinpath(*path.parts).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label} resolves outside the project root")
        return None
    if not target.is_file():
        errors.append(f"{label} does not exist: {value}")
        return None
    return target


def validate(document: object, root: Path, bibliography: Path) -> dict:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "complete": False, "papers": 0, "errors": ["archive must be a JSON object"]}
    if document.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    generated_at = document.get("generated_at")
    if not isinstance(generated_at, str) or not DATE_TIME.fullmatch(generated_at):
        errors.append("generated_at must be an ISO-8601 timestamp with timezone")
    try:
        cited = bibliography_keys(bibliography)
    except OSError as exc:
        return {"valid": False, "complete": False, "papers": 0, "errors": [f"cannot read bibliography: {exc}"]}
    if not cited:
        errors.append("bibliography contains no BibTeX entries or \\bibitem keys")

    papers = document.get("papers")
    if not isinstance(papers, list):
        return {"valid": False, "complete": False, "papers": 0, "errors": errors + ["papers must be a list"]}
    seen: set[str] = set()
    downloaded = 0
    for index, paper in enumerate(papers, 1):
        if not isinstance(paper, dict):
            errors.append(f"paper {index} must be an object")
            continue
        citekey = paper.get("citekey")
        if not nonempty(citekey):
            errors.append(f"paper {index} requires citekey")
            continue
        prefix = f"paper {citekey!r}"
        if citekey in seen:
            errors.append(f"duplicate citekey {citekey!r}")
        seen.add(citekey)
        title = paper.get("title")
        authors = paper.get("authors")
        if not nonempty(title):
            errors.append(f"{prefix} requires title")
        if not isinstance(authors, list) or not authors or not all(nonempty(item) for item in authors):
            errors.append(f"{prefix} requires a non-empty authors list")
        if not isinstance(paper.get("year"), int):
            errors.append(f"{prefix} requires integer year")
        if not https_url(paper.get("canonical_locator")):
            errors.append(f"{prefix} canonical_locator must be HTTPS")
        verified_at = paper.get("verified_at")
        if not isinstance(verified_at, str) or not DATE_TIME.fullmatch(verified_at):
            errors.append(f"{prefix} verified_at must be an ISO-8601 timestamp with timezone")
        if not nonempty(paper.get("access_basis")):
            errors.append(f"{prefix} requires license or lawful access_basis")

        status = paper.get("access_status")
        if status not in STATUSES:
            errors.append(f"{prefix} access_status must be one of {sorted(STATUSES)}")
            continue
        if status == "downloaded":
            downloaded += 1
            if not https_url(paper.get("download_locator")):
                errors.append(f"{prefix} download_locator must be HTTPS")
            retrieved_at = paper.get("retrieved_at")
            if not isinstance(retrieved_at, str) or not DATE_TIME.fullmatch(retrieved_at):
                errors.append(f"{prefix} retrieved_at must be an ISO-8601 timestamp with timezone")
            target = safe_file(root, paper.get("file"), f"{prefix} file", errors)
            file_value = paper.get("file")
            if nonempty(file_value):
                posix = PurePosixPath(file_value)
                if posix.parts[:2] != ("literature", "papers"):
                    errors.append(f"{prefix} file must be below literature/papers")
                if nonempty(title) and posix.name != expected_filename(citekey, title):
                    errors.append(f"{prefix} filename must be {expected_filename(citekey, title)!r}")
            digest = paper.get("sha256")
            if not isinstance(digest, str) or not HASH.fullmatch(digest):
                errors.append(f"{prefix} requires lowercase SHA-256")
            elif target is not None:
                content = target.read_bytes()
                if not content.startswith(b"%PDF-"):
                    errors.append(f"{prefix} file is not a PDF")
                if hashlib.sha256(content).hexdigest() != digest:
                    errors.append(f"{prefix} checksum mismatch")
        elif not nonempty(paper.get("reason")):
            errors.append(f"{prefix} {status} record requires reason")

    missing = sorted(cited - seen)
    extra = sorted(seen - cited)
    if missing:
        errors.append(f"bibliography entries missing from archive: {missing}")
    if extra:
        errors.append(f"archive entries absent from bibliography: {extra}")
    complete = bool(cited) and not missing and downloaded == len(cited)
    return {"valid": not errors, "complete": complete, "papers": len(papers), "downloaded": downloaded, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--bibliography", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--require-complete", action="store_true", help="fail when a cited PDF is not downloaded")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    archive = args.archive if args.archive.is_absolute() else root / args.archive
    bibliography = args.bibliography if args.bibliography.is_absolute() else root / args.bibliography
    if not archive.is_file() or not bibliography.is_file():
        print("[Error] Archive or bibliography file not found", file=sys.stderr)
        return 2
    try:
        report = validate(json.loads(archive.read_text(encoding="utf-8")), root, bibliography)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot read literature archive: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("valid" if report["valid"] else "invalid")
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["valid"] and (report["complete"] or not args.require_complete) else 1


if __name__ == "__main__":
    raise SystemExit(main())
