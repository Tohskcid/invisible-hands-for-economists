#!/usr/bin/env python3
"""Validate the bundled economics paper and result-card library."""

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODES = {"theory", "empirical", "structural"}
RESULT_TYPES = {"algorithm", "characterization", "estimator", "identification", "theorem", "warning"}
RELATIONS = {"alternative", "builds_on", "complements", "corrects", "shares_method"}
VERIFICATION = {"metadata_checked", "abstract_checked", "statement_checked", "full_text_checked"}


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records, errors = [], []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{path.name}: {exc}"]
    for line_no, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{line_no}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(record, dict):
            errors.append(f"{path.name}:{line_no}: record must be an object")
            continue
        record["_line"] = line_no
        records.append(record)
    return records, errors


def required(record: dict, fields: tuple[str, ...], source: str) -> list[str]:
    return [f"{source}:{record['_line']}: requires {field}" for field in fields if record.get(field) in (None, "", [])]


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    values = {}
    for line in lines[1:]:
        if line == "---":
            return values
        if ": " in line:
            key, value = line.split(": ", 1)
            values[key] = value
    return {}


def validate(catalog: list[dict], results: list[dict], relations: list[dict], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    all_records = [("catalog.jsonl", item) for item in catalog] + [("index.jsonl", item) for item in results]
    ids: dict[str, str] = {}
    for source, record in all_records:
        errors.extend(required(record, ("id",), source))
        record_id = record.get("id")
        if record_id in ids:
            errors.append(f"{source}:{record['_line']}: duplicate id {record_id!r}")
        elif isinstance(record_id, str):
            ids[record_id] = source

    paper_ids = {paper.get("id") for paper in catalog}
    result_ids = {card.get("id") for card in results}
    for paper in catalog:
        source = "catalog.jsonl"
        errors.extend(required(paper, ("title", "authors", "year", "venue", "doi", "url", "verification"), source))
        if paper.get("verification") not in VERIFICATION:
            errors.append(f"{source}:{paper['_line']}: invalid verification")
        if not isinstance(paper.get("authors"), list):
            errors.append(f"{source}:{paper['_line']}: authors must be a list")

    for card in results:
        source = "index.jsonl"
        errors.extend(required(card, ("paper_id", "title", "mode", "result_type", "problem", "method", "keywords", "path"), source))
        if card.get("paper_id") not in paper_ids:
            errors.append(f"{source}:{card['_line']}: unknown paper_id {card.get('paper_id')!r}")
        if card.get("mode") not in MODES:
            errors.append(f"{source}:{card['_line']}: invalid mode")
        if card.get("result_type") not in RESULT_TYPES:
            errors.append(f"{source}:{card['_line']}: invalid result_type")
        for field in ("problem", "keywords"):
            if not isinstance(card.get(field), list):
                errors.append(f"{source}:{card['_line']}: {field} must be a list")
        path = root / str(card.get("path", ""))
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{source}:{card['_line']}: cannot read Markdown card ({exc})")
            continue
        metadata = parse_frontmatter(text)
        for field in ("id", "paper_id", "mode", "result_type"):
            if metadata.get(field) != card.get(field):
                errors.append(f"{source}:{card['_line']}: Markdown {field} does not match index")
        if metadata.get("verification") not in VERIFICATION:
            errors.append(f"{source}:{card['_line']}: invalid Markdown verification")
        lines = text.splitlines()
        headings = ("## Problem", "## Assumptions", "## Conclusion", "## Failure conditions", "## Primary source")
        if not any(line.startswith("# ") for line in lines):
            errors.append(f"{source}:{card['_line']}: Markdown card requires a title")
        for heading in headings:
            if heading not in lines:
                errors.append(f"{source}:{card['_line']}: Markdown card requires {heading}")

    for relation in relations:
        source = "relations.jsonl"
        errors.extend(required(relation, ("from", "to", "type", "note"), source))
        if relation.get("from") not in result_ids or relation.get("to") not in result_ids:
            errors.append(f"{source}:{relation['_line']}: relation endpoints must reference result cards")
        if relation.get("type") not in RELATIONS:
            errors.append(f"{source}:{relation['_line']}: invalid relation type")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=ROOT / "library")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    catalog, errors = load_jsonl(args.library / "catalog.jsonl")
    results, result_errors = load_jsonl(args.library / "index.jsonl")
    relations, relation_errors = load_jsonl(args.library / "relations.jsonl")
    errors.extend(result_errors + relation_errors)
    errors.extend(validate(catalog, results, relations))
    report = {"valid": not errors, "papers": len(catalog), "results": len(results), "relations": len(relations), "errors": errors}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("valid" if not errors else "invalid")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
