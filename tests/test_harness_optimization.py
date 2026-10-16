#!/usr/bin/env python3
"""Engineering acceptance test suite for Harness Optimization Plan (Section 8.1).

Verifies the 10 engineering acceptance scenarios:
1. Deleting required gate or using skipped config never counts as completion.
2. Code discrepancy with results (0 vs 999), stale tables, and missing raw inputs.
3. Single evidence piece improperly covering multiple central obligations.
4. Theory subclass assumption (contraction) falsely claimed as general theorem.
5. Aggregate assignment unit (state) conflicting with individual iid inference.
6. Interruption preserving cumulative cost, pending queue, and avoiding duplication.
7. Locatable CLI / build errors and bounded self-patching.
8. Modifying source files invalidates existing visual review.
9. Release PDF differing from reviewed PDF hash fails verification.
10. Proxy data without proxy_only scope or unverified formal proof claim.
"""

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Import scripts dynamically
def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

pkg_checker = load_module("check_research_package", ROOT / "scripts/check_research_package.py")
latex_checker = load_module("check_latex", ROOT / "scripts/check_latex.py")
manifest_validator = load_module("validate_research_manifest", ROOT / "scripts/validate_research_manifest.py")
replication_runner = load_module("run_replication", ROOT / "scripts/run_replication.py")
dream_simulator = load_module("dream_replay_simulator", ROOT / "scripts/dream_replay_simulator.py")
workflow_module = load_module("run_research_workflow", ROOT / "scripts/run_research_workflow.py")


class HarnessOptimizationAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_next_tasks_include_failed_replay_and_unreviewed_build(self):
        tasks = workflow_module.plan_next_tasks(
            {"valid": True, "checks": []}, [],
            {"reproducible": False, "error": "table changed"},
            {"check": {"automated_passed": True}, "finalize": {"delivery_ready": False, "errors": ["page 2 not reviewed"]}},
        )
        self.assertEqual([task["stage"] for task in tasks], ["replication", "delivery"])
        self.assertEqual(tasks[0]["reason"], "table changed")
        self.assertEqual(tasks[1]["reason"], ["page 2 not reviewed"])

    def test_rework_plan_starts_at_earliest_failed_stage(self):
        plan = workflow_module.rework_plan([
            {"stage": "delivery", "source": "check_latex.py"},
            {"stage": "data", "source": "check_data_provenance.py"},
        ])
        self.assertEqual(plan["restart_from"], "data")
        self.assertIn("delivery", plan["invalidate_stages"])
        self.assertNotIn("literature", plan["invalidate_stages"])
        self.assertIsNone(workflow_module.rework_plan([]))
        workflow_module.save_rework_state(self.root, {"status": "blocked", "rework_plan": plan})
        state_path = self.root / "research/rework-state.json"
        self.assertEqual(json.loads(state_path.read_text())["status"], "open")
        workflow_module.save_rework_state(self.root, {"status": "complete", "rework_plan": None})
        self.assertEqual(json.loads(state_path.read_text())["status"], "cleared")

    # --- Scenario 1: Deleting required gate / skipped config false completion ---
    def test_scenario_1_delete_required_gate_or_skipped_config(self):
        """WP1 & Section 8.1.1: Missing required gate or skipped config must fail."""
        pkg_path = self.root / "research/package.json"
        pkg_path.parent.mkdir(parents=True, exist_ok=True)

        # Empirical manuscript requires design_audit
        config = {
            "mode": "empirical",
            "deliverable": "manuscript",
            "manifest": "research/manifest.jsonl",
            "topic_survey": "research/topic.json",
            "data_provenance": "research/data.json",
            "results": "research/results.json",
            # "design_audit" intentionally omitted
            "manuscript": "paper/main.tex",
            "coverage": "research/coverage.json",
            "bibliography": "paper/ref.bib",
            "literature_archive": "research/archive.json",
            "logic_review": "research/logic.json",
            "latex_main": "paper/main.tex",
            "latex_visual_review": "research/review.json",
        }
        pkg_path.write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "design_audit"):
            pkg_checker.check(self.root, pkg_path, ROOT / "scripts")

        config["unapplicable_justification"] = {"design_audit": "skip difficult gate"}
        pkg_path.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "design_audit"):
            pkg_checker.check(self.root, pkg_path, ROOT / "scripts")

        # Skipped config via --allow-missing must not return 0 or valid
        non_existent = self.root / "research/missing_package.json"
        res = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_research_package.py"), "--config", str(non_existent), "--allow-missing"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 2)
        report = json.loads(res.stdout)
        self.assertFalse(report["valid"])
        self.assertTrue(report["skipped"])

    # --- Scenario 2: Code vs results discrepancy, stale tables, missing raw input ---
    def test_scenario_2_code_results_discrepancy_and_stale_table_and_missing_raw(self):
        """WP3 & Section 8.1.2: Detect mismatch (0 vs 999), stale artifacts, and missing inputs."""
        scripts_dir = self.root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        data_dir = self.root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir = self.root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        res_dir = self.root / "research"
        res_dir.mkdir(parents=True, exist_ok=True)

        # 1. Missing raw input test
        raw_file = data_dir / "raw.csv"
        rep_missing = replication_runner.run_replication(
            root=self.root,
            entry_commands=[[sys.executable, "-c", "print('ok')"]],
            raw_inputs=["data/raw.csv"],
            generated=[],
            clean_before_run=False,
        )
        self.assertFalse(rep_missing["reproducible"])
        self.assertIn("data/raw.csv", rep_missing["missing_raw_inputs"])

        # Create raw data
        raw_file.write_text("id,val\n1,10\n", encoding="utf-8")

        # 2. Code produces 0.0, but results.json claims 999.0
        results_file = res_dir / "results.json"
        results_file.write_text(json.dumps({"results": {"primary": {"estimate": 999.0}}}), encoding="utf-8")

        # Script that writes 0.0 into results.json
        compute_script = scripts_dir / "compute.py"
        compute_script.write_text(
            "import json; from pathlib import Path; Path('research/results.json').write_text(json.dumps({'results': {'primary': {'estimate': 0.0}}}))",
            encoding="utf-8",
        )

        rep_discrepancy = replication_runner.run_replication(
            root=self.root,
            entry_commands=[[sys.executable, "scripts/compute.py"]],
            raw_inputs=["data/raw.csv"],
            generated=[],
            expected_results_file=results_file,
            clean_before_run=False,
        )
        self.assertFalse(rep_discrepancy["reproducible"])
        self.assertTrue(any("numeric discrepancy" in err for err in rep_discrepancy["numeric_discrepancies"]))
        self.assertEqual(json.loads(results_file.read_text())["results"]["primary"]["estimate"], 999.0)

        # 3. Stale table test (table exists before run, but compute script doesn't update it)
        table_file = output_dir / "table1.tex"
        table_file.write_text("old table content", encoding="utf-8")
        time.sleep(0.02)  # ensure timestamp gap
        rep_stale = replication_runner.run_replication(
            root=self.root,
            entry_commands=[[sys.executable, "-c", "pass"]],
            raw_inputs=["data/raw.csv"],
            generated=["output/table1.tex"],
            clean_before_run=False,
        )
        self.assertFalse(rep_stale["reproducible"])
        self.assertIn("output/table1.tex", rep_stale["stale_artifacts"])

        # A regenerated table with different bytes is also a release mismatch.
        compute_script.write_text("from pathlib import Path; Path('output/table1.tex').write_text('new table content')", encoding="utf-8")
        rep_table_mismatch = replication_runner.run_replication(
            root=self.root,
            entry_commands=[[sys.executable, "scripts/compute.py"]],
            raw_inputs=["data/raw.csv"],
            generated=["output/table1.tex"],
        )
        self.assertFalse(rep_table_mismatch["reproducible"])
        self.assertTrue(rep_table_mismatch["artifact_discrepancies"])

    # --- Scenario 3: Single evidence improperly covering multiple obligations ---
    def test_scenario_3_evidence_misused_for_multiple_obligations(self):
        """WP2 & Section 8.1.3: Evidence for A cannot satisfy A+B conclusion."""
        records = [
            {"id": "ev-1", "type": "evidence", "source": "src", "locator": "loc", "verified_at": "now", "supports_obligations": ["anticipation"], "_line": 1},
            {"id": "f-1", "type": "finding", "statement": "no anticipation", "run_ids": ["r-1"], "status": "supported", "supports_obligations": ["anticipation"], "_line": 2},
            {"id": "c-1", "type": "claim", "statement": "causal effect", "role": "conclusion", "central": True, "status": "supported",
             "scope": "observed", "uncertainty": "p<0.05", "finding_ids": ["f-1"], "evidence_ids": ["ev-1"],
             "obligations": ["anticipation", "parallel_trends"], "_line": 3},
        ]
        errors = manifest_validator.validate_argument(records)
        self.assertTrue(any("undischarged obligations remain: ['parallel_trends']" in err for err in errors))

    # --- Scenario 4: Subclass assumption falsely claimed as general theorem ---
    def test_scenario_4_subclass_assumption_claimed_as_general_theorem(self):
        """WP2 & Section 8.1.4: Contraction subclass premise cannot prove general theorem."""
        records = [
            {"id": "ev-1", "type": "evidence", "source": "paper", "locator": "p1", "verified_at": "now", "_line": 1},
            {"id": "c-premise", "type": "claim", "statement": "contraction mapping lemma", "role": "premise", "central": True,
             "status": "supported", "scope": "theoretical", "uncertainty": "exact", "evidence_ids": ["ev-1"],
             "domain": "contraction", "_line": 2},
            {"id": "c-general", "type": "claim", "statement": "general preference equilibrium theorem", "role": "conclusion", "central": True,
             "status": "supported", "scope": "theoretical", "uncertainty": "exact", "premise_ids": ["c-premise"],
             "domain": "general", "_line": 3},
        ]
        errors = manifest_validator.validate_argument(records)
        self.assertTrue(any("depends on narrower premise 'c-premise' with domain 'contraction'" in err for err in errors))

    # --- Scenario 5: Aggregate assignment unit conflicting with individual SE ---
    def test_scenario_5_assignment_unit_conflicts_with_individual_se(self):
        """WP2 & Section 8.1.5: State assignment with restaurant iid SE fails."""
        records = [
            {"id": "c-1", "type": "claim", "statement": "minimum wage increases employment", "role": "conclusion", "central": True,
             "status": "supported", "scope": "observed", "uncertainty": "se", "evidence_ids": ["ev-1"],
             "assignment_unit": "state", "inference_procedure": "iid", "_line": 1},
        ]
        errors = manifest_validator.validate_argument(records)
        self.assertTrue(any("assignment unit 'state' conflicts with individual inference procedure 'iid'" in err for err in errors))

    # --- Scenario 6: Interruption preserves cumulative cost and pending queue ---
    def test_scenario_6_interruption_preserves_cost_and_queue_and_no_duplication(self):
        """WP5 & Section 8.1.6: Restart does not reset cost and does not lose/duplicate actions."""
        tree_file = self.root / "research/discovery_tree.jsonl"
        tree_file.parent.mkdir(parents=True, exist_ok=True)

        # Simulate prior run that spent 8.0 and completed action a1, leaving a2 pending
        initial_nodes = [
            {
                "node_id": "node-1", "parent_id": None, "cost": 8.0,
                "action": {"id": "a1", "stage": "estimation", "kind": "reg", "estimated_cost": 8.0},
                "outcome_status": "complete", "next_actions": [{"id": "a2", "stage": "estimation", "kind": "reg", "estimated_cost": 3.0}],
            }
        ]
        tree_file.write_text("\n".join(json.dumps(n) for n in initial_nodes) + "\n", encoding="utf-8")

        def package_runner(*_args):
            return {"valid": False, "return_to": ["estimation"], "checks": []}

        executed_actions = []
        def adapter_runner(_adapter, req, _timeout):
            executed_actions.append(req["action"]["id"])
            return {"status": "complete", "cost": 3.0, "next_actions": []}

        # Max cost is 10.0. Spent is already 8.0. a2 requires 3.0 -> 8+3=11 > 10!
        res = dream_simulator.online_loop(
            tree_path=tree_file,
            policy={"policy_id": "p", "exploration": 1.0, "action_priorities": [], "statistics": {}},
            actions=[],  # queue recovered from node-1 next_actions!
            adapter=Path("adapter"),
            root=self.root,
            config=Path("package.json"),
            max_steps=5,
            max_cost=10.0,
            package_runner=package_runner,
            adapter_runner=adapter_runner,
        )

        # Budget exhausted, a1 was not duplicated, a2 not executed because 8.0 + 3.0 > 10.0
        self.assertEqual(res["status"], "blocked")
        self.assertEqual(res["cost"], 8.0)
        self.assertEqual(len(executed_actions), 0)

    # --- Scenario 7: Bounded self-patching for CLI flag defect ---
    def test_scenario_7_cli_and_build_path_errors_and_bounded_self_patching(self):
        """WP5 & Section 8.1.7: Unsupported CLI flag is self-patched in loop."""
        tree_file = self.root / "research/discovery_tree.jsonl"
        tree_file.parent.mkdir(parents=True, exist_ok=True)

        package_states = iter([
            {"valid": False, "return_to": ["build"], "checks": []},
            {"valid": True, "return_to": [], "checks": []},
        ])
        def package_runner(*_args):
            return next(package_states)

        calls = []
        def adapter_runner(_adapter, req, _timeout):
            cmd = req["action"]["payload"]["command"]
            calls.append(list(cmd))
            if "--json" in cmd:
                # Simulates CLI failure like 'error: unrecognized arguments: --json'
                return {"status": "failed", "cost": 0.2, "stderr": "unrecognized arguments: --json", "stdout": ""}
            return {"status": "complete", "cost": 1.0, "next_actions": []}

        action = {
            "id": "act-cli",
            "stage": "build",
            "kind": "compile",
            "estimated_cost": 1.0,
            "payload": {"command": ["python", "script.py", "--json"]},
        }

        res = dream_simulator.online_loop(
            tree_path=tree_file,
            policy={"policy_id": "p", "exploration": 1.0, "action_priorities": [], "statistics": {}},
            actions=[action],
            adapter=Path("adapter"),
            root=self.root,
            config=Path("package.json"),
            max_steps=5,
            max_cost=10.0,
            package_runner=package_runner,
            adapter_runner=adapter_runner,
        )

        self.assertEqual(res["status"], "complete")
        self.assertAlmostEqual(res["cost"], 1.2)
        # First call had --json, retry removed --json
        self.assertEqual(len(calls), 2)
        self.assertIn("--json", calls[0])
        self.assertNotIn("--json", calls[1])

        # Check self_patch recorded in tree
        nodes = dream_simulator.load_discovery_tree(tree_file)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["self_patch"]["type"], "cli_flag_removal")

    # --- Scenario 8: Source change invalidates existing visual review ---
    def test_scenario_8_source_change_invalidates_visual_review(self):
        """WP6 & Section 8.1.8: TeX/source file change invalidates existing review."""
        src_dir = self.root / "paper"
        src_dir.mkdir(parents=True, exist_ok=True)
        tex_file = src_dir / "main.tex"
        tex_file.write_text("\\documentclass{article}\\begin{document}Original\\end{document}", encoding="utf-8")
        h_orig = hashlib.sha256(tex_file.read_bytes()).hexdigest()

        report = {
            "automated_passed": True,
            "rendering": {"pdf_sha256": "abc123pdf", "page_count": 1},
            "source_dir": str(src_dir),
            "input_hashes": {"main.tex": h_orig},
        }
        review = {
            "pdf_sha256": "abc123pdf",
            "status": "pass",
            "reviewer": "fresh-referee",
            "pages_reviewed": [1],
            "issues": [],
        }

        # Initially passes
        res_init = latex_checker.finalize(report, review, source_dir=src_dir)
        self.assertTrue(res_init["delivery_ready"])

        # Modify source file after build/review
        tex_file.write_text("\\documentclass{article}\\begin{document}Modified\\end{document}", encoding="utf-8")
        res_after = latex_checker.finalize(report, review, source_dir=src_dir)
        self.assertFalse(res_after["delivery_ready"])
        self.assertTrue(any("modified after build" in err for err in res_after["errors"]))

    def test_bibliography_change_invalidates_review_with_recorder_file(self):
        manuscript = self.root / "paper/manuscript"
        build = self.root / "paper/build"
        manuscript.mkdir(parents=True)
        build.mkdir(parents=True)
        main = manuscript / "main.tex"
        main.write_text("\\documentclass{article}", encoding="utf-8")
        bib = self.root / "paper/ref.bib"
        bib.write_text("@article{a,title={A}}", encoding="utf-8")
        (build / "main.fls").write_text("INPUT main.tex\n", encoding="utf-8")
        source_dir, hashes = latex_checker.collect_build_input_hashes(main, build, build / "rendered")
        self.assertIn("paper/ref.bib", hashes)
        bib.write_text("@article{a,title={Changed}}", encoding="utf-8")
        self.assertTrue(any("ref.bib" in error for error in latex_checker.verify_input_freshness(hashes, source_dir)))

    # --- Scenario 9: Release PDF differing from reviewed PDF fails ---
    def test_scenario_9_release_pdf_different_from_reviewed_pdf(self):
        """WP6 & Section 8.1.9: Release PDF hash mismatch fails verification."""
        pdf_dir = self.root / "output/pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        rel_pdf = pdf_dir / "main.pdf"
        rel_pdf.write_bytes(b"modified release binary")

        report = {
            "automated_passed": True,
            "rendering": {"pdf_sha256": "reviewed_hash_xyz", "page_count": 1},
        }
        review = {
            "pdf_sha256": "reviewed_hash_xyz",
            "status": "pass",
            "reviewer": "agent-reviewer",
            "pages_reviewed": [1],
            "issues": [],
        }

        res = latex_checker.finalize(report, review, release_pdf=rel_pdf)
        self.assertFalse(res["delivery_ready"])
        self.assertTrue(any("does not match reviewed PDF hash" in err for err in res["errors"]))

    # --- Scenario 10: Proxy without proxy_only scope & unverified formal proof ---
    def test_scenario_10_proxy_and_formal_proof_marking_errors(self):
        """WP2 & Section 8.1.10: Proxy requires proxy_only scope; formal proof requires Lean artifact."""
        # 1. Proxy used but claim scope is "observed"
        proxy_records = [
            {"id": "px-1", "type": "proxy", "name": "sim", "reason": "synth", "generator": "g", "seed": 42,
             "schema": "s", "intended_use": "test", "_line": 1},
            {"id": "c-1", "type": "claim", "statement": "proxy claim", "data_ids": ["px-1"],
             "scope": "observed", "evidence_ids": ["ev-dummy"], "_line": 2},
        ]
        errs_proxy = manifest_validator.validate(proxy_records)
        self.assertTrue(any("requires scope 'proxy_only'" in err for err in errs_proxy))

        # 2. Formal proof claimed without Lean artifact
        theory_records = [
            {"id": "c-thm", "type": "claim", "statement": "bargaining uniqueness", "role": "conclusion", "central": True,
             "status": "formally_proved", "proof_method": "formal_proof", "formal_proof_id": "missing_run",
             "scope": "theoretical", "uncertainty": "exact", "evidence_ids": ["ev-1"], "_line": 1},
        ]
        errs_formal = manifest_validator.validate_argument(theory_records)
        self.assertTrue(any("claims formally_proved but lacks verified Lean formal proof run/artifact" in err for err in errs_formal))

    # --- Automated Paper-Writing Workflow Orchestrator End-to-End ---
    def test_automated_workflow_orchestrator_execution(self):
        """Verify run_research_workflow.py initializes contract, records events, and executes gates."""
        contract = {
            "mode": "theory",
            "deliverable": "feasibility_report",
            "claim_scope": "research-only",
            "max_budget": 5.0,
            "question": "Does unique SPE exist in alternating offers bargaining?",
            "obstacles": [
                {
                    "obstacle_id": "obs-1",
                    "blocked_claim_id": "thm-1",
                    "discriminating_test": "check non-stationary deviation",
                    "test_command": [sys.executable, "-c", "import sys; sys.exit(0)"],
                }
            ],
        }
        workflow = workflow_module.ResearchWorkflow(self.root, contract)
        result = workflow.execute_workflow()

        self.assertIn("status", result)
        self.assertEqual(len(result["obstacles"]), 1)
        self.assertEqual(result["obstacles"][0]["status"], "unresolved")
        self.assertEqual(result["status"], "in-progress")

        # Check ledger created and recorded events
        ledger = self.root / "research/ledger.jsonl"
        self.assertTrue(ledger.is_file())
        events = workflow_module.load_ledger_events(ledger)
        event_types = [e["event_type"] for e in events]
        self.assertIn("contract_frozen", event_types)
        self.assertIn("scientific_obstacle_iteration", event_types)
        self.assertIn("workflow_summary", event_types)

        changed = dict(contract, question="Can the question be changed after a run?")
        with self.assertRaisesRegex(ValueError, "changed after it was frozen"):
            workflow_module.ResearchWorkflow(self.root, changed).execute_workflow()

    def test_workflow_stops_after_measured_budget_exhaustion(self):
        contract = {
            "mode": "theory", "deliverable": "feasibility_report", "max_budget": 0.001,
            "obstacles": [{
                "obstacle_id": "slow", "blocked_claim_id": "c1", "discriminating_test": "wait",
                "test_command": [sys.executable, "-c", "import time; time.sleep(0.03)"],
            }],
            "analysis_commands": [[sys.executable, "-c", "print('should not run')"]],
        }
        result = workflow_module.ResearchWorkflow(self.root, contract).execute_workflow()
        self.assertEqual(result["status"], "budget-exhausted")
        self.assertIsNone(result["replication"])
        event_types = [e["event_type"] for e in workflow_module.load_ledger_events(self.root / "research/ledger.jsonl")]
        self.assertNotIn("clean_replay", event_types)

    def test_package_scope_must_match_frozen_contract(self):
        contract = {"mode": "theory", "deliverable": "feasibility_report", "claim_scope": "research-only"}
        package = self.root / "research/package.json"
        package.parent.mkdir(parents=True)
        package.write_text(json.dumps({"mode": "theory", "deliverable": "feasibility_report", "claim_scope": "real-world"}), encoding="utf-8")
        result = workflow_module.ResearchWorkflow(self.root, contract).execute_workflow()
        self.assertFalse(result["package_audit"]["valid"])
        self.assertIn("claim_scope", result["package_audit"]["error"])

    def test_existing_build_report_must_bind_declared_latex_source(self):
        paper = self.root / "paper"
        build = paper / "build"
        build.mkdir(parents=True)
        main = paper / "main.tex"
        main.write_text("\\documentclass{article}", encoding="utf-8")
        review = self.root / "research/review.json"
        review.parent.mkdir(parents=True)
        review.write_text("{}", encoding="utf-8")
        (build / "report.json").write_text(json.dumps({
            "source_dir": str(paper), "input_hashes": {"main.tex": "wrong hash"}
        }), encoding="utf-8")
        package = self.root / "research/package.json"
        package.write_text(json.dumps({
            "latex_main": "paper/main.tex", "latex_visual_review": "research/review.json",
            "latex_build_dir": "paper/build",
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "current latex_main bytes"):
            pkg_checker.check(self.root, package, ROOT / "scripts")

    def test_feasibility_package_can_complete_when_all_required_gates_pass(self):
        research = self.root / "research"
        research.mkdir(parents=True)
        manifest = research / "manifest.jsonl"
        records = [
            {"id": "source", "type": "evidence", "source": "synthetic test source", "locator": "fixture:1", "verified_at": "2026-10-16"},
            {"id": "claim", "type": "claim", "statement": "A scoped theoretical proposition", "role": "conclusion", "central": True,
             "status": "provisional", "scope": "theoretical", "uncertainty": "awaits proof", "evidence_ids": ["source"]},
        ]
        manifest.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
        (research / "package.json").write_text(json.dumps({
            "mode": "theory", "deliverable": "feasibility_report", "claim_scope": "research-only",
            "mechanism_scope": "not-claimed", "manifest": "research/manifest.jsonl",
        }), encoding="utf-8")
        result = workflow_module.ResearchWorkflow(self.root, {
            "mode": "theory", "deliverable": "feasibility_report", "claim_scope": "research-only",
        }).execute_workflow()
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["package_audit"]["valid"])

    def test_manifest_validator_handles_run_without_data_ids(self):
        records = [
            {"id": "run", "type": "run", "_line": 1},
            {"id": "finding", "type": "finding", "run_ids": ["run"], "_line": 2},
            {"id": "claim", "type": "claim", "scope": "theoretical", "finding_ids": ["finding"], "_line": 3},
        ]
        self.assertIsInstance(manifest_validator.validate(records), list)

    def test_scientific_obstacle_requires_hash_bound_assessment(self):
        research = self.root / "research"
        research.mkdir(parents=True)
        evidence = research / "test-result.txt"
        evidence.write_text("counterexample ruled out under stated assumptions", encoding="utf-8")
        (research / "obstacle-assessments.json").write_text(json.dumps({"obstacles": {
            "o1": {
                "status": "resolved", "rationale": "The stated restricted proposition survives this test.",
                "reviewer_kind": "agent", "reviewer": "fresh-reviewer",
                "evidence": [{"path": "research/test-result.txt", "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}],
            }
        }}), encoding="utf-8")
        contract = {"mode": "theory", "deliverable": "feasibility_report", "max_budget": 10,
                    "obstacles": [{"obstacle_id": "o1", "blocked_claim_id": "c1", "discriminating_test": "check counterexample"}]}
        workflow = workflow_module.ResearchWorkflow(self.root, contract)
        first = workflow.execute_workflow()
        self.assertEqual(first["obstacles"][0]["status"], "resolved")
        self.assertFalse(any(task["stage"] == "scientific_obstacle" for task in first["next_tasks"]))

        evidence.write_text("changed result", encoding="utf-8")
        second = workflow.execute_workflow()
        self.assertEqual(second["obstacles"][0]["status"], "unresolved")
        self.assertTrue(any(task["stage"] == "scientific_obstacle" for task in second["next_tasks"]))

    def test_failed_gate_returns_research_task(self):
        tasks = workflow_module.plan_next_tasks({"valid": False, "checks": [{
            "passed": False, "command": [sys.executable, str(ROOT / "scripts/check_data_provenance.py")],
            "stdout": json.dumps({"errors": ["source license missing"]}),
        }]}, [])
        self.assertEqual(tasks[0]["stage"], "data")
        self.assertTrue(tasks[0]["requires_scientific_judgment"])
        self.assertIn("source license missing", tasks[0]["reason"])


if __name__ == "__main__":
    unittest.main()
