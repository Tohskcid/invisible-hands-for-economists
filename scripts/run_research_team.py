#!/usr/bin/env python3
"""Run bounded, real Codex research agents around the existing workflow gates.

This dispatches CLI sessions; scientific acceptance remains with the coordinator
agent and the package gates. An agent's successful exit is never a research pass.
"""

import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path

from run_research_workflow import ResearchWorkflow, STAGE_ORDER, log_event, rework_plan


ROLE_STAGE = {
    "literature": "literature", "prior_art_review": "literature", "planning": "literature", "data_acquisition": "data",
    "data_cleaning": "data", "model": "design", "exploration": "exploration",
    "validation": "analysis", "interpretation": "manuscript", "writing": "manuscript",
    "review": "review", "coordination": "review",
}
COMMON = ("literature", "prior_art_review", "planning", "model", "exploration", "validation", "interpretation", "writing", "review", "coordination")
DATA = ("data_acquisition", "data_cleaning")
CONTRIBUTION_PROBE_FIELDS = (
    "nearest_result", "proposed_delta", "field_significance", "discriminating_test",
    "failure_condition", "feasible_evidence",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roles_for(mode: str, restart: str | None = None) -> list[str]:
    roles = list(COMMON)
    if mode in {"empirical", "descriptive", "structural", "replication"}:
        roles[3:3] = DATA
    if mode == "replication":
        roles.remove("model")
    if restart:
        restart = "design" if restart == "scientific_obstacle" else restart
        if restart == "package":
            return roles
        if restart == "delivery":
            return ["writing", "review", "coordination"]
        if restart not in STAGE_ORDER:
            raise ValueError(f"unknown restart stage: {restart}")
        roles = [role for role in roles if STAGE_ORDER.index(ROLE_STAGE[role]) >= STAGE_ORDER.index(restart)]
        # Every revision gets a fresh independent review and PI adjudication.
        roles = list(dict.fromkeys(roles + ["review", "coordination"]))
    return roles


def handoff(root: Path, path: Path, role: str) -> dict:
    root = root.resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("role") != role or data.get("status") not in {"complete", "blocked"}:
        raise ValueError(f"{role} handoff needs role and complete/blocked status")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError(f"{role} handoff needs artifact paths and hashes")
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise ValueError(f"{role} handoff has invalid artifact")
        relative = Path(item["path"])
        full = (root / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or not full.is_relative_to(root) or not full.is_file() or digest(full) != item["sha256"]:
            raise ValueError(f"{role} handoff artifact missing or changed: {item['path']}")
    return data


def verify_review_output(root: Path, target: Path, handoff_data: dict, reviewer_id: str,
                         before: str | None, prior_art: bool) -> None:
    if not target.is_file() or (before is not None and digest(target) == before):
        raise ValueError("review agent did not create or update its review record")
    relative = target.relative_to(root).as_posix()
    if not any(item.get("path") == relative and item.get("sha256") == digest(target)
               for item in handoff_data["artifacts"]):
        raise ValueError("review handoff must bind the review file")
    document = json.loads(target.read_text(encoding="utf-8"))
    holder = document.get("independent_review") if prior_art else document
    if not isinstance(holder, dict) or holder.get("reviewer_id") != reviewer_id:
        raise ValueError("review record must carry the assigned reviewer identity")


def verify_exploration_append(before: bytes, after: bytes) -> None:
    if before and not after.startswith(before):
        raise ValueError("exploration history was rewritten")
    def rows(data: bytes) -> int:
        if not data:
            return 0
        return len(list(csv.DictReader(io.StringIO(data.decode("utf-8")), delimiter="\t")))
    if rows(after) <= rows(before):
        raise ValueError("exploration round did not add a new trial")


def snapshot(root: Path, round_number: int) -> Path:
    """Preserve mutable research outputs before a later revision; leave raw data untouched."""
    dest = root / "research/round-snapshots" / f"before-round-{round_number:02d}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest = dest.with_name(f"before-round-{round_number:02d}-{uuid.uuid4().hex}.zip")
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for dirname in ("research", "paper", "output", "code", "data/processed"):
            folder = root / dirname
            if not folder.is_dir():
                continue
            for path in folder.rglob("*"):
                relative = path.relative_to(root)
                if path.is_file() and not path.is_symlink() and not any(part in {"agent-runs", "round-snapshots"} for part in relative.parts):
                    archive.write(path, relative.as_posix())
    return dest


def topic_rejected(root: Path) -> bool:
    review = root / "research/substantive-review.json"
    if not review.is_file():
        return False
    try:
        data = json.loads(review.read_text(encoding="utf-8"))
        dimensions = data.get("dimensions", {})
        return any(isinstance(dimensions.get(name), dict) and dimensions[name].get("verdict") != "pass"
                   for name in ("novelty", "overlap"))
    except (ValueError, AttributeError):
        return False


def publication_goal(contract: dict) -> str:
    goal = contract.get("publication_goal", "replication" if contract.get("mode") == "replication" else "original")
    if goal not in {"original", "replication"}:
        raise ValueError("publication_goal must be original or replication")
    return goal


def contribution_gap(root: Path, goal: str) -> str | None:
    """A replication decision cannot clear an original-contribution objective."""
    if goal != "original":
        return None
    path = root / "research/topic-survey.json"
    if not path.is_file():
        return None
    survey = json.loads(path.read_text(encoding="utf-8"))
    if survey.get("decision") == "replicate" or survey.get("contribution_class") in {"replication", "duplicate", "synthesis"}:
        return "Prior-art review supports replication or an already established contribution, not the frozen original-publication goal."
    probe = survey.get("contribution_probe")
    if not isinstance(probe, dict) or any(not isinstance(probe.get(field), str) or not probe[field].strip()
                                           for field in CONTRIBUTION_PROBE_FIELDS):
        return f"Original-publication survey needs a concrete contribution_probe with {', '.join(CONTRIBUTION_PROBE_FIELDS)}."
    return None


def review_rework_task(root: Path) -> dict | None:
    """Route a referee's scientific objection to the earliest useful research stage."""
    path = root / "research/substantive-review.json"
    if not path.is_file():
        return None
    review = json.loads(path.read_text(encoding="utf-8"))
    dimensions = review.get("dimensions", {})
    if not isinstance(dimensions, dict):
        return None
    for names, stage, instruction in (
        (("novelty", "overlap"), "literature", "Find a defensible new contribution within the frozen question; compare its exact claim with nearest prior art before design."),
        (("research_design", "inference_or_proof"), "design", "Propose and test a design or proof that distinguishes the leading competing explanations; record its failure criterion."),
        (("logic",), "argument", "Repair the weakest claim-to-evidence or proof link, then rerun the relevant validation."),
        (("completeness",), "manuscript", "Complete the missing evidence-backed material identified by the referee."),
    ):
        failed = [name for name in names if isinstance(dimensions.get(name), dict) and dimensions[name].get("verdict") != "pass"]
        if failed:
            requested = review.get("rework_stage")
            if stage == "design" and requested in {"literature", "data", "design"}:
                stage = requested
                if stage == "data":
                    instruction = "Acquire and verify the real data needed for the referee's discriminating design, then redo its analysis."
                elif stage == "literature":
                    instruction = "Check the proposed design against the nearest competing literature before acquiring data or estimating."
            return {"stage": stage, "source": "substantive-review.json", "instruction": instruction,
                    "reason": {name: dimensions[name].get("reason") for name in failed},
                    "requires_scientific_judgment": True}
    return None


def record_contribution_branch(root: Path, round_number: int, reason: str, source: str) -> str:
    path = root / "research/contribution-branches.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"round": round_number, "source": source, "reason": reason,
              "survey_sha256": digest(root / "research/topic-survey.json") if (root / "research/topic-survey.json").is_file() else None,
              "prior_art_sha256": digest(root / "research/prior-art-review.json") if (root / "research/prior-art-review.json").is_file() else None,
              "substantive_review_sha256": digest(root / "research/substantive-review.json") if (root / "research/substantive-review.json").is_file() else None,
              "next_action": "Search a distinct estimand, mechanism, setting, or data advantage; state a falsifiable test and independently recheck prior art before design."}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path.relative_to(root).as_posix()


def prompt(root: Path, contract: dict, role: str, round_dir: Path, handoff_path: Path,
           prior: list[dict], tasks: list[dict], rework: dict | None, ids: dict[str, str]) -> str:
    relative_handoff = handoff_path.relative_to(root).as_posix()
    role_instructions = {
        "literature": "Search verified primary sources, read nearest full texts where accessible, compare claims/results and publication dates; decide duplication, extension, or abandonment before methods. For an original-publication goal, search for a distinct estimand, mechanism, setting, or data advantage within the frozen question. Add contribution_probe to research/topic-survey.json with nearest_result, proposed_delta, field_significance, discriminating_test, failure_condition, and feasible_evidence. An updated endpoint alone is not a substantive contribution. Write the survey and draft proposed claims, works, and comparisons in research/prior-art-review.json; leave independent_review to the separately dispatched reviewer. Include both files in your handoff. Do not invent access; unresolved access blocks design.",
        "prior_art_review": "Independently audit the literature agent's nearest-work full texts, publication dates, proposed claim comparisons, contribution_probe where present, and topic decision. Read the actual sources, not only the prior handoff. Create or update independent_review in research/prior-art-review.json, include this file in the handoff, and write an honest reject/block if evidence is missing. Never modify research/topic-survey.json or author claims to manufacture clearance.",
        "planning": "Freeze a feasible estimand or theorem, assumptions, design, stop conditions, and source/data needs. Preserve the original question.",
        "data_acquisition": "Acquire only real or restricted empirical data; record source URL, license/access, date, and raw hashes. No simulated empirical evidence.",
        "data_cleaning": "Clean verified real data reproducibly; record schema, exclusions, merges, sample changes, and code. Never substitute simulated data.",
        "model": "Develop the empirical identification or theory model with assumptions, obligations, and falsifiable implications.",
        "exploration": "State a hypothesis, run a discriminating test or derivation, assess evidence and choose keep/discard/inconclusive/blocked/crash. Append a tab-separated row to research/experiments.tsv with exactly iteration, mode, hypothesis, validation, status, artifact, artifact_sha256, reason, next_action. Propose the next branch; do not call a successful command scientific success.",
        "validation": "Independently check computations, identification, proofs/counterexamples, competing explanations, and failed attempts. Mark unresolved obligations honestly.",
        "interpretation": "Write bounded claims and explicit limitations tied to evidence, with alternative interpretations.",
        "writing": "Produce a complete economics manuscript in LaTeX, with evidence-backed sections, clear limitations, full proof appendix where relevant, and package inputs.",
        "review": "Act as a fresh independent AI referee. Read the frozen manuscript, source audit and evidence, not author reasoning or prior handoffs. Do not edit author artifacts. Create or update research/substantive-review.json, include it in the handoff, and give candid verdicts and critical issues; reject if novelty or validity fails. For each failed dimension, explain the closest prior claim or competing explanation and the specific evidence or test needed to overturn the objection. If design repair requires new sources or data, set rework_stage to literature or data; otherwise use design.",
        "coordination": "Act as accountable PI. Inspect actual agent artifacts and receipts, adjudicate handoffs, and write research/team.json only for genuinely accepted hash-bound handoffs. Include exactly the mode-required roles from check_research_team.py; prior_art_review and exploration are separately audited, not team.json roles. Research roles use native CLI thread IDs. The whole-paper review role uses its assigned reviewer_id alias in team.json agent_id so it matches substantive-review.json; also record its distinct native CLI thread ID as native_agent_id from the receipt. Bind its handoff to research/substantive-review.json. Preserve unresolved defects and do not mark failed reviews as passing.",
    }
    return (
        f"You are a separate Codex CLI research agent, role={role}, round={round_dir.name}. "
        f"Project root: {root}. Read {Path(__file__).resolve().parent.parent / 'SKILL.md'} and relevant references. "
        f"Frozen contract: {json.dumps(contract, ensure_ascii=False)}. "
        f"Current gate tasks: {json.dumps(tasks, ensure_ascii=False)}. Rework plan: {json.dumps(rework, ensure_ascii=False)}. "
        f"Prior verified handoffs: {json.dumps(prior, ensure_ascii=False)}. Actual agent IDs: {json.dumps(ids, ensure_ascii=False)}. "
        f"Task: {role_instructions[role]} Write only role-owned files and {relative_handoff}; do not alter research/contract.json or contract-input.json. "
        "For manuscript delivery, research/package.json must declare protocol_version='2', prior_art_review and exploration_ledger. "
        f"Your handoff JSON must have role='{role}', status='complete' or 'blocked', findings, unresolved_issues, next_action, "
        f"and artifacts=[{{'path': project-relative file, 'sha256': current SHA-256}}]. At least one artifact must be a separate role note under {round_dir.relative_to(root).as_posix()}/{role}/. "
        "Do not claim package success unless the actual gates pass. Stop when access or evidence blocks the task. "
        "If you are review or coordination, preserve independence and never rewrite the manuscript to fit your verdict."
    )


def dispatch(root: Path, agent_command: str, role: str, round_dir: Path, instruction: str,
             timeout: float, ledger: Path) -> tuple[str, dict]:
    role_dir = round_dir / role
    role_dir.mkdir(parents=True, exist_ok=True)
    events, stderr, final = (role_dir / name for name in ("events.jsonl", "stderr.txt", "last-message.txt"))
    command = [agent_command, "exec", "--json", "--skip-git-repo-check", "-C", str(root), "-o", str(final), "-"]
    started = time.monotonic()
    with events.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out, stderr=err, text=True)
        try:
            process.communicate(instruction, timeout=max(1, timeout))
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            log_event(ledger, {"event_type": "agent_dispatch", "role": role, "agent_id": None,
                               "exit_code": "timeout", "events": events.relative_to(root).as_posix(),
                               "cost": round(time.monotonic() - started, 6)})
            raise TimeoutError(f"{role} agent exceeded remaining budget")
    agent_id = None
    for line in events.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
            if event.get("type") == "thread.started":
                agent_id = event.get("thread_id")
                break
        except json.JSONDecodeError:
            continue
    elapsed = round(time.monotonic() - started, 6)
    log_event(ledger, {"event_type": "agent_dispatch", "role": role, "agent_id": agent_id,
                       "exit_code": process.returncode, "events": events.relative_to(root).as_posix(), "cost": elapsed})
    if process.returncode != 0 or not agent_id:
        raise RuntimeError(f"{role} agent failed (exit {process.returncode}); see {stderr}")
    return agent_id, {"role": role, "agent_id": agent_id, "events": events.relative_to(root).as_posix()}


def run(root: Path, contract_path: Path, agent_command: str, max_rounds: int) -> dict:
    root = root.resolve()
    contract_path = contract_path if contract_path.is_absolute() else root / contract_path
    contract_path = contract_path.resolve()
    if not contract_path.is_relative_to(root) or not contract_path.is_file():
        raise ValueError("contract must be an existing file under the project root")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("deliverable") != "manuscript" or contract.get("mode") not in {"theory", "empirical", "descriptive", "structural", "replication"}:
        raise ValueError("this runner requires a manuscript contract with a supported research mode")
    goal = publication_goal(contract)
    budget = float(contract.get("max_budget", 0))
    if budget <= 0 or max_rounds < 1:
        raise ValueError("positive max_budget and max_rounds are required")
    if not shutil.which(agent_command):
        raise ValueError(f"agent command unavailable: {agent_command}")
    workflow = ResearchWorkflow(root, contract)
    initial = workflow.execute_workflow()
    frozen = digest(root / "research/contract.json")
    original = digest(contract_path)
    deadline = time.monotonic() + max(0, budget - workflow.get_spent_budget())
    result = initial
    completed = []
    earlier = []
    run_dir = root / "research/agent-runs" / f"run-{uuid.uuid4().hex}"
    for number in range(1, max_rounds + 1):
        if time.monotonic() >= deadline:
            return {"status": "budget-exhausted", "rounds": completed, "workflow": result}
        if number > 1:
            saved = snapshot(root, number)
            log_event(workflow.ledger_path, {"event_type": "pre_revision_snapshot",
                                             "artifact": saved.relative_to(root).as_posix(),
                                             "sha256": digest(saved), "cost": 0.0})
        round_dir = run_dir / f"round-{number:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        prior, ids = list(earlier), {}
        branch_reason = branch_source = None
        restart = result.get("rework_plan", {}).get("restart_from") if number > 1 else None
        for role in roles_for(contract["mode"], restart):
            if digest(contract_path) != original or digest(root / "research/contract.json") != frozen:
                return {"status": "contract-changed", "rounds": completed, "role": role}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"status": "budget-exhausted", "rounds": completed, "role": role}
            handoff_path = round_dir / role / "handoff.json"
            survey_path = root / "research/topic-survey.json"
            survey_before = digest(survey_path) if role == "prior_art_review" and survey_path.is_file() else None
            review_target = root / ("research/prior-art-review.json" if role == "prior_art_review" else "research/substantive-review.json")
            review_before = digest(review_target) if role in {"prior_art_review", "review"} and review_target.is_file() else None
            reviewer_id = f"{role}-{uuid.uuid4().hex}" if role in {"prior_art_review", "review"} else None
            exploration_path = root / "research/experiments.tsv"
            exploration_before = exploration_path.read_bytes() if role == "exploration" and exploration_path.is_file() else b""
            reviewed_inputs = {}
            if role == "review":
                for folder in (root / "paper",):
                    if folder.is_dir():
                        reviewed_inputs.update({path: digest(path) for path in folder.rglob("*") if path.is_file()})
                if survey_path.is_file():
                    reviewed_inputs[survey_path] = digest(survey_path)
            instruction = prompt(root, contract, role, round_dir, handoff_path, [] if role == "review" else prior,
                                 result.get("next_tasks", []), result.get("rework_plan"), ids)
            if reviewer_id:
                instruction += f" Your assigned reviewer_id is {reviewer_id}; write that exact value in your review record and handoff."
            try:
                agent_id, receipt = dispatch(root, agent_command, role, round_dir, instruction, remaining,
                                             workflow.ledger_path)
                ids[role] = reviewer_id or agent_id
                if reviewer_id:
                    receipt["declared_agent_id"] = reviewer_id
                if role == "prior_art_review":
                    if survey_before is None or digest(survey_path) != survey_before:
                        return {"status": "prior-art-contaminated", "rounds": completed, "role": role}
                if role == "review":
                    if any(not path.is_file() or digest(path) != before for path, before in reviewed_inputs.items()):
                        return {"status": "review-contaminated", "rounds": completed, "role": role}
                content = handoff(root, handoff_path, role)
                if reviewer_id:
                    verify_review_output(root, review_target, content, reviewer_id, review_before,
                                         role == "prior_art_review")
                receipt["handoff"] = handoff_path.relative_to(root).as_posix()
                prior.append(receipt)
                if content["status"] == "blocked":
                    return {"status": "agent-blocked", "role": role, "rounds": completed, "handoff": receipt}
                if role == "literature":
                    scripts = Path(__file__).resolve().parent
                    command = [sys.executable, str(scripts / "check_topic_survey.py"), str(survey_path),
                               "--root", str(root), "--require-approved", "--json"]
                    checked = subprocess.run(command, capture_output=True, text=True, check=False)
                    if checked.returncode:
                        return {"status": "prior-art-blocked", "rounds": completed, "role": role,
                                "report": checked.stdout or checked.stderr}
                    branch_reason = contribution_gap(root, goal)
                    if branch_reason:
                        branch_source = "prior-art-review.json"
                        break
                if role == "prior_art_review":
                    scripts = Path(__file__).resolve().parent
                    command = [sys.executable, str(scripts / "check_prior_art_review.py"),
                               str(root / "research/prior-art-review.json"), "--topic-survey", str(survey_path),
                               "--root", str(root), "--json"]
                    checked = subprocess.run(command, capture_output=True, text=True, check=False)
                    if checked.returncode:
                        return {"status": "prior-art-blocked", "rounds": completed, "role": role,
                                "report": checked.stdout or checked.stderr}
                if role == "exploration":
                    verify_exploration_append(exploration_before, exploration_path.read_bytes() if exploration_path.is_file() else b"")
                    checker = Path(__file__).resolve().parent / "check_exploration_ledger.py"
                    if not checker.is_file():
                        return {"status": "exploration-checker-missing", "rounds": completed}
                    check = subprocess.run([sys.executable, str(checker), str(root / "research/experiments.tsv"),
                                            "--root", str(root), "--json"], capture_output=True, text=True, check=False)
                    if check.returncode:
                        return {"status": "exploration-invalid", "rounds": completed, "report": check.stdout or check.stderr}
                if role == "review" and goal == "original" and topic_rejected(root):
                    branch_reason = "Independent referee rejected novelty or overlap for the original-publication goal."
                    branch_source = "substantive-review.json"
                    break
            except TimeoutError as exc:
                return {"status": "budget-exhausted", "role": role, "rounds": completed, "error": str(exc)}
            except (OSError, ValueError, RuntimeError) as exc:
                return {"status": "agent-failed", "role": role, "rounds": completed, "error": str(exc)}
        if branch_reason:
            branch_path = record_contribution_branch(root, number, branch_reason, branch_source)
            log_event(workflow.ledger_path, {"event_type": "contribution_branch", "round": number,
                                             "source": branch_source, "artifact": branch_path, "cost": 0.0})
            completed.append({"round": number, "handoffs": prior, "branch": branch_path})
            earlier = prior
            task = {"stage": "literature", "source": branch_source,
                    "instruction": "Find and falsify a distinct contribution within the frozen question before another design or manuscript attempt.",
                    "reason": branch_reason, "requires_scientific_judgment": True}
            result = {"status": "in-progress", "next_tasks": [task], "rework_plan": rework_plan([task])}
            if number == max_rounds:
                return {"status": "contribution-unresolved", "rounds": completed, "workflow": result,
                        "reason": branch_reason}
            continue
        completed.append({"round": number, "handoffs": prior})
        earlier = prior
        if digest(contract_path) != original or digest(root / "research/contract.json") != frozen:
            return {"status": "contract-changed", "rounds": completed}
        result = workflow.execute_workflow()
        if result["status"] == "complete":
            if time.monotonic() > deadline:
                return {"status": "budget-exhausted", "rounds": completed, "workflow": result}
            package_path = root / "research/package.json"
            package = json.loads(package_path.read_text(encoding="utf-8")) if package_path.is_file() else {}
            if package.get("protocol_version") != "2":
                return {"status": "package-protocol-invalid", "rounds": completed, "workflow": result,
                        "error": "autonomous manuscript completion requires protocol_version 2"}
            return {"status": "complete", "rounds": completed, "workflow": result}
        if goal == "original" and topic_rejected(root):
            return {"status": "contribution-unresolved", "rounds": completed, "workflow": result}
        review_task = review_rework_task(root)
        if review_task and result["status"] != "complete":
            tasks = [review_task, *result.get("next_tasks", [])]
            result["next_tasks"] = tasks
            result["rework_plan"] = rework_plan(tasks)
        if not result.get("rework_plan"):
            return {"status": "blocked", "rounds": completed, "workflow": result}
    return {"status": "max-rounds", "rounds": completed, "workflow": result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True, help="Path relative to --root")
    parser.add_argument("--agent-command", default="codex", help="Codex-compatible CLI executable")
    parser.add_argument("--max-rounds", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.root, args.contract, args.agent_command, args.max_rounds)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"status": "error", "error": str(exc)}
    if args.root.is_dir():
        output = args.root / "research/agent-runs/latest-result.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
