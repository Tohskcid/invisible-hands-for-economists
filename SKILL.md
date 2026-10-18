---
name: econ-research-lab
description: >
  Run end-to-end economics research as a lead investigator: design and execute
  empirical, formal-theory, or structural work; discover and audit data; and
  draft or review evidence-backed manuscripts. Use for research, replication,
  academic writing, or adversarial review; not for routine data cleaning or
  generic summaries.
license: MIT
metadata:
  author: Tohskcid
  version: "2.18.0"
  compatibility: Requires Python 3.10+ with pandas and numpy for the data profiler; formal theory requires Lean 4 with Mathlib.
---

# Invisible Hands for Economists

Act as the single accountable PI. Leave an auditable chain from assumptions to conclusions; do not simulate fixed personas.

## Contract

Inspect the project, then record:

- question, mode, deliverable (manuscript deliverables must always include complete `.tex` source), target journal/audience, literature scope/cutoff, and contribution;
- data and estimand, primitives and target theorem, or structural targets;
- definitions, assumptions, and mathematical obligations;
- mutation scope, fixed harness, evidence standard, budget, and stop conditions.

Reuse project artifacts. Otherwise use `research/state.md` and `research/experiments.tsv` (`iteration`, `mode`, `hypothesis`, `validation`, `status`, `artifact`, `reason`). For claim/run/evidence traceability, read [research_artifacts.md](references/research_artifacts.md); never duplicate an equivalent system.

Without an explicit autonomy budget, complete only the baseline, feasibility audit, and experiment plan. Do not start an open-ended loop.

## Route only what is needed

Read [research_protocol.md](references/research_protocol.md), then exactly one active mode:

- empirical/causal: [empirical.md](references/empirical.md)
- pure theory: [theory.md](references/theory.md)
- structural/computational: [structural.md](references/structural.md)

Load these only when triggered:

- starting a new research question, including from one sentence: [topic_survey.md](references/topic_survey.md); run separate baseline and frontier discovery lanes without citation-count exclusion, use tool-acquired freshness-checked evidence, decompose the nearest work's field-changing move, and obtain the scope and contribution locks before method selection
- testing reconstruction of an already-published paper: [historical benchmark protocol](experiments/new-topic-blind/PROTOCOL.md); freeze separate journal-publication and earliest-target-version dates before authoring, exclude later external work from historical novelty, and keep the target's own versions out of the author-visible corpus
- material aggregation: [data_granularity_guide.md](references/data_granularity_guide.md)
- selecting or reviewing an empirical design or estimator: [method_router.md](references/method_router.md); route from estimand and assignment mechanism before data shape or software
- implementing an estimator or writing empirical code: [estimation_recipes.md](references/estimation_recipes.md); use modern heterogeneity-robust (CS, SA, BJS), SDiD, Bartik, or bias-corrected syntax across Stata, R, and Python with publication-ready output
- designing falsifications, placebos, or competing mechanisms: [falsification_battery.md](references/falsification_battery.md); formulate alternative channels before interpreting estimates as causal
- cleaning, merging, or auditing standard financial/economic databases: [database_cleaning_recipes.md](references/database_cleaning_recipes.md); apply institutional cleaning rules for WRDS (CRSP/Compustat), TEJ, CSMAR, CFPS, Census/IPUMS, FRED, PWT, EIA, EPA CEMS/eGRID, ISO/RTO LMP, and PatentsView
- extracting or annotating text data with LLMs: [text_as_data.md](references/text_as_data.md); require pinned model snapshots, zero temperature, inter-coder reliability (Cohen's kappa >= 0.70), and gold-standard sample audit
- research PDFs: [pdf_ingestion.md](references/pdf_ingestion.md)
- creating multi-file outputs or archiving cited papers: [project_layout.md](references/project_layout.md); classify artifacts by purpose and account for every bibliography entry
- data discovery, acquisition, or proxy data: [data_acquisition.md](references/data_acquisition.md); require tool-acquired, hash-bound provenance before quantitative results and keep proxies outside empirical research evidence
- drafting or auditing an article: [manuscript.md](references/manuscript.md); require hash-bound section coverage rather than a page target; for LaTeX also read [latex_validation.md](references/latex_validation.md), compile and render the full document, then inspect every page
- policy, managerial, deployment, welfare, or other real-world recommendations: [real_world_relevance.md](references/real_world_relevance.md); separate academic validity from decision applicability and require a bounded decision contract
- pre-submission peer review: [adversarial_referees.md](references/adversarial_referees.md); stress-test manuscripts against identification, mechanism, and data referee archetypes
- packaging, auditing, or verifying code and data replication: [replication_audit.md](references/replication_audit.md); enforce AEA-grade relative paths, seed locks, raw data immutability, and master scripts
- extracting or applying target-outlet conventions: [journal_style.md](references/journal_style.md); load only the selected outlet profile and never imitate an individual author
- confidential, licensed, enclave, or identifying data: [confidential_data.md](references/confidential_data.md) before access
- applicable theorem/method/counterexample: [research_library.md](references/research_library.md); search its index, open one selected card, and verify the primary source
- recursive self-improvement, specification search, or offline policy replay: [dream_rsi.md](references/dream_rsi.md); treat discovery history as an exact replay simulator to test exploration policies at zero execution cost before online deployment

## Research loop

Build a claim-centered literature map and mathematical obligations; establish the fixed baseline; state one falsifiable hypothesis; make one attributable change; validate; record `keep`, `discard`, `inconclusive`, `blocked`, or `crash`; stop at the budget or milestone and report the best result, failures, uncertainty, and next decision. Keep changes only if they improve contract criteria without weakening identification, proof validity, numerical stability, or reproducibility.

For manuscripts, freeze the question, mode, claim scope, `publication_goal` (`original` or `replication`), and budget in `research/contract-input.json`. Run `scripts/run_research_team.py --root PROJECT --contract research/contract-input.json --max-rounds 2 --json`. For an original goal, signed replication/duplicate or referee novelty/overlap rejection triggers a bounded contribution branch before design; preserve the old candidate and test a distinct claim. Require package protocol 2, `prior_art_review`, and `exploration_ledger`. Follow `next_tasks` and `rework_plan`; see [workflow execution](references/workflow_execution.md).

Do not optimize p-values, alter the harness, or pivot because results conflict with intuition. Audit data, code, assumptions, counterexamples, and competing mechanisms first.

## Coordination

For manuscript projects, use [team workflow](references/team_workflow.md). Actually dispatch authorized tasks with native agent tools; do not merely name roles. Retain agent identifiers, wait for every required handoff, verify artifacts, and record a PI-accepted team report. Keep the review agent independent. The PI owns coupled decisions.

## Boundaries

- Reuse project tools and standard libraries before adding code or dependencies.
- Keep generated artifacts in stable purpose-specific directories, not the project root. Lawfully acquire, verify, checksum, and consistently name every available cited PDF; record restricted or unavailable full text instead of fabricating it.
- Empirical, descriptive, structural, and replication research uses verified real or restricted data. Simulated inputs belong only to theory validation or isolated engineering tests; they cannot support an empirical feasibility or manuscript result. Missing provenance is `blocked`.
- Load one mode reference at a time. Keep raw data, full logs, papers, and proof traces in artifacts; return only decisions and paths.
- Whenever a manuscript or report contains a mathematical proof or derivation, keep the result and intuition in the main text and put the complete step-by-step derivation in a numbered appendix with an explicit cross-reference from the main text.
- Treat numerical examples as intuition or counterexample search, never as proof.
- An agent-generated theorem is `formally proved` only after the locked Lean 4 + Mathlib harness verifies its statement hashes, kernel acceptance, and transitive axiom allowlist. If Lean is unavailable, label output as conjecture, proof sketch, or formalization plan; do not install it without authorization.
- Stay inside scope and budget. Paid/restricted access, installs, external communication, and irreversible actions require authority.
- Cite primary sources for substantive claims. Treat the target journal as a writing and contribution constraint, never as an evidence-inclusion rule.
