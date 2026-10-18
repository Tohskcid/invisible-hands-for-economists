#!/usr/bin/env python3
"""Classify dated sources for a retrospective paper-reconstruction benchmark."""

import argparse
import calendar
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def date(value: object) -> dt.date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def date_bounds(value: object) -> tuple[dt.date, dt.date] | None:
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        return dt.date(year, 1, 1), dt.date(year, 12, 31)
    if re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        if not 1 <= month <= 12:
            return None
        return dt.date(year, month, 1), dt.date(year, month, calendar.monthrange(year, month)[1])
    day = date(value)
    return (day, day) if day else None


def https(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def evaluate(record: object) -> dict:
    errors = []
    if not isinstance(record, dict):
        return {"valid": False, "errors": ["record must be an object"], "comparators": []}
    target = record.get("target")
    if not isinstance(target, dict):
        return {"valid": False, "errors": ["target must be an object"], "comparators": []}
    journal_date = date(target.get("first_journal_public_at"))
    target_date = date(target.get("first_target_public_at"))
    if journal_date is None:
        errors.append("target.first_journal_public_at requires YYYY-MM-DD")
    if target_date is None:
        errors.append("target.first_target_public_at requires YYYY-MM-DD")
    if journal_date and target_date and target_date > journal_date:
        errors.append("first target version cannot postdate first journal publication")
    for field in ("journal_date_source", "target_date_source"):
        if not https(target.get(field)):
            errors.append(f"target.{field} requires an HTTPS source")
    works = record.get("comparators")
    if not isinstance(works, list):
        return {"valid": False, "errors": errors + ["comparators must be a list"], "comparators": []}
    classified = []
    author_sources = []
    unsafe_author_sources = []
    for index, work in enumerate(works, 1):
        if not isinstance(work, dict):
            errors.append(f"comparator {index} must be an object")
            continue
        if not isinstance(work.get("title"), str) or not work["title"].strip():
            errors.append(f"comparator {index} requires a title")
        bounds = date_bounds(work.get("first_public_at"))
        if bounds is None:
            errors.append(f"comparator {index} first_public_at requires YYYY, YYYY-MM, or YYYY-MM-DD")
        if not https(work.get("date_source")):
            errors.append(f"comparator {index} date_source requires an HTTPS source")
        if not isinstance(work.get("is_target_version"), bool):
            errors.append(f"comparator {index} is_target_version must be boolean")
        if not isinstance(work.get("author_material", False), bool):
            errors.append(f"comparator {index} author_material must be boolean")
        if bounds is None or journal_date is None or target_date is None or not isinstance(work.get("is_target_version"), bool):
            continue
        if work["is_target_version"]:
            reason = "target-version"
            prior_art = author_visible = False
        else:
            author_visible = True if bounds[1] < target_date else False if bounds[0] >= target_date else None
            if bounds[0] >= journal_date:
                reason, prior_art = "at-or-after-journal-publication", False
            elif bounds[1] >= journal_date:
                reason, prior_art = "publication-date-overlaps-cutoff", None
            else:
                reason, prior_art = "pre-publication-external-work", True
        classified.append({
            "title": work.get("title"),
            "first_public_at": work["first_public_at"],
            "historical_prior_art": prior_art,
            "author_visible_for_strict_blind": author_visible,
            "classification": reason,
        })
        if work.get("author_material") is True:
            author_sources.append(work.get("title"))
            if author_visible is not True:
                unsafe_author_sources.append(work.get("title"))
    return {
        "valid": not errors,
        "historical_cutoff_exclusive": target.get("first_journal_public_at"),
        "strict_blind_cutoff_exclusive": target.get("first_target_public_at"),
        "comparators": classified,
        "author_corpus_safe": bool(author_sources) and not unsafe_author_sources,
        "unsafe_author_material": unsafe_author_sources,
        "errors": errors,
        "note": "Date eligibility only; substantive overlap and novelty require source-based review.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--require-author-safe", action="store_true", help="fail if any author material lacks pre-target public evidence")
    args = parser.parse_args()
    result = evaluate(json.loads(args.record.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] and (not args.require_author_safe or result["author_corpus_safe"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
