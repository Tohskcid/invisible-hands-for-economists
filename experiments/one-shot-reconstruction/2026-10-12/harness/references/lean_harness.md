# Locked Lean proof harness

Read this reference only when an agent will formalize or verify a theorem. The locked mode separates the immutable theorem task from the candidate proof term, compiles the generated file, and audits transitive axiom dependencies.

## Task contract

Create `proof-task.json` before proof search:

```json
{
  "version": 1,
  "theorem_name": "identity",
  "source_statement": "Every natural number equals itself.",
  "formalization_status": "approved",
  "assumptions": [],
  "statement": "∀ n : Nat, n = n",
  "imports": ["Mathlib"],
  "preamble": "",
  "allowed_axioms": ["propext", "Classical.choice", "Quot.sound"],
  "timeout_seconds": 60,
  "project_dir": "."
}
```

Require a PI or independent formalization review before setting `formalization_status` to `approved`. Put every economic assumption in both the audit list and the theorem type as an explicit hypothesis. Keep `preamble` limited to trusted definitions; the harness rejects proof escapes, axiom declarations, and hidden imports there. Lock the task once, then put it outside the agent's mutation scope:

```bash
python3 scripts/check_lean_proof.py --lock-task proof-task.json --json
```

Locking writes `statement_sha256` and `task_sha256`. The latter covers imports, preamble, theorem type, allowed axioms, timeout, and project location. Hashes detect later changes but are not a security boundary if the proving agent may edit and relock the contract.

## Closed loop

The candidate file contains only a Lean proof term, for example:

```lean
by
  intro n
  rfl
```

Run one bounded attempt:

```bash
python3 scripts/check_lean_proof.py \
  --task proof-task.json \
  --proof candidate.lean \
  --artifact research/proof-attempt-001.json \
  --json
```

On failure, read only the returned diagnostic, change the proof term, and run the next budgeted attempt. Record strategy, parent attempt, status, and artifact in the existing experiment ledger. Branch only when alternatives are materially distinct; this harness does not implement MCTS or generate tactics.

`formally_proved` requires all of the following:

- task and statement hashes match;
- proof and trusted preamble contain no `sorry`, `admit`, `sorryAx`, or `axiom` escape;
- Lean exits successfully before the task timeout;
- `#print axioms EconResearchHarness.target` is present and parseable;
- every direct or transitive axiom is in `allowed_axioms`, which itself may contain only Lean's standard `propext`, `Classical.choice`, and `Quot.sound` axioms.

The proof term is embedded inside a parenthesized theorem value, so it cannot replace the theorem type or add top-level commands. Full stdout and stderr belong in the artifact; return only the status and next actionable diagnostic to the agent context.

## Boundary

Legacy `python3 scripts/check_lean_proof.py FILE.lean` remains available for trusted files, but it does not lock the theorem statement or audit imported axioms. Do not use legacy mode as the sole basis for an agent-generated `formally proved` claim.

The script enforces a wall-clock timeout, not an operating-system sandbox or memory quota. Run Lean inside the host's filesystem/network sandbox when the candidate is untrusted. Pin Lean and Mathlib in the proof project's `lean-toolchain` and Lake manifest; the skill does not install them automatically.
