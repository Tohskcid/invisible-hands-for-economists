# Research-question survey gate

Read this reference at the start of a new research question, before choosing an empirical design, structural model, or theorem strategy. Skip only when the user explicitly requests replication of a named work or supplies a current, auditable survey; record that basis.

## Normalize and search

Translate the initial question into the population or model class, outcome or target theorem, treatment/exposure or mechanism, candidate estimand, setting, and time horizon. Preserve the user's original wording alongside the normalized form.

Freeze a search cutoff and scope. The cutoff is the date the tools actually ran, not the model's knowledge date. Set `refresh_after_days` (normally 30; use 7 for fast-moving working-paper topics), and rerun the search when the gate is stale. Search several formulations rather than the exact title phrase:

For a historical paper-reconstruction benchmark, keep **search date** separate from **historical novelty date**. Compare the target's contribution only with external work first publicly available strictly before the target's first journal publication (normally its online publication date, not the later volume/issue year). The target's own working-paper and preprint versions are not competing prior art. To protect a strict author-blind test, use the earlier date of the target's first public version as the author-visible literature cutoff; quarantine all target versions and sources first public at or after that date. An external work between the target's preprint and journal dates can inform the retrospective reviewer, but not the blind author. Record publication-date evidence and classify comparator eligibility with `scripts/check_historical_prior_art.py`; the script checks chronology only, so a reviewer must still compare claims and priority. Never use a later paper to deny historical originality, or a historical pass to assert originality of a manuscript submitted today.

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

For every frontier candidate record `first_public_at` at the precision supported by its source (`YYYY`, `YYYY-MM`, or `YYYY-MM-DD`); the validators use the latest possible day at that precision for conservative chronological checks. Do not invent a publication day from a month-only publisher record. Also record at least two `quality_signals`, a falsifiable `frontier_case`, and a `manuscript_action` of `cite`, `discuss`, or `exclude` with a reason. Quality signals concern substance—important question, credible design/proof, unique data, new method, surprising discriminating result, reuse potential, transparent boundaries—not author fame, institution, journal, downloads, or citations. An approved project must select at least one verified work inside the frontier window for citation or discussion.

For `run_research_team.py` with `publication_goal: "original"`, add `contribution_probe` to the survey before design. Record the closest `nearest_result`, the exact `proposed_delta`, `field_significance`, a `discriminating_test` against the closest competing explanation, its `failure_condition`, and `feasible_evidence` (real data for empirical work or a proof path for theory). A populated probe makes the candidate auditable; the independent reviewer must still judge whether it is substantively new and important. A date extension or a different mean alone does not satisfy that scientific judgment.

Compare differences that can support a contribution: a distinct question, new credible variation, new data measurement, relaxed or sharper assumptions, new mechanism, materially broader scope, external-validity test, or informative replication. A different country, sample, estimator, or recent period is not automatically a contribution; explain why it changes what can be learned.

No exact prior study is required. If none is found, compare the nearest related studies and record the search boundary. Do not turn "no exact match found" into a claim that no one has ever studied the question.

## Decision gate

Write `research/topic-survey.json` and validate it:

```bash
python3 scripts/check_topic_survey.py research/topic-survey.json --root . --json
```

The schema audit distinguishes a valid stopped/blocked record from permission to continue. Add `--require-approved` before entering design or use the research-package gate, which adds it automatically. The gate fails when the tool evidence is absent or hash-mismatched, when the search is older than `refresh_after_days`, when baseline/frontier coverage is missing, when a nearest work lacks an innovation decomposition, or when the decision is stopped/blocked. At manuscript delivery, the package gate also requires every frontier work selected for `cite` or `discuss` to appear in both the bibliography and an actual manuscript citation. For reproducible historical audits pass `--as-of YYYY-MM-DD`; ordinary runs use today's date.

Before drafting an original contribution, add `research/prior-art-review.json` and run:

```bash
python3 scripts/check_prior_art_review.py research/prior-art-review.json \
  --topic-survey research/topic-survey.json --root . --json
```

The review binds the current survey through `topic_survey_sha256`. Its `proposed_claims` give stable claim IDs and statements. Its `works` list covers every `nearest_works` citation key exactly once, using the same title, canonical locator and first-public date as the survey, a primary `date_source`, `full_text_status: "checked"`, `full_text_locator`, `full_text_retrieved_at`, and a retained PDF or HTML `full_text_artifact` plus `full_text_sha256`. Its `comparisons` list covers **each proposed claim against each nearest work**, with `prior_claim`, an exact `source_pointer` (page, section, theorem, table, or figure), a short `source_excerpt` present in the retained text at that pointer, `difference`, and `overlap` (`same`, `partial`, `distinct`, or `uncertain`). PDF checks require `pdfinfo` and `pdftotext`; a scan without extractable text remains blocked. At manuscript delivery, the reviewed IDs and statements must exactly match every central claim in the manifest. A distinct reviewer or reviewer agent fills `independent_review` with `reviewer_id`, `independent_of_author: true`, `source_passages_verified: true`, `source_dates_verified: true`, `reviewed_at`, decision, and rationale; its decision must match the survey. Record the drafting agent as `author_id`. For a historical blind test, set `historical_author_cutoff_exclusive` to the target's first public date; uncertain publication precision is treated conservatively.

The checker blocks an approved project when a nearest work is abstract-only, its retained text or hash is missing, any claim/work pair lacks a comparison, dates violate the author cutoff, or the reviewer is the author. `proceed` and `reframe` cannot retain `same`/`uncertain` overlap; explicit `replicate` may retain `same` overlap but cannot retain `uncertain`. A reviewer must resolve semantic overlap by reading the cited passages and may reframe, replicate, or stop the project. The machine verifies evidence and attestations only: even a passing report returns `novelty_certified: false`. An inaccessible close work should remain a documented blocker until another legitimate source or a narrower claim resolves it; never assert novelty from the absence of accessible text.

For PDF `source_pointer`, use the PDF page index (for example, `page 7`) so the checker can find the excerpt on that page; a printed journal page number may differ. A parseable file and matching excerpt do not establish that its URL, date, identity, or interpretation are genuine; the independent reviewer must check those against the primary source.

Minimal shape (replace every illustrative value and hash with acquired evidence):

```json
{
  "schema_version": "1",
  "author_id": "writer-agent",
  "topic_survey_sha256": "<SHA-256 of exact survey bytes>",
  "proposed_claims": [{"id": "C1", "statement": "Precise proposed theorem or estimand"}],
  "works": [{
    "citation_key": "nearest2025", "title": "Nearest work",
    "locator": "https://publisher.example/article", "first_public_at": "2025-03",
    "date_source": "https://publisher.example/article",
    "full_text_status": "checked", "full_text_locator": "https://publisher.example/article.pdf",
    "full_text_retrieved_at": "2026-10-17",
    "full_text_artifact": "literature/nearest2025.pdf", "full_text_sha256": "<SHA-256 of PDF>"
  }],
  "comparisons": [{
    "claim_id": "C1", "citation_key": "nearest2025",
    "prior_claim": "What that paper actually establishes",
    "source_pointer": "Theorem 2, page 7", "difference": "A precise testable or provable difference",
    "overlap": "partial"
  }],
  "independent_review": {
    "reviewer_id": "referee-agent", "independent_of_author": true,
    "source_passages_verified": true, "source_dates_verified": true,
    "reviewed_at": "2026-10-17",
    "decision": "proceed", "rationale": "Specific source-based reason for the bounded decision"
  }
}
```

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
