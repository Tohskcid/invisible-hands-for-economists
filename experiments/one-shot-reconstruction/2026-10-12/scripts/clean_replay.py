#!/usr/bin/env python3
"""Rebuild the empirical computation in a clean temporary project, without editing the attempt."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base = Path(__file__).resolve().parents[1]
    source = base / "attempt"
    canonical = json.loads((source / "research/results.json").read_text())
    expected = {
        "paper/manuscript/main.tex": sha(source / "paper/manuscript/main.tex"),
        **{str(p.relative_to(source)): sha(p) for p in (source / "output/tables").glob("*.tex")},
    }
    report = {
        "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Post-hoc frozen-input computational replay, not a new question-only research run or a full package pass.",
        "original_results_sha256": sha(source / "research/results.json"),
        "deleted_generated_outputs_before_run": True,
        "commands": [],
    }
    with tempfile.TemporaryDirectory(prefix="econ-reconstruction-replay-") as temporary:
        root = Path(temporary)
        attempt = root / "attempt"
        shutil.copytree(base / "harness", root / "harness", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(source, attempt, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "mpl-cache", "latex-build", "reproducibility-build",
            "pages", "build", "processed", "output"))
        for name in ["results.json", "results-detail.json", "base-r-verification.json", "manifest.jsonl",
                     "manuscript-coverage.json", "design-audit.json", "environment.json"]:
            path = attempt / "research" / name
            if path.exists():
                path.unlink()
        sections = attempt / "research/sections"
        if sections.exists():
            shutil.rmtree(sections)
        for name in ["data/processed", "output/tables", "output/figures", "output/pdf", "research/sections"]:
            (attempt / name).mkdir(parents=True, exist_ok=True)
        assert not (attempt / "research/results.json").exists()
        assert not list((attempt / "output/tables").iterdir())
        env = os.environ.copy()
        env["MPLCONFIGDIR"] = str(attempt / "research/mpl-cache")
        for command in [[sys.executable, "scripts/analyze.py"], ["Rscript", "scripts/verify.R"],
                        [sys.executable, "scripts/build_package.py"]]:
            completed = subprocess.run(command, cwd=attempt, env=env, capture_output=True,
                                       text=True, timeout=180, check=False)
            report["commands"].append({"command": command, "exit_code": completed.returncode,
                                       "stdout": completed.stdout, "stderr": completed.stderr})
            if completed.returncode:
                report["passed"] = False
                break
        else:
            regenerated = json.loads((attempt / "research/results.json").read_text())
            r = json.loads((attempt / "research/base-r-verification.json").read_text())
            primary = regenerated["results"]["primary"]
            report["results_tree_exact_match"] = regenerated["results"] == canonical["results"]
            report["base_r_primary_agreement"] = all(
                abs(r[r_key] - primary[p_key]) < 1e-10
                for r_key, p_key in [("estimate", "estimate"),
                                     ("se_homoskedastic", "se_homoskedastic"),
                                     ("se_hc1", "std_error")]) and r["n"] == primary["n"]
            report["regenerated_text_and_tables"] = {
                name: {"expected_sha256": digest, "actual_sha256": sha(attempt / name),
                       "match": sha(attempt / name) == digest}
                for name, digest in expected.items()
            }
            report["passed"] = (report["results_tree_exact_match"] and report["base_r_primary_agreement"]
                                and all(item["match"] for item in report["regenerated_text_and_tables"].values()))
            report["computed_primary"] = {key: primary[key] for key in ["estimate", "std_error", "n", "n_nj", "n_pa"]}
    destination = base / "research/clean-replay.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ["passed", "results_tree_exact_match", "base_r_primary_agreement"]
                      if key in report}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
