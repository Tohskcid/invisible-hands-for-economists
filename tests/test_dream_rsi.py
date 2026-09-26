import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dream_replay_simulator", ROOT / "scripts/dream_replay_simulator.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DreamRSITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tree_file = Path(self.temp_dir.name) / "discovery_tree.jsonl"
        self.sample_nodes = [
            {
                "node_id": "root",
                "parent_id": None,
                "metrics": {"direct_effect": -0.0030, "first_stage_f": 35.0},
                "referee_vulnerabilities": ["greg_correlation"]
            },
            {
                "node_id": "branch-1",
                "parent_id": "root",
                "metrics": {"direct_effect": -0.0035, "first_stage_f": 28.0},
                "referee_vulnerabilities": ["macro_shock"]
            },
            {
                "node_id": "branch-2",
                "parent_id": "root",
                "metrics": {"direct_effect": -0.0028, "first_stage_f": 8.0},  # weak IV
                "referee_vulnerabilities": []
            }
        ]
        with open(self.tree_file, "w", encoding="utf-8") as f:
            for n in self.sample_nodes:
                f.write(json.dumps(n) + "\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_and_audit(self):
        nodes = MODULE.load_discovery_tree(self.tree_file)
        self.assertEqual(len(nodes), 3)
        audit = MODULE.audit_tree_structure(nodes)
        self.assertTrue(audit["valid"])
        self.assertEqual(audit["node_count"], 3)

    def test_audit_rejects_dangling_parent(self):
        nodes = list(self.sample_nodes)
        nodes[1] = {**nodes[1], "parent_id": "missing"}
        audit = MODULE.audit_tree_structure(nodes)
        self.assertFalse(audit["valid"])
        self.assertIn("unknown parent", audit["reason"])

    def test_dream_spec_curve_filters_weak_iv(self):
        nodes = MODULE.load_discovery_tree(self.tree_file)
        res = MODULE.dream_offline_spec_curve(nodes, min_f_stat=10.0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["screened_candidates"], 3)
        self.assertEqual(res["retained_specifications"], 2)
        self.assertAlmostEqual(res["sign_stability"], 1.0)

    def test_evolve_adversarial_pool(self):
        nodes = MODULE.load_discovery_tree(self.tree_file)
        pool_path = Path(self.temp_dir.name) / "adversarial-pool.json"
        pool = MODULE.evolve_adversarial_pool(nodes, pool_path)
        self.assertIn("greg_correlation", pool)
        self.assertIn("macro_shock", pool)
        self.assertEqual(json.loads(pool_path.read_text(encoding="utf-8")), pool)

    def test_policy_learning_uses_gate_reward_not_effect_size(self):
        nodes = [
            {
                "action": {"stage": "evidence_generation", "kind": "placebo"},
                "reward": 0.8,
                "reward_source": "package-gate-v1",
                "metrics": {"direct_effect": 999.0},
            },
            {
                "action": {"stage": "evidence_generation", "kind": "negative-control"},
                "reward": 0.2,
                "reward_source": "package-gate-v1",
                "metrics": {"direct_effect": 0.0},
            },
        ]
        policy = MODULE.learn_policy(nodes)
        stats = policy["statistics"]
        self.assertEqual(stats["evidence_generation|placebo"]["mean_reward"], 0.8)
        nodes[0]["metrics"]["direct_effect"] = -999.0
        self.assertEqual(MODULE.learn_policy(nodes), policy)

    def test_action_selection_respects_gate_stage_budget_and_researcher_lock(self):
        policy = {
            "exploration": 1.0,
            "action_priorities": ["negative-control", "placebo"],
            "statistics": {},
        }
        actions = [
            {"id": "wrong", "stage": "design", "kind": "negative-control", "estimated_cost": 1},
            {"id": "locked", "stage": "evidence_generation", "kind": "negative-control", "estimated_cost": 1, "requires_researcher": True},
            {"id": "eligible", "stage": "evidence_generation", "kind": "placebo", "estimated_cost": 2},
        ]
        selected = MODULE.select_action(policy, ["evidence_generation"], actions, remaining_cost=2)
        self.assertEqual(selected["id"], "eligible")

    def test_online_loop_executes_and_records_until_package_passes(self):
        actions = [{"id": "a1", "stage": "evidence_generation", "kind": "placebo", "estimated_cost": 1}]
        package_reports = iter([
            {"valid": False, "return_to": ["evidence_generation"], "checks": [{"passed": False}]},
            {"valid": True, "return_to": [], "checks": [{"passed": True}]},
        ])

        def package_runner(*_args):
            return next(package_reports)

        def adapter_runner(_adapter, request, _timeout):
            self.assertEqual(request["action"]["id"], "a1")
            return {"status": "complete", "cost": 1, "next_actions": []}

        report = MODULE.online_loop(
            tree_path=self.tree_file,
            policy={"policy_id": "p1", "exploration": 1.0, "action_priorities": [], "statistics": {}},
            actions=actions,
            adapter=Path("adapter"),
            root=Path(self.temp_dir.name),
            config=Path("research/package.json"),
            max_steps=3,
            max_cost=3,
            package_runner=package_runner,
            adapter_runner=adapter_runner,
        )
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["steps"], 1)
        self.assertEqual(len(MODULE.load_discovery_tree(self.tree_file)), 4)


if __name__ == "__main__":
    unittest.main()
