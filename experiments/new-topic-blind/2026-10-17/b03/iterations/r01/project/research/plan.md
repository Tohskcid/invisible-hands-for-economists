# r01 post-unblinding repair plan

This is a development iteration of the frozen b03 submission, not another blind benchmark. The original submission, referee report, and 4/10 historical-reconstruction score remain unchanged.

The frozen question and theory/manuscript claim scope are retained. The local wall-clock budget is 3,600 seconds from `iteration.json`. Exact published overlap ends any novel-journal claim; technical gate repair and proof auditing may continue within the budget as a harness development exercise. The repository runner counts only its subprocess time, so the separate start time is the actual iteration clock.

1. Establish the baseline from `b03/evaluation/workflow-replay-result.json`: package missing six artifacts, PDF review schema and hash mismatch, incomplete EX equilibrium proof, and blocked novelty decision.
2. Make one scientific change: attempt to close the EX equilibrium argument with a complete proof or exact external theorem mapping; otherwise retain the gap. Do not use the sealed target as author evidence.
3. Regenerate only the affected artifact chain in `r01/project`: manuscript, bibliography/build, manifest and coverage, independent review, team record, and delivery checks. Record each gate result without inventing a pass.
4. Run `scripts/run_research_workflow.py` on the revision. If blocked, follow its `next_tasks` and `rework_plan` once more within the budget. Treat direct publication overlap as a scientific novelty block, not a technical error to bypass.

Success for the historical reconstruction benchmark remains the original frozen b03 score and independent review; r01 cannot replace them. A workflow result of `complete` would certify only this revised research package's declared gates. A remaining truthful `blocked` with an exact evidence trail is a valid development outcome but not research-task completion.
