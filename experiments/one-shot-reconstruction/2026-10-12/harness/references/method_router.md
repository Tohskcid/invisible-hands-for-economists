# Empirical method router

Read this reference when choosing, comparing, or auditing an empirical design, estimator, or specialized model. Route from the estimand and assignment mechanism before data shape and estimator. The router produces a design memo; it does not select a method from column names, significance, convention, or available software.

## Required inputs

Freeze before routing:

- question and decision use;
- target population, unit, outcome, treatment/exposure, time, and estimand;
- institutional assignment narrative, intervention timing, comparison group, and plausible interference;
- observed sampling, panel/repeated-cross-section structure, support, attrition, missingness, measurement, and dependence;
- counterfactual, welfare, equilibrium, prediction, or external-validity claims actually required.

If the assignment story or timing is unknown, route first to institutional literature and data audit. Do not let a regression fill the gap.

## Route the research target

1. No intervention or counterfactual claim: descriptive estimation.
2. Future outcomes or labels under the observed regime: prediction; use honest train/validation/test separation and leakage controls.
3. Effect of an intervention or exposure: reduced-form causal design, conditional on a defensible assignment mechanism.
4. New-policy, equilibrium, welfare, or out-of-support counterfactual: structural/computational mode unless a reduced-form design directly identifies the requested object.
5. Claim about all economies, games, or parameter values: theory mode; empirical patterns can motivate but not prove it.

Hybrid papers may have several targets. Route each estimand separately and state which is primary.

## Identification design screen

Treat `natural experiment` as a description of institutional variation, not an estimator. Determine which design that variation supports.

| Candidate | Evidence that makes it plausible | Required audit or interpretation | Reject or narrow when |
| --- | --- | --- | --- |
| Randomized experiment | documented random assignment | randomization unit, noncompliance, attrition, interference, randomization-based or design-matched inference | allocation was predictable, compromised, or analyzed at the wrong assignment level |
| DiD / causal event study | treated and credible not-yet/never-treated comparisons with pre/post outcomes | cohort timing, anticipation, conditional parallel trends, composition, spillovers, treatment reversals, estimator weights; use heterogeneity-robust cohort-time effects when effects or timing vary | no credible comparison group, differential shocks, contaminated controls, or only a post-treatment cross-section |
| IV / LATE | an institutionally assigned instrument shifts treatment | relevance, independence, exclusion, monotonicity, SUTVA, first-stage heterogeneity, weak-IV-robust inference; report complier population and instrument-specific LATE | instrument directly affects the outcome, sorting breaks independence, defiers are plausible, support is weak, or the desired ATE is not identified |
| Sharp or fuzzy RDD | treatment probability changes at a known threshold | assignment rule, continuity, manipulation/heaping, local support, bandwidth and polynomial sensitivity, robust bias correction; fuzzy RDD identifies a local complier effect under IV assumptions | other rules change at the cutoff, agents precisely sort, few observations support the threshold, or global effects are claimed |
| Synthetic control / SDID | few treated aggregate units, long pre-period, donor pool | donor contamination, pre-fit, convex-hull support, time-place placebo distribution, anticipation, inference appropriate to small treated counts | no credible donors or pre-treatment fit, common shocks are differentially loaded, or post-treatment tuning drives fit |
| Selection on observables | treatment is plausibly ignorable after pre-treatment covariates | overlap/positivity, covariate timing, balance, sensitivity to hidden confounding, doubly robust or design-consistent estimation | important confounders are unmeasured, overlap fails, or post-treatment variables are required |
| Panel fixed effects | stable unit heterogeneity is the stated threat and within-unit variation is informative | strict/sequential exogeneity, treatment timing, dynamics, measurement error, serial dependence | time-varying confounding carries identification; fixed effects alone do not make exposure exogenous |
| Interrupted time series | a dated intervention affects one series with adequate pre/post observations | trend and seasonality, concurrent shocks, autocorrelation, functional-form breaks, unaffected comparison series when available | intervention timing coincides with other breaks or the pre-period cannot anchor the counterfactual |
| Finance market event study | a sharply timed event and an estimable normal-return model | event-time leakage, overlapping events, confounding news, estimation window, expected-return model, cross-sectional dependence | announcement timing is diffuse or abnormal returns are interpreted as a causal real outcome without further design |
| Spatial/network exposure | treatment can spill across locations or links | exposure mapping, partial-interference assumptions, direct and spillover estimands, network formation, spatial inference | exposure mapping is arbitrary or controls are contaminated |

Failure of one design is not permission to relabel the same variation. Record the failure and compare genuinely different identifying variation.

## Specialized estimators come second

After choosing a design, select an estimator that preserves its estimand and assumptions:

- staggered timing or heterogeneous effects: avoid automatic two-way fixed-effects interpretations; choose cohort-time or interaction-weighted estimates appropriate to the comparison set;
- noncompliance: distinguish ITT, treatment-on-treated under justified assumptions, and LATE; never silently rename LATE as ATE;
- high-dimensional nuisance functions: DML, forests, boosting, or neural models may estimate nuisance components or heterogeneity with sample splitting and overlap, but do not create exogeneity;
- binary, count, fractional, censored, duration, or repeated-event outcomes: choose a likelihood, link, or semiparametric estimator compatible with support while keeping the same identifying design;
- few clusters, spatial correlation, serial correlation, survey weights, repeated observations, or generated regressors: adapt inference to assignment and dependence, not whichever standard error is smallest;
- rare treatment, weak overlap, measurement error, attrition, and missing-not-at-random processes: diagnose them before fitting; use bounds, sensitivity analysis, redesign, or a narrower estimand when point identification is not credible.

Use structural mode when behavior, equilibrium feedback, welfare, or counterfactual policy outside observed support carries the conclusion. Use predictive models when prediction itself is the target. Model complexity is never evidence for identification.

## Design memo and decision

Return a compact memo with:

1. primary estimand and assignment narrative;
2. data facts that support or rule out designs;
3. candidate designs, explicit rejection reasons, and unresolved institutional facts;
4. primary and fallback design, estimator, comparison group, and inference level;
5. identifying assumptions, diagnostics, falsifications, sensitivity analyses, and what each failure would change;
6. interpretation boundary: ATE, ATT, cohort-time effect, LATE/compliers, local RDD effect, descriptive association, prediction, or model-dependent counterfactual;
7. status: `supported`, `provisional`, or `infeasible`.

When two designs remain credible, do not choose by p-value. Run the smallest discriminating institutional or data check, retain both if they answer different estimands, or report the ambiguity. Freeze the accepted memo in the research contract before the main specification loop.

## Design-specific audit gate

Write `research/design-audit.json` after the primary design is frozen. Each diagnostic records `id`, `status` (`pass`, `fail`, `inconclusive`, or `blocked`), a short `finding`, and an `artifact` path. Validate it with:

```bash
python3 scripts/check_design_audit.py research/design-audit.json \
  --root . --require-pass --json
```

The gate selects obligations for the declared design: for example, DiD receives timing, comparison, anticipation, parallel-trends, spillover, and heterogeneous-effect checks, whereas IV receives relevance, independence, exclusion, monotonicity, weak-identification, and complier-scope checks. Do not add an inapplicable universal placebo, coefficient-stability, or significance threshold. A failed or inconclusive obligation blocks the strong interpretation; it does not automatically authorize a different estimator or alter the research contract.
