#!/usr/bin/env python3
"""Check that an independent, current whole-paper review covers research risks."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


DIMENSIONS = {"novelty", "overlap", "research_design", "inference_or_proof", "logic", "completeness"}


def validate(review: object, manuscript: Path, survey: Path | None = None, root: Path | None = None) -> dict:
    if not isinstance(review, dict):
        return {"valid": False, "errors": ["substantive review must be an object"]}
    errors = []
    text = manuscript.read_text(encoding="utf-8")
    if review.get("manuscript_sha256") != hashlib.sha256(manuscript.read_bytes()).hexdigest():
        errors.append("review does not bind the current manuscript")
    if survey is not None and review.get("topic_survey_sha256") != hashlib.sha256(survey.read_bytes()).hexdigest():
        errors.append("review does not bind the current topic survey")
    reviewer, authors = review.get("reviewer_id"), review.get("author_agent_ids")
    if not isinstance(reviewer, str) or not reviewer.strip():
        errors.append("review requires reviewer_id")
    if not isinstance(authors, list) or not authors or any(not isinstance(value, str) or not value.strip() for value in authors):
        errors.append("review requires author_agent_ids")
    elif reviewer in authors:
        errors.append("reviewer must be independent of the author agents")
    if review.get("verdict") != "pass":
        errors.append("substantive review verdict must be pass for delivery")
    dimensions = review.get("dimensions")
    root = (root or manuscript.parent).resolve()
    if not isinstance(dimensions, dict) or set(dimensions) != DIMENSIONS:
        errors.append(f"review dimensions must be exactly {sorted(DIMENSIONS)}")
    else:
        for name, item in dimensions.items():
            if not isinstance(item, dict) or item.get("verdict") != "pass" or not isinstance(item.get("reason"), str) or not item["reason"].strip():
                errors.append(f"dimension {name} needs a passing verdict and reason")
                continue
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"dimension {name} requires hash-bound evidence")
                continue
            bound_paths = set()
            for reference in evidence:
                if not isinstance(reference, dict) or not isinstance(reference.get("path"), str) or not isinstance(reference.get("sha256"), str):
                    errors.append(f"dimension {name} has an invalid evidence reference")
                    continue
                relative = PurePosixPath(reference["path"])
                path = (root / relative).resolve()
                if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root) or not path.is_file():
                    errors.append(f"dimension {name} evidence is missing or outside project")
                elif hashlib.sha256(path.read_bytes()).hexdigest() != reference["sha256"]:
                    errors.append(f"dimension {name} evidence changed")
                else:
                    bound_paths.add(path)
            if name in {"novelty", "overlap"} and survey is not None and survey.resolve() not in bound_paths:
                errors.append(f"dimension {name} must cite the current topic survey")
    limitations = review.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        errors.append("review requires explicit manuscript limitations")
    else:
        for index, item in enumerate(limitations, 1):
            if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip() for key in ("text_anchor", "effect_on_claim", "boundary_or_mitigation")):
                errors.append(f"limitation {index} requires text_anchor, effect_on_claim, and boundary_or_mitigation")
            elif item["text_anchor"] not in text:
                errors.append(f"limitation {index} text_anchor is absent from manuscript")
    if review.get("open_critical_issues") != []:
        errors.append("open_critical_issues must be an empty list for delivery")
    return {"valid": not errors, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--topic-survey", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.review.read_text(encoding="utf-8")), args.manuscript, args.topic_survey, args.root)
    except (OSError, ValueError) as exc:
        result = {"valid": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
