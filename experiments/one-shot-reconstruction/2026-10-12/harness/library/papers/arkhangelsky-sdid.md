---
id: arkhangelsky-sdid
paper_id: paper-arkhangelsky-et-al-2021
mode: empirical
result_type: estimator
verification: abstract_checked
---

# Synthetic difference-in-differences for panel treatment effects

## Problem

- combine unit balancing from synthetic control with time differencing from DiD
- estimate a panel treatment effect under latent unit-by-time structure

## Assumptions

- the paper's panel assignment and latent-factor regularity conditions
- sufficient untreated units and pre-treatment periods for stable weights
- no contamination of the intended comparison by anticipation or spillovers

## Conclusion

SDID combines unit and time weights to estimate treatment effects and has consistency and asymptotic-normality results under the paper's latent-factor conditions.

## Method

regularized unit weights, time weights, and weighted two-way differencing

## Failure conditions

- short pre-periods or unstable weights weaken balancing
- staggered timing requires an explicitly suitable extension
- the estimator does not repair an invalid treatment assignment story

## Scope note

Match the exact treatment-timing setup and inference procedure to the application.

## Primary source

Synthetic Difference-in-Differences, Dmitry Arkhangelsky, Susan Athey, David A. Hirshberg, Guido W. Imbens, Stefan Wager (2021), [American Economic Review](https://doi.org/10.1257/aer.20190159).

Locator: Estimator and asymptotic analysis, AER 111(12), pp. 4088-4118

## Keywords

synthetic difference in differences, SDID, panel data, latent factors, unit weights, time weights
