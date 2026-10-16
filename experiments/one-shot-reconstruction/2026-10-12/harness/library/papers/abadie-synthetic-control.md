---
id: abadie-synthetic-control
paper_id: paper-abadie-diamond-hainmueller-2010
mode: empirical
result_type: estimator
verification: abstract_checked
---

# Synthetic control for comparative case studies

## Problem

- construct a counterfactual for one or a few treated aggregate units
- replace an arbitrary single comparison unit with a weighted donor combination

## Assumptions

- untreated donor units can approximate the treated unit's relevant pre-treatment predictors and latent factor loadings
- no relevant treatment or spillover reaches donor units
- a sufficiently informative pre-treatment period

## Conclusion

A weighted combination of untreated units can estimate the treated unit's counterfactual path under the paper's comparative-case conditions.

## Method

constrained donor weighting with pre-treatment fit

## Failure conditions

- poor pre-treatment fit undermines the counterfactual
- anticipation or spillovers contaminate treated or donor outcomes
- data-driven donor selection and few treated units require design-specific inference

## Scope note

Do not interpret good pre-fit alone as proof of an unbiased post-treatment counterfactual.

## Primary source

Synthetic Control Methods for Comparative Case Studies: Estimating the Effect of California's Tobacco Control Program, Alberto Abadie, Alexis Diamond, Jens Hainmueller (2010), [Journal of the American Statistical Association](https://doi.org/10.1198/jasa.2009.ap08746).

Locator: Method and California application, JASA 105(490), pp. 493-505

## Keywords

synthetic control, comparative case study, donor pool, counterfactual, pre-treatment fit, placebo inference
