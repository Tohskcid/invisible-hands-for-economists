---
id: conley-spatial-gmm
paper_id: paper-conley-1999
mode: empirical
result_type: estimator
verification: abstract_checked
---

# Distance-based covariance estimation under cross-sectional dependence

## Problem

- conduct GMM inference with spatial or economic-distance dependence
- avoid treating nearby cross-sectional observations as independent

## Assumptions

- a defensible metric of economic distance
- dependence and sampling conditions supporting the paper's asymptotics
- a kernel and cutoff sequence appropriate to the dependence process

## Conclusion

The paper constructs nonparametric positive-semidefinite covariance estimators that permit general dependence characterized by economic distance.

## Method

distance-kernel covariance estimation for cross-sectional GMM

## Failure conditions

- spatial HAC changes inference but cannot fix endogenous exposure
- arbitrary coordinates, cutoff, or kernel choices can misrepresent dependence
- few effective spatial clusters weaken asymptotic approximations

## Scope note

Predeclare the distance measure and sensitivity grid from the dependence mechanism, not the desired standard error.

## Primary source

GMM Estimation with Cross Sectional Dependence, Timothy G. Conley (1999), [Journal of Econometrics](https://doi.org/10.1016/S0304-4076(98)00084-0).

Locator: Covariance construction and asymptotic results, Journal of Econometrics 92(1), pp. 1-45

## Keywords

Conley standard errors, spatial HAC, cross-sectional dependence, GMM, economic distance, covariance
