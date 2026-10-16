---
id: chernozhukov-et-al-dml
paper_id: paper-chernozhukov-et-al-2018
mode: empirical
result_type: estimator
verification: abstract_checked
---

# Orthogonal-score and cross-fit inference with machine-learned nuisances

## Problem

- estimate a low-dimensional parameter with high-dimensional nuisance functions
- reduce regularization and overfitting bias in plug-in inference

## Assumptions

- a valid identifying score or moment
- Neyman orthogonality
- sample splitting or cross-fitting
- rate, moment, and regularity conditions for the selected model

## Conclusion

Orthogonal scores combined with cross-fitting can support valid inference on the target parameter despite flexible nuisance estimation under the paper's conditions.

## Method

double or debiased machine learning

## Failure conditions

- cross-fitting does not establish causal identification
- a non-orthogonal score can retain first-order nuisance bias
- poor nuisance rates or overlap can invalidate inference

## Scope note

Derive the score and estimand first; do not treat DML as an automatic causal estimator.

## Primary source

Double/Debiased Machine Learning for Treatment and Structural Parameters, Victor Chernozhukov, Denis Chetverikov, Mert Demirer, Esther Duflo, Christian Hansen, Whitney Newey, James Robins (2018), [The Econometrics Journal](https://doi.org/10.1111/ectj.12097).

Locator: Sections 2-5 and appendices, The Econometrics Journal 21(1), pp. C1-C68

## Keywords

double machine learning, debiased ML, Neyman orthogonality, cross-fitting, nuisance functions, semiparametric inference
