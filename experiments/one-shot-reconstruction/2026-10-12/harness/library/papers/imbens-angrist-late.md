---
id: imbens-angrist-late
paper_id: paper-imbens-angrist-1994
mode: empirical
result_type: identification
verification: abstract_checked
---

# Identification of a local average treatment effect

## Problem

- interpret an instrumental-variable estimand with heterogeneous treatment effects
- identify an effect when treatment take-up is incomplete

## Assumptions

- instrument independence as defined in the paper
- exclusion restriction
- first-stage relevance
- monotonicity of treatment response to the instrument

## Conclusion

The instrument identifies the average treatment effect for units whose treatment status is changed by the instrument.

## Method

potential-outcomes decomposition of instrument-induced treatment changes

## Failure conditions

- defiers violate monotonicity
- the result is local to instrument-specific compliers rather than a population ATE
- exclusion or independence failure invalidates the interpretation

## Scope note

State the instrument, complier population, and treatment contrast explicitly.

## Primary source

Identification and Estimation of Local Average Treatment Effects, Guido W. Imbens, Joshua D. Angrist (1994), [Econometrica](https://doi.org/10.2307/2951620).

Locator: Identification argument, Econometrica 62(2), pp. 467-475

## Keywords

LATE, instrumental variables, compliers, monotonicity, exclusion restriction, heterogeneous treatment effects
