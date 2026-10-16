#!/usr/bin/env python3
"""Orchestrate reproducibility, manuscript build, and research-package checks.

Implements the 5-phase harness optimization workflow:
1. Frozen contract & delivery profile initialization (WP1)
2. Feasibility, claim graph & obligation registration (WP2)
3. Scientific obstacle registration & clean computational replay (WP3, WP4)
4. Preflight-locked single-build LaTeX compilation & visual review (WP6)
5. Multi-layer deterministic package audit & release verification (WP1-WP6)

This runner validates supplied artifacts; it does not draft a paper or resolve
scientific obstacles without researcher evidence and interpretation.
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path, PurePosixPath


def log_event(ledger_path: Path, event: dict) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **event,
    }
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_ledger_events(ledger_path: Path) -> list[dict]:
    if not ledger_path.is_file():
        return []
    events = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


GATE_TASKS = {
    "check_topic_survey.py": ("literature", "Verify nearest research and the contribution decision", True),
    "check_data_provenance.py": ("data", "Acquire and verify source data, access, license, and hashes", True),
    "check_literature_archive.py": ("literature", "Retrieve cited sources or record access gaps", True),
    "validate_research_manifest.py": ("argument", "Repair claim, evidence, and obligation links", True),
    "check_design_audit.py": ("design", "Run identification diagnostics and assess inference", True),
    "check_structural_audit.py": ("design", "Test structural identification and computation", True),
    "check_manuscript_coverage.py": ("manuscript", "Complete the missing evidence-backed sections", True),
    "check_logic_review.py": ("review", "Review central claims and weakest links", True),
    "check_result_bindings.py": ("analysis", "Regenerate results and align manuscript numbers", False),
    "run_replication.py": ("replication", "Repair clean replay or inconsistent generated artifacts", False),
    "check_latex.py": ("delivery", "Repair the build and inspect every rendered page", True),
    "check_research_team.py": ("review", "Complete and verify independent agent handoffs", True),
    "check_substantive_review.py": ("review", "Obtain a current independent review of novelty, validity, logic, and limitations", True),
}

STAGE_ORDER = ("package", "literature", "data", "design", "argument", "analysis", "replication", "manuscript", "review", "delivery")


def rework_plan(tasks: list[dict]) -> dict | None:
    if not tasks:
        return None
    aliases = {"scientific_obstacle": "design", "gate_remediation": "package"}
    stages = [aliases.get(task.get("stage"), task.get("stage")) for task in tasks]
    restart = min((stage for stage in stages if stage in STAGE_ORDER), key=STAGE_ORDER.index, default="package")
    return {"restart_from": restart, "invalidate_stages": list(STAGE_ORDER[STAGE_ORDER.index(restart):]),
            "reason_sources": [task.get("source") for task in tasks]}


def save_rework_state(root: Path, result: dict) -> None:
    path = root / "research/rework-state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {"status": "open" if result.get("rework_plan") else "cleared" if result.get("status") == "complete" else "pending",
             "workflow_status": result.get("status"), "rework_plan": result.get("rework_plan"),
             "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def plan_next_tasks(package_report: dict | None, obstacles: list[dict],
                    replay_report: dict | None = None, latex_report: dict | None = None) -> list[dict]:
    tasks = []
    if replay_report is not None and replay_report.get("reproducible") is not True:
        tasks.append({"stage": "replication", "source": "run_replication.py",
                      "instruction": "Repair the clean replay and regenerate matching outputs",
                      "reason": replay_report.get("errors") or replay_report.get("error") or replay_report,
                      "requires_scientific_judgment": False})
    if latex_report is not None and latex_report.get("finalize", {}).get("delivery_ready") is not True:
        tasks.append({"stage": "delivery", "source": "check_latex.py",
                      "instruction": "Repair the manuscript build and review the exact rendered PDF",
                      "reason": latex_report.get("finalize", {}).get("errors") or latex_report.get("check", {}).get("error") or latex_report,
                      "requires_scientific_judgment": True})
    for obstacle in obstacles:
        if obstacle.get("status") != "resolved":
            tasks.append({
                "stage": "scientific_obstacle", "source": obstacle.get("obstacle_id"),
                "instruction": "Interpret a discriminating test or obtain missing evidence; record a hash-bound assessment",
                "reason": obstacle.get("assessment_errors") or obstacle.get("outcome"),
                "requires_scientific_judgment": True,
            })
    if package_report is None:
        tasks.append({"stage": "package", "source": "research/package.json", "instruction": "Declare the frozen delivery profile and required artifacts", "reason": "package audit has not run", "requires_scientific_judgment": False})
    elif package_report.get("error"):
        tasks.append({"stage": "package", "source": "research/package.json", "instruction": "Repair the package contract or configuration", "reason": package_report["error"], "requires_scientific_judgment": False})
    else:
        for check in package_report.get("checks", []):
            if check.get("passed") is True:
                continue
            command = check.get("command", [])
            gate = Path(command[1]).name if len(command) > 1 else "unknown"
            stage, instruction, scientific = GATE_TASKS.get(gate, ("gate_remediation", "Inspect and repair the failed gate", False))
            try:
                detail = json.loads(check.get("stdout", ""))
                reason = detail.get("errors") or detail.get("error") or check.get("stderr")
            except (ValueError, AttributeError):
                reason = check.get("stderr") or check.get("stdout")
            tasks.append({"stage": stage, "source": gate, "instruction": instruction,
                          "reason": reason, "requires_scientific_judgment": scientific})
    return tasks


class ResearchWorkflow:
    def __init__(self, root: Path, contract: dict, scripts_dir: Path | None = None):
        self.root = root.resolve()
        self.contract = contract
        self.scripts_dir = (scripts_dir or Path(__file__).resolve().parent).resolve()
        self.ledger_path = self.root / "research/ledger.jsonl"
        self.package_config_path = self.root / "research/package.json"
        self.manifest_path = self.root / "research/manifest.jsonl"
        self.results_path = self.root / "research/results.json"
        self.assessments_path = self.root / "research/obstacle-assessments.json"
        self.python = sys.executable

    def get_spent_budget(self) -> float:
        events = load_ledger_events(self.ledger_path)
        return sum(float(e.get("cost", 0.0)) for e in events if isinstance(e.get("cost"), (int, float)))

    def initialize_contract(self) -> dict:
        mode = self.contract.get("mode", "empirical")
        deliverable = self.contract.get("deliverable", "manuscript")
        claim_scope = self.contract.get("claim_scope", "research-only")
        mechanism_scope = self.contract.get("mechanism_scope", "not-claimed")

        contract_record = {
            "version": "1.0",
            "inputs": self.contract,
            "mode": mode,
            "deliverable": deliverable,
            "claim_scope": claim_scope,
            "mechanism_scope": mechanism_scope,
            "max_budget": float(self.contract.get("max_budget", 10.0)),
            "budget_unit": "measured_wall_seconds",
            "target_journal": self.contract.get("target_journal", "AER"),
            "question": self.contract.get("question", ""),
            "obligations": self.contract.get("obligations", []),
        }
        (self.root / "research").mkdir(parents=True, exist_ok=True)
        contract_file = self.root / "research/contract.json"
        if contract_file.is_file():
            existing = json.loads(contract_file.read_text(encoding="utf-8"))
            if existing != contract_record:
                raise ValueError("research contract changed after it was frozen")
        else:
            contract_file.write_text(
                json.dumps(contract_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            log_event(self.ledger_path, {
                "event_type": "contract_frozen",
                "contract": contract_record,
                "cost": 0.0,
            })
        return contract_record

    def run_clean_replay(self, entry_commands: list[list[str]], raw_inputs: list[str], generated: list[str]) -> dict:
        started = time.monotonic()
        cmd = [
            self.python, str(self.scripts_dir / "run_replication.py"),
            "--root", str(self.root),
            "--clean",
            "--json",
        ]
        for c in entry_commands:
            cmd.extend(["--command", *c])
        if raw_inputs:
            cmd.extend(["--raw-inputs", *raw_inputs])
        if generated:
            cmd.extend(["--generated", *generated])
        if self.results_path.is_file():
            cmd.extend(["--results", str(self.results_path)])

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        try:
            report = json.loads(res.stdout)
        except json.JSONDecodeError:
            report = {"reproducible": False, "error": res.stderr.strip() or res.stdout.strip()}

        log_event(self.ledger_path, {
            "event_type": "clean_replay",
            "passed": report.get("reproducible") is True,
            "report": report,
            "cost": round(time.monotonic() - started, 6),
        })
        return report

    def compile_single_build(self, main_tex: Path, build_dir: Path, visual_review_path: Path, engine: str = "auto") -> dict:
        started = time.monotonic()
        main_tex = main_tex.resolve()
        build_dir = build_dir.resolve()
        visual_review_path = visual_review_path.resolve()
        report_file = build_dir / "report.json"

        if report_file.is_file():
            check_data = json.loads(report_file.read_text(encoding="utf-8"))
            if engine != "auto" and check_data.get("compilation", {}).get("engine") != engine:
                check_data = {"automated_passed": False, "error": "existing build uses a different LaTeX engine"}
        else:
            check_cmd = [
                self.python, str(self.scripts_dir / "check_latex.py"), "check",
                "--main", str(main_tex),
                "--build-dir", str(build_dir),
                "--report", str(report_file),
                "--engine", engine,
            ]
            check_res = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
            try:
                check_data = json.loads(check_res.stdout)
            except json.JSONDecodeError:
                check_data = {"automated_passed": False, "error": check_res.stderr.strip()}

        # 2. Finalize review if automated compilation passed
        finalize_data = {"delivery_ready": False}
        if check_data.get("automated_passed"):
            fin_cmd = [
                self.python, str(self.scripts_dir / "check_latex.py"), "finalize",
                "--report", str(report_file),
                "--visual-review", str(visual_review_path),
            ]
            fin_res = subprocess.run(fin_cmd, capture_output=True, text=True, check=False)
            try:
                finalize_data = json.loads(fin_res.stdout)
            except json.JSONDecodeError:
                finalize_data = {"delivery_ready": False, "error": fin_res.stderr.strip()}

        log_event(self.ledger_path, {
            "event_type": "latex_build",
            "automated_passed": check_data.get("automated_passed") is True,
            "delivery_ready": finalize_data.get("delivery_ready") is True,
            "cost": round(time.monotonic() - started, 6),
        })
        return {"check": check_data, "finalize": finalize_data}

    def verify_research_package(self) -> dict:
        started = time.monotonic()
        cmd = [
            self.python, str(self.scripts_dir / "check_research_package.py"),
            "--root", str(self.root),
            "--config", str(self.package_config_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        try:
            report = json.loads(res.stdout)
        except json.JSONDecodeError:
            report = {"valid": False, "error": res.stderr.strip() or res.stdout.strip()}

        log_event(self.ledger_path, {
            "event_type": "package_audit",
            "valid": report.get("valid") is True,
            "return_to": report.get("return_to", []),
            "cost": round(time.monotonic() - started, 6),
        })
        return report

    def obstacle_assessment(self, obstacle_id: str) -> tuple[dict | None, list[str]]:
        if not self.assessments_path.is_file():
            return None, []
        try:
            source = json.loads(self.assessments_path.read_text(encoding="utf-8"))
            assessment = source.get("obstacles", {}).get(obstacle_id)
        except (OSError, ValueError, AttributeError):
            return None, ["obstacle assessment file must be a JSON object with obstacles map"]
        if assessment is None:
            return None, []
        if not isinstance(assessment, dict):
            return None, ["obstacle assessment must be an object"]
        errors = []
        if assessment.get("status") not in {"resolved", "blocked", "unresolved"}:
            errors.append("assessment status must be resolved, blocked, or unresolved")
        if not isinstance(assessment.get("rationale"), str) or not assessment["rationale"].strip():
            errors.append("assessment requires a rationale")
        if assessment.get("reviewer_kind") not in {"agent", "human"} or not isinstance(assessment.get("reviewer"), str) or not assessment["reviewer"].strip():
            errors.append("assessment requires a named agent or human reviewer")
        evidence = assessment.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append("assessment evidence must be a list")
        if assessment.get("status") == "resolved" and (not isinstance(evidence, list) or not evidence):
            errors.append("resolved obstacle requires hash-bound evidence")
        for item in evidence if isinstance(evidence, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
                errors.append("each evidence item requires path and sha256")
                continue
            declared = Path(item["path"])
            try:
                if declared.is_absolute() or ".." in declared.parts:
                    raise ValueError
                path = (self.root / declared).resolve()
                path.relative_to(self.root)
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                    errors.append(f"evidence missing or changed: {item['path']}")
            except ValueError:
                errors.append(f"evidence path leaves project root: {item['path']}")
        return (assessment if not errors else None), errors

    def resolve_obstacles(self, obstacles: list[dict], max_budget: float | None = None) -> list[dict]:
        """WP4: Track and attempt minimal discriminating tests for scientific obstacles."""
        resolved = []
        for obs in obstacles:
            if max_budget is not None and self.get_spent_budget() >= max_budget:
                break
            started = time.monotonic()
            obs_id = obs.get("obstacle_id")
            claim_id = obs.get("blocked_claim_id")
            disc_test = obs.get("discriminating_test")

            assessment, assessment_errors = self.obstacle_assessment(obs_id) if isinstance(obs_id, str) else (None, [])
            # An existing reviewed finding does not need another command execution.
            test_cmd = obs.get("test_command")
            test_passed = False
            if assessment is None and test_cmd and isinstance(test_cmd, list):
                try:
                    res = subprocess.run(test_cmd, cwd=self.root, capture_output=True, text=True, timeout=300, check=False)
                    test_passed = (res.returncode == 0)
                except subprocess.TimeoutExpired:
                    test_passed = False

            status = assessment["status"] if assessment else ("blocked" if obs.get("requires_new_data") else "unresolved")
            record = {
                "obstacle_id": obs_id,
                "blocked_claim_id": claim_id,
                "discriminating_test": disc_test,
                "status": status,
                "test_executed": test_passed,
                "outcome": "reviewed assessment with hash-bound evidence" if assessment and status == "resolved" else "test ran; scientific interpretation remains to be reviewed" if test_passed else "obstacle remains active",
                "assessment_errors": assessment_errors,
                "reviewer": assessment.get("reviewer") if assessment else None,
                "reviewer_kind": assessment.get("reviewer_kind") if assessment else None,
            }
            resolved.append(record)
            log_event(self.ledger_path, {
                "event_type": "scientific_obstacle_iteration",
                "obstacle": record,
                "cost": round(time.monotonic() - started, 6),
            })
        return resolved

    def execute_workflow(self) -> dict:
        spent = self.get_spent_budget()
        max_budget = float(self.contract.get("max_budget", 10.0))
        if spent >= max_budget:
            return {
                "status": "budget-exhausted",
                "spent_budget": spent,
                "max_budget": max_budget,
                "message": "Autonomous budget limit exceeded; halting loop.",
            }

        # 1. Initialize Contract
        contract_info = self.initialize_contract()
        obstacle_reports = []
        replay_report = None
        latex_report = None
        package_report = None

        def budget_stop() -> dict | None:
            current = self.get_spent_budget()
            if current < max_budget:
                return None
            result = {
                "status": "budget-exhausted",
                "spent_budget": round(current, 3),
                "max_budget": max_budget,
                "contract": contract_info,
                "obstacles": obstacle_reports,
                "replication": replay_report,
                "latex_build": latex_report,
                "package_audit": package_report,
                "next_tasks": plan_next_tasks(package_report, obstacle_reports, replay_report, latex_report),
                "message": "Measured budget exhausted; later stages were not run.",
            }
            result["rework_plan"] = rework_plan(result["next_tasks"])
            save_rework_state(self.root, result)
            log_event(self.ledger_path, {"event_type": "workflow_summary", "result_status": result["status"], "spent_budget": result["spent_budget"], "cost": 0.0})
            return result

        # 2. Handle Obstacles (if any declared in contract or research state)
        obstacles = self.contract.get("obstacles", [])
        if obstacles:
            obstacle_reports = self.resolve_obstacles(obstacles, max_budget)
            stopped = budget_stop()
            if stopped:
                return stopped

        # 3. Clean Replay (if analysis commands are declared)
        analysis_cmds = self.contract.get("analysis_commands", [])
        if analysis_cmds:
            raw_inputs = self.contract.get("raw_inputs", [])
            generated = self.contract.get("generated_outputs", [])
            replay_report = self.run_clean_replay(analysis_cmds, raw_inputs, generated)
            stopped = budget_stop()
            if stopped:
                return stopped

        # 4. LaTeX build & review (if manuscript deliverable)
        if self.contract.get("deliverable", "manuscript") == "manuscript":
            main_tex = self.root / self.contract.get("latex_main", "paper/manuscript/main.tex")
            build_dir = self.root / self.contract.get("latex_build_dir", "paper/build")
            visual_review = self.root / self.contract.get("latex_visual_review", "research/latex-visual-review.json")
            if main_tex.is_file() and visual_review.is_file():
                engine = self.contract.get("latex_engine", "auto")
                latex_report = self.compile_single_build(main_tex, build_dir, visual_review, engine)
                stopped = budget_stop()
                if stopped:
                    return stopped

        # 5. Full Package Audit. Its declared scope must match the frozen request.
        if self.package_config_path.is_file():
            package_config = json.loads(self.package_config_path.read_text(encoding="utf-8"))
            contract_fields = ("mode", "deliverable", "claim_scope", "mechanism_scope")
            mismatches = [
                field for field in contract_fields
                if package_config.get(field, package_config.get("profile") if field == "mode" else "not-claimed" if field == "mechanism_scope" else None)
                != contract_info[field]
            ]
            if mismatches:
                package_report = {"valid": False, "error": f"package fields differ from frozen research contract: {mismatches}"}
            else:
                package_report = self.verify_research_package()

        final_valid = bool(
            package_report and package_report.get("valid") is True
            and (not analysis_cmds or (replay_report and replay_report.get("reproducible") is True))
            and (contract_info["deliverable"] != "manuscript" or (latex_report and latex_report["finalize"].get("delivery_ready") is True))
            and all(item["status"] == "resolved" for item in obstacle_reports)
        )
        final_spent = self.get_spent_budget()

        result = {
            "status": "complete" if final_valid else ("blocked" if (package_report and not final_valid) else "in-progress"),
            "spent_budget": round(final_spent, 3),
            "max_budget": max_budget,
            "contract": contract_info,
            "obstacles": obstacle_reports,
            "replication": replay_report,
            "latex_build": latex_report,
            "package_audit": package_report,
            "next_tasks": plan_next_tasks(package_report, obstacle_reports, replay_report, latex_report),
        }
        result["rework_plan"] = rework_plan(result["next_tasks"])
        save_rework_state(self.root, result)

        log_event(self.ledger_path, {
            "event_type": "workflow_summary",
            "result_status": result["status"],
            "spent_budget": result["spent_budget"],
            "cost": 0.0,
        })
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--contract", type=Path, help="Path to research contract JSON")
    parser.add_argument("--mode", choices=("empirical", "theory", "structural", "descriptive", "replication", "feasibility"), default="empirical")
    parser.add_argument("--deliverable", choices=("manuscript", "replication_package", "feasibility_report"), default="manuscript")
    parser.add_argument("--claim-scope", choices=("research-only", "real-world"), default="research-only")
    parser.add_argument("--max-budget", type=float, default=10.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    contract_data = {}
    if args.contract:
        c_path = args.contract if args.contract.is_absolute() else root / args.contract
        if c_path.is_file():
            contract_data = json.loads(c_path.read_text(encoding="utf-8"))

    contract_data.setdefault("mode", args.mode)
    contract_data.setdefault("deliverable", args.deliverable)
    contract_data.setdefault("claim_scope", args.claim_scope)
    contract_data.setdefault("max_budget", args.max_budget)

    workflow = ResearchWorkflow(root, contract_data)
    result = workflow.execute_workflow()

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    return 0 if result["status"] == "complete" else (0 if result["status"] == "in-progress" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
