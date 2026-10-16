# Real-world relevance and applicability gate

Read this reference when research is used to recommend, prioritize, deploy, regulate, fund, or otherwise change a real-world decision. Academic validity remains necessary but does not establish applicability. Skip this gate for claims explicitly scoped as `research-only`.

## Decision contract

Freeze the decision maker, target decision, deployment context, target population, time horizon, and acceptable failure before translating a result into advice. State whether the evidence supports the actual decision, a bounded pilot, further measurement, or research only. Do not convert statistical significance, journal placement, model fit, or novelty into practical relevance.

## Required diagnostics

Create `research/real-world-audit.json`. Each diagnostic records `status` (`pass`, `fail`, `inconclusive`, `blocked`, or `not_applicable`), a concise `finding`, a relative evidence `artifact` path, and its `artifact_sha256`:

- `target-population`: sample coverage, eligibility, selection, and affected groups;
- `institutional-match`: incentives, rules, implementation authority, and market or administrative setting;
- `measurement-validity`: whether outcomes and proxies measure the decision-relevant construct;
- `data-freshness`: whether the period, revisions, and current regime support present use;
- `transportability`: assumptions required across places, populations, institutions, or time;
- `decision-sensitivity`: whether plausible effects and uncertainty would change the decision;
- `implementation-feasibility`: cost, capacity, timing, legal, and operational constraints;
- `distributional-effects`: who benefits, pays, or bears risk;
- `equilibrium-response`: behavior, spillovers, displacement, adaptation, or general-equilibrium effects;
- `monitoring-plan`: pilot metrics, failure thresholds, drift detection, and stopping or rollback rules.

Use `not_applicable` only with a concrete reason. Missing evidence is `blocked` or `inconclusive`, not `not_applicable`.

## Conclusion and package gate

Choose one conclusion:

- `applicable`: supports the specified decision within the recorded scope;
- `provisional`: supports only a pilot or additional validation;
- `research-only`: academically informative but not decision-ready;
- `blocked`: required institutional or operational evidence is unavailable;
- `contradicted`: real-world evidence conflicts with the proposed application.

Validate with:

```bash
python3 scripts/check_real_world_audit.py research/real-world-audit.json \
  --root . --require-applicable --json
```

In `research/package.json`, set `claim_scope` to `research-only` or `real-world`. A `real-world` package must declare `real_world_audit`; delivery is blocked unless its conclusion is `applicable` and every required diagnostic passes or is defensibly not applicable. Narrowing a claim to `research-only` is valid only when the manuscript, abstract, conclusion, and downstream communication remove the real-world recommendation.
