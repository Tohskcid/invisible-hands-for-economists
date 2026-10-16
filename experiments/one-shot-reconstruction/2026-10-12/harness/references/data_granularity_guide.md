# Data granularity and proxy guide

Load this reference only when spatial or temporal aggregation, linkage, or proxy construction affects the research object.

## Preserve the object

Before transforming data, classify each variable:

- flow: aggregate by summing over the target interval or area;
- stock: use an explicitly chosen point-in-time value or defensible average;
- rate or price: define the relevant weights and denominator;
- indicator: define whether aggregation means any, all, share, or exposure;
- distribution: retain quantiles or sufficient statistics when a mean would erase the mechanism.

Record source unit, target unit, transformation, weights, coverage, and information lost. Never infer a finer unit from coarse data without an explicit model and validation target.

## Spatial linkage

For point-to-area assignment, preserve coordinates and boundary vintage. For area-to-area conversion, report the crosswalk and whether weights represent land, population, employment, sales, or another exposure. Test unmatched records, one-to-many links, boundary changes, and mass preservation when totals should be conserved.

Do not substitute geographic adjacency for an economic network. Transport, trade, social, production, and grid links require their own exposure definition.

## Temporal linkage

Align information availability, not only calendar labels. Prevent look-ahead by distinguishing event date, announcement date, release date, revision vintage, and effective date. Document interpolation, carry-forward rules, partial periods, and frequency conversion.

## Proxies

A published precedent is useful but not sufficient. Accept a proxy only when:

1. it measures the intended construct in the current population and period;
2. its error process and likely bias are stated;
3. it is validated against an observed benchmark or independent measure where possible;
4. uncertainty from construction is propagated when material;
5. conclusions remain within the proxy's supported scope.

If validation fails, narrow the claim, report the result as descriptive or inconclusive, obtain better data, or revise the question. Journal rank does not decide proxy validity.

## Minimum audit artifact

For every derived field record: formula/code location, input versions, unit, valid range, missingness, coverage dates, validation result, and known limitation. A transformation is complete only when another researcher can reproduce it from immutable inputs.
