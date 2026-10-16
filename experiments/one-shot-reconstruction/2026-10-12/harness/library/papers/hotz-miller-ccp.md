---
id: hotz-miller-ccp
paper_id: paper-hotz-miller-1993
mode: structural
result_type: estimator
verification: abstract_checked
---

# Conditional-choice-probability representation for dynamic models

## Problem

- reduce repeated solution cost in dynamic discrete-choice estimation
- recover value differences from observed choice probabilities

## Assumptions

- dynamic discrete-choice model with the paper's additive shock structure
- conditional choice probabilities identified over relevant states
- transition and support conditions needed for the representation

## Conclusion

Choice-specific value differences can be represented using conditional choice probabilities, enabling estimation without solving the full dynamic program at every trial parameter in the same way as nested fixed point.

## Method

conditional-choice-probability inversion and two-step estimation

## Failure conditions

- sparse state support makes nonparametric CCP estimates unstable
- misspecified shock distributions invalidate the inversion
- first-stage CCP error must be propagated into inference

## Scope note

Check whether the application's state space and transition process support reliable first-stage CCP estimation.

## Primary source

Conditional Choice Probabilities and the Estimation of Dynamic Models, V. Joseph Hotz, Robert A. Miller (1993), [Review of Economic Studies](https://doi.org/10.2307/2298122).

Locator: CCP representation and estimator, Review of Economic Studies 60(3), pp. 497-529

## Keywords

conditional choice probability, CCP, dynamic discrete choice, value-function inversion, two-step estimator, Hotz Miller
