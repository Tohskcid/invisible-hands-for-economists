# Dream-RSI research iteration

Use Dream-RSI only for bounded research iteration with a frozen research contract. It improves the exploration policy, not the estimand, validity gates, or preferred result. The design follows the public Dream-RSI separation between offline replay and deployment: historical discovery trees provide cheap policy feedback; only the selected policy enters a real online iteration.

## Closed loop

1. Run the current policy online through an explicit executable adapter.
2. Rerun `check_research_package.py` after every action.
3. Append state, action, gate-derived reward, cost, artifact hash, and failure stage to `research/discovery_tree.jsonl`.
4. Learn stage-conditioned action values from accumulated worlds.
5. Reuse the learned policy in the next bounded run.

The reward is derived only from deterministic gate completion, the fraction of applicable checks passed, and execution cost. Coefficients, effect direction, p-values, journal fit, and agreement with researcher intuition never enter the reward. A policy cannot waive a failed gate.

## Offline policy improvement

```bash
python3 scripts/dream_replay_simulator.py \
  --tree research/discovery_tree.jsonl \
  --policy-out research/dream-policy.json
```

Each transition contributes to statistics keyed by `return_to stage | action kind`. Action selection uses an upper-confidence-bound rule so successful actions are reused while untried actions still receive bounded exploration. This is RL-like policy improvement over recorded trajectories, not model-weight training.

The same command also reports a specification summary for audit. Estimate magnitudes are intentionally isolated from policy learning.

## Online execution

Supply candidate actions and an executable adapter:

```json
{
  "actions": [
    {
      "id": "mechanism-placebo-1",
      "stage": "evidence_generation",
      "kind": "negative-control",
      "estimated_cost": 1.0,
      "requires_researcher": false,
      "payload": {
        "command": ["python3", "scripts/run_placebo.py"],
        "artifact": "output/diagnostics/placebo.json"
      }
    }
  ]
}
```

```bash
python3 scripts/dream_replay_simulator.py --online \
  --tree research/discovery_tree.jsonl \
  --policy research/dream-policy.json \
  --actions research/dream-actions.json \
  --adapter scripts/research_action_adapter.py \
  --root . --config research/package.json \
  --max-steps 10 --max-cost 50
```

The bundled adapter executes `payload.command` as an explicit argument list without a shell. A custom adapter may instead receive one JSON request on stdin and return:

```json
{
  "status": "complete",
  "cost": 1.0,
  "artifact": "output/diagnostics/placebo.json",
  "referee_vulnerabilities": ["concurrent-shock"],
  "next_actions": []
}
```

The harness, not the adapter, reruns the research-package gate and computes reward. Artifacts returned by the adapter are SHA-256-bound when they exist below the package root.

## Stop and safety rules

- `requires_researcher: true` actions are never selected automatically.
- Stop on package pass, budget exhaustion, blocked/failed adapter status, or lack of eligible actions.
- A scope, contribution, estimand, data-authority, or claim-boundary change requires researcher input.
- Histories are append-only. Never erase failed actions or retroactively change their rewards.
- Public/shared worlds may contain policies, action kinds, gate results, costs, and anonymized failure modes; do not export licensed data, manuscript text, confidential metadata, or undisclosed results.

Audit tree structure with:

```bash
python3 scripts/dream_replay_simulator.py --tree research/discovery_tree.jsonl --audit
```

The implementation deliberately stops short of Agent Lightning-style model training. Add weight-level RL only after reward semantics are stable and a sufficiently large, leakage-audited trajectory set exists.
