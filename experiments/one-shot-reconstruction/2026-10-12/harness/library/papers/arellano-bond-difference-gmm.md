---
id: arellano-bond-difference-gmm
paper_id: paper-arellano-bond-1991
mode: empirical
result_type: estimator
verification: abstract_checked
---

# Difference-GMM estimation and specification tests for dynamic panels

## Problem

- estimate a dynamic panel with unit effects and lagged outcomes
- test moment restrictions and residual serial correlation

## Assumptions

- the paper's restrictions on idiosyncratic-error serial correlation
- valid lagged-level instruments for differenced equations
- appropriate exogeneity classification of other regressors

## Conclusion

Lagged levels provide linear moment restrictions for GMM estimation of the differenced dynamic panel, accompanied by residual serial-correlation and overidentification tests.

## Method

first-differenced GMM with internal instruments

## Failure conditions

- second-order serial correlation invalidates commonly used lag instruments
- persistent series can make lagged levels weak instruments for differences
- instrument proliferation can overfit endogenous variables and weaken diagnostics

## Scope note

Record instrument lags and count; specification-test acceptance does not prove all instruments valid.

## Primary source

Some Tests of Specification for Panel Data: Monte Carlo Evidence and an Application to Employment Equations, Manuel Arellano, Stephen Bond (1991), [Review of Economic Studies](https://doi.org/10.2307/2297968).

Locator: Estimator, Monte Carlo, and specification tests, Review of Economic Studies 58(2), pp. 277-297

## Keywords

Arellano Bond, dynamic panel, difference GMM, internal instruments, AR2 test, Sargan test
