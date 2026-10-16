#!/usr/bin/env python3
"""Verify that this experiment used the unchanged working-tree harness."""

import hashlib
import json
from pathlib import Path


def main():
    experiment = Path(__file__).resolve().parents[1]
    repository = experiment.parents[2]
    snapshot = json.loads((experiment / "research/harness-snapshot.json").read_text())
    mismatches = []
    for record in snapshot["files"]:
        for label, root in (("frozen", experiment / "harness"), ("repository", repository)):
            path = root / record["path"]
            if not path.is_file():
                mismatches.append({"tree": label, "path": record["path"], "reason": "missing"})
            elif hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                mismatches.append({"tree": label, "path": record["path"], "reason": "changed"})
    report = {
        "valid": not mismatches,
        "source_files": len(snapshot["files"]),
        "trees_checked": ["frozen", "repository"],
        "mismatches": mismatches,
    }
    destination = experiment / "research/snapshot-verification.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
