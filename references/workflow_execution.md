# One-shot research execution

Use this sequence when a researcher delegates a complete paper from an initial question. The agent authors and investigates; `run_research_workflow.py` records and checks supplied artifacts. No deterministic gate can certify novelty, identification, a proof, or publication quality by itself.

1. **Freeze the original task.** In the project root, create `research/contract-input.json` with the exact question, `mode`, `deliverable`, `claim_scope`, `mechanism_scope`, target journal, `max_budget` (measured wall-clock seconds), required obligations, and planned analysis commands/outputs if known. Run this skill's `scripts/run_research_workflow.py --root <project> --contract research/contract-input.json --json` immediately. The resulting `research/contract.json` and `research/ledger.jsonl` are the frozen baseline. Do not silently edit the question, mode, deliverable, or claim scope later; a narrower result is a branch, not completion of the original task.
2. **Establish feasibility.** Follow `topic_survey.md` and the active mode reference. Record retrieved primary sources with exact locators, acquisition state, license, retrieval date, and file hashes. Mark inaccessible or unverified sources as gaps. Decide whether the question is distinct, a replication, a bounded extension, or blocked; do not infer novelty from memory or citation count.
3. **Map obligations before writing conclusions.** Add central claims, supporting findings and evidence, assignment/inference details or theorem premises to the manifest. Identify the single obstacle that most blocks the original claim. Run a discriminating test or obtain the missing source; keep a test's successful exit separate from the scientific conclusion. Record unresolved or blocked obligations and stop when the budget or access boundary is reached.
4. **Produce research artifacts.** Empirical, descriptive, structural, and replication research uses verified real or restricted data, including feasibility work that declares data. Simulated inputs belong only to theory validation or isolated engineering tests; they cannot support empirical research results. Write a master analysis script and generated results, tables, diagnostics, and provenance. For theory, write complete derivations and mark Lean verification only when it actually ran. Draft all sections, a clear limitations section, and appendices in LaTeX. Dispatch roles through native agent tools and record accepted handoffs using [team workflow](team_workflow.md). Run independent substantive review before release.
5. **Declare and run delivery gates.** Create `research/package.json` using the required profile for the frozen `mode` and `deliverable`; set its `claim_scope` and `mechanism_scope` to the contract values. A manuscript also requires `team_report` and `substantive_review`. Include all profile-required artifact paths. Rerun the workflow command. Work through `next_tasks` in priority order. Use `rework_plan.restart_from` to restart at the earliest failed stage and treat `invalidate_stages` as stale; preserve old artifacts and regenerate dependent work. A deterministic defect can use the bounded `dream_replay_simulator.py --online` command queue; the queue and an in-flight receipt survive interruption. Inspect the side effects of an interrupted command before retry. Scientific failures require new evidence, revised claims within scope, or an honest block. Do not remove a required gate or mark a pending visual review as passed.
6. **Release the exact reviewed build.** Render each PDF page, record who or what actually inspected it, resolve issues, and bind the review to the PDF SHA-256. Confirm the final release PDF and all TeX, bibliography, table, and figure inputs still match the build. Report completion only when the workflow returns `complete`; otherwise provide the artifacts, failed gates, unresolved science, budget spent, and next concrete action.

For an empirical manuscript the package profile requires topic survey, real-data provenance, manifest, results, clean replication, design audit, manuscript, limitations coverage, bibliography, literature archive, logic review, team report, independent substantive review, and the locked PDF build/review/release. Theory and other modes have their own required sets in `scripts/check_research_package.py`. The workflow does not currently create these files on its own; the research agents must do the substantive work. See [implementation status](../docs/research/workflow-implementation-status.md) for the verified engineering scope.

An obstacle is resolved only after a reviewer records an interpretation and hash-bound evidence in `research/obstacle-assessments.json`. The reviewer may be an agent or a human and must be identified accurately. For example:

```json
{
  "obstacles": {
    "parallel-trends": {
      "status": "resolved",
      "rationale": "The pre-period diagnostic supports the stated restricted claim; see its limitations.",
      "reviewer_kind": "agent",
      "reviewer": "fresh-context-reviewer",
      "evidence": [{"path": "output/diagnostics/pretrends.json", "sha256": "<actual 64-character SHA-256>"}]
    }
  }
}
```

The workflow verifies the file hash and reviewer metadata, not the correctness of the economic interpretation. A changed or missing evidence file reopens the obstacle. If no defensible assessment exists, leave it `unresolved` or `blocked` and report the gap.

The optional MCP server exposes the same local workflow as `project_status`, `audit_package`, `run_workflow`, and `run_iteration` tools, plus the `econ://workflow` resource and `research_question` prompt. Bind it to one project root at launch. `run_iteration` executes only actions already declared in `research/dream-actions.json`; the research agent must formulate, check, and add those actions. The MCP server does not invent sources or write a paper by itself.
