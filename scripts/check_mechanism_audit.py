#!/usr/bin/env python3
"""Validate hash-bound tests that distinguish a claimed mechanism from alternatives."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


SHA256 = re.compile(r"^[0-9a-f]{64}$")
TEST_STATUSES = {"distinguished", "not-distinguished", "inconclusive", "blocked"}
VERDICTS = {"pass", "revise", "unsupported"}
REVIEW_VERDICTS = {"pass", "revise", "reject"}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_review(review: object, audit_path: Path) -> list[str]:
    if not isinstance(review, dict):
        return ["mechanism review must be a JSON object"]
    errors = []
    if review.get("schema_version") != "1":
        errors.append("review schema_version must be '1'")
    expected = {"mechanism_audit": file_hash(audit_path)}
    if review.get("reviewed_sha256") != expected:
        errors.append("reviewed_sha256 must match the current mechanism audit")
    if review.get("independent_context") is not True:
        errors.append("mechanism review must be performed in independent_context")
    verdict = review.get("verdict")
    if verdict not in REVIEW_VERDICTS:
        errors.append(f"review verdict must be one of {sorted(REVIEW_VERDICTS)}")
    for field in (
        "weakest_link",
        "observationally_equivalent_explanation",
        "discriminating_test_assessment",
        "required_revision",
    ):
        if not isinstance(review.get(field), str):
            errors.append(f"review {field} must be a string")
    if verdict == "pass" and review.get("required_revision"):
        errors.append("a passing mechanism review cannot require a revision")
    return errors


def validate(
    document: object,
    root: Path | None = None,
    review: object | None = None,
    audit_path: Path | None = None,
    require_pass: bool = False,
) -> dict:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {
            "valid": False,
            "gate_passed": False,
            "iteration_required": True,
            "return_to": "mechanism_specification",
            "errors": ["mechanism audit must be a JSON object"],
        }
    if document.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    for field in ("claim_id", "claim", "bounded_conclusion"):
        if not nonempty(document.get(field)):
            errors.append(f"{field} must be a non-empty string")

    preferred = document.get("preferred_mechanism")
    if not isinstance(preferred, dict):
        errors.append("preferred_mechanism must be an object")
        preferred = {}
    for field in ("id", "statement", "distinctive_prediction"):
        if not nonempty(preferred.get(field)):
            errors.append(f"preferred_mechanism.{field} must be a non-empty string")
    chain = preferred.get("causal_chain")
    if not isinstance(chain, list) or len(chain) < 2 or not all(nonempty(item) for item in chain):
        errors.append("preferred_mechanism.causal_chain must contain at least two non-empty steps")

    alternatives = document.get("alternatives")
    if not isinstance(alternatives, list):
        errors.append("alternatives must be a list")
        alternatives = []
    elif len(alternatives) < 3:
        errors.append("at least three competing alternatives are required")
    alternative_ids: list[str] = []
    for index, alternative in enumerate(alternatives):
        if not isinstance(alternative, dict):
            errors.append(f"alternatives[{index}] must be an object")
            continue
        for field in ("id", "statement", "observable_implication"):
            if not nonempty(alternative.get(field)):
                errors.append(f"alternatives[{index}].{field} must be a non-empty string")
        if nonempty(alternative.get("id")):
            alternative_ids.append(alternative["id"])
    if len(set(alternative_ids)) != len(alternative_ids):
        errors.append("alternative ids must be unique")
    if preferred.get("id") in alternative_ids:
        errors.append("preferred mechanism id must differ from alternative ids")

    tests = document.get("tests")
    if not isinstance(tests, list):
        errors.append("tests must be a list")
        tests = []
    test_ids: list[str] = []
    covered: dict[str, list[str]] = {alternative_id: [] for alternative_id in alternative_ids}
    for index, test in enumerate(tests):
        if not isinstance(test, dict):
            errors.append(f"tests[{index}] must be an object")
            continue
        for field in (
            "id",
            "alternative_id",
            "preferred_prediction",
            "alternative_prediction",
            "design",
            "decision_rule",
            "finding",
        ):
            if not nonempty(test.get(field)):
                errors.append(f"tests[{index}].{field} must be a non-empty string")
        test_id = test.get("id")
        if nonempty(test_id):
            test_ids.append(test_id)
        alternative_id = test.get("alternative_id")
        if alternative_id not in covered:
            errors.append(f"tests[{index}].alternative_id must name a declared alternative")
        else:
            covered[alternative_id].append(test.get("status"))
        if test.get("preferred_prediction") == test.get("alternative_prediction"):
            errors.append(f"tests[{index}] must encode opposing predictions")
        if test.get("status") not in TEST_STATUSES:
            errors.append(f"tests[{index}].status must be one of {sorted(TEST_STATUSES)}")
        artifact = test.get("artifact")
        digest = test.get("artifact_sha256")
        if not safe_relative(artifact):
            errors.append(f"tests[{index}].artifact must be a safe relative path")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"tests[{index}].artifact_sha256 must be a lowercase SHA-256")
        elif root is not None and safe_relative(artifact):
            path = root / artifact
            if not path.is_file():
                errors.append(f"tests[{index}] artifact does not exist: {artifact}")
            elif file_hash(path) != digest:
                errors.append(f"tests[{index}] artifact_sha256 does not match {artifact}")
    if len(set(test_ids)) != len(test_ids):
        errors.append("test ids must be unique")
    for alternative_id, statuses in covered.items():
        if not statuses:
            errors.append(f"alternative {alternative_id!r} has no discriminating test")

    nonpassing = sorted(
        alternative_id
        for alternative_id, statuses in covered.items()
        if "distinguished" not in statuses
    )
    unresolved = document.get("unresolved_alternatives")
    if not isinstance(unresolved, list) or not all(isinstance(item, str) for item in unresolved):
        errors.append("unresolved_alternatives must be a list of alternative ids")
    elif set(unresolved) != set(nonpassing):
        errors.append("unresolved_alternatives must exactly match alternatives not distinguished by evidence")
    verdict = document.get("overall_verdict")
    if verdict not in VERDICTS:
        errors.append(f"overall_verdict must be one of {sorted(VERDICTS)}")
    if verdict == "pass" and nonpassing:
        errors.append("overall_verdict cannot pass with unresolved alternatives")
    if verdict != "pass" and not nonpassing:
        errors.append("a nonpassing overall_verdict requires an unresolved alternative")
    claim_status = document.get("claim_status")
    if claim_status not in {"mechanism-supported", "consistent-with", "unsupported"}:
        errors.append("claim_status must be mechanism-supported, consistent-with, or unsupported")
    elif verdict == "pass" and claim_status != "mechanism-supported":
        errors.append("a passing mechanism audit requires claim_status mechanism-supported")
    elif verdict != "pass" and claim_status == "mechanism-supported":
        errors.append("an unresolved mechanism cannot have claim_status mechanism-supported")

    audit_passed = not errors and verdict == "pass" and not nonpassing
    review_errors: list[str] = []
    review_passed = False
    if review is not None:
        if audit_path is None:
            review_errors.append("audit_path is required to validate the mechanism review")
        else:
            review_errors = validate_review(review, audit_path)
            review_passed = not review_errors and review.get("verdict") == "pass"
    elif require_pass:
        review_errors.append("an independent hash-bound mechanism review is required for delivery")

    all_errors = errors + review_errors
    gate_passed = audit_passed and (review_passed if require_pass else not review_errors)
    if errors:
        return_to = "mechanism_specification"
    elif nonpassing or verdict != "pass":
        return_to = "evidence_generation"
    elif review_errors or (review is not None and not review_passed):
        return_to = "independent_mechanism_review"
    else:
        return_to = None
    return {
        "valid": not all_errors,
        "gate_passed": gate_passed,
        "iteration_required": not gate_passed,
        "return_to": return_to,
        "nonpassing_alternatives": nonpassing,
        "errors": all_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--root", type=Path, help="verify artifact paths and hashes below this root")
    parser.add_argument("--review", type=Path, help="independent, hash-bound mechanism review")
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.audit.read_text(encoding="utf-8"))
        review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
        report = validate(
            document,
            args.root.resolve() if args.root else None,
            review,
            args.audit,
            args.require_pass,
        )
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot read mechanism audit: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("pass" if report["gate_passed"] else "not passed")
        for error in report["errors"]:
            print(f"- {error}")
        if report["return_to"]:
            print(f"- return_to: {report['return_to']}")
    failed = not report["valid"] or (args.require_pass and not report["gate_passed"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
