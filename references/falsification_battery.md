# Competing Mechanisms and Falsification Battery

Read this reference when designing robustness, placebo, or sensitivity checks for an empirical research design. Causal claims require active attempts at refutation; statistical significance alone is not evidence of causality.

---

## 1. Mandatory Competing Mechanisms Matrix

Before interpreting an empirical estimate as a causal effect, construct a competing mechanisms matrix with at least three alternative explanations:

| Hypothesis ID | Mechanism / Confounder | Concrete Observable Implication | Discriminating Test / Falsification |
| --- | --- | --- | --- |
| $H_0$ (Baseline) | Intended policy/treatment effect | Shift occurs at event time in treated group | Main specification |
| $H_1$ (Concomitant Policy) | Another policy was implemented simultaneously | Effect should concentrate in jurisdictions with the co-policy | Subsample split by co-policy presence |
| $H_2$ (Differential Pre-trends) | Treated units were already on a different trajectory | Pre-treatment leads should show trend divergence | Event-study leads test ($H_0: \beta_{-k} = 0$) |
| $H_3$ (Selective Sorting / Attrition) | Units strategically chose treatment or exited | Composition of units changes at the cutoff/event | Balance test on time-invariant covariates over time |

If an alternative mechanism cannot be ruled out by institutional facts or discriminating tests, the manuscript must explicitly disclose it as an unadjudicated threat to identification.

### Mechanism audit hard gate

When a manuscript claims that an effect operates through a particular channel, write `research/mechanism-audit.json`. It must identify the claim and preferred mechanism, state a causal chain and distinctive prediction, enumerate at least three credible alternatives, and bind each alternative to a test with opposing predictions, a pre-specified decision rule, a finding, and a SHA-256-verified artifact. A generic robustness check that predicts the same result under both mechanisms is not discriminating evidence.

Use test status `distinguished` only when the recorded evidence favors the preferred prediction over that specific alternative. Otherwise use `not-distinguished`, `inconclusive`, or `blocked`, list the alternative in `unresolved_alternatives`, and set `claim_status` to `consistent-with` or `unsupported`; only an audit with no unresolved alternatives may use `mechanism-supported`. Never translate an identified treatment effect into an identified mechanism without this separate evidence.

Run a fresh-context mechanism referee after the audit is frozen. Save `research/mechanism-review.json` with the audit SHA-256, `independent_context: true`, verdict, weakest link, strongest observationally equivalent explanation, assessment of the discriminating tests, and any required revision. Validate both artifacts with:

```bash
python3 scripts/check_mechanism_audit.py research/mechanism-audit.json \
  --root . --review research/mechanism-review.json --require-pass --json
```

Failure returns a machine-readable `return_to`: malformed or unsupported specifications return to `mechanism_specification`, unresolved alternatives return to `evidence_generation`, and a stale or adverse review returns to `independent_mechanism_review`. The research controller must perform the indicated work and rerun the entire package gate; it may stop only on a pass, an explicit budget/stop condition, an irreducible block, or a researcher decision that narrows the claim.

---

## 2. The Core Falsification Battery

Execute the applicable refutation tests based on the research design:

### A. Temporal Placebo (Fake Event Timing)
- **Design**: Shift the treatment date $T^*$ backward to a fictitious prior date $T_0 < T^*$ during the pure pre-treatment window.
- **Decision Rule**: The placebo treatment effect must be statistically indistinguishable from zero ($p > 0.10$). If the placebo is significant, the design suffers from unobserved trends or anticipation.

### B. Placebo Units (Permutation / Donor Swaps)
- **Design**: Randomly reassign treatment across the pool of true control units (or in Synthetic Control, iterate through every donor unit).
- **Decision Rule**: The true treatment effect must lie in the extreme tail (e.g., top/bottom 5%) of the empirical placebo distribution ($p$-value $= \sum \mathbb{I}(|\hat{\beta}^{placebo}| \ge |\hat{\beta}^{true}|) / N_{placebos} < 0.05$).

### C. Negative Control Outcomes (Placebo Outcomes)
- **Design**: Estimate the baseline specification using a dependent variable that is institutionally known to be unaffected by the treatment (e.g., adult mortality for a school-lunch subsidy).
- **Decision Rule**: The effect on the placebo outcome must be null. A significant coefficient indicates systemic concurrent shocks or selection bias.

### D. Density Discontinuity / Manipulation (RDD)
- **Design**: Perform Cattaneo, Jansson & Ma (2020) local polynomial density testing (`rddensity`) or McCrary (2008) sorting tests at the threshold.
- **Decision Rule**: Reject the null of continuity ($p < 0.05$) indicates sorting/manipulation; point identification fails.

### E. Donut-Hole & Sample Sensitivity
- **Design**:
  - For RDD: Exclude observations immediately adjacent to the cutoff (e.g., $\pm 0.5\%$).
  - For Panel: Drop the largest cluster or most volatile unit (Leave-One-Cluster-Out).
  - Trimming: Compare results under 1% winsorization vs. 5% trimming vs. raw distribution.
- **Decision Rule**: Point estimates must remain qualitatively stable. If the effect disappears when excluding boundary units, document boundary sensitivity.

---

## 3. Unobserved Selection Bounds (Oster 2019 / Altonji et al.)

When relying on selection-on-observables or conditional independence:
1. Estimate restricted model ($Y$ on $D$) $\to (\hat{\beta}_R, R^2_R)$.
2. Estimate full model with observed controls ($Y$ on $D + X$) $\to (\hat{\beta}_F, R^2_F)$.
3. Compute Oster's degree of selection proportionality $\delta$ that would drive the true effect to zero, assuming $R_{max} = \min(1, 1.3 \times R^2_F)$.
4. **Standard**: If $|\delta| > 1$, selection on unobservables would have to be stronger than selection on all observed controls to wipe out the effect, providing evidence of robustness.

---

## 4. Ledger and Reporting Protocol

Never discard a failed falsification test or rerun tests with adjusted parameters to achieve a pass.
- Record every test in `research/experiments.tsv` with validation flags.
- Present falsification tests in a dedicated Robustness & Validity section or appendix table in the manuscript.
