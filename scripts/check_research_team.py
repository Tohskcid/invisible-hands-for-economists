#!/usr/bin/env python3
"""Verify bounded multi-agent handoffs for a manuscript delivery."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


ROLES = {
    "empirical": {"literature", "planning", "data_acquisition", "data_cleaning", "model", "validation", "interpretation", "writing", "review"},
    "descriptive": {"literature", "planning", "data_acquisition", "data_cleaning", "model", "validation", "interpretation", "writing", "review"},
    "replication": {"literature", "planning", "data_acquisition", "data_cleaning", "validation", "interpretation", "writing", "review"},
    "structural": {"literature", "planning", "data_acquisition", "data_cleaning", "model", "validation", "interpretation", "writing", "review"},
    "theory": {"literature", "planning", "model", "validation", "interpretation", "writing", "review"},
}


def validate(report: object, root: Path, mode: str, review_path: Path | None = None) -> dict:
    errors = []
    if not isinstance(report, dict):
        return {"valid": False, "errors": ["team report must be an object"]}
    coordinator = report.get("coordinator_id")
    if not isinstance(coordinator, str) or not coordinator.strip():
        errors.append("team report requires coordinator_id")
    tasks = report.get("tasks")
    if not isinstance(tasks, list):
        return {"valid": False, "errors": errors + ["tasks must be a list"]}
    required = ROLES.get(mode)
    if required is None:
        errors.append(f"unsupported research mode: {mode}")
        required = set()
    seen, authors, reviewers = set(), set(), set()
    root = root.resolve()
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            errors.append(f"task {index} must be an object")
            continue
        role, agent = task.get("role"), task.get("agent_id")
        if not isinstance(role, str) or role not in required:
            errors.append(f"task {index} has an invalid role")
            continue
        if role in seen:
            errors.append(f"role {role} has multiple final handoffs")
        seen.add(role)
        if not isinstance(agent, str) or not agent.strip():
            errors.append(f"role {role} requires a named agent_id")
            continue
        (reviewers if role == "review" else authors).add(agent)
        if task.get("status") != "accepted" or task.get("accepted_by") != coordinator:
            errors.append(f"role {role} requires a PI-accepted handoff")
        artifacts = task.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"role {role} requires hash-bound artifacts")
            continue
        for item in artifacts:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
                errors.append(f"role {role} has an invalid artifact record")
                continue
            relative = PurePosixPath(item["path"])
            path = (root / relative).resolve()
            if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root) or not path.is_file():
                errors.append(f"role {role} artifact missing or outside project: {item['path']}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                errors.append(f"role {role} artifact changed: {item['path']}")
    missing = sorted(required - seen)
    if missing:
        errors.append(f"missing research roles: {missing}")
    if reviewers & authors:
        errors.append("review agent must be independent of research and writing agents")
    if len(authors) < 2 or len(reviewers) != 1:
        errors.append("manuscript delivery requires two research agents and one independent review agent")
    if review_path is not None:
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if not isinstance(review, dict) or review.get("reviewer_id") not in reviewers:
            errors.append("substantive review reviewer_id must match the team review agent")
        review_digest = hashlib.sha256(review_path.read_bytes()).hexdigest()
        review_artifacts = [item for task in tasks if isinstance(task, dict) and task.get("role") == "review" and isinstance(task.get("artifacts"), list)
                            for item in task.get("artifacts", []) if isinstance(item, dict) and isinstance(item.get("path"), str)]
        if not any((root / item.get("path", "")).resolve() == review_path.resolve()
                   and item.get("sha256") == review_digest for item in review_artifacts):
            errors.append("team review handoff must bind the substantive review file")
    return {"valid": not errors, "roles": sorted(seen), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--mode", choices=sorted(ROLES), required=True)
    parser.add_argument("--review", type=Path, help="bind the team review handoff to substantive review")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.report.read_text(encoding="utf-8")), args.root, args.mode, args.review)
    except (OSError, ValueError) as exc:
        result = {"valid": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
