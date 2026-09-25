# Research artifacts and deterministic gates

Read this reference when a project lacks an artifact convention, when auditing a manuscript, or when evolving this skill. Prefer the project's existing equivalent when it preserves the same links.

## Provenance graph

Use `research/manifest.jsonl` when stronger traceability than the compact experiment ledger is needed. Write one JSON object per line with a unique `id` and one of these types:

- `hypothesis`: `statement`, `falsifier`;
- `experiment`: `hypothesis_id`, `validation`;
- `run`: `experiment_id`, `harness_version`, `status`, `artifact`; add commit, input hash, seed, and environment when material;
- `evidence`: `source`, `locator`, `verified_at`; add DOI/version, access status, scope, and `relation` (`supports`, `contradicts`, or `qualifies`) when available;
- `dataset`: `name`, `source`, `locator`, `verified_at`, `access_status`, and `license`; add release/version, checksum, codebook, unit, coverage, and restrictions when material;
- `proxy`: `name`, `reason`, `generator`, `seed`, `schema`, and `intended_use`; add calibration sources and known mismatches;
- `finding`: `statement`, `run_ids`, `status`;
- `claim`: `statement` plus at least one `evidence_ids`, `finding_ids`, or `premise_ids` link. For the small set of conclusion-carrying claims add `central: true`, `role` (`premise`, `intermediate`, or `conclusion`), `status` (`supported`, `provisional`, `contradicted`, or `unsupported`), `scope`, and `uncertainty`.

Add `data_ids` to each consuming `run` and, when useful, directly to a `claim`. A claim that reaches a `proxy` either directly or through its finding/run chain must use `scope: "proxy_only"`; proxy data cannot support a claim about the real population.

IDs are immutable. Never rewrite a failed run or redirect an old ID to a new object. A changed harness creates a new baseline. Validate links with:

```bash
python3 scripts/validate_research_manifest.py research/manifest.jsonl
python3 scripts/validate_research_manifest.py research/manifest.jsonl --require-argument-graph
```

## Literature evidence bank

Represent the literature map with `evidence` and `claim` records rather than summaries alone. Preserve the query, database, cutoff date, version, page/theorem/table locator, inclusion reason, and whether full text was checked. Record contradictions directly; do not collapse them into a consensus paragraph.

For prospective idea evaluation, freeze a historical literature cutoff before generating hypotheses and use later publications only for evaluation. Do not use a future-paper match as proof that a hypothesis was correct or novel.

## Manuscript traceability

Put `[claim:CLAIM_ID]` beside material claims and `[data:DATA_ID]` where a dataset or proxy is introduced or interpreted in Markdown. Run:

```bash
python3 scripts/audit_claims.py manuscript.md research/manifest.jsonl
python3 scripts/audit_claims.py manuscript.md research/manifest.jsonl --strict-numbers
python3 scripts/audit_claims.py manuscript.md research/manifest.jsonl --strict-numbers --require-data-markers
python3 scripts/audit_claims.py manuscript.md research/manifest.jsonl --require-central-claims
```

Use `--require-data-markers` for empirical or structural manuscripts, not data-free theory papers. The argument gate rejects claim-premise cycles, ungrounded central conclusions, supported conclusions that depend on contradicted or unsupported premises, and proxy taint hidden behind premise chains. `--require-central-claims` requires every central claim ID to appear in the manuscript. These checks prove graph completeness and traceability, not semantic entailment; a fresh-context logic referee must still attack wording, scope, numbers, and competing explanations.

## Result-to-manuscript binding

For quantitative manuscripts, export estimates from analysis code to `research/results.json`; never transcribe values from a console or model response. The minimal schema is:

```json
{
  "schema_version": "1",
  "run_id": "RUN_ID",
  "source_sha256": {"scripts/estimate.py": "64_HEX", "data/manifest.json": "64_HEX"},
  "required_bindings": ["main.estimate", "main.std_error", "main.n"],
  "results": {"main": {"estimate": 0.125, "std_error": 0.041, "n": 1200}}
}
```

Bind Markdown values as `0.125 [result:main.estimate]`. In LaTeX define `\newcommand{\result}[2]{#2}` and write `\result{main.estimate}{0.125}`. Put `[results-sha256:HASH]` in a source comment or non-rendered metadata block, where `HASH` is the SHA-256 of the exact results file. Then run:

```bash
python3 scripts/check_result_bindings.py \
  --results research/results.json --manuscript paper/main.tex --root . --json
```

The checker accepts honest display rounding, rejects changed or missing required values, and rejects a stale results hash. Hash agreement proves that the manuscript used a specific artifact, not that the estimator or source data are correct; those remain design and provenance obligations.

## Research package CI

Projects may declare applicable gates in `research/package.json`:

```json
{
  "topic_survey": "research/topic-survey.json",
  "data_provenance": "research/data-provenance.json",
  "manifest": "research/manifest.jsonl",
  "manuscript": "paper/main.md",
  "coverage": "research/manuscript-coverage.json",
  "bibliography": "paper/references.bib",
  "literature_archive": "research/literature-archive.json",
  "results": "research/results.json",
  "design_audit": "research/design-audit.json",
  "mechanism_scope": "claimed",
  "mechanism_audit": "research/mechanism-audit.json",
  "mechanism_review": "research/mechanism-review.json",
  "claim_scope": "real-world",
  "real_world_audit": "research/real-world-audit.json",
  "text_audit": "research/text-audit.json",
  "latex_main": "paper/main.tex"
}
```

Run `python3 scripts/check_research_package.py --root .`. Only declared, existing artifacts are checked, except that quantitative `results` require valid `data_provenance`, while a `manuscript` requires a manifest, ready coverage matrix, bibliography, complete literature archive, a passing hash-bound logic review, and `mechanism_scope` set to `claimed` or `not-claimed`. Claimed mechanisms require a passing hash-bound mechanism audit and independent review; `not-claimed` means the prose must not assert that a channel was established. A package with a manuscript or results must declare `claim_scope` as `research-only` or `real-world`; real-world scope requires a passing `real_world_audit`. Declare `design_audit` or `structural_audit` for the applicable quantitative mode, and declare `text_audit` when LLM-annotated text variables are included. Declaring `latex_main` also requires a hash-bound visual review that covers every rendered page. A failed package emits `iteration_required` and `return_to`; the controller remediates those stages and reruns the complete package instead of waiving a gate. Repository CI tests both the generic harness and the bounded bundled audit; research projects should run their own package gate for project-specific artifacts.

File organization and the local cited-paper archive follow [project_layout.md](project_layout.md). Keep literature metadata in `research/literature-archive.json` and PDFs under `literature/papers/`; do not mix papers, data, tables, and build products in one output directory.

## Skill evals

`evals/cases.jsonl` contains public development cases. An independent evaluator or deterministic artifact check produces JSONL records of the form:

```json
{"case_id":"empirical-panel","gates":["contract","estimand-frozen"],"token_count":1200}
```

Aggregate them with:

```bash
python3 scripts/run_skill_evals.py --results path/to/results.jsonl
```

The runner aggregates observed gates; it does not decide that a gate is true. Keep release holdouts outside the public skill, freeze graders before candidate runs, and retain per-mode hard gates instead of optimizing one score.
