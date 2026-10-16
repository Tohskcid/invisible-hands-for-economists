# Multi-agent research team and rework

Use this protocol for a manuscript. The host agent is the accountable PI. The Python checker verifies handoff records; it cannot spawn agents or verify that a named agent actually did the work. Dispatch through the host's native agent tools and retain the returned agent identifiers. If the host cannot create independent agents, stop manuscript delivery and report the missing capability.

## Dispatch by research mode

Assign bounded tasks with non-overlapping writes. At least two research agents and one independent review agent must participate. One agent may cover more than one role, but the review agent must not do research or writing. The required role names are defined by `scripts/check_research_team.py`:

| Role | Required output |
|---|---|
| `literature` | Search log, nearest-work comparison, verified source list, duplicate risk |
| `planning` | Frozen question, estimand/theorem, design, feasibility and stop conditions |
| `data_acquisition` | Real/restricted data provenance and access record; not used in pure theory |
| `data_cleaning` | Reproducible transformations, schema and sample audit; not used in pure theory |
| `model` | Empirical design or theory/structural model with assumptions; omitted for pure replication |
| `validation` | Replication, diagnostics, counterexamples, proof checks and failure records |
| `interpretation` | Bounded claims, competing explanations and limitations |
| `writing` | Evidence-backed section packets and complete manuscript |
| `review` | Independent whole-paper review, including novelty, overlap, validity, logic and completeness |

Give each agent the accepted contract, relevant prior handoffs, exact task, artifact directory, budget and stopping rule. Ask it to return findings, evidence paths, unresolved issues and next action. The PI checks the files and accepts or rejects the handoff. Wait for dependent tasks before assigning later stages. Do not use agreement among agents as evidence of truth.

## Team report

Write `research/team.json` after the actual work. Give each required role one final handoff. Record the native agent identifier, `status: "accepted"`, `accepted_by` equal to `coordinator_id`, and one or more project-relative artifact paths with current SHA-256 hashes. The `review` handoff must include `research/substantive-review.json`. Run:

```bash
python3 scripts/check_research_team.py research/team.json --root . --mode empirical \
  --review research/substantive-review.json --json
```

A checker pass proves that the declared files and hashes match. It does not prove agent identity or research quality. Keep host dispatch receipts in the ledger for external audit.

## Independent review

Write `research/substantive-review.json` after the draft and topic survey are frozen. Bind it to their SHA-256 hashes. Name the reviewer and author agents. Give each dimension—`novelty`, `overlap`, `research_design`, `inference_or_proof`, `logic`, `completeness`—a verdict, specific reason, and nonempty `evidence` list of project-relative `path` plus current `sha256`. Novelty and overlap must cite the current topic survey. Record at least one real limitation with a `text_anchor` that appears in the manuscript, its `effect_on_claim`, and its `boundary_or_mitigation`. A passing delivery has no `open_critical_issues`. A critical unresolved defect means `revise` or `reject`, even if other dimensions pass.

Run `scripts/check_substantive_review.py` before delivery. A passing JSON record verifies coverage and current inputs. A second reader must still assess whether the reasons are sound.

## Failure and restart

Read `next_tasks` and `rework_plan` after every workflow run. The same plan persists in `research/rework-state.json` so another session can resume. `restart_from` identifies the earliest failed stage. Treat all `invalidate_stages` as stale. Preserve old artifacts for audit; regenerate the affected outputs and all dependent reviews from the accepted contract. Recheck every applicable gate. A failed novelty decision returns to literature and may require a new contract branch. A failed source or design returns to that stage and invalidates later estimates and prose. A PDF-only error returns to delivery. Stop at the declared budget or an access block. Do not erase failed paths or retry an interrupted external action before checking its side effects.
