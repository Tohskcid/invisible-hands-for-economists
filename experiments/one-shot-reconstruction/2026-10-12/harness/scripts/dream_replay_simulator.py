#!/usr/bin/env python3
"""Replay research histories, learn a safe action policy, and run bounded online iterations."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


DEFAULT_POLICY = {"schema_version": "1", "policy_id": "dream-rsi-bandit-v1", "exploration": 1.0, "action_priorities": [], "statistics": {}}


def load_discovery_tree(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    nodes = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            node = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupt discovery tree at line {number}: {exc.msg}") from exc
        if not isinstance(node, dict):
            raise ValueError(f"discovery tree line {number} must be an object")
        nodes.append(node)
    return nodes


def audit_tree_structure(nodes: list[dict]) -> dict:
    if not nodes:
        return {"valid": False, "reason": "empty discovery tree", "node_count": 0}
    parents = {}
    for node in nodes:
        node_id = node.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            return {"valid": False, "reason": "node missing node_id", "node_count": len(nodes)}
        if node_id in parents:
            return {"valid": False, "reason": f"duplicate node_id: {node_id}", "node_count": len(nodes)}
        parents[node_id] = node.get("parent_id")
    for node_id, parent in parents.items():
        if parent is not None and parent not in parents:
            return {"valid": False, "reason": f"node {node_id} has unknown parent {parent}", "node_count": len(nodes)}
        seen, current = {node_id}, parent
        while current is not None:
            if current in seen:
                return {"valid": False, "reason": f"cycle reaches {current}", "node_count": len(nodes)}
            seen.add(current)
            current = parents.get(current)
    parent_ids = {value for value in parents.values() if value is not None}
    return {"valid": True, "node_count": len(nodes), "root_nodes": sum(value is None for value in parents.values()), "leaf_nodes": len(set(parents) - parent_ids)}


def dream_offline_spec_curve(nodes: list[dict], min_f_stat: float = 10.0) -> dict:
    """Describe estimates for audit; estimates never enter the policy reward."""
    values = sorted(
        node.get("metrics", {}).get("direct_effect")
        for node in nodes
        if node.get("metrics", {}).get("first_stage_f", 0.0) >= min_f_stat
        and node.get("metrics", {}).get("direct_effect") is not None
    )
    if not values:
        return {"status": "inconclusive", "screened_candidates": len(nodes), "retained_specifications": 0}
    count, median = len(values), values[len(values) // 2]
    return {
        "status": "success", "screened_candidates": len(nodes), "retained_specifications": count,
        "direct_effect_p10": values[int(0.10 * count)], "direct_effect_median": median,
        "direct_effect_p90": values[min(int(0.90 * count), count - 1)],
        "sign_stability": sum(math.copysign(1, value) == math.copysign(1, median) for value in values) / count,
    }


def evolve_adversarial_pool(nodes: list[dict], path: Path | None = None) -> list[str]:
    values = {item for node in nodes for item in node.get("referee_vulnerabilities", []) if isinstance(item, str) and item}
    if path and path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing, list):
            values.update(item for item in existing if isinstance(item, str) and item)
    result = sorted(values)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def learn_policy(nodes: list[dict], base: dict | None = None) -> dict:
    policy = {**DEFAULT_POLICY, **(base or {})}
    totals: dict[str, list[float]] = {}
    for node in nodes:
        action, reward = node.get("action"), node.get("reward")
        if node.get("reward_source") != "package-gate-v1" or not isinstance(action, dict) or not isinstance(reward, (int, float)):
            continue
        stage, kind = action.get("stage"), action.get("kind")
        if isinstance(stage, str) and isinstance(kind, str):
            item = totals.setdefault(f"{stage}|{kind}", [0.0, 0.0])
            item[0] += 1
            item[1] += float(reward)
    policy["statistics"] = {key: {"count": int(count), "mean_reward": total / count} for key, (count, total) in sorted(totals.items())}
    return policy


def select_action(policy: dict, stages: list[str], actions: list[dict], remaining_cost: float) -> dict | None:
    eligible = [action for action in actions if isinstance(action, dict) and isinstance(action.get("id"), str)
                and isinstance(action.get("kind"), str) and action.get("stage") in stages + ["*"]
                and action.get("requires_researcher") is not True
                and isinstance(action.get("estimated_cost", 0), (int, float))
                and 0 <= action.get("estimated_cost", 0) <= remaining_cost]
    if not eligible:
        return None
    statistics, priorities = policy.get("statistics", {}), policy.get("action_priorities", [])
    total, exploration = sum(item.get("count", 0) for item in statistics.values()) + 1, float(policy.get("exploration", 1.0))

    def rank(action: dict) -> tuple:
        stat = statistics.get(f"{action.get('stage')}|{action['kind']}", {})
        count = stat.get("count", 0)
        ucb = float("inf") if count == 0 else stat.get("mean_reward", 0.0) + exploration * math.sqrt(math.log(total) / count)
        priority = priorities.index(action["kind"]) if action["kind"] in priorities else len(priorities)
        return (-ucb, priority, action.get("estimated_cost", 0), action["id"])

    return min(eligible, key=rank)


def package_reward(report: dict, cost: float, max_cost: float) -> float:
    """Reward deterministic gate progress and completion, never estimates or p-values."""
    checks = report.get("checks", [])
    progress = sum(item.get("passed") is True for item in checks if isinstance(item, dict)) / len(checks) if checks else 0.0
    return max(0.0, (1.0 if report.get("valid") else 0.5 * progress) - 0.1 * min(cost / max(max_cost, 1.0), 1.0))


def run_package(root: Path, config: Path) -> dict:
    command = [sys.executable, str(Path(__file__).with_name("check_research_package.py")), "--root", str(root), "--config", str(config)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"valid": False, "return_to": ["gate_remediation"], "checks": [], "error": completed.stderr.strip()}


def run_adapter(adapter: Path, request: dict, timeout: int) -> dict:
    command = [sys.executable, str(adapter)] if adapter.suffix == ".py" else [str(adapter)]
    completed = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True, timeout=timeout, check=False)
    if completed.returncode:
        return {"status": "failed", "cost": 0, "error": completed.stderr.strip(), "next_actions": []}
    result = json.loads(completed.stdout)
    if not isinstance(result, dict) or result.get("status") not in {"complete", "blocked", "failed"}:
        raise ValueError("adapter must return status complete, blocked, or failed")
    return result


def append_transition(path: Path, node: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(node, ensure_ascii=False) + "\n")


def online_loop(tree_path: Path, policy: dict, actions: list[dict], adapter: Path, root: Path, config: Path,
                max_steps: int, max_cost: float, timeout: int = 3600, package_runner=run_package,
                adapter_runner=run_adapter) -> dict:
    nodes = load_discovery_tree(tree_path)
    parent_id, spent, steps = (nodes[-1].get("node_id") if nodes else None), 0.0, 0
    report = package_runner(root, config)
    while not report.get("valid") and steps < max_steps and spent < max_cost:
        stages = report.get("return_to") or ["gate_remediation"]
        action = select_action(policy, stages, actions, max_cost - spent)
        if action is None:
            locked = any(item.get("requires_researcher") is True and item.get("stage") in stages + ["*"] for item in actions)
            return {"status": "researcher-input-required" if locked else "blocked", "steps": steps, "cost": spent, "package": report}
        outcome = adapter_runner(adapter, {"policy_id": policy.get("policy_id"), "action": action, "package": report, "root": str(root)}, timeout)
        cost = float(outcome.get("cost", action.get("estimated_cost", 0)))
        if not math.isfinite(cost) or cost < 0:
            raise ValueError("adapter cost must be a finite non-negative number")
        spent += cost
        updated, node_id = package_runner(root, config), uuid.uuid4().hex
        node = {
            "node_id": node_id, "parent_id": parent_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy_id": policy.get("policy_id"), "action": action, "outcome_status": outcome.get("status"),
            "cost": cost, "reward": package_reward(updated, cost, max_cost), "reward_source": "package-gate-v1",
            "package_valid": updated.get("valid") is True, "return_to": updated.get("return_to", []),
            "referee_vulnerabilities": outcome.get("referee_vulnerabilities", []),
        }
        artifact = outcome.get("artifact")
        artifact_path = PurePosixPath(artifact) if isinstance(artifact, str) else None
        if artifact_path and not artifact_path.is_absolute() and ".." not in artifact_path.parts and (root / artifact).is_file():
            node.update({"artifact": artifact, "artifact_sha256": hashlib.sha256((root / artifact).read_bytes()).hexdigest()})
        append_transition(tree_path, node)
        parent_id, steps, report = node_id, steps + 1, updated
        actions = outcome.get("next_actions", [])
        if outcome.get("status") != "complete":
            return {"status": outcome.get("status"), "steps": steps, "cost": spent, "package": report}
        policy = learn_policy(load_discovery_tree(tree_path), policy)
    return {"status": "complete" if report.get("valid") else "budget-exhausted", "steps": steps, "cost": spent, "package": report, "policy": policy}


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, default=Path("research/discovery_tree.jsonl"))
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--dream", action="store_true", help="learn a policy offline (default mode)")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--policy-out", type=Path)
    parser.add_argument("--actions", type=Path)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("research/package.json"))
    parser.add_argument("--max-steps", type=int, default=1)
    parser.add_argument("--max-cost", type=float, default=10.0)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--min-f", type=float, default=10.0)
    parser.add_argument("--pool", type=Path)
    parser.add_argument("--json", action="store_true", help="retained for CLI compatibility; output is always JSON")
    args = parser.parse_args()
    try:
        nodes = load_discovery_tree(args.tree)
        if args.audit:
            result = audit_tree_structure(nodes)
        elif args.online:
            if not args.actions or not args.adapter:
                raise ValueError("--online requires --actions and --adapter")
            value = load_json(args.actions)
            actions = value.get("actions", []) if isinstance(value, dict) else value
            if not isinstance(actions, list):
                raise ValueError("actions must be a list")
            policy = load_json(args.policy) if args.policy else learn_policy(nodes)
            result = online_loop(args.tree, policy, actions, args.adapter, args.root.resolve(), args.config,
                                 args.max_steps, args.max_cost, args.timeout)
        else:
            policy = learn_policy(nodes, load_json(args.policy) if args.policy else None)
            if args.policy_out:
                args.policy_out.parent.mkdir(parents=True, exist_ok=True)
                args.policy_out.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = {"tree_audit": audit_tree_structure(nodes), "specification_summary": dream_offline_spec_curve(nodes, args.min_f),
                      "learned_policy": policy, "adversarial_pool": evolve_adversarial_pool(nodes, args.pool)}
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        result = {"status": "failed", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("valid") is False:
        return 1
    return 0 if result.get("status") in {None, "complete"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
