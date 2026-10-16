# Research-question survey gate

Read this reference at the start of a new research question, before choosing an empirical design, structural model, or theorem strategy. Skip only when the user explicitly requests replication of a named work or supplies a current, auditable survey; record that basis.

## Normalize and search

Translate the initial question into the population or model class, outcome or target theorem, treatment/exposure or mechanism, candidate estimand, setting, and time horizon. Preserve the user's original wording alongside the normalized form.

Freeze a search cutoff and scope. The cutoff is the date the tools actually ran, not the model's knowledge date. Set `refresh_after_days` (normally 30; use 7 for fast-moving working-paper topics), and rerun the search when the gate is stale. Search several formulations rather than the exact title phrase:

- question and outcome/exposure synonyms;
- proposed mechanism and competing mechanisms;
- candidate estimands, designs, or proof concepts;
- population, institution, geography, period, and data source;
- backward references from close works and forward citations to them.

Use an actual browser, API, publisher search, or bibliographic database for every query; model memory and generated citations are never search evidence. `scripts/search_literature.py` provides a standard-library Crossref path and saves the raw responses and hashes. Other tools are acceptable when their query, retrieval date, canonical results, raw or rendered evidence artifact, and checksum are preserved. Use discovery indexes to find candidates, then verify bibliographic metadata and substantive comparisons against primary papers or credible working papers. An abstract-only or inaccessible work remains explicitly limited. Absence from one database is not evidence of novelty.

Run two separate discovery lanes. The **baseline lane** searches established published work and citation chains. The **frontier lane** searches at least two different channels among working-paper series (NBER, CEPR, IZA), preprint repositories (SSRN, arXiv, RePEc), journal advance/forthcoming pages, major conference programs, and author repositories. Set `frontier_window_years` from 1 to 5 and `citation_policy: "never-exclude"`. Citation counts may describe diffusion but may never exclude or down-rank a frontier candidate; new work has not had equal time to accumulate citations.

## Nearest-work matrix

For each close work record a canonical HTTPS locator to the DOI, publisher, working-paper archive, or official repository; a free-form citation is not verification. Bind the checked metadata or saved landing-page record through `source_evidence_artifact` and `source_evidence_sha256`, including the non-model retrieval tool and retrieval date. Also record its question, estimand or theorem, design or proof method, mechanism, data/model class, scope, main result, and exact difference from the proposal. Mark at least one nearest alternative and classify the relationship as `duplicate`, `replication`, `extension`, `external-validity`, `adjacent`, or `contradiction`.

Do not equate placement or citations with intellectual importance. For each nearest or exemplar work decompose `prior_bottleneck`, `innovation`, `why_field_cares`, `validation`, and `influence_or_reuse`. Read [breakthrough_anatomy.md](breakthrough_anatomy.md) for the comparison rubric. The aim is to recover a reusable move—new object, new variation, new measurement, new theorem, or a bridge that makes previously infeasible work possible—not to copy surface style.

For every frontier candidate record `first_public_at`, at least two `quality_signals`, a falsifiable `frontier_case`, and a `manuscript_action` of `cite`, `discuss`, or `exclude` with a reason. Quality signals concern substance—important question, credible design/proof, unique data, new method, surprising discriminating result, reuse potential, transparent boundaries—not author fame, institution, journal, downloads, or citations. An approved project must select at least one verified work inside the frontier window for citation or discussion.

Compare differences that can support a contribution: a distinct question, new credible variation, new data measurement, relaxed or sharper assumptions, new mechanism, materially broader scope, external-validity test, or informative replication. A different country, sample, estimator, or recent period is not automatically a contribution; explain why it changes what can be learned.

## Decision gate

Write `research/topic-survey.json` and validate it:

```bash
python3 scripts/check_topic_survey.py research/topic-survey.json --root . --json
```

The schema audit distinguishes a valid stopped/blocked record from permission to continue. Add `--require-approved` before entering design or use the research-package gate, which adds it automatically. The gate fails when the tool evidence is absent or hash-mismatched, when the search is older than `refresh_after_days`, when baseline/frontier coverage is missing, when a nearest work lacks an innovation decomposition, or when the decision is stopped/blocked. At manuscript delivery, the package gate also requires every frontier work selected for `cite` or `discuss` to appear in both the bibliography and an actual manuscript citation. For reproducible historical audits pass `--as-of YYYY-MM-DD`; ordinary runs use today's date.

## Researcher checkpoints

Default from the one-sentence question wherever the answer is reversible. Pause only at decisions that change the scientific claim:

1. **Scope lock**, after normalization and a first search: show the operational question, population/model class, outcome/theorem, causal/descriptive/theory mode, and target audience. Ask the researcher to accept or revise this boundary.
2. **Contribution lock**, after the nearest-work and breakthrough comparison: show the strongest duplicate risk and at most three defensible contribution lanes. Ask which lane to pursue or whether to stop/replicate.
3. **Design/data lock**, before estimation, proof search, licensed data access, or a costly acquisition: show the estimand/theorem, identifying assumptions, feasible data, and the largest validity risk. Record the choice in the research contract or decision ledger.
4. **Claim lock**, after falsification and before manuscript drafting: show what is supported, contradicted, and unresolved. Ask the researcher to accept the bounded claim and target outlet or request another predeclared test.

The topic survey records answered `scope-lock` and `contribution-lock` checkpoints. Later checkpoints live with the frozen design and result/claim artifacts. A blocked answer stops downstream work; silence is not consent. Do not repeatedly ask about implementation details that follow mechanically from an accepted choice.

Choose one decision:

- `proceed`: sufficiently distinct under the recorded search, with a bounded contribution statement;
- `reframe`: closest work absorbs the original claim but a defensible different estimand, mechanism, data advantage, or scope remains;
- `replicate`: the value is verification, transportability, or correction rather than novelty;
- `stop`: the proposed contribution is duplicated or not decision-relevant;
- `blocked`: coverage, access, or institutional information is insufficient.

Use contribution class `distinct-under-search`, never “proven novel.” Preserve search limitations. A duplicate cannot proceed unchanged, and zero verified close works yields `blocked`/`unresolved`, not a novelty claim. Freeze an accepted survey decision in the research contract before entering the method router or main research loop.
