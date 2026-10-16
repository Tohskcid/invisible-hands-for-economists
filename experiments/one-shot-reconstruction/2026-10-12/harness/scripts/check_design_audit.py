#!/usr/bin/env python3
"""Validate design-specific empirical diagnostics without imposing universal tests."""

import argparse
import json
import sys
from pathlib import Path, PurePosixPath


COMMON = {"assignment", "support", "inference"}
REQUIRED = {
    "randomized": {"randomization-unit", "noncompliance", "attrition", "interference"},
    "did": {"timing", "comparison-groups", "anticipation", "parallel-trends", "spillovers", "heterogeneous-effects"},
    "iv": {"relevance", "independence", "exclusion", "monotonicity", "weak-identification", "complier-scope"},
    "rdd": {"threshold-rule", "manipulation", "continuity", "local-support", "bandwidth"},
    "fuzzy-rdd": {"threshold-rule", "manipulation", "continuity", "local-support", "bandwidth", "first-stage", "exclusion", "monotonicity", "weak-identification", "complier-scope"},
    "synthetic-control": {"donor-pool", "pre-fit", "placebo-distribution", "anticipation", "donor-contamination"},
    "selection-on-observables": {"covariate-timing", "overlap", "balance", "hidden-confounding-sensitivity"},
    "panel-fe": {"within-variation", "exogeneity", "dynamics", "serial-dependence"},
    "interrupted-time-series": {"pre-trend", "seasonality", "concurrent-shocks", "autocorrelation"},
    "finance-event-study": {"event-time", "information-leakage", "confounding-news", "normal-return-model", "cross-sectional-dependence"},
    "spatial-network": {"exposure-mapping", "interference", "network-formation", "spatial-dependence"},
}
STATUSES = {"pass", "fail", "inconclusive", "blocked"}


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def validate(document: object, root: Path | None = None) -> dict:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "gate_passed": False, "errors": ["audit must be a JSON object"]}
    design = document.get("design")
    if design not in REQUIRED:
        errors.append(f"design must be one of {sorted(REQUIRED)}")
        required: set[str] = set()
    else:
        required = COMMON | REQUIRED[design]
    for field in ("estimand", "assignment_narrative", "interpretation_boundary"):
        if not isinstance(document.get(field), str) or not document[field].strip():
            errors.append(f"{field} must be a non-empty string")

    diagnostics = document.get("diagnostics")
    by_id: dict[str, dict] = {}
    if not isinstance(diagnostics, list):
        errors.append("diagnostics must be a list")
        diagnostics = []
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
        for field in ("finding", "artifact"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"diagnostic {diagnostic_id!r} requires {field}")
        artifact = item.get("artifact")
        if not safe_relative(artifact):
            errors.append(f"diagnostic {diagnostic_id!r} has unsafe artifact path")
        elif root is not None and not (root / artifact).is_file():
            errors.append(f"diagnostic {diagnostic_id!r} artifact does not exist: {artifact}")

    missing = sorted(required - set(by_id))
    for diagnostic_id in missing:
        errors.append(f"required diagnostic {diagnostic_id!r} is missing")
    nonpassing = sorted(key for key in required & set(by_id) if by_id[key].get("status") != "pass")
    return {
        "valid": not errors,
        "gate_passed": not errors and not nonpassing,
        "design": design,
        "required": sorted(required),
        "nonpassing": nonpassing,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--root", type=Path, help="require artifact paths to exist below this root")
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.audit.is_file():
        print(f"[Error] File not found: {args.audit}", file=sys.stderr)
        return 2
    try:
        document = json.loads(args.audit.read_text(encoding="utf-8"))
        report = validate(document, args.root.resolve() if args.root else None)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot read design audit: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("pass" if report["gate_passed"] else "not passed")
        for error in report["errors"]:
            print(f"- {error}")
        if report["nonpassing"]:
            print(f"- nonpassing diagnostics: {', '.join(report['nonpassing'])}")
    failed = not report["valid"] or (args.require_pass and not report["gate_passed"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
