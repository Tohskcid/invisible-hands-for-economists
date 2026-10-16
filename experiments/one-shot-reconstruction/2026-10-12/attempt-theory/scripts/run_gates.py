"""Run the immutable harness and preserve its actual statuses, including failures."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT.parent / "harness/scripts"
RESEARCH = ROOT / "research"
env = os.environ.copy()
env.update({"openout_any": "r", "SOURCE_DATE_EPOCH": "1791763200", "FORCE_SOURCE_DATE": "1"})
commands = {
    "manifest": ["validate_research_manifest.py", "research/manifest.jsonl", "--require-argument-graph", "--json"],
    "claims": ["audit_claims.py", "paper/manuscript/main.tex", "research/manifest.jsonl", "--strict-numbers", "--require-central-claims", "--json"],
    "coverage": ["check_manuscript_coverage.py", "research/manuscript-coverage.json", "--manuscript", "paper/manuscript/main.tex", "--manifest", "research/manifest.jsonl", "--root", ".", "--require-ready", "--json"],
    "layout": ["check_project_layout.py", "--root", ".", "--json"],
    "literature_archive": ["check_literature_archive.py", "research/literature-archive.json", "--bibliography", "paper/references/references.bib", "--root", ".", "--require-complete", "--json"],
    "topic_survey": ["check_topic_survey.py", "research/topic-survey.json", "--root", ".", "--require-approved", "--json"],
}
if (RESEARCH / "logic-review.json").exists():
    commands["logic_review"] = ["check_logic_review.py", "--manuscript", "paper/manuscript/main.tex", "--manifest", "research/manifest.jsonl", "--review", "research/logic-review.json", "--require-pass", "--json"]
if (RESEARCH / "latex-visual-review.json").exists():
    commands["latex_finalize"] = ["check_latex.py", "finalize", "--report", "research/latex-report.json", "--visual-review", "research/latex-visual-review.json", "--output", "research/latex-final.json"]
if {"logic_review", "latex_finalize"}.issubset(commands):
    commands["package"] = ["check_research_package.py", "--root", "."]

gates = {}
for name, args in commands.items():
    command = [sys.executable, str(HARNESS / args[0]), *args[1:]]
    done = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=180)
    record = {"command": command, "exit_code": done.returncode, "passed": done.returncode == 0, "stdout": done.stdout, "stderr": done.stderr}
    try:
        record["report"] = json.loads(done.stdout)
    except json.JSONDecodeError:
        pass
    gates[name] = record
    (RESEARCH / (name + "-gate.json")).write_text(json.dumps(record, indent=2) + "\n")

for name in ["latex-report", "latex-as-is-failure"]:
    path = RESEARCH / (name + ".json")
    if path.exists():
        value = json.loads(path.read_text())
        gates[name] = {"report_path": str(path.relative_to(ROOT)), "passed": value.get("automated_passed", False), "report": value}

record = {"schema_version": "1", "harness_modified": False, "runtime_compatibility": {"openout_any": "r", "scope": "child processes only, permitting BibTeX absolute build paths; no global TeX settings modified", "SOURCE_DATE_EPOCH": "1791763200", "FORCE_SOURCE_DATE": "1", "overfull_limit": "unchanged zero"}, "gates": gates, "formal_verification": {"status": "not applicable to a claimed human-readable paper proof", "lean_available": shutil.which("lean") is not None, "lake_available": shutil.which("lake") is not None, "kernel_verified": False, "reason": "No Lean installation or externally locked theorem task; no install authorized and no formal-proof claim."}, "all_applicable_gates_passed": all(v["passed"] for v in gates.values()), "limitations": ["Topic survey and complete literature archive remain real blocking generic manuscript gates; no pass is fabricated.", "As-is compiler failure is retained separately from the child-process-compatible compile pass."]}
(RESEARCH / "gate-results.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"gates": {k: v["passed"] for k, v in gates.items()}, "all_applicable_gates_passed": record["all_applicable_gates_passed"]}, indent=2))
