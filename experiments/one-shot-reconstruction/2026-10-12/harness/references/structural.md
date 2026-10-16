# Structural and computational mode

Use for structural estimation, calibration, simulation, numerical equilibrium, counterfactuals, or computational macro/IO/finance/trade.

## Contract additions

Freeze the economic environment, parameterization, identified and calibrated parameters, moments or likelihood, holdout targets, solver and tolerances, random seeds, counterfactual, hardware/time budget, and primary fit and welfare metrics.

## Baseline and validity gates

1. Map the model lineage, inherited primitives, identification arguments, targeted moments, and competing mechanisms.
2. Reproduce a transparent benchmark and limiting cases.
3. Verify units, constraints, equilibrium conditions, and accounting identities.
4. Establish the relevant existence, uniqueness, equilibrium-mapping, rank, or local/global identification properties analytically where feasible; otherwise label them as numerical evidence or unresolved obligations.
5. Report convergence, sensitivity to starting values, numerical error, runtime, and seed stability.
6. Separate in-sample targeted moments from holdout validation.
7. Diagnose identification or observational equivalence before interpreting parameters.
8. For counterfactuals, state which policy-invariant primitives and equilibrium responses carry the result.

When optimization or numerical equilibrium carries the conclusion, also check analytical against numerical derivatives when feasible, multiple starting values, a tolerance ladder, solver history, constraint violations, condition numbers or flat directions, and equilibrium/Euler residuals. Distinguish local from global evidence. Use existing project solvers first; optimagic or QuantEcon routines are optional only when already available or explicitly authorized.

For jobs that may exceed interactive memory or time, estimate resources on a bounded engineering pilot, then use the project's scheduler or resumable batch mechanism. Save checkpoints, immutable inputs, environment, seed, solver state and partial diagnostics as artifacts; do not stream raw arrays or full logs into context. A sampled pilot validates execution mechanics, not the full-data optimum or counterfactual. Use [confidential_data.md](confidential_data.md) when access or export is restricted.

Fit improvement cannot compensate for non-convergence, failed identities, weaker identification, or an altered validation sample.

## Structural audit gate

Write `research/structural-audit.json` with `schema_version`, `model`, `target`, `estimator_or_solver`, `counterfactual_required`, and diagnostics. Required diagnostic IDs are `benchmark`, `identities`, `convergence`, `starting-values`, `tolerance-ladder`, `numerical-error`, `seed-stability`, `identification`, and `holdout-validation`. Add `counterfactual-invariance` when a counterfactual is required. Every diagnostic records `status` (`pass`, `fail`, `inconclusive`, or `blocked`), `finding`, and a relative `artifact` path. Run:

```bash
python3 scripts/check_structural_audit.py research/structural-audit.json \
  --root . --require-pass --json
```

A valid but nonpassing audit may document an unresolved model. It cannot support parameter interpretation, welfare claims, or policy counterfactual delivery.

## Iteration

Run one attributable change per row: a moment, parameter restriction, numerical method, or model mechanism. Evaluate it with the frozen harness and record fit, holdout performance, convergence, runtime, and complexity. Keep equal-performing simplifications; discard cosmetic complexity and changes that only retune the evaluation target.

The harness may be revised only when a defect is documented. Record the revision as a new baseline so results across harness versions are not compared as if identical.
