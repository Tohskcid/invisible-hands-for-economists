#!/usr/bin/env python3
"""Validate LLM-assisted text-as-data annotation, inter-coder reliability, and prompt determinism."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


REQUIRED_DIAGNOSTICS = {
    "inter-coder-reliability",
    "prompt-drift-invariance",
    "deterministic-temperature",
    "hallucination-rate",
    "context-window-truncation",
}
STATUSES = {"pass", "fail", "inconclusive", "blocked"}
METRICS = {"cohen_kappa", "krippendorff_alpha", "f1_score", "accuracy"}
MIN_SCORES = {
    "cohen_kappa": 0.70,
    "krippendorff_alpha": 0.70,
    "f1_score": 0.85,
    "accuracy": 0.85,
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
UNPINNED_MODELS = re.compile(r"^(gpt-4|gpt-3\.5-turbo|claude-3|gemini|latest|default)$", re.IGNORECASE)


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

    for field in ("task_description", "model_version", "prompt_template", "prompt_sha256"):
        if not isinstance(document.get(field), str) or not document[field].strip():
            errors.append(f"{field} must be a non-empty string")

    model_version = document.get("model_version")
    if isinstance(model_version, str) and UNPINNED_MODELS.fullmatch(model_version.strip()):
        errors.append(f"model_version {model_version!r} is unpinned; specify exact snapshot version")

    prompt_hash = document.get("prompt_sha256")
    if isinstance(prompt_hash, str) and not SHA256.fullmatch(prompt_hash):
        errors.append("prompt_sha256 must be a 64-character lowercase hex SHA-256 hash")

    temp = document.get("temperature")
    if not isinstance(temp, (int, float)) or temp != 0:
        errors.append("temperature must be exactly 0 (or 0.0) for deterministic scientific reproduction")

    # Human audit & reliability validation
    human_audit = document.get("human_audit")
    metric_passed = False
    if not isinstance(human_audit, dict):
        errors.append("human_audit must be an object")
    else:
        sample_size = human_audit.get("sample_size")
        if not isinstance(sample_size, int) or sample_size < 100:
            errors.append("human_audit.sample_size must be an integer >= 100")

        metric = human_audit.get("metric")
        if metric not in METRICS:
            errors.append(f"human_audit.metric must be one of {sorted(METRICS)}")

        score = human_audit.get("score")
        if not isinstance(score, (int, float)):
            errors.append("human_audit.score must be a number")
        elif metric in MIN_SCORES:
            if score < MIN_SCORES[metric]:
                errors.append(
                    f"human_audit.score {score} is below required threshold {MIN_SCORES[metric]} for {metric}"
                )
            else:
                metric_passed = True

        artifact = human_audit.get("artifact")
        digest = human_audit.get("artifact_sha256")
        if not safe_relative(artifact):
            errors.append("human_audit has unsafe or missing artifact path")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append("human_audit requires a lowercase 64-character artifact_sha256")
        elif root is not None and safe_relative(artifact):
            target = root / artifact
            if not target.is_file():
                errors.append(f"human_audit artifact does not exist: {artifact}")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                errors.append("human_audit artifact checksum mismatch")

    # Diagnostics verification
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

    for diagnostic_id in sorted(REQUIRED_DIAGNOSTICS - set(by_id)):
        errors.append(f"required diagnostic {diagnostic_id!r} is missing")

    nonpassing = sorted(
        key for key in REQUIRED_DIAGNOSTICS & set(by_id)
        if by_id[key].get("status") != "pass"
    )

    gate_passed = not errors and not nonpassing and metric_passed
    return {
        "valid": not errors,
        "gate_passed": gate_passed,
        "required_diagnostics": sorted(REQUIRED_DIAGNOSTICS),
        "nonpassing": nonpassing,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path, help="Path to text-audit.json")
    parser.add_argument("--root", type=Path, help="Root directory to verify artifact existence and sha256")
    parser.add_argument("--require-pass", action="store_true", help="Require all diagnostics and reliability thresholds to pass")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if not args.audit.is_file():
        print(f"[Error] File not found: {args.audit}", file=sys.stderr)
        return 2

    try:
        document = json.loads(args.audit.read_text(encoding="utf-8"))
        report = validate(document, args.root.resolve() if args.root else None)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot read text audit file: {exc}", file=sys.stderr)
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
