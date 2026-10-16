#!/usr/bin/env python3
"""Validate the pre-design survey and bounded contribution decision for a new question."""

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


AXES = {"question", "mechanism", "method", "setting"}
SEARCH_LANES = {"baseline", "frontier"}
FRONTIER_CHANNELS = {"working-paper-series", "preprint-repository", "journal-advance", "conference", "author-repository"}
QUALITY_SIGNALS = {
    "important-question", "credible-design-or-proof", "unique-data", "new-method-or-measurement",
    "discriminating-result", "reusable-research-move", "transparent-boundaries",
}
RETRIEVAL_TOOLS = {"browser", "api", "database", "publisher-search", "scripts/search_literature.py"}
RELATIONS = {"duplicate", "replication", "extension", "external-validity", "adjacent", "contradiction"}
DECISIONS = {"proceed", "reframe", "replicate", "stop", "blocked"}
CONTRIBUTIONS = {"distinct-under-search", "extension", "external-validity", "replication", "synthesis", "duplicate", "unresolved"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CITATION_KEY = re.compile(r"^[A-Za-z0-9_.:-]+$")


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def canonical_locator(value: object) -> bool:
    if not nonempty(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def safe_relative(value: object) -> bool:
    if not nonempty(value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def validate(document: object, root: Path | None = None, as_of: dt.date | None = None) -> dict:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "errors": ["survey must be a JSON object"]}
    if document.get("schema_version") != "2":
        errors.append("schema_version must be '2'")
    for field in ("question", "scope", "contribution_statement"):
        if not nonempty(document.get(field)):
            errors.append(f"{field} must be a non-empty string")
    cutoff = document.get("cutoff")
    if not isinstance(cutoff, str) or not DATE.fullmatch(cutoff):
        errors.append("cutoff must use YYYY-MM-DD")
    refresh_after_days = document.get("refresh_after_days")
    if not isinstance(refresh_after_days, int) or isinstance(refresh_after_days, bool) or not 1 <= refresh_after_days <= 365:
        errors.append("refresh_after_days must be an integer from 1 to 365")
    elif isinstance(cutoff, str) and DATE.fullmatch(cutoff) and as_of is not None:
        age = (as_of - dt.date.fromisoformat(cutoff)).days
        if age < 0:
            errors.append("cutoff cannot be after the audit date")
        elif age > refresh_after_days:
            errors.append(f"literature search is stale ({age} days old; refresh after {refresh_after_days})")
    frontier_window_years = document.get("frontier_window_years")
    if not isinstance(frontier_window_years, int) or isinstance(frontier_window_years, bool) or not 1 <= frontier_window_years <= 5:
        errors.append("frontier_window_years must be an integer from 1 to 5")
    if document.get("citation_policy") != "never-exclude":
        errors.append("citation_policy must be 'never-exclude'")

    searches = document.get("searches")
    observed_axes: set[str] = set()
    observed_lanes: set[str] = set()
    frontier_channels: set[str] = set()
    evidence_cache: dict[str, object] = {}
    if not isinstance(searches, list) or not searches:
        errors.append("searches must be a non-empty list")
        searches = []
    for index, search in enumerate(searches, 1):
        if not isinstance(search, dict):
            errors.append(f"search {index} must be an object")
            continue
        axis = search.get("axis")
        if axis not in AXES:
            errors.append(f"search {index} axis must be one of {sorted(AXES)}")
        else:
            observed_axes.add(axis)
        lane = search.get("lane")
        if lane not in SEARCH_LANES:
            errors.append(f"search {index} lane must be one of {sorted(SEARCH_LANES)}")
        else:
            observed_lanes.add(lane)
        channel = search.get("channel")
        if lane == "frontier":
            if channel not in FRONTIER_CHANNELS:
                errors.append(f"frontier search {index} channel must be one of {sorted(FRONTIER_CHANNELS)}")
            else:
                frontier_channels.add(channel)
        for field in ("source", "query", "searched_at"):
            if not nonempty(search.get(field)):
                errors.append(f"search {index} requires {field}")
        if nonempty(search.get("searched_at")) and not DATE.fullmatch(search["searched_at"]):
            errors.append(f"search {index} searched_at must use YYYY-MM-DD")
        tool = search.get("retrieval_tool")
        if tool not in RETRIEVAL_TOOLS:
            errors.append(f"search {index} retrieval_tool must be a non-model retrieval tool")
        artifact = search.get("source_evidence_artifact")
        digest = search.get("source_evidence_sha256")
        if not safe_relative(artifact):
            errors.append(f"search {index} requires a safe source_evidence_artifact path")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"search {index} requires a lowercase source_evidence_sha256")
        elif root is not None and safe_relative(artifact):
            evidence = root / artifact
            if not evidence.is_file():
                errors.append(f"search {index} source evidence does not exist: {artifact}")
            elif hashlib.sha256(evidence.read_bytes()).hexdigest() != digest:
                errors.append(f"search {index} source evidence checksum mismatch")
            else:
                try:
                    record = evidence_cache.setdefault(artifact, json.loads(evidence.read_text(encoding="utf-8")))
                    source_searches = record.get("searches", []) if isinstance(record, dict) else []
                except (OSError, json.JSONDecodeError):
                    source_searches = []
                if not any(
                    isinstance(item, dict)
                    and item.get("source") == search.get("source")
                    and item.get("query") == search.get("query")
                    and item.get("retrieved_at") == search.get("searched_at")
                    and item.get("retrieval_tool") == tool
                    for item in source_searches
                ):
                    errors.append(f"search {index} is not present in its tool evidence")
    if "question" not in observed_axes:
        errors.append("survey requires a question-axis search")
    if not observed_axes.intersection({"mechanism", "method", "setting"}):
        errors.append("survey requires at least one mechanism, method, or setting search")
    if observed_lanes != SEARCH_LANES:
        errors.append("survey requires both baseline and frontier search lanes")
    if len(frontier_channels) < 2:
        errors.append("survey requires at least two distinct frontier discovery channels")

    works = document.get("nearest_works")
    if not isinstance(works, list):
        errors.append("nearest_works must be a list")
        works = []
    nearest_count = 0
    frontier_works: list[dict] = []
    relations: set[str] = set()
    for index, work in enumerate(works, 1):
        if not isinstance(work, dict):
            errors.append(f"nearest work {index} must be an object")
            continue
        if work.get("nearest") is True:
            nearest_count += 1
        lane = work.get("discovery_lane")
        if lane not in SEARCH_LANES:
            errors.append(f"nearest work {index} discovery_lane must be one of {sorted(SEARCH_LANES)}")
        elif lane == "frontier":
            frontier_works.append(work)
        relation = work.get("relation")
        if relation not in RELATIONS:
            errors.append(f"nearest work {index} relation must be one of {sorted(RELATIONS)}")
        else:
            relations.add(relation)
        for field in (
            "title", "locator", "verified_at", "question", "estimand_or_theorem", "method_or_proof", "difference",
            "prior_bottleneck", "innovation", "why_field_cares", "validation", "influence_or_reuse",
        ):
            if not nonempty(work.get(field)):
                errors.append(f"nearest work {index} requires {field}")
        if nonempty(work.get("locator")) and not canonical_locator(work["locator"]):
            errors.append(f"nearest work {index} locator must be a canonical HTTPS URL")
        artifact = work.get("source_evidence_artifact")
        digest = work.get("source_evidence_sha256")
        if not safe_relative(artifact):
            errors.append(f"nearest work {index} requires a safe source_evidence_artifact path")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"nearest work {index} requires a lowercase source_evidence_sha256")
        elif root is not None and safe_relative(artifact):
            evidence = root / artifact
            if not evidence.is_file():
                errors.append(f"nearest work {index} source evidence does not exist: {artifact}")
            elif hashlib.sha256(evidence.read_bytes()).hexdigest() != digest:
                errors.append(f"nearest work {index} source evidence checksum mismatch")
            else:
                try:
                    source_records = json.loads(evidence.read_text(encoding="utf-8")).get("sources", [])
                except (OSError, AttributeError, json.JSONDecodeError):
                    source_records = []
                if not any(
                    isinstance(record, dict)
                    and record.get("title") == work.get("title")
                    and record.get("canonical_locator") == work.get("locator")
                    and record.get("retrieval_tool") in RETRIEVAL_TOOLS
                    and record.get("retrieved_at") == work.get("verified_at")
                    for record in source_records
                ):
                    errors.append(f"nearest work {index} is not present in tool-acquired source evidence")
        if nonempty(work.get("verified_at")) and not DATE.fullmatch(work["verified_at"]):
            errors.append(f"nearest work {index} verified_at must use YYYY-MM-DD")
        if work.get("full_text_status") not in {"checked", "abstract-only", "inaccessible"}:
            errors.append(f"nearest work {index} requires valid full_text_status")
        for field in ("backward_checked", "forward_checked"):
            if not isinstance(work.get(field), bool):
                errors.append(f"nearest work {index} requires boolean {field}")
        first_public_at = work.get("first_public_at")
        if not isinstance(first_public_at, str) or not DATE.fullmatch(first_public_at):
            errors.append(f"nearest work {index} first_public_at must use YYYY-MM-DD")
        citation_key = work.get("citation_key")
        if not isinstance(citation_key, str) or not CITATION_KEY.fullmatch(citation_key):
            errors.append(f"nearest work {index} requires a valid citation_key")
        if lane == "frontier":
            signals = work.get("quality_signals")
            if not isinstance(signals, list) or len(set(signals)) < 2 or not set(signals).issubset(QUALITY_SIGNALS):
                errors.append(f"frontier work {index} requires at least two allowed quality_signals")
            for field in ("frontier_case", "manuscript_action", "selection_reason"):
                if not nonempty(work.get(field)):
                    errors.append(f"frontier work {index} requires {field}")
            if work.get("manuscript_action") not in {"cite", "discuss", "exclude"}:
                errors.append(f"frontier work {index} manuscript_action must be cite, discuss, or exclude")
            if work.get("full_text_status") == "inaccessible" and work.get("manuscript_action") == "discuss":
                errors.append(f"frontier work {index} cannot be discussed substantively without accessible text")

    decision = document.get("decision")
    contribution = document.get("contribution_class")
    if decision not in DECISIONS:
        errors.append(f"decision must be one of {sorted(DECISIONS)}")
    if contribution not in CONTRIBUTIONS:
        errors.append(f"contribution_class must be one of {sorted(CONTRIBUTIONS)}")
    limitations = document.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(nonempty(item) for item in limitations):
        errors.append("limitations must be a non-empty list of strings")

    checkpoints = document.get("researcher_checkpoints")
    checkpoint_ids: set[str] = set()
    if not isinstance(checkpoints, list):
        errors.append("researcher_checkpoints must be a list")
        checkpoints = []
    for index, checkpoint in enumerate(checkpoints, 1):
        if not isinstance(checkpoint, dict):
            errors.append(f"researcher checkpoint {index} must be an object")
            continue
        checkpoint_id = checkpoint.get("id")
        if checkpoint_id in checkpoint_ids:
            errors.append(f"duplicate researcher checkpoint {checkpoint_id!r}")
        elif isinstance(checkpoint_id, str):
            checkpoint_ids.add(checkpoint_id)
        for field in ("id", "question", "response", "decided_at"):
            if not nonempty(checkpoint.get(field)):
                errors.append(f"researcher checkpoint {index} requires {field}")
        if nonempty(checkpoint.get("decided_at")) and not DATE.fullmatch(checkpoint["decided_at"]):
            errors.append(f"researcher checkpoint {index} decided_at must use YYYY-MM-DD")
        if checkpoint.get("status") not in {"accepted", "revised", "blocked"}:
            errors.append(f"researcher checkpoint {index} requires valid status")

    if works and nearest_count == 0:
        errors.append("at least one work must be marked nearest")
    if not works and (decision != "blocked" or contribution != "unresolved"):
        errors.append("no verified nearest work requires blocked/unresolved rather than a novelty claim")
    if "duplicate" in relations and decision == "proceed":
        errors.append("a duplicate nearest work forbids proceeding without reframe, replication, or stop")
    if contribution == "duplicate" and decision not in {"reframe", "replicate", "stop"}:
        errors.append("duplicate contribution requires reframe, replicate, or stop")
    if isinstance(cutoff, str) and DATE.fullmatch(cutoff) and isinstance(frontier_window_years, int):
        oldest_year = dt.date.fromisoformat(cutoff).year - frontier_window_years
        recent_frontier = [
            work for work in frontier_works
            if isinstance(work.get("first_public_at"), str)
            and DATE.fullmatch(work["first_public_at"])
            and dt.date.fromisoformat(work["first_public_at"]).year >= oldest_year
        ]
        if not recent_frontier:
            errors.append("survey requires a verified work inside the frontier window")
        if decision in {"proceed", "reframe", "replicate"} and not any(
            work.get("manuscript_action") in {"cite", "discuss"} for work in recent_frontier
        ):
            errors.append("approved research requires at least one recent frontier work selected for the manuscript")
    if decision in {"proceed", "reframe", "replicate"}:
        missing = {"scope-lock", "contribution-lock"} - checkpoint_ids
        if missing:
            errors.append(f"decision requires answered researcher checkpoints {sorted(missing)}")
        if any(item.get("status") == "blocked" for item in checkpoints if isinstance(item, dict)):
            errors.append("cannot enter design while a researcher checkpoint is blocked")
    return {
        "valid": not errors,
        "gate_passed": not errors and decision in {"proceed", "reframe", "replicate"},
        "decision": decision,
        "contribution_class": contribution,
        "errors": errors,
    }


def audit_frontier_bindings(document: dict, manuscript: str, bibliography: str) -> list[str]:
    errors: list[str] = []
    for work in document.get("nearest_works", []):
        if not isinstance(work, dict) or work.get("discovery_lane") != "frontier":
            continue
        if work.get("manuscript_action") not in {"cite", "discuss"}:
            continue
        key = work.get("citation_key", "")
        if not re.search(r"@[A-Za-z]+\s*\{\s*" + re.escape(key) + r"\s*,", bibliography, re.IGNORECASE):
            errors.append(f"selected frontier work {key!r} is missing from bibliography")
        latex_cite = re.search(r"\\cite\w*\s*\{[^}]*\b" + re.escape(key) + r"\b[^}]*\}", manuscript)
        markdown_cite = re.search(r"\[@[^\]]*\b" + re.escape(key) + r"\b[^\]]*\]", manuscript)
        if not latex_cite and not markdown_cite:
            errors.append(f"selected frontier work {key!r} is not cited in the manuscript")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey", type=Path)
    parser.add_argument("--root", type=Path, help="verify source-evidence artifacts below this root")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date.today(), help="freshness audit date (YYYY-MM-DD)")
    parser.add_argument("--require-approved", action="store_true", help="fail unless the survey may enter design")
    parser.add_argument("--manuscript", type=Path, help="verify selected frontier papers are cited")
    parser.add_argument("--bibliography", type=Path, help="verify selected frontier papers have entries")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.survey.is_file():
        print(f"[Error] File not found: {args.survey}", file=sys.stderr)
        return 2
    try:
        report = validate(
            json.loads(args.survey.read_text(encoding="utf-8")),
            args.root.resolve() if args.root else None,
            args.as_of,
        )
        if bool(args.manuscript) != bool(args.bibliography):
            report["errors"].append("--manuscript and --bibliography must be provided together")
        elif args.manuscript and args.bibliography:
            report["errors"].extend(audit_frontier_bindings(
                json.loads(args.survey.read_text(encoding="utf-8")),
                args.manuscript.read_text(encoding="utf-8"),
                args.bibliography.read_text(encoding="utf-8"),
            ))
        report["valid"] = not report["errors"]
        report["gate_passed"] = report["valid"] and report["decision"] in {"proceed", "reframe", "replicate"}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot read topic survey: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("valid" if report["valid"] else "invalid")
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["valid"] and (report["gate_passed"] or not args.require_approved) else 1


if __name__ == "__main__":
    raise SystemExit(main())
