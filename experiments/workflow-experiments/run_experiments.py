#!/usr/bin/env python3
"""Run engineering experiments, validation, and debugging for the automated paper workflow.

Exercises engineering paths with small illustrative fixtures. The fixtures do not
establish historical replication, causal identification, complete proofs, or real
financial inference; failed package gates remain failed in the report.

Cases:
1. Synthetic DiD: execution, clean replay, and package gates.
2. Bargaining illustration: manuscript, argument graph, and package gates.
3. Synthetic event returns: build handling, replay, and package gates.
4. Case 4 (Debugging & Self-Patching): Automated recovery from unsupported CLI flags and directory errors.
5. Case 5 (Interruption & Budget Control): Preserving cumulative cost and resuming pending queues without duplicate runs.
"""

import argparse
import base64
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


workflow_module = load_mod("run_research_workflow", ROOT / "scripts/run_research_workflow.py")
dream_simulator = load_mod("dream_replay_simulator", ROOT / "scripts/dream_replay_simulator.py")


def record_pending_review(exp_dir: Path, report_file: Path) -> bool:
    """Record build state without pretending that a page review was performed."""
    report = json.loads(report_file.read_text(encoding="utf-8"))
    rendering = report.get("rendering", {})
    (exp_dir / "research/visual-review.json").write_text(json.dumps({
        "pdf_sha256": rendering.get("pdf_sha256"),
        "status": "pending",
        "reviewer": "unassigned",
        "pages_reviewed": [],
        "issues": [],
    }), encoding="utf-8")
    return report.get("automated_passed") is True


def record_unreviewed_team(exp_dir: Path) -> None:
    """Expose missing research handoffs without inventing agents or approval."""
    (exp_dir / "research/team.json").write_text(json.dumps({"coordinator_id": "unassigned", "tasks": []}), encoding="utf-8")
    (exp_dir / "research/substantive-review.json").write_text(json.dumps({"verdict": "pending"}), encoding="utf-8")


def failed_gates(package_report: dict | None) -> list[dict]:
    if not package_report:
        return [{"gate": "package", "reason": "audit did not run"}]
    if package_report.get("error"):
        return [{"gate": "package", "reason": package_report["error"]}]
    failures = []
    for check in package_report.get("checks", []):
        if check.get("passed"):
            continue
        command = check.get("command", [])
        try:
            detail = json.loads(check.get("stdout", ""))
            reason = detail.get("errors") or detail.get("error") or detail.get("reason") or check.get("stderr")
        except json.JSONDecodeError:
            reason = check.get("stderr") or check.get("stdout")
        failures.append({"gate": Path(command[1]).name if len(command) > 1 else "unknown", "reason": reason})
    return failures


def run_experiment_1_empirical_did(base_dir: Path) -> dict:
    """Case 1: Synthetic difference-in-differences engineering fixture."""
    exp_dir = base_dir / "empirical_did"
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "data").mkdir(exist_ok=True)
    (exp_dir / "scripts").mkdir(exist_ok=True)
    (exp_dir / "research/diagnostics").mkdir(parents=True, exist_ok=True)
    (exp_dir / "research/sections").mkdir(parents=True, exist_ok=True)
    (exp_dir / "paper/manuscript").mkdir(parents=True, exist_ok=True)
    (exp_dir / "paper/build").mkdir(parents=True, exist_ok=True)
    (exp_dir / "output/tables").mkdir(parents=True, exist_ok=True)

    # 1. Raw Data
    raw_data = exp_dir / "data/restaurants.csv"
    raw_data.write_text(
        "store_id,state,post,fte\n"
        "1,NJ,0,20.0\n1,NJ,1,23.5\n"
        "2,NJ,0,18.5\n2,NJ,1,21.0\n"
        "3,PA,0,22.0\n3,PA,1,22.5\n"
        "4,PA,0,21.0\n4,PA,1,20.5\n",
        encoding="utf-8",
    )
    raw_hash = hashlib.sha256(raw_data.read_bytes()).hexdigest()

    # 2. Analysis script
    t1_bytes = ("\\begin{tabular}{lc}\nEstimate & 3.00 " + r"\\" + "\nSE & 0.45 " + r"\\" + "\n\\end{tabular}\n").encode()
    t1_b64 = base64.b64encode(t1_bytes).decode("ascii")

    analyze_script = exp_dir / "scripts/analyze.py"
    analyze_script.write_text(
        "import base64, json, hashlib\n"
        "from pathlib import Path\n"
        "root = Path('.').resolve()\n"
        "est, se = 3.0, 0.45\n"
        "results = {\n"
        "  'schema_version': '1',\n"
        "  'run_id': 'run-did-001',\n"
        "  'source_sha256': {'data/restaurants.csv': '" + raw_hash + "'},\n"
        "  'required_bindings': ['primary.estimate', 'primary.std_error'],\n"
        "  'results': {'primary': {'estimate': est, 'std_error': se}}\n"
        "}\n"
        "(root / 'research/results.json').write_text(json.dumps(results, indent=2))\n"
        f"(root / 'output/tables/table1.tex').write_bytes(base64.b64decode('{t1_b64}'))\n",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(analyze_script)], cwd=exp_dir, check=True)
    res_hash = hashlib.sha256((exp_dir / "research/results.json").read_bytes()).hexdigest()

    # 3. Research Manifest
    manifest = exp_dir / "research/manifest.jsonl"
    manifest_records = [
        {"id": "hyp-1", "type": "hypothesis", "statement": "Minimum wage increase does not reduce fast food employment", "falsifier": "significant negative FTE effect", "_line": 1},
        {"id": "exp-1", "type": "experiment", "hypothesis_id": "hyp-1", "validation": "DiD between NJ and PA", "assignment_unit": "state", "inference_procedure": "cluster_state", "_line": 2},
        {"id": "run-1", "type": "run", "experiment_id": "exp-1", "harness_version": "2.18.0", "status": "complete", "artifact": "output/tables/table1.tex", "data_ids": ["ds-1"], "_line": 3},
        {"id": "ds-1", "type": "dataset", "name": "synthetic_restaurant_fixture", "source": "generated engineering fixture", "locator": "data/restaurants.csv", "verified_at": "2026-10-16", "access_status": "local", "license": "test-fixture", "_line": 4},
        {"id": "ev-1", "type": "evidence", "source": "synthetic restaurants.csv", "locator": "data/restaurants.csv", "verified_at": "2026-10-16", "supports_obligations": [], "_line": 5},
        {"id": "find-1", "type": "finding", "statement": "FTE increased by 3.0 in NJ relative to PA", "run_ids": ["run-1"], "status": "supported", "supports_obligations": ["parallel_trends", "cluster_inference"], "_line": 6},
        {"id": "c-did", "type": "claim", "statement": "Synthetic NJ-PA difference in differences equals 3.00 [claim:c-did]", "role": "conclusion", "central": True, "status": "provisional", "scope": "proxy_only", "uncertainty": "illustrative SE is not valid with two state clusters", "finding_ids": ["find-1"], "evidence_ids": ["ev-1"], "obligations": ["parallel_trends", "cluster_inference"], "assignment_unit": "state", "inference_procedure": "cluster_state", "_line": 7},
    ]
    manifest.write_text("\n".join(json.dumps(r) for r in manifest_records) + "\n", encoding="utf-8")

    # 4. Diagnostics & Design Audit
    did_diagnostics = ["anticipation", "assignment", "comparison-groups", "heterogeneous-effects", "inference", "parallel-trends", "spillovers", "support", "timing"]
    for d in did_diagnostics:
        (exp_dir / f"research/diagnostics/{d}.json").write_text("{}", encoding="utf-8")
    (exp_dir / "research/design-audit.json").write_text(json.dumps({
        "design": "did",
        "estimand": "Average treatment effect on the treated fast-food employment",
        "assignment_narrative": "New Jersey state minimum wage law",
        "interpretation_boundary": "Fast-food restaurants in NJ and eastern PA",
        "diagnostics": [
            {"id": d, "status": "pending", "finding": f"Synthetic fixture; {d} not scientifically audited", "artifact": f"research/diagnostics/{d}.json"}
            for d in did_diagnostics
        ]
    }), encoding="utf-8")

    # 5. Metadata
    (exp_dir / "paper/ref.bib").write_text("@article{card1994, author={Card, David and Krueger, Alan B.}, title={Case Study}, journal={AER}, year={1994}}\n", encoding="utf-8")
    (exp_dir / "research/topic.json").write_text(json.dumps({"approved": False, "status": "pending", "note": "No frontier literature search performed"}), encoding="utf-8")
    (exp_dir / "research/data.json").write_text(json.dumps({"status": "synthetic-fixture", "sources": [{"name": "synthetic_restaurants", "status": "local", "locator": "data/restaurants.csv"}]}), encoding="utf-8")
    (exp_dir / "research/archive.json").write_text(json.dumps({"complete": False, "papers": 0, "downloaded": 0, "status": "pending"}), encoding="utf-8")

    # 6. Manuscript TeX
    main_tex = exp_dir / "paper/manuscript/main.tex"
    main_tex.write_text(
        "\\documentclass{article}\n"
        "\\usepackage{amsmath}\n"
        "\\newcommand{\\result}[2]{#2}\n"
        "\\begin{document}\n"
        "\\title{Minimum Wages and Fast Food Employment: Evidence from New Jersey}\n"
        "\\author{Research Team}\n"
        "\\maketitle\n"
        "\\section{Introduction}\n"
        "In 1992, New Jersey increased the minimum wage. We estimate the employment effect [claim:c-did] \\cite{card1994}.\n"
        "\\section{Empirical Results}\n"
        "The estimated difference-in-differences employment effect is \\result{primary.estimate}{3.00}\n"
        "with standard error \\result{primary.std_error}{0.45}.\n"
        "% [results-sha256:" + res_hash + "]\n"
        "\\par\\medskip\\noindent\\input{../../output/tables/table1.tex}\n"
        "\\bibliographystyle{plain}\n"
        "\\bibliography{../ref}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    # 7. Coverage
    (exp_dir / "research/sections/packet1.md").write_text("intro packet", encoding="utf-8")
    (exp_dir / "research/sections/packet2.md").write_text("results packet", encoding="utf-8")
    (exp_dir / "research/coverage.json").write_text(json.dumps({
        "schema_version": "1",
        "mode": "empirical",
        "manuscript_sha256": hashlib.sha256(main_tex.read_bytes()).hexdigest(),
        "sections": [
            {
                "id": "introduction",
                "role": "introduction",
                "status": "ready",
                "headings": ["Introduction"],
                "claim_ids": ["c-did"],
                "artifacts": [{"kind": "section_packet", "path": "research/sections/packet1.md", "sha256": hashlib.sha256((exp_dir / "research/sections/packet1.md").read_bytes()).hexdigest()}]
            },
            {
                "id": "results",
                "role": "results",
                "status": "ready",
                "headings": ["Empirical Results"],
                "claim_ids": ["c-did"],
                "artifacts": [
                    {"kind": "section_packet", "path": "research/sections/packet2.md", "sha256": hashlib.sha256((exp_dir / "research/sections/packet2.md").read_bytes()).hexdigest()},
                    {"kind": "analysis_code", "path": "scripts/analyze.py", "sha256": hashlib.sha256(analyze_script.read_bytes()).hexdigest()},
                    {"kind": "result", "path": "research/results.json", "sha256": hashlib.sha256((exp_dir / "research/results.json").read_bytes()).hexdigest()},
                    {"kind": "table", "path": "output/tables/table1.tex", "sha256": hashlib.sha256((exp_dir / "output/tables/table1.tex").read_bytes()).hexdigest()},
                ]
            }
        ]
    }), encoding="utf-8")

    # 8. Logic Review
    (exp_dir / "research/logic.json").write_text(json.dumps({
        "reviewed_sha256": {
            "manuscript": hashlib.sha256(main_tex.read_bytes()).hexdigest(),
            "manifest": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        },
        "overall_verdict": "pending",
        "global_gaps": [],
        "uncertainty": "Uncertainty bounded by clustered standard errors.",
        "claim_reviews": [
            {
                "claim_id": "c-did",
                "verdict": "coherent",
                "weakest_link": "Two-state policy variation",
                "scope_or_number_mismatch": "",
                "competing_explanation": "",
                "required_revision": "",
            }
        ]
    }), encoding="utf-8")

    # 9. Single-build compile
    build_dir = exp_dir / "paper/build"
    report_file = build_dir / "report.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts/check_latex.py"), "check",
        "--main", str(main_tex),
        "--build-dir", str(build_dir),
        "--report", str(report_file),
        "--engine", "pdflatex",
    ], capture_output=True, text=True, check=False)

    build_passed = record_pending_review(exp_dir, report_file)
    record_unreviewed_team(exp_dir)

    # 10. Package config
    (exp_dir / "research/replication.json").write_text(json.dumps({
        "commands": [[sys.executable, "scripts/analyze.py"]],
        "raw_inputs": ["data/restaurants.csv"],
        "generated": ["research/results.json", "output/tables/table1.tex"],
        "results": "research/results.json",
        "clean": True,
    }), encoding="utf-8")
    (exp_dir / "research/package.json").write_text(json.dumps({
        "mode": "empirical",
        "deliverable": "manuscript",
        "claim_scope": "research-only",
        "mechanism_scope": "not-claimed",
        "manifest": "research/manifest.jsonl",
        "topic_survey": "research/topic.json",
        "data_provenance": "research/data.json",
        "results": "research/results.json",
        "replication": "research/replication.json",
        "design_audit": "research/design-audit.json",
        "manuscript": "paper/manuscript/main.tex",
        "coverage": "research/coverage.json",
        "bibliography": "paper/ref.bib",
        "literature_archive": "research/archive.json",
        "logic_review": "research/logic.json",
        "team_report": "research/team.json",
        "substantive_review": "research/substantive-review.json",
        "latex_main": "paper/manuscript/main.tex",
        "latex_build_dir": "paper/build",
        "latex_engine": "pdflatex",
        "release_pdf": "paper/build/main.pdf",
        "latex_visual_review": "research/visual-review.json",
    }, indent=2), encoding="utf-8")

    workflow = workflow_module.ResearchWorkflow(exp_dir, {
        "mode": "empirical",
        "deliverable": "manuscript",
        "claim_scope": "research-only",
        "max_budget": 10.0,
        "analysis_commands": [[sys.executable, "scripts/analyze.py"]],
        "raw_inputs": ["data/restaurants.csv"],
        "generated_outputs": ["research/results.json", "output/tables/table1.tex"],
        "latex_engine": "pdflatex",
    })
    wf_result = workflow.execute_workflow()
    return {
        "case": "Case 1: Synthetic DiD engineering fixture",
        "reproducible": wf_result.get("replication", {}).get("reproducible") is True,
        "package_valid": wf_result.get("package_audit", {}).get("valid") is True,
        "status": wf_result.get("status"),
        "build_passed": build_passed,
        "failed_gates": failed_gates(wf_result.get("package_audit")),
        "spent_budget": wf_result.get("spent_budget"),
    }


def run_experiment_2_theory_bargaining(base_dir: Path) -> dict:
    """Case 2: Illustrative bargaining manuscript fixture."""
    exp_dir = base_dir / "theory_bargaining"
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "research/sections").mkdir(parents=True, exist_ok=True)
    (exp_dir / "paper/manuscript").mkdir(parents=True, exist_ok=True)
    (exp_dir / "paper/build").mkdir(parents=True, exist_ok=True)

    manifest = exp_dir / "research/manifest.jsonl"
    records = [
        {"id": "ax-1", "type": "evidence", "source": "Rubinstein (1982)", "locator": "Axiom 1", "verified_at": "1982-01-01", "supports_obligations": ["complete_derivation"], "_line": 1},
        {"id": "find-1", "type": "finding", "statement": "Stationary cutoff strategies are unique subgame perfect equilibrium", "run_ids": ["r-1"], "status": "supported", "supports_obligations": ["complete_derivation"], "_line": 2},
        {"id": "thm-1", "type": "claim", "statement": "In alternating offers with discount delta, unique SPE share is (1-delta2)/(1-delta1 delta2) [claim:thm-1]", "role": "conclusion", "central": True,
         "status": "supported", "scope": "theoretical", "uncertainty": "exact", "finding_ids": ["find-1"], "evidence_ids": ["ax-1"],
         "obligations": ["complete_derivation"], "domain": "discounted_alternating_offers", "_line": 3},
    ]
    manifest.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    (exp_dir / "paper/ref.bib").write_text("@article{rubinstein1982, author={Rubinstein, Ariel}, title={Perfect Equilibrium in a Bargaining Model}, journal={Econometrica}, year={1982}}\n", encoding="utf-8")
    (exp_dir / "research/archive.json").write_text(json.dumps({"complete": False, "papers": 0, "downloaded": 0, "status": "pending"}), encoding="utf-8")
    (exp_dir / "research/topic.json").write_text(json.dumps({"decision": "blocked", "note": "No live nearest-work search performed"}), encoding="utf-8")

    main_tex = exp_dir / "paper/manuscript/main.tex"
    main_tex.write_text(
        "\\documentclass{article}\n"
        "\\usepackage{amsmath,amsthm}\n"
        "\\newtheorem{theorem}{Theorem}\n"
        "\\begin{document}\n"
        "\\title{A Note on Infinite Horizon Alternating Offers Bargaining}\n"
        "\\author{Research Team}\n"
        "\\maketitle\n"
        "\\section{Introduction}\n"
        "We study the bargaining game [claim:thm-1] \\cite{rubinstein1982}. The formal derivation is presented in Appendix A.\n"
        "\\section{Main Results}\n"
        "\\begin{theorem}\n"
        "The unique subgame perfect equilibrium payoff to Player 1 is $x^* = \\frac{1-\\delta_2}{1-\\delta_1\\delta_2}$.\n"
        "\\end{theorem}\n"
        "\\section{Appendix: Mathematical Derivations}\n"
        "Let $M_1$ and $m_1$ be the supremum and infimum of Player 1's SPE payoffs.\n"
        "In round 2, Player 2 accepts any offer $y > \\delta_2 M_1$, yielding $m_1 \\ge 1 - \\delta_2 M_2$.\n"
        "Symmetrically, $M_1 \\le 1 - \\delta_2 m_2$. Solving yields $M_1 = m_1 = \\frac{1-\\delta_2}{1-\\delta_1\\delta_2}$.\n"
        "\\bibliographystyle{plain}\n"
        "\\bibliography{../ref}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    (exp_dir / "research/sections/packet1.md").write_text("intro packet", encoding="utf-8")
    (exp_dir / "research/sections/packet2.md").write_text("results packet", encoding="utf-8")
    (exp_dir / "research/sections/packet3.md").write_text("appendix packet", encoding="utf-8")
    (exp_dir / "research/coverage.json").write_text(json.dumps({
        "schema_version": "1",
        "mode": "theory",
        "manuscript_sha256": hashlib.sha256(main_tex.read_bytes()).hexdigest(),
        "sections": [
            {
                "id": "introduction",
                "role": "introduction",
                "status": "ready",
                "headings": ["Introduction"],
                "claim_ids": ["thm-1"],
                "artifacts": [{"kind": "section_packet", "path": "research/sections/packet1.md", "sha256": hashlib.sha256((exp_dir / "research/sections/packet1.md").read_bytes()).hexdigest()}]
            },
            {
                "id": "results",
                "role": "results",
                "status": "ready",
                "headings": ["Main Results"],
                "claim_ids": ["thm-1"],
                "artifacts": [{"kind": "section_packet", "path": "research/sections/packet2.md", "sha256": hashlib.sha256((exp_dir / "research/sections/packet2.md").read_bytes()).hexdigest()}]
            },
            {
                "id": "appendix",
                "role": "appendix",
                "status": "ready",
                "headings": ["Appendix: Mathematical Derivations"],
                "claim_ids": ["thm-1"],
                "artifacts": [{"kind": "appendix", "path": "research/sections/packet3.md", "sha256": hashlib.sha256((exp_dir / "research/sections/packet3.md").read_bytes()).hexdigest()}]
            }
        ]
    }), encoding="utf-8")

    (exp_dir / "research/logic.json").write_text(json.dumps({
        "reviewed_sha256": {
            "manuscript": hashlib.sha256(main_tex.read_bytes()).hexdigest(),
            "manifest": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        },
        "overall_verdict": "pending",
        "global_gaps": [],
        "uncertainty": "Exact game-theoretic characterization within stated primitives.",
        "claim_reviews": [
            {
                "claim_id": "thm-1",
                "verdict": "coherent",
                "weakest_link": "Stationary continuation payoff bounds",
                "scope_or_number_mismatch": "",
                "competing_explanation": "",
                "required_revision": "",
            }
        ]
    }), encoding="utf-8")

    build_dir = exp_dir / "paper/build"
    report_file = build_dir / "report.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts/check_latex.py"), "check",
        "--main", str(main_tex),
        "--build-dir", str(build_dir),
        "--report", str(report_file),
        "--engine", "pdflatex",
    ], capture_output=True, text=True, check=False)

    build_passed = record_pending_review(exp_dir, report_file)
    record_unreviewed_team(exp_dir)

    (exp_dir / "research/package.json").write_text(json.dumps({
        "mode": "theory",
        "deliverable": "manuscript",
        "claim_scope": "research-only",
        "mechanism_scope": "not-claimed",
        "manifest": "research/manifest.jsonl",
        "topic_survey": "research/topic.json",
        "manuscript": "paper/manuscript/main.tex",
        "coverage": "research/coverage.json",
        "bibliography": "paper/ref.bib",
        "literature_archive": "research/archive.json",
        "logic_review": "research/logic.json",
        "team_report": "research/team.json",
        "substantive_review": "research/substantive-review.json",
        "latex_main": "paper/manuscript/main.tex",
        "latex_build_dir": "paper/build",
        "latex_engine": "pdflatex",
        "release_pdf": "paper/build/main.pdf",
        "latex_visual_review": "research/visual-review.json",
    }, indent=2), encoding="utf-8")

    workflow = workflow_module.ResearchWorkflow(exp_dir, {
        "mode": "theory",
        "deliverable": "manuscript",
        "claim_scope": "research-only",
        "max_budget": 10.0,
    })
    wf_result = workflow.execute_workflow()
    return {
        "case": "Case 2: Bargaining manuscript fixture",
        "package_valid": wf_result.get("package_audit", {}).get("valid") is True,
        "status": wf_result.get("status"),
        "build_passed": build_passed,
        "failed_gates": failed_gates(wf_result.get("package_audit")),
        "spent_budget": wf_result.get("spent_budget"),
    }


def run_experiment_3_finance_event_study(base_dir: Path) -> dict:
    """Case 3: Synthetic event-return engineering fixture."""
    exp_dir = base_dir / "finance_event_study"
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "data").mkdir(exist_ok=True)
    (exp_dir / "scripts").mkdir(exist_ok=True)
    (exp_dir / "research/diagnostics").mkdir(parents=True, exist_ok=True)
    (exp_dir / "research/sections").mkdir(parents=True, exist_ok=True)
    (exp_dir / "paper/manuscript").mkdir(parents=True, exist_ok=True)
    (exp_dir / "paper/build").mkdir(parents=True, exist_ok=True)
    (exp_dir / "output/tables").mkdir(parents=True, exist_ok=True)

    raw_data = exp_dir / "data/event_returns.csv"
    raw_data.write_text("firm_id,event_date,car_3d,market_cap\n1,2023-03-01,-0.042,500\n2,2023-03-01,-0.038,1200\n3,2023-03-02,-0.051,800\n", encoding="utf-8")
    raw_hash = hashlib.sha256(raw_data.read_bytes()).hexdigest()

    t3_bytes = ("\\begin{tabular}{lc}\nMean CAR & -0.0437 " + r"\\" + "\nSE & 0.0038 " + r"\\" + "\n\\end{tabular}\n").encode()
    t3_b64 = base64.b64encode(t3_bytes).decode("ascii")

    analyze_script = exp_dir / "scripts/analyze.py"
    analyze_script.write_text(
        "import base64, json\n"
        "from pathlib import Path\n"
        "root = Path('.').resolve()\n"
        "car_mean, se = -0.0437, 0.0038\n"
        "results = {\n"
        "  'schema_version': '1',\n"
        "  'run_id': 'run-fin-001',\n"
        "  'source_sha256': {'data/event_returns.csv': '" + raw_hash + "'},\n"
        "  'required_bindings': ['primary.car_mean', 'primary.std_error'],\n"
        "  'results': {'primary': {'car_mean': car_mean, 'std_error': se}}\n"
        "}\n"
        "(root / 'research/results.json').write_text(json.dumps(results, indent=2))\n"
        f"(root / 'output/tables/car_table.tex').write_bytes(base64.b64decode('{t3_b64}'))\n",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(analyze_script)], cwd=exp_dir, check=True)
    res_hash = hashlib.sha256((exp_dir / "research/results.json").read_bytes()).hexdigest()

    manifest = exp_dir / "research/manifest.jsonl"
    records = [
        {"id": "ev-1", "type": "evidence", "source": "synthetic event-return fixture", "locator": "data/event_returns.csv", "verified_at": "2026-10-16", "supports_obligations": [], "_line": 1},
        {"id": "find-1", "type": "finding", "statement": "Mean CAR is -4.37%", "run_ids": ["r-1"], "status": "supported", "supports_obligations": ["event_clustering"], "_line": 2},
        {"id": "c-car", "type": "claim", "statement": "Regulatory disclosure induces negative CAR of -0.0437 [claim:c-car]", "role": "conclusion", "central": True,
         "status": "provisional", "scope": "proxy_only", "uncertainty": "three synthetic firms do not support clustered inference", "finding_ids": ["find-1"], "evidence_ids": ["ev-1"],
         "obligations": ["event_clustering"], "assignment_unit": "firm", "inference_procedure": "cluster_firm", "_line": 3},
    ]
    manifest.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    fin_diagnostics = ["event-time", "information-leakage", "confounding-news", "normal-return-model", "cross-sectional-dependence", "assignment", "support", "inference"]
    for d in fin_diagnostics:
        (exp_dir / f"research/diagnostics/{d}.json").write_text("{}", encoding="utf-8")
    (exp_dir / "research/design-audit.json").write_text(json.dumps({
        "design": "finance-event-study",
        "estimand": "Cumulative abnormal returns around regulatory announcement",
        "assignment_narrative": "synthetic event dates; no observed regulatory shock",
        "interpretation_boundary": "Publicly traded commercial banks",
        "diagnostics": [
            {"id": d, "status": "pending", "finding": f"Synthetic fixture; {d} not scientifically audited", "artifact": f"research/diagnostics/{d}.json"}
            for d in fin_diagnostics
        ]
    }), encoding="utf-8")

    (exp_dir / "paper/ref.bib").write_text("@article{fama1969, author={Fama, Eugene}, title={Adjustment of Stock Prices}, journal={Int Econ Rev}, year={1969}}\n", encoding="utf-8")
    (exp_dir / "research/topic.json").write_text(json.dumps({"approved": False, "status": "pending", "note": "No frontier literature search performed"}), encoding="utf-8")
    (exp_dir / "research/data.json").write_text(json.dumps({"status": "synthetic-fixture", "sources": [{"name": "synthetic_events", "status": "local", "locator": "data/event_returns.csv"}]}), encoding="utf-8")
    (exp_dir / "research/archive.json").write_text(json.dumps({"complete": False, "papers": 0, "downloaded": 0, "status": "pending"}), encoding="utf-8")

    main_tex = exp_dir / "paper/manuscript/main.tex"
    main_tex.write_text(
        "\\documentclass{article}\n"
        "\\usepackage{amsmath}\n"
        "\\newcommand{\\result}[2]{#2}\n"
        "\\begin{document}\n"
        "\\title{Market Reactions to Regulatory Disclosure: An Event Study}\n"
        "\\author{Research Team}\n"
        "\\maketitle\n"
        "\\section{Introduction}\n"
        "We measure cumulative abnormal returns [claim:c-car] \\cite{fama1969}.\n"
        "\\section{Empirical Results}\n"
        "The 3-day mean CAR is \\result{primary.car_mean}{-0.0437}\n"
        "with an illustrative standard-error placeholder \\result{primary.std_error}{0.0038}; clustered inference is unverified.\n"
        "% [results-sha256:" + res_hash + "]\n"
        "\\par\\medskip\\noindent\\input{../../output/tables/car_table.tex}\n"
        "\\bibliographystyle{plain}\n"
        "\\bibliography{../ref}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    (exp_dir / "research/sections/packet1.md").write_text("intro packet", encoding="utf-8")
    (exp_dir / "research/sections/packet2.md").write_text("results packet", encoding="utf-8")
    (exp_dir / "research/coverage.json").write_text(json.dumps({
        "schema_version": "1",
        "mode": "empirical",
        "manuscript_sha256": hashlib.sha256(main_tex.read_bytes()).hexdigest(),
        "sections": [
            {
                "id": "introduction",
                "role": "introduction",
                "status": "ready",
                "headings": ["Introduction"],
                "claim_ids": ["c-car"],
                "artifacts": [{"kind": "section_packet", "path": "research/sections/packet1.md", "sha256": hashlib.sha256((exp_dir / "research/sections/packet1.md").read_bytes()).hexdigest()}]
            },
            {
                "id": "results",
                "role": "results",
                "status": "ready",
                "headings": ["Empirical Results"],
                "claim_ids": ["c-car"],
                "artifacts": [
                    {"kind": "section_packet", "path": "research/sections/packet2.md", "sha256": hashlib.sha256((exp_dir / "research/sections/packet2.md").read_bytes()).hexdigest()},
                    {"kind": "analysis_code", "path": "scripts/analyze.py", "sha256": hashlib.sha256(analyze_script.read_bytes()).hexdigest()},
                    {"kind": "result", "path": "research/results.json", "sha256": hashlib.sha256((exp_dir / "research/results.json").read_bytes()).hexdigest()},
                    {"kind": "table", "path": "output/tables/car_table.tex", "sha256": hashlib.sha256((exp_dir / "output/tables/car_table.tex").read_bytes()).hexdigest()},
                ]
            }
        ]
    }), encoding="utf-8")

    (exp_dir / "research/logic.json").write_text(json.dumps({
        "reviewed_sha256": {
            "manuscript": hashlib.sha256(main_tex.read_bytes()).hexdigest(),
            "manifest": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        },
        "overall_verdict": "pending",
        "global_gaps": [],
        "uncertainty": "Cluster standard errors account for cross-sectional event correlation.",
        "claim_reviews": [
            {
                "claim_id": "c-car",
                "verdict": "coherent",
                "weakest_link": "Market model benchmark window estimation",
                "scope_or_number_mismatch": "",
                "competing_explanation": "",
                "required_revision": "",
            }
        ]
    }), encoding="utf-8")

    build_dir = exp_dir / "paper/build"
    report_file = build_dir / "report.json"
    subprocess.run([
        sys.executable, str(ROOT / "scripts/check_latex.py"), "check",
        "--main", str(main_tex),
        "--build-dir", str(build_dir),
        "--report", str(report_file),
        "--engine", "pdflatex",
    ], capture_output=True, text=True, check=False)

    build_passed = record_pending_review(exp_dir, report_file)
    record_unreviewed_team(exp_dir)

    (exp_dir / "research/replication.json").write_text(json.dumps({
        "commands": [[sys.executable, "scripts/analyze.py"]],
        "raw_inputs": ["data/event_returns.csv"],
        "generated": ["research/results.json", "output/tables/car_table.tex"],
        "results": "research/results.json",
        "clean": True,
    }), encoding="utf-8")
    (exp_dir / "research/package.json").write_text(json.dumps({
        "mode": "empirical",
        "deliverable": "manuscript",
        "claim_scope": "research-only",
        "mechanism_scope": "not-claimed",
        "manifest": "research/manifest.jsonl",
        "topic_survey": "research/topic.json",
        "data_provenance": "research/data.json",
        "results": "research/results.json",
        "replication": "research/replication.json",
        "design_audit": "research/design-audit.json",
        "manuscript": "paper/manuscript/main.tex",
        "coverage": "research/coverage.json",
        "bibliography": "paper/ref.bib",
        "literature_archive": "research/archive.json",
        "logic_review": "research/logic.json",
        "team_report": "research/team.json",
        "substantive_review": "research/substantive-review.json",
        "latex_main": "paper/manuscript/main.tex",
        "latex_build_dir": "paper/build",
        "latex_engine": "pdflatex",
        "release_pdf": "paper/build/main.pdf",
        "latex_visual_review": "research/visual-review.json",
    }, indent=2), encoding="utf-8")

    workflow = workflow_module.ResearchWorkflow(exp_dir, {
        "mode": "empirical",
        "deliverable": "manuscript",
        "claim_scope": "research-only",
        "max_budget": 10.0,
        "analysis_commands": [[sys.executable, "scripts/analyze.py"]],
        "raw_inputs": ["data/event_returns.csv"],
        "generated_outputs": ["research/results.json", "output/tables/car_table.tex"],
        "latex_engine": "pdflatex",
    })
    wf_result = workflow.execute_workflow()
    return {
        "case": "Case 3: Synthetic event-return engineering fixture",
        "reproducible": wf_result.get("replication", {}).get("reproducible") is True,
        "package_valid": wf_result.get("package_audit", {}).get("valid") is True,
        "status": wf_result.get("status"),
        "build_passed": build_passed,
        "failed_gates": failed_gates(wf_result.get("package_audit")),
        "spent_budget": wf_result.get("spent_budget"),
    }


def run_experiment_4_debugging_self_patch(base_dir: Path) -> dict:
    """Case 4: Debugging & Bounded Self-Patching Experiment."""
    exp_dir = base_dir / "debugging_patch"
    exp_dir.mkdir(parents=True, exist_ok=True)
    tree_file = exp_dir / "research/discovery_tree.jsonl"
    tree_file.parent.mkdir(parents=True, exist_ok=True)

    calls = []
    def adapter_runner(_adapter, req, _timeout):
        cmd = req["action"]["payload"]["command"]
        calls.append(list(cmd))
        if "--json" in cmd:
            return {"status": "failed", "cost": 0, "stderr": "unrecognized arguments: --json", "stdout": ""}
        return {"status": "complete", "cost": 1.2, "next_actions": []}

    package_states = iter([
        {"valid": False, "return_to": ["build"], "checks": []},
        {"valid": True, "return_to": [], "checks": []},
    ])
    def package_runner(*_args):
        return next(package_states)

    action = {
        "id": "act-unsupported-flag",
        "stage": "build",
        "kind": "compile",
        "estimated_cost": 1.2,
        "payload": {"command": [sys.executable, "build.py", "--json"]},
    }

    dream_simulator.online_loop(
        tree_path=tree_file,
        policy={"policy_id": "p", "exploration": 1.0, "action_priorities": [], "statistics": {}},
        actions=[action],
        adapter=Path("adapter"),
        root=exp_dir,
        config=Path("package.json"),
        max_steps=5,
        max_cost=10.0,
        package_runner=package_runner,
        adapter_runner=adapter_runner,
    )

    nodes = dream_simulator.load_discovery_tree(tree_file)
    self_patched = any("self_patch" in n for n in nodes)
    return {
        "case": "Case 4: Bounded Self-Patching for CLI Flag Defect",
        "attempted_calls": len(calls),
        "recovered_successfully": len(calls) == 2 and "--json" not in calls[1],
        "self_patch_recorded": self_patched,
        "patch_detail": nodes[0].get("self_patch") if nodes else None,
    }


def run_experiment_5_interruption_budget(base_dir: Path) -> dict:
    """Case 5: Interruption & Budget Exhaustion Control."""
    exp_dir = base_dir / "interruption_budget"
    exp_dir.mkdir(parents=True, exist_ok=True)
    tree_file = exp_dir / "research/discovery_tree.jsonl"
    tree_file.parent.mkdir(parents=True, exist_ok=True)

    initial_nodes = [
        {
            "node_id": "n1", "parent_id": None, "cost": 9.0,
            "action": {"id": "a1", "stage": "estimation", "kind": "reg", "estimated_cost": 9.0},
            "outcome_status": "complete", "next_actions": [{"id": "a2", "stage": "estimation", "kind": "reg", "estimated_cost": 2.0}],
        }
    ]
    tree_file.write_text("\n".join(json.dumps(n) for n in initial_nodes) + "\n", encoding="utf-8")

    res = dream_simulator.online_loop(
        tree_path=tree_file,
        policy={"policy_id": "p", "exploration": 1.0, "action_priorities": [], "statistics": {}},
        actions=[],
        adapter=Path("adapter"),
        root=exp_dir,
        config=Path("package.json"),
        max_steps=5,
        max_cost=10.0,
        package_runner=lambda *a: {"valid": False, "return_to": ["estimation"], "checks": []},
        adapter_runner=lambda *a: {"status": "complete", "cost": 2.0},
    )

    return {
        "case": "Case 5: Interruption & Budget Control",
        "spent_preserved": res["cost"] == 9.0,
        "halted_correctly": res["status"] in {"blocked", "budget-exhausted"},
        "budget_limit": 10.0,
        "recorded_cost": res["cost"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="new directory for this run; existing directories are rejected")
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base = args.output_dir or Path(__file__).resolve().parent / "runs" / stamp
    base.mkdir(parents=True, exist_ok=False)

    cases = [
        run_experiment_1_empirical_did,
        run_experiment_2_theory_bargaining,
        run_experiment_3_finance_event_study,
        run_experiment_4_debugging_self_patch,
        run_experiment_5_interruption_budget,
    ]
    results = []
    for case in cases:
        started = time.monotonic()
        try:
            result = case(base)
        except Exception as exc:
            result = {"case": case.__name__, "error": f"{type(exc).__name__}: {exc}"}
        result["duration_sec"] = round(time.monotonic() - started, 3)
        results.append(result)
        print(f"{result['case']}: {result.get('status', 'engineering test')} ")

    (base / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 自動論文工作流：工程實驗紀錄", "",
        f"執行時間：{datetime.datetime.now(datetime.timezone.utc).isoformat()}", "",
        "此批使用小型合成或示意資料，測試重跑、編譯、gate、修補與中斷恢復。它不衡量真實論文品質。", "",
        "| 案例 | 重跑 | 自動編譯 | 完整 package | 狀態 |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result['case']} | {result.get('reproducible', '—')} | {result.get('build_passed', '—')} | "
            f"{result.get('package_valid', '—')} | {result.get('status', result.get('error', 'engineering test'))} |"
        )
    lines.extend(["", "## 未通過的關卡", ""])
    for result in results[:3]:
        lines.append(f"- {result['case']}：")
        if result.get("error"):
            lines.append(f"  - 執行錯誤：{result['error']}")
        elif result.get("failed_gates"):
            for failure in result["failed_gates"]:
                reason = failure.get("reason")
                if isinstance(reason, list):
                    reason = "; ".join(str(item) for item in reason[:3])
                    if len(failure.get("reason", [])) > 3:
                        reason += "；其餘見 report.json"
                lines.append(f"  - {failure['gate']}：{reason}")
        else:
            lines.append("  - 無失敗關卡紀錄；請核對 package 審計結果。")
    lines.extend([
        "", "完整 package 的結果以表格與上述逐項關卡為準；未完成的研究義務不可由工程 fixture 代替。",
        "案例 4 僅測不支援 CLI 旗標的有限修補；案例 5 僅測已記錄成本與待辦保留。",
        "`build_passed` 只代表自動 LaTeX 檢查；本批沒有人工或獨立 agent 的逐頁審閱。",
        "原始輸入是合成 fixture，不能推論政策因果效果、有效群聚標準誤、正式理論證明或頂刊貢獻。",
        "", "詳細機器結果見 `report.json`；每個案例的 artifacts 保留在同一目錄。", "",
    ])
    (base / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Reports: {base / 'report.md'}")
    return 1 if any("error" in result for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
