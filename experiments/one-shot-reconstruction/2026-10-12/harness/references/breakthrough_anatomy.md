# Anatomy of field-changing economics papers

Use this reference during the topic survey to distinguish a promising paper from a merely competent application. Journal placement is an outcome and an editorial signal, not the explanation. Compare papers on the intellectual constraint they removed and the work that became possible afterward.

## The reusable anatomy

For each exemplar answer six questions with primary-source locators:

1. **Research question:** What economically meaningful object was unknown, unidentified, unmeasurable, or computationally infeasible?
2. **Prior bottleneck:** Why could the literature not answer it credibly before this paper?
3. **Core move:** What one conceptual move changed the feasible set—new estimand, variation, data construction, theorem, algorithm, or synthesis?
4. **Credibility:** What theorem, design, counterexample, simulation, institutional fact, or out-of-sample implication disciplines the move?
5. **Generativity:** Can other researchers reuse it across settings, or does it answer only one case?
6. **Boundary:** Which assumption or failure condition prevents overclaiming?

A strong contribution usually combines importance, surprise, credibility, and generativity. It need not invent all components. Many landmark papers connect existing components in a way that makes a previously unusable object operational.

For frontier papers, assess these properties directly and ignore citation scarcity. Citations are a lagging diffusion measure: useful later for tracing descendants, but structurally biased against recent work. Search working papers, advance articles, conferences, and author repositories separately from the established-literature lane, then ask whether the paper exposes a real bottleneck, offers a discriminating validation, and creates a reusable research move.

## Patterns in the bundled corpus

| Paper | Research question and bottleneck | Field-changing move | Why it became generative |
|---|---|---|---|
| Imbens–Angrist (1994), LATE | What does IV identify when treatment effects differ and take-up is incomplete? The conventional population-effect reading was not generally valid. | Reinterprets IV around instrument-induced compliers under explicit independence, exclusion, relevance, and monotonicity conditions. | Turns an ambiguity into a precise estimand and makes instrument-specific external validity a research obligation. |
| Berry–Levinsohn–Pakes (1995), differentiated-products demand | How can aggregate market shares identify realistic substitution and endogenous price effects? Simple logit demand imposed implausible substitution, while richer heterogeneity was computationally difficult. | Combines share inversion, random coefficients, instruments, simulation, and supply-side equilibrium conditions. | Creates an estimable framework that supports demand, markups, mergers, and counterfactual policy analysis across industries. |
| Rust (1987), dynamic discrete choice | How can forward-looking behavior be estimated when every trial parameter changes the value function? | Nests a solved Bellman fixed point inside likelihood optimization and makes numerical tolerances part of estimation. | Makes a broad class of dynamic decisions empirically operational and exposes computation as part of identification and inference. |
| Arkhangelsky et al. (2021), synthetic DiD | Can panel treatment effects use both synthetic-control balancing and DiD differencing under latent unit-by-time structure? | Joint unit and time weighting combines complementary protections of two established designs. | Supplies an explicit estimator and theory that can be reused when neither plain DiD nor synthetic control alone matches the assignment structure. |
| Borusyak–Hull–Jaravel (2022), shift-share IV | When can shift-share IV be justified if exposure shares are endogenous? Unit-level orthogonality obscured the actual assignment mechanism. | Shows equivalence to shock-level moments and relocates identification and inference to quasi-random shocks. | Changes how applied work states assumptions, selects controls, measures effective sample size, and computes inference. |

These are method exemplars, not a claim that method papers are inherently superior. An empirical paper can be equally generative by revealing a high-value fact with uniquely credible variation or data; a theory paper can do so by identifying the minimal assumptions behind a broad phenomenon. Always verify the paper and current descendants with tools before using these sketches as evidence.

## Contribution screen for a new one-sentence question

Write one sentence for each item:

- **stakes:** who changes a belief or decision if the answer changes;
- **nearest known answer:** the strongest existing answer, not a straw paper;
- **binding bottleneck:** identification, measurement, theory, computation, scope, or data access;
- **proposed move:** the smallest new move that removes that bottleneck;
- **killer test:** the result or counterexample that would make the contribution disappear;
- **reuse path:** what another researcher could do afterward that is difficult now.

Proceed only if the proposed move survives the nearest-work comparison and there is a feasible credibility test. A new setting with the same estimand and no changed economics is usually an application; label it honestly. A surprising claim without a discriminating design is a hypothesis, not a contribution.
