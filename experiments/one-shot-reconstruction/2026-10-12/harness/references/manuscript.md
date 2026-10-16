# Economics manuscript workflow

Read this reference when drafting, revising, translating, or auditing an economics paper, thesis chapter, working paper, referee response, or research article.

## Contract and outline

Confirm the target journal or intended audience, format, language, length, expected contribution, deliverable, and permitted files. Manuscript deliverables must always output and include the complete LaTeX source file (`.tex`) alongside modular table inputs (`.tex`) and any compiled `.pdf` or `.md`. Treat journal choice as a constraint on framing, length, style, and contribution—not as a shortcut for judging evidence. Inspect the existing manuscript, bibliography, tables, figures, model, code, and project conventions before creating a new structure. Preserve the user's chosen LaTeX, Quarto, Markdown, or word-processing workflow.

Build an evidence-backed outline from the research contract. State one primary question and contribution, then map each section to the claims, evidence or findings, assumptions, tables/figures, and unresolved gaps it needs. Do not manufacture results, references, mechanisms, robustness checks, or novelty. A missing input becomes a marked gap or a scoped research task.

## Evidence-driven scale

Do not target a page count or draft a full empirical paper in one context pass. Length follows the validated evidence package and outlet rules; concise main text may coexist with a substantial online appendix. Draft from section packets stored as artifacts, then integrate and audit the whole argument. Keep only compact outlines and cross-section decisions in active context.

Before prose, build `research/manuscript-coverage.json`, mapping every manuscript section to its central claims, a compact section packet, and hash-bound supporting artifacts. Depending on the question, this may include institutional setting, data provenance and construction, measurement validation, identification, main estimates, design-specific diagnostics, robustness tied to actual threats, heterogeneity, mechanisms, counterfactual or welfare analysis, external validity, and limitations. Do not add a component merely to increase length; mark unsupported components absent or blocked.

For empirical delivery, the introduction, literature, data, identification, results, robustness, conclusion, and appendix roles must be ready. Every ready section needs a section packet and manifest claim IDs. Data requires documentation and construction code; identification requires code plus a diagnostic or design audit; results and robustness require analysis code, structured results, and a generated table, figure, or diagnostic. Additional mechanism, heterogeneity, and external-validity sections inherit the same quantitative obligations when included. Run:

```json
{
  "schema_version": "1",
  "mode": "empirical",
  "manuscript_sha256": "64_HEX",
  "sections": [{
    "id": "main-results",
    "role": "results",
    "status": "ready",
    "headings": ["Empirical Results"],
    "claim_ids": ["C_MAIN"],
    "artifacts": [
      {"kind": "section_packet", "path": "research/sections/results.md", "sha256": "64_HEX"},
      {"kind": "analysis_code", "path": "scripts/analyze/main.py", "sha256": "64_HEX"},
      {"kind": "result", "path": "research/results.json", "sha256": "64_HEX"},
      {"kind": "table", "path": "output/tables/main.tex", "sha256": "64_HEX"}
    ]
  }]
}
```

```bash
python3 scripts/check_manuscript_coverage.py research/manuscript-coverage.json \
  --manuscript paper/main.tex --manifest research/manifest.jsonl \
  --root . --require-ready --json
```

The checker binds the coverage matrix to the manuscript hash, verifies every top-level heading is accounted for, resolves claim IDs against the manifest, and verifies artifact hashes. A valid but incomplete matrix may contain `blocked` sections with explicit gaps; `--require-ready` prevents delivery until every required role is supported. Never convert a blocked section into prose merely to increase page count.

Place material needed to verify but not carry the main argument in modular appendices: variable definitions, sample construction, additional diagnostics, alternative specifications, derivations or proofs, simulation and numerical checks, data-quality audits, disclosure constraints, and reproducibility instructions. If the manuscript contains any mathematical proof or derivation, state the result and intuition in the main text, cross-reference a numbered appendix, and put the complete step-by-step derivation there; justify each nontrivial equality, inequality, implication, optimization step, limit or interchange, and case transition rather than replacing it with “standard,” “obvious,” or “similarly.” Generate tables and figures from analysis artifacts rather than re-describing raw logs, and register them in the coverage matrix. A long manuscript with repeated specifications is not more complete; a short manuscript missing identification evidence is not ready.

If outlet-specific writing is requested, first read [journal_style.md](journal_style.md). Official author instructions are hard constraints; an evidence-backed outlet profile supplies soft conventions only. Research validity always overrides stylistic fit.

## Research-merit gates

Before polishing prose, grade each dimension `pass`, `revise`, or `blocked` and cite the supporting artifact. Style cannot repair a failed gate.

1. **Identification.** Define the causal or descriptive estimand and assignment mechanism; enumerate reverse causality, omitted variables, selection, interference, anticipation, and measurement threats as applicable; then tie each identifying assumption to institutional evidence, diagnostics, sensitivity analysis, or an explicit limitation. Use RCT, IV, DiD, RDD, structural estimation, or another design only when its assumptions fit the setting. A pre-trend test can reveal violations but cannot prove parallel trends. Do not search controls, samples, fixed effects, clustering, or outcomes for preferred significance.
2. **Economic mechanism.** State why optimizing households, firms, intermediaries, or institutions generate the prediction, and distinguish model implication, reduced-form mechanism evidence, and speculation. Mediation is causal only under its additional identification assumptions. Run a counterfactual or welfare exercise only when the design or identified model supports it; otherwise label it illustrative.
3. **Data and econometrics.** Audit provenance, construction, linkage, measurement, missingness, representativeness, timing, geography, weights, disclosure limits, and the match between variation and estimand. Justify inference, fixed effects, clustering, and robustness tests from the data-generating and assignment process. Robustness means testing credible alternatives and failure modes, not accumulating specifications.
4. **Contribution and relevance.** Establish the nearest literature gap as a difference in question, mechanism, data, identification, or method; bound external validity; quantify economically meaningful magnitudes where justified; and derive policy, welfare, or managerial implications no stronger than the evidence. A fashionable topic or prestigious outlet is not a contribution.

If the manuscript makes a policy, managerial, deployment, welfare, or other real-world recommendation, read [real_world_relevance.md](real_world_relevance.md), declare `claim_scope: real-world`, and pass the applicability gate. Otherwise declare `claim_scope: research-only` and keep conclusions explicitly academic. Statistical significance and internal validity alone do not make a result decision-ready.

## Drafting

Use the structure appropriate to the paper rather than forcing fixed headings. Ensure that:

- the title and abstract report the actual question, method, main result, scope, and uncertainty;
- the introduction connects motivation, question, contribution, closest literature, result, and roadmap without overstating novelty;
- the literature review is organized by claims and differences, not one paragraph per paper;
- theory separates primitives, assumptions, definitions, propositions, intuition, proof status, and welfare or comparative-static scope;
- empirical sections distinguish estimand, assignment mechanism, data construction, estimator, inference, diagnostics, robustness, and external validity;
- structural work reports identification, moments, computation, fit, sensitivity, and counterfactual assumptions;
- conclusions do not introduce new evidence or exceed the identified population, model class, or proof status;
- LaTeX deliverables pass the compile, log, page-render, and independent visual-review gates in [latex_validation.md](latex_validation.md). Prefer redesigning or splitting wide tables, calibrated columns, `tabularx`, `longtable`, or landscape floats; use `\resizebox` only when readability survives review.

Read [data_acquisition.md](data_acquisition.md) before writing or revising any data section. Put `[claim:CLAIM_ID]` beside material Markdown claims and `[data:DATA_ID]` where a dataset or proxy is introduced or materially interpreted. For quantitative claims, export a structured result artifact and apply the result-to-manuscript binding gate in [research_artifacts.md](research_artifacts.md); never type estimates from memory or raw logs. Use the project's citation manager; verify citation metadata and page, theorem, table, or appendix locators against primary sources. Before delivery, follow [project_layout.md](project_layout.md): account for every bibliography key, lawfully download and consistently name every available cited PDF, and record any access gap explicitly. Audit replication readiness against [replication_audit.md](replication_audit.md) and stress-test claims against [adversarial_referees.md](adversarial_referees.md).

## Whole-manuscript argument audit

Before delivery, read the paper as one argument rather than isolated prose. Put only the 5–15 conclusion-carrying claims in the manifest argument graph using `premise_ids`, `role`, `central`, `status`, `scope`, and `uncertainty`; do not copy the manuscript into the graph. Produce a compact claim map and test:

1. Does every conclusion answer the stated question and follow from named premises, evidence, or proved results?
2. Is causal, welfare, equilibrium, identification, novelty, or generality language stronger than the design or theorem permits?
3. Are maintained assumptions presented as assumptions rather than findings, and are the conclusion-carrying ones defended?
4. Do abstract, introduction, results, tables/figures, and conclusion report consistent samples, signs, magnitudes, uncertainty, definitions, and proof status?
5. Are plausible competing explanations, counterexamples, null results, failed paths, and limitations represented fairly?
6. Can a reader reconstruct the data and analysis from the cited sources, transformations, code, environment, and manifest links?
7. Is any proxy result confined to `proxy_only` claims and described as synthetic or proxy everywhere it appears?

Classify each central claim as supported, provisional, contradicted, or unsupported. Revise wording to the strongest defensible statement; do not repair a logical gap with rhetoric. Run the deterministic manifest audit with `--require-argument-graph` and the manuscript audit with `--require-central-claims`, adding `--require-data-markers` for empirical or structural papers.

Only after those gates pass, dispatch a fresh-context `logic-referee` agent with the frozen question, manuscript, manifest, deterministic reports, necessary tables/figures, and file hashes—but none of the author's reasoning, confidence, or prior handoffs. It reviews each central claim's weakest link, scope or number mismatch, competing explanation, and required revision without editing the manuscript. The PI adjudicates every finding, revises or downgrades claims, and reruns both gates after material changes. Structural graph validity and referee review reduce logical errors; neither constitutes a formal proof that natural-language entailment is correct.

The referee returns one compact JSON object, not a rewritten paper or chain-of-thought. Include `reviewed_sha256` for `manuscript` and `manifest`; `overall_verdict` (`pass`, `revise`, or `reject`); string-list `global_gaps`; string `uncertainty`; and exactly one `claim_reviews` item per central claim. Each item contains `claim_id`, `verdict` (`coherent`, `revise`, `unsupported`, or `uncertain`), and short strings for `weakest_link`, `scope_or_number_mismatch`, `competing_explanation`, and `required_revision`.

Validate freshness and coverage before accepting the handoff:

```bash
python3 scripts/check_logic_review.py \
  --manuscript manuscript.md \
  --manifest research/manifest.jsonl \
  --review research/logic-review.json --json
```

A passing report requires current hashes, every central claim exactly once, no global gap, no required revision, and a `coherent` verdict for each claim. After any manuscript or manifest change, the old review is stale. Keep detailed notes outside the active context; pass only claim-level decisions, artifact paths, and unresolved uncertainty to the PI.
