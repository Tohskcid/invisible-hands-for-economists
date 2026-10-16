---
id: sun-abraham-event-study
paper_id: paper-sun-abraham-2021
mode: empirical
result_type: estimator
verification: abstract_checked
---

# Interaction-weighted event studies with heterogeneous effects

## Problem

- estimate dynamic effects under staggered treatment timing
- avoid contaminated two-way fixed-effects event-study coefficients

## Assumptions

- absorbing treatment with variation in adoption timing
- a valid comparison group and parallel-trends conditions for cohort-time contrasts
- no anticipation for the targeted pre-treatment comparisons

## Conclusion

Cohort-by-relative-time effects can be estimated and aggregated without the cross-period contamination of conventional lead-lag TWFE coefficients.

## Method

cohort-specific interaction regression and aggregation

## Failure conditions

- conventional TWFE leads and lags can mix effects from other relative periods
- apparent pretrends may arise from treatment-effect heterogeneity
- invalid comparison cohorts still invalidate the alternative estimator

## Scope note

Freeze the aggregation weights and admissible comparison cohorts before estimation.

## Primary source

Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects, Liyang Sun, Sarah Abraham (2021), [Journal of Econometrics](https://doi.org/10.1016/j.jeconom.2020.09.006).

Locator: Contamination result and alternative estimator, Journal of Econometrics 225(2), pp. 175-199

## Keywords

event study, staggered adoption, heterogeneous treatment effects, TWFE, interaction weighted, pretrend
