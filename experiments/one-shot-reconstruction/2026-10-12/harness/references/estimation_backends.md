# Estimation backend protocol

Read this reference when implementing or auditing an empirical estimator. The skill does not treat any package as an identification guarantee.

Freeze an estimator contract before running code:

- estimand and identifying equation;
- sample rule, missing-data rule, transformations, and weights;
- fixed effects, absorbed effects, and reference categories;
- variance estimator, clustering or spatial kernel, and finite-sample correction;
- backend, package and language versions;
- solver, tolerances, seed, and convergence criteria when applicable;
- coefficient, uncertainty, sample count, dropped observations, and diagnostics expected in the artifact.

Reuse the project's established backend. Mature packages such as R `fixest`, `did`, and `rdrobust`, or Python `pyfixest` and `linearmodels`, are optional adapters—not core dependencies. Check exact installed-version documentation before calling them.

Before using an unfamiliar adapter on research data, reproduce a small known DGP or package example and verify coefficient, standard error convention, fixed-effect handling, and sample count. For a claim carried by unusual weighting, clustering, weak identification, or numerical optimization, compare against a second implementation or a hand-computed limiting case when feasible. A wrapper or successful function call does not validate the estimand.

Keep raw output out of context. Save the formula, versions, data hash, command, diagnostics, and machine-readable results as artifacts; return only decision-relevant values and paths.
