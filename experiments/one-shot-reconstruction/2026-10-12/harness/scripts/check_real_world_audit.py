#!/usr/bin/env python3
"""Validate whether research claims support a specified real-world decision."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


REQUIRED = {
    "target-population",
    "institutional-match",
    "measurement-validity",
    "data-freshness",
    "transportability",
    "decision-sensitivity",
    "implementation-feasibility",
    "distributional-effects",
    "equilibrium-response",
    "monitoring-plan",
}
STATUSES = {"pass", "fail", "inconclusive", "blocked", "not_applicable"}
CONCLUSIONS = {"applicable", "provisional", "research-only", "blocked", "contradicted"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def validate(document: object, root: Path | None = None) -> dict:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "gate_passed": False, "errors": ["audit must be a JSON object"]}
    if document.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    for field in (
        "decision_maker", "target_decision", "deployment_context", "target_population",
        "time_horizon", "acceptable_failure",
    ):
        if not isinstance(document.get(field), str) or not document[field].strip():
            errors.append(f"{field} must be a non-empty string")
    conclusion = document.get("conclusion")
    if conclusion not in CONCLUSIONS:
        errors.append(f"conclusion must be one of {sorted(CONCLUSIONS)}")

    diagnostics = document.get("diagnostics")
    if not isinstance(diagnostics, list):
        errors.append("diagnostics must be a list")
        diagnostics = []
    by_id: dict[str, dict] = {}
    for index, item in enumerate(diagnostics, 1):
        if not isinstance(item, dict):
            errors.append(f"diagnostic {index} must be an object")
            continue
        diagnostic_id = item.get("id")
        if not isinstance(diagnostic_id, str) or not diagnostic_id:
            errors.append(f"diagnostic {index} requires id")
            continue
        if diagnostic_id in by_id:
            errors.append(f"duplicate diagnostic {diagnostic_id!r}")
        else:
            by_id[diagnostic_id] = item
        if item.get("status") not in STATUSES:
            errors.append(f"diagnostic {diagnostic_id!r} has invalid status")
        if not isinstance(item.get("finding"), str) or not item["finding"].strip():
            errors.append(f"diagnostic {diagnostic_id!r} requires finding")
        artifact = item.get("artifact")
        digest = item.get("artifact_sha256")
        if not safe_relative(artifact):
            errors.append(f"diagnostic {diagnostic_id!r} has unsafe artifact path")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"diagnostic {diagnostic_id!r} requires a lowercase artifact_sha256")
        elif root is not None and safe_relative(artifact):
            target = root / artifact
            if not target.is_file():
                errors.append(f"diagnostic {diagnostic_id!r} artifact does not exist: {artifact}")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                errors.append(f"diagnostic {diagnostic_id!r} artifact checksum mismatch")

    for diagnostic_id in sorted(REQUIRED - set(by_id)):
        errors.append(f"required diagnostic {diagnostic_id!r} is missing")
    nonpassing = sorted(
        key for key in REQUIRED & set(by_id)
        if by_id[key].get("status") not in {"pass", "not_applicable"}
    )
    gate_passed = not errors and not nonpassing and conclusion == "applicable"
    return {
        "valid": not errors,
        "gate_passed": gate_passed,
        "conclusion": conclusion,
        "required": sorted(REQUIRED),
        "nonpassing": nonpassing,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--root", type=Path, help="require artifact paths to exist below this root")
    parser.add_argument("--require-applicable", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.audit.read_text(encoding="utf-8"))
        report = validate(document, args.root.resolve() if args.root else None)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot read real-world audit: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("applicable" if report["gate_passed"] else report.get("conclusion") or "not passed")
        for error in report["errors"]:
            print(f"- {error}")
        if report["nonpassing"]:
            print(f"- nonpassing diagnostics: {', '.join(report['nonpassing'])}")
    failed = not report["valid"] or (args.require_applicable and not report["gate_passed"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
