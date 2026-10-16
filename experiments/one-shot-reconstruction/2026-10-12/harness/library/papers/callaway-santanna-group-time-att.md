---
id: callaway-santanna-group-time-att
paper_id: paper-callaway-santanna-2021
mode: empirical
result_type: identification
verification: abstract_checked
---

# Group-time ATT identification in multi-period DiD

## Problem

- estimate treatment effects with multiple periods and staggered adoption
- aggregate heterogeneous cohort-time effects transparently

## Assumptions

- conditional or unconditional parallel trends for the chosen comparison group
- no anticipation under the targeted setup
- overlap for covariate-adjusted identification

## Conclusion

A family of group-time average treatment effects is identified and can be aggregated along explicitly chosen dimensions.

## Method

outcome-regression, inverse-probability, or doubly robust group-time estimands

## Failure conditions

- using already-treated units as invalid controls can contaminate comparisons
- aggregation can hide cohort and dynamic heterogeneity
- conditioning does not repair an indefensible parallel-trends assumption

## Scope note

Record the comparison group and aggregation target as part of the estimand.

## Primary source

Difference-in-Differences with Multiple Time Periods, Brantly Callaway, Pedro H. C. Sant'Anna (2021), [Journal of Econometrics](https://doi.org/10.1016/j.jeconom.2020.12.001).

Locator: Identification, estimation, and aggregation results, Journal of Econometrics 225(2), pp. 200-230

## Keywords

difference in differences, DiD, group-time ATT, staggered adoption, multiple periods, doubly robust
