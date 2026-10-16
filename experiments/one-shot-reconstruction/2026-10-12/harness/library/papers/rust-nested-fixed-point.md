---
id: rust-nested-fixed-point
paper_id: paper-rust-1987
mode: structural
result_type: algorithm
verification: abstract_checked
---

# Nested fixed-point estimation of a dynamic discrete-choice model

## Problem

- estimate dynamic discrete choices when value functions depend on structural parameters
- compute optimal replacement decisions

## Assumptions

- specified per-period utility and transition law
- dynamic optimality and the paper's stochastic assumptions
- a uniquely solved inner dynamic-programming problem for each trial parameter

## Conclusion

Structural parameters can be estimated by nesting solution of the dynamic program inside the outer likelihood optimization.

## Method

nested fixed-point maximum likelihood

## Failure conditions

- inner-solver error contaminates the outer objective
- multiple or poorly resolved fixed points undermine interpretation
- misspecified transitions or payoff shocks bias structural conclusions

## Scope note

Record inner and outer tolerances, starting values, and convergence diagnostics.

## Primary source

Optimal Replacement of GMC Bus Engines: An Empirical Model of Harold Zurcher, John Rust (1987), [Econometrica](https://doi.org/10.2307/1911259).

Locator: Model and nested fixed-point estimation method, Econometrica 55(5), pp. 999-1033

## Keywords

dynamic discrete choice, nested fixed point, NFXP, Bellman equation, replacement, structural estimation
