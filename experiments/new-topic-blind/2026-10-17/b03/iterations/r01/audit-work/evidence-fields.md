# Fields to fill from final evidence

This file is a checklist only. Do not copy placeholders into the package as completed evidence. Use the scripts named below as the authoritative schema; hash final bytes with SHA-256 and use project-relative paths.

## `research/coverage.json` — `check_manuscript_coverage.py`

- Top level: `schema_version: "1"`, `mode: "theory"`, `manuscript_sha256`, nonempty `sections`.
- For each final `\section{...}` heading exactly once: unique `id`, `role`, `status` (`ready`, `blocked`, or `not_applicable`), `headings`, `claim_ids` from the final manifest, and `artifacts` with `kind`, `path`, `sha256`. A nonready entry needs `gap`.
- Required ready roles for theory delivery: introduction, literature, model, results, conclusion, appendix, limitations. Every ready section needs `section_packet`; model also needs `model`, results need `proof`, appendix needs `appendix`. Review section packets for actual coverage before marking ready.

## `research/logic-review.json` — `check_logic_review.py`

- `reviewed_sha256: {"manuscript": <final SHA>, "manifest": <final SHA>}`.
- `overall_verdict`: pass, revise, or reject; `global_gaps`: string list; `uncertainty`: string.
- One `claim_reviews` entry per central manifest claim ID, exactly once. Each has `claim_id`, `verdict` (coherent, revise, unsupported, uncertain), `weakest_link`, `scope_or_number_mismatch`, `competing_explanation`, `required_revision`.
- The r01 manifest has 12 central IDs (`CL-B03-P1` through `P8`, `CL-B03-C1` through `C3`, `CL-B03-L1`); recompute after final manifest edits. A pass needs every verdict coherent and no revision or global gap.

## `research/mechanism-audit.json` and `research/mechanism-review.json` — `check_mechanism_audit.py`

- Audit: `schema_version: "1"`, `claim_id`, `claim`, `bounded_conclusion`; `preferred_mechanism` with `id`, `statement`, `distinctive_prediction`, `causal_chain` of at least two real steps; at least three `alternatives`, each with `id`, `statement`, `observable_implication`.
- For each alternative, at least one genuine test with `id`, `alternative_id`, distinct `preferred_prediction` and `alternative_prediction`, `design`, `decision_rule`, `finding`, `status` (`distinguished`, `not-distinguished`, `inconclusive`, `blocked`), `artifact`, `artifact_sha256`. `unresolved_alternatives` must equal alternatives lacking any distinguished test. `overall_verdict` and `claim_status` must reflect the evidence.
- Review: `schema_version: "1"`, `reviewed_sha256: {"mechanism_audit": <final audit SHA>}`, `independent_context: true` only if true, `verdict`, `weakest_link`, `observationally_equivalent_explanation`, `discriminating_test_assessment`, `required_revision`. A passing review cannot require revision.

## `research/substantive-review.json` — `check_substantive_review.py`

- After final manuscript and topic survey: `manuscript_sha256`, `topic_survey_sha256`, actual `reviewer_id`, actual `author_agent_ids`, `verdict`.
- `dimensions` must have exactly novelty, overlap, research_design, inference_or_proof, logic, completeness. Each dimension needs `verdict`, substantive `reason`, nonempty hash-bound `evidence` (`path`, `sha256`). Novelty and overlap must bind the current topic survey file.
- `limitations`: nonempty list with `text_anchor` literally found in final manuscript, `effect_on_claim`, `boundary_or_mitigation`. `open_critical_issues` must be empty for delivery. An independent reviewer must decide these fields.

## `research/team.json` — `check_research_team.py`

- `coordinator_id`; one final task for each theory role: literature, planning, model, validation, interpretation, writing, review.
- Each task: actual `role`, actual native `agent_id`, `status: "accepted"` only after PI acceptance, `accepted_by` equal to coordinator ID, nonempty hash-bound `artifacts` (`path`, `sha256`). At least two research/writing agents; review agent must be independent. The review task artifact must include the exact substantive-review file and hash.

## `research/latex-visual-review.json` — `check_latex.py finalize`

- After a fresh build and actual inspection: `pdf_sha256` from `paper/build/report.json`, `status: "pass"`, actual `reviewer`, `pages_reviewed` as every page number exactly once, `issues: []` only after all issues are resolved. The checker does not consume the existing `page_count`, `all_pages_visually_inspected`, `visual_defects`, or `delivery_visual_check_passed` fields. Any source input change invalidates the review/build binding.
