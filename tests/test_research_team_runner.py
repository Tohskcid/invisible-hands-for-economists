import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_research_team import (
    contribution_gap, handoff, publication_goal, review_rework_task, roles_for, run, snapshot,
    topic_rejected, verify_exploration_append, verify_review_output,
)


class ResearchTeamRunnerTests(unittest.TestCase):
    def test_rework_routing_keeps_fresh_referee(self):
        self.assertEqual(roles_for("theory", "delivery"), ["writing", "review", "coordination"])
        self.assertEqual(roles_for("theory", "literature")[0], "literature")
        self.assertEqual(roles_for("theory", "analysis")[0], "validation")
        self.assertEqual(roles_for("theory", "exploration")[0], "exploration")
        self.assertIn("data_acquisition", roles_for("empirical"))
        self.assertEqual(roles_for("empirical")[:5], ["literature", "prior_art_review", "planning", "data_acquisition", "data_cleaning"])
        self.assertNotIn("model", roles_for("replication"))

    def test_each_revision_appends_an_unchanged_experiment_row(self):
        first = b"iteration\tmode\n1\ttheory\n"
        verify_exploration_append(first, first + b"2\ttheory\n")
        with self.assertRaisesRegex(ValueError, "did not add"):
            verify_exploration_append(first, first)
        with self.assertRaisesRegex(ValueError, "rewritten"):
            verify_exploration_append(first, b"iteration\tmode\n1\tempirical\n2\ttheory\n")

    def test_handoff_rejects_unbound_and_escaped_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = root / "note.txt"
            note.write_text("evidence", encoding="utf-8")
            report = root / "handoff.json"
            report.write_text(json.dumps({"role": "literature", "status": "complete", "artifacts": [
                {"path": "note.txt", "sha256": hashlib.sha256(note.read_bytes()).hexdigest()}]}))
            self.assertEqual(handoff(root, report, "literature")["status"], "complete")
            note.write_text("changed", encoding="utf-8")
            with self.assertRaises(ValueError):
                handoff(root, report, "literature")

    def test_snapshot_keeps_prior_paper_without_recursing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paper = root / "paper/main.tex"
            paper.parent.mkdir()
            paper.write_text("old", encoding="utf-8")
            archive = snapshot(root, 2)
            paper.write_text("new", encoding="utf-8")
            second = snapshot(root, 2)
            self.assertNotEqual(archive, second)
            import zipfile
            with zipfile.ZipFile(archive) as saved:
                self.assertEqual(saved.read("paper/main.tex"), b"old")
                self.assertNotIn("research/round-snapshots/before-round-02.zip", saved.namelist())

    def test_review_requires_fresh_record_with_assigned_identity_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            target = root / "research/substantive-review.json"
            target.parent.mkdir()
            target.write_text(json.dumps({"reviewer_id": "old-id", "verdict": "reject"}))
            before = hashlib.sha256(target.read_bytes()).hexdigest()
            record = {"artifacts": [{"path": "research/substantive-review.json", "sha256": before}]}
            with self.assertRaisesRegex(ValueError, "did not create or update"):
                verify_review_output(root, target, record, "new-id", before, False)
            target.write_text(json.dumps({"reviewer_id": "wrong-id", "verdict": "reject"}))
            record["artifacts"][0]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "assigned reviewer"):
                verify_review_output(root, target, record, "new-id", before, False)
            target.write_text(json.dumps({"reviewer_id": "new-id", "verdict": "reject"}))
            record["artifacts"][0]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            verify_review_output(root, target, record, "new-id", before, False)
            self.assertEqual(json.loads(target.read_text())["verdict"], "reject")

    def test_uncertain_novelty_requires_a_separate_topic_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = root / "research/substantive-review.json"
            review.parent.mkdir()
            review.write_text(json.dumps({"dimensions": {"novelty": {"verdict": "uncertain"}}}))
            self.assertTrue(topic_rejected(root))

    def test_original_goal_rejects_replication_decision_before_design(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            survey = root / "research/topic-survey.json"
            survey.parent.mkdir()
            survey.write_text(json.dumps({"decision": "replicate", "contribution_class": "replication"}))
            self.assertEqual(publication_goal({"mode": "empirical"}), "original")
            self.assertEqual(publication_goal({"mode": "replication"}), "replication")
            self.assertIsNotNone(contribution_gap(root, "original"))
            self.assertIsNone(contribution_gap(root, "replication"))
            survey.write_text(json.dumps({"decision": "proceed", "contribution_class": "distinct-under-search"}))
            self.assertIn("contribution_probe", contribution_gap(root, "original"))
            survey.write_text(json.dumps({"decision": "proceed", "contribution_class": "distinct-under-search",
                                          "contribution_probe": {
                                              "nearest_result": "Prior result", "proposed_delta": "New estimand",
                                              "field_significance": "Changes policy choice", "discriminating_test": "Compare predictions",
                                              "failure_condition": "Predictions coincide", "feasible_evidence": "Official panel data",
                                          }}))
            self.assertIsNone(contribution_gap(root, "original"))

    def test_referee_design_failure_routes_to_design(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = root / "research/substantive-review.json"
            review.parent.mkdir()
            review.write_text(json.dumps({"dimensions": {
                "novelty": {"verdict": "pass"}, "overlap": {"verdict": "pass"},
                "research_design": {"verdict": "revise", "reason": "No discriminating test"},
            }}))
            task = review_rework_task(root)
            self.assertEqual(task["stage"], "design")
            self.assertIn("No discriminating test", task["reason"]["research_design"])
            document = json.loads(review.read_text())
            document["rework_stage"] = "data"
            review.write_text(json.dumps(document))
            self.assertEqual(review_rework_task(root)["stage"], "data")

    def test_real_subprocess_dispatch_records_ids_and_stops_at_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "research").mkdir()
            (root / "research/contract-input.json").write_text(json.dumps({
                "question": "Can a rule be derived?", "mode": "theory", "deliverable": "manuscript",
                "claim_scope": "research-only", "publication_goal": "replication", "max_budget": 20,
            }), encoding="utf-8")
            fake = root / "fake-codex"
            fake.write_text('''#!/usr/bin/env python3
import hashlib, json, pathlib, re, sys
args=sys.argv
root=pathlib.Path(args[args.index("-C")+1])
final=pathlib.Path(args[args.index("-o")+1])
message=sys.stdin.read()
role=re.search(r"role=(\\w+)", message).group(1)
folder=(root/re.search(r"(research/agent-runs/[^ ]+/round-01/"+role+r"/handoff.json)",message).group(1)).parent
folder.mkdir(parents=True, exist_ok=True)
note=folder/"note.txt"
note.write_text(role)
if role=="literature":
    (root/"research/topic-survey.json").write_text("{}")
if role in {"prior_art_review","review"}:
    reviewer=re.search(r"assigned reviewer_id is ([\\w-]+)",message).group(1)
    review=root/("research/prior-art-review.json" if role=="prior_art_review" else "research/substantive-review.json")
    review.write_text(json.dumps({"independent_review":{"reviewer_id":reviewer}} if role=="prior_art_review" else {"reviewer_id":reviewer,"dimensions":{}}))
if role=="exploration":
    tsv=root/"research/experiments.tsv"
    tsv.write_text("iteration\\tmode\\thypothesis\\tvalidation\\tstatus\\tartifact\\tartifact_sha256\\treason\\tnext_action\\n"+"1\\ttheory\\th\\ttest\\tkeep\\t"+str(note.relative_to(root))+"\\t"+hashlib.sha256(note.read_bytes()).hexdigest()+"\\tobserved\\tcontinue\\n")
artifacts=[{"path":str(note.relative_to(root)),"sha256":hashlib.sha256(note.read_bytes()).hexdigest()}]
if role in {"prior_art_review","review"}:
    artifacts.append({"path":str(review.relative_to(root)),"sha256":hashlib.sha256(review.read_bytes()).hexdigest()})
handoff={"role":role,"status":"complete","findings":"test","unresolved_issues":[],"next_action":"continue","artifacts":artifacts}
(folder/"handoff.json").write_text(json.dumps(handoff))
final.write_text("done")
print(json.dumps({"type":"thread.started","thread_id":"fake-"+role}))
''', encoding="utf-8")
            fake.chmod(0o755)
            blocked = run(root, Path("research/contract-input.json"), str(fake), 1)
            self.assertEqual(blocked["status"], "prior-art-blocked")
            self.assertFalse(list((root / "research/agent-runs").glob("run-*/round-01/planning")))
            real_run = subprocess.run

            def pass_preflight(command, *args, **kwargs):
                if any("check_topic_survey.py" in str(part) or "check_prior_art_review.py" in str(part)
                       or "check_exploration_ledger.py" in str(part) for part in command):
                    return subprocess.CompletedProcess(command, 0, '{"valid":true}', "")
                return real_run(command, *args, **kwargs)

            with patch("run_research_team.subprocess.run", side_effect=pass_preflight):
                result = run(root, Path("research/contract-input.json"), str(fake), 1)
            self.assertEqual(result["status"], "max-rounds")
            self.assertEqual(len(list((root / "research/agent-runs").glob("run-*/round-01"))), 2)
            self.assertEqual(len(result["rounds"][0]["handoffs"]), len(roles_for("theory")))
            ledger = (root / "research/ledger.jsonl").read_text(encoding="utf-8")
            self.assertIn('"agent_id": "fake-review"', ledger)

    def test_replication_candidate_branches_with_receipts_and_no_design_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "research").mkdir()
            (root / "research/contract-input.json").write_text(json.dumps({
                "question": "What is the original mechanism?", "mode": "theory", "deliverable": "manuscript",
                "claim_scope": "research-only", "publication_goal": "original", "max_budget": 20,
            }), encoding="utf-8")
            fake = root / "fake-codex"
            fake.write_text('''#!/usr/bin/env python3
import hashlib, json, pathlib, re, sys
args=sys.argv
root=pathlib.Path(args[args.index("-C")+1])
final=pathlib.Path(args[args.index("-o")+1])
message=sys.stdin.read()
role=re.search(r"role=(\\w+)", message).group(1)
handoff=root/re.search(r"Write only role-owned files and (research/agent-runs/[^ ]+/round-\\d+/"+role+r"/handoff.json)",message).group(1)
folder=handoff.parent
folder.mkdir(parents=True,exist_ok=True)
note=folder/"note.txt"
note.write_text(role)
if role=="literature":
    (root/"research/topic-survey.json").write_text(json.dumps({"decision":"replicate","contribution_class":"replication"}))
artifacts=[{"path":str(note.relative_to(root)),"sha256":hashlib.sha256(note.read_bytes()).hexdigest()}]
if role=="prior_art_review":
    reviewer=re.search(r"assigned reviewer_id is ([\\w-]+)",message).group(1)
    review=root/"research/prior-art-review.json"
    review.write_text(json.dumps({"independent_review":{"reviewer_id":reviewer}}))
    artifacts.append({"path":str(review.relative_to(root)),"sha256":hashlib.sha256(review.read_bytes()).hexdigest()})
handoff.write_text(json.dumps({"role":role,"status":"complete","artifacts":artifacts}))
final.write_text("done")
print(json.dumps({"type":"thread.started","thread_id":"fake-"+role}))
''', encoding="utf-8")
            fake.chmod(0o755)
            real_run = subprocess.run

            def pass_preflight(command, *args, **kwargs):
                if any("check_topic_survey.py" in str(part) or "check_prior_art_review.py" in str(part) for part in command):
                    return subprocess.CompletedProcess(command, 0, '{"valid":true}', "")
                return real_run(command, *args, **kwargs)

            with patch("run_research_team.subprocess.run", side_effect=pass_preflight):
                result = run(root, Path("research/contract-input.json"), str(fake), 2)
            self.assertEqual(result["status"], "contribution-unresolved", result)
            self.assertEqual(len(result["rounds"]), 2)
            self.assertEqual(len((root / "research/contribution-branches.jsonl").read_text().splitlines()), 2)
            self.assertFalse(list((root / "research/agent-runs").glob("run-*/round-*/planning")))
            self.assertTrue(list((root / "research/round-snapshots").glob("before-round-02*.zip")))


if __name__ == "__main__":
    unittest.main()
