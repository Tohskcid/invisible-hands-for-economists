# Empirical research mode

Use for descriptive, predictive, causal, panel, experimental, spatial, or policy research.

## Contract additions

Freeze the unit, sample, outcome, treatment or exposure, estimand, assignment mechanism, comparison group, fixed effects, inference level, and primary specification. State which variables are measured, constructed, or proxied and how missingness enters the sample.

For prediction, freeze the split, target metric, leakage rules, and baseline. For causal work, predictive accuracy is at most a nuisance-model criterion; it does not establish identification.

When the design or estimator is not already fixed and defended, use [method_router.md](method_router.md). Data shape can screen feasibility, but the estimand and assignment mechanism select the identification strategy.

## Baseline and validity gates

1. Use the shared literature checkpoint to compare the closest estimands, designs, data settings, identifying assumptions, and conflicting findings.
2. Audit keys, duplicates, missingness, support, treatment timing, and outcome construction.
3. Produce descriptive facts without causal language.
4. Fit the simplest specification that identifies the estimand under stated assumptions.
5. Match inference to assignment and dependence; record cluster counts and spatial or temporal correlation.
6. Define falsification and sensitivity tests from the actual threat, not a universal checklist.

For causal work, preserve the assumed causal graph or an equivalent assignment narrative and map each material threat to a refutation. Depending on the design, consider placebo treatment or outcome, random-common-cause, data-subset/bootstrap, negative controls, hidden-confounding sensitivity, and support/overlap checks. Passing these tests does not prove identification. When flexible nuisance models are used, freeze sample splitting or cross-fitting and the orthogonal score before comparison.

## Mathematical audit

When a conclusion depends on a mathematical property, write the population estimand or identifying moment and derive the mapping from observables under explicit assumptions. Check the relevant support/positivity, rank, functional-form, transformation, weighting, and asymptotic or finite-sample conditions. Verify algebra and limiting cases; seek a data-generating process that breaks the claim. Do not require a formal proof for routine estimation, but do not present an identifying assumption or software output as a proved implication.

Do not use significance as a keep criterion. Compare effect magnitude and uncertainty, identification credibility, out-of-sample performance when relevant, and robustness under predeclared alternatives.

## Design-specific cautions

- DiD: inspect treatment cohorts, anticipation, lead magnitudes and power. Non-significant leads do not prove parallel trends; avoid untreated-invalid TWFE comparisons.
- IV: defend relevance and exclusion institutionally; use weak-IV-robust inference where needed. `F > 10` is not sufficient.
- RDD: establish treatment assignment at the cutoff, manipulation tests, local support, bandwidth sensitivity, and robust bias-corrected inference.
- Selection: matching, fixed effects, or Heckman corrections are not automatic solutions; connect them to the assignment process.
- Spatial/network work: define exposure mapping and direct/spillover estimands. Spatial HAC changes inference, not identification.
- Generated outcomes or treatments: preserve construction code and propagate first-stage uncertainty where material.

Use `scripts/econ_data_profiler.py` for deterministic panel checks and descriptive tables. Consult `data_granularity_guide.md` only when aggregation or proxy construction affects the estimand. For standard financial, micro, or macro database cleaning (WRDS, TEJ, CSMAR, CFPS, Census/IPUMS, FRED, PWT), apply [database_cleaning_recipes.md](database_cleaning_recipes.md).

When implementing an estimator, read [estimation_backends.md](estimation_backends.md) and [estimation_recipes.md](estimation_recipes.md). Freeze semantics before selecting a package; a backend adapter does not establish identification. For sensitivity, placebos, and competing explanations, consult [falsification_battery.md](falsification_battery.md). When the data are restricted or cannot be inspected safely, read [confidential_data.md](confidential_data.md) before accessing them.

## Iteration

Change one data rule, specification, or estimator at a time. Keep it only if it improves the fixed research criteria without changing the estimand silently, introducing leakage or post-treatment controls, or weakening inference. Record null and failed results.
