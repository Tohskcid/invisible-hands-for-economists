#!/usr/bin/env python3
"""Check traceable full-text comparisons before a research claim enters drafting."""

import argparse
import calendar
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


SHA256 = re.compile(r"^[0-9a-f]{64}$")
APPROVED = {"proceed", "reframe", "replicate"}
OVERLAP = {"same", "partial", "distinct", "uncertain"}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalized(value):
    return " ".join(value.split()).casefold()


def full_text(root, name, errors, label):
    """Extract checkable text; this does not prove the file is the cited paper."""
    path = (root / name).resolve()
    if path.suffix.lower() in {".html", ".htm"}:
        parser = VisibleText()
        parser.feed(path.read_text(encoding="utf-8"))
        content = " ".join(parser.parts)
        if not content.strip():
            errors.append(f"{label} HTML has no visible text")
        return [content]
    if path.suffix.lower() != ".pdf":
        errors.append(f"{label} must be a readable PDF or HTML full text")
        return []
    if not path.read_bytes().startswith(b"%PDF-"):
        errors.append(f"{label} is not a PDF")
        return []
    if not shutil.which("pdfinfo") or not shutil.which("pdftotext"):
        errors.append("pdfinfo and pdftotext are required to verify full-text excerpts")
        return []
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
    match = re.search(r"^Pages:\s*(\d+)$", info.stdout, re.MULTILINE)
    if info.returncode or not match or int(match.group(1)) < 1:
        errors.append(f"{label} PDF page count cannot be verified")
        return []
    pages = []
    for page in range(1, int(match.group(1)) + 1):
        extracted = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), str(path), "-"],
                                   capture_output=True, text=True, check=False)
        if extracted.returncode:
            errors.append(f"{label} PDF page {page} cannot be extracted")
            return []
        pages.append(extracted.stdout)
    if not any(page.strip() for page in pages):
        errors.append(f"{label} PDF has no extractable text")
    return pages


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def day(value):
    try:
        return dt.date.fromisoformat(value) if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None
    except ValueError:
        return None


def latest_possible_day(value):
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{4}", value):
            return dt.date(int(value), 12, 31)
        if re.fullmatch(r"\d{4}-\d{2}", value):
            year, month = map(int, value.split("-"))
            if 1 <= month <= 12:
                return dt.date(year, month, calendar.monthrange(year, month)[1])
    except ValueError:
        return None
    return day(value)


def https(value):
    if not nonempty(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def artifact(root, name, digest, label, errors):
    if not nonempty(name) or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
        errors.append(f"{label} requires a safe artifact path")
        return
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        errors.append(f"{label} requires a lowercase SHA-256")
        return
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size == 0:
        errors.append(f"{label} artifact is missing or outside root: {name}")
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        errors.append(f"{label} artifact checksum mismatch: {name}")


def validate(review, survey, survey_bytes, root, manifest: list[dict] | None = None):
    errors = []
    if not isinstance(review, dict) or not isinstance(survey, dict):
        return {"valid": False, "gate_passed": False, "evidence_complete": False,
                "novelty_certified": False, "decision": None, "errors": ["review and survey must be JSON objects"]}
    if review.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    if review.get("topic_survey_sha256") != hashlib.sha256(survey_bytes).hexdigest():
        errors.append("topic_survey_sha256 does not bind the current survey")
    if survey.get("decision") not in APPROVED:
        errors.append("topic survey has not approved entry to design")
    nearest_works = survey.get("nearest_works")
    if not isinstance(nearest_works, list):
        nearest_works = []
    survey_keys = [work.get("citation_key") for work in nearest_works if isinstance(work, dict)]
    if not survey_keys or len(set(survey_keys)) != len(survey_keys) or not all(nonempty(key) for key in survey_keys):
        errors.append("survey needs uniquely keyed nearest works")
    claims = review.get("proposed_claims")
    if not isinstance(claims, list) or not claims:
        errors.append("proposed_claims must be a non-empty list")
        claims = []
    claim_ids = []
    for index, claim in enumerate(claims, 1):
        if not isinstance(claim, dict) or not nonempty(claim.get("id")) or not nonempty(claim.get("statement")):
            errors.append(f"proposed claim {index} requires id and statement")
        else:
            claim_ids.append(claim["id"])
    if len(set(claim_ids)) != len(claim_ids):
        errors.append("proposed claim ids must be unique")
    if manifest is not None:
        central = {item.get("id"): item.get("statement") for item in manifest
                   if isinstance(item, dict) and item.get("type") == "claim" and item.get("central") is True}
        proposed = {item.get("id"): item.get("statement") for item in claims if isinstance(item, dict)}
        if not central or proposed != central:
            errors.append("proposed_claims must exactly match current central manifest claim IDs and statements")

    cutoff = day(review.get("historical_author_cutoff_exclusive")) if review.get("historical_author_cutoff_exclusive") else None
    if review.get("historical_author_cutoff_exclusive") and cutoff is None:
        errors.append("historical_author_cutoff_exclusive requires YYYY-MM-DD")
    search_cutoff = day(survey.get("cutoff"))
    if search_cutoff is None:
        errors.append("survey cutoff requires YYYY-MM-DD")
    works = review.get("works")
    if not isinstance(works, list):
        errors.append("works must be a list")
        works = []
    work_keys = []
    extracted_by_key = {}
    for index, work in enumerate(works, 1):
        if not isinstance(work, dict):
            errors.append(f"work {index} must be an object")
            continue
        key = work.get("citation_key")
        if not nonempty(key):
            errors.append(f"work {index} requires citation_key")
        else:
            work_keys.append(key)
        if not nonempty(work.get("title")) or not https(work.get("locator")) or not https(work.get("date_source")):
            errors.append(f"work {index} requires title, HTTPS locator and date_source")
        source_day = latest_possible_day(work.get("first_public_at"))
        if source_day is None:
            errors.append(f"work {index} first_public_at requires YYYY, YYYY-MM, or YYYY-MM-DD")
        elif (cutoff and source_day >= cutoff) or (search_cutoff and source_day > search_cutoff):
            errors.append(f"work {index} was not public before the applicable author cutoff")
        if work.get("full_text_status") != "checked":
            errors.append(f"work {index} requires checked full text; abstracts cannot support a novelty clearance")
        if not https(work.get("full_text_locator")) or day(work.get("full_text_retrieved_at")) is None:
            errors.append(f"work {index} requires full_text_locator and full_text_retrieved_at")
        artifact(root, work.get("full_text_artifact"), work.get("full_text_sha256"), f"work {index} full text", errors)
        retained = work.get("full_text_artifact")
        if nonempty(retained) and ".." not in PurePosixPath(retained).parts:
            retained_path = (root / retained).resolve()
            if retained_path.is_relative_to(root.resolve()) and retained_path.is_file():
                extracted_by_key[key] = full_text(root, retained, errors, f"work {index} full text")
        match = next((item for item in nearest_works
                      if isinstance(item, dict) and item.get("citation_key") == key), None)
        if match is None or match.get("title") != work.get("title") or match.get("locator") != work.get("locator"):
            errors.append(f"work {index} does not match the survey nearest-work record")
        elif match.get("full_text_status") != "checked":
            errors.append(f"work {index} survey record does not confirm checked full text")
        elif match.get("first_public_at") != work.get("first_public_at"):
            errors.append(f"work {index} first_public_at differs from the survey")
    if len(set(work_keys)) != len(work_keys) or set(work_keys) != set(survey_keys):
        errors.append("works must cover each survey nearest work exactly once")

    comparisons = review.get("comparisons")
    if not isinstance(comparisons, list):
        errors.append("comparisons must be a list")
        comparisons = []
    pairs = set()
    unresolved = []
    for index, item in enumerate(comparisons, 1):
        if not isinstance(item, dict):
            errors.append(f"comparison {index} must be an object")
            continue
        if not nonempty(item.get("claim_id")) or not nonempty(item.get("citation_key")):
            errors.append(f"comparison {index} requires claim_id and citation_key")
            continue
        pair = (item["claim_id"], item["citation_key"])
        if pair in pairs:
            errors.append(f"comparison {index} duplicates a claim/work pair")
        pairs.add(pair)
        for field in ("prior_claim", "source_pointer", "source_excerpt", "difference"):
            if not nonempty(item.get(field)):
                errors.append(f"comparison {index} requires {field}")
        excerpt = item.get("source_excerpt")
        if nonempty(excerpt):
            if len(normalized(excerpt)) < 10:
                errors.append(f"comparison {index} source_excerpt is too short to verify")
            pages = extracted_by_key.get(item["citation_key"], [])
            pointer = item.get("source_pointer", "")
            page_match = re.search(r"\b(?:page|p\.)\s*(\d+)\b", pointer, re.IGNORECASE) if isinstance(pointer, str) else None
            if page_match:
                page = int(page_match.group(1))
                if page < 1 or page > len(pages):
                    errors.append(f"comparison {index} source_pointer page is outside the retained PDF")
                    pages = []
                else:
                    pages = [pages[page - 1]]
            if not any(normalized(excerpt) in normalized(page) for page in pages):
                errors.append(f"comparison {index} source_excerpt is not found at the retained source pointer")
        if item.get("overlap") not in OVERLAP:
            errors.append(f"comparison {index} overlap must be one of {sorted(OVERLAP)}")
        elif item["overlap"] in {"same", "uncertain"}:
            unresolved.append(pair)
    missing = set(claim_ids).difference({pair[0] for pair in pairs})
    if missing:
        errors.append(f"proposed claims lack comparisons: {sorted(missing)}")
    expected = {(claim, work) for claim in claim_ids for work in work_keys}
    if pairs != expected:
        errors.append("comparisons must cover every proposed claim against every nearest work exactly once")

    attestation = review.get("independent_review")
    decision = None
    if not isinstance(attestation, dict):
        errors.append("independent_review must be an object")
    else:
        decision = attestation.get("decision")
        if decision not in APPROVED | {"stop", "blocked"}:
            errors.append("independent_review decision is invalid")
        if not nonempty(attestation.get("reviewer_id")) or attestation.get("reviewer_id") == review.get("author_id"):
            errors.append("independent_review requires a reviewer distinct from the author")
        if attestation.get("independent_of_author") is not True:
            errors.append("independent_review requires independence attestation")
        if attestation.get("source_passages_verified") is not True:
            errors.append("independent_review must attest that cited full-text passages were checked")
        if attestation.get("source_dates_verified") is not True:
            errors.append("independent_review must attest that publication-date sources were checked")
        if day(attestation.get("reviewed_at")) is None or not nonempty(attestation.get("rationale")):
            errors.append("independent_review requires date and rationale")
        if decision != survey.get("decision"):
            errors.append("independent_review decision must match the survey decision")
    if not nonempty(review.get("author_id")):
        errors.append("author_id is required")
    if decision in {"proceed", "reframe"} and unresolved:
        errors.append("same or uncertain overlap requires reworking the claim before approval")
    if decision == "replicate" and any(item.get("overlap") == "uncertain" for item in comparisons if isinstance(item, dict)):
        errors.append("uncertain overlap must be resolved before replication approval")
    complete = not errors
    return {"valid": complete, "gate_passed": complete and decision in APPROVED,
            "evidence_complete": complete, "novelty_certified": False,
            "decision": decision, "errors": errors,
            "note": "This checks evidence, dates, coverage and attestation, not semantic originality."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--topic-survey", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="bind reviewed claims to final central manuscript claims")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        survey_bytes = args.topic_survey.read_bytes()
        manifest = ([json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
                    if args.manifest else None)
        report = validate(json.loads(args.review.read_text(encoding="utf-8")),
                          json.loads(survey_bytes), survey_bytes, args.root.resolve(), manifest)
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("passed" if report["gate_passed"] else "blocked")
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
