# Target-outlet style distillation

Read this reference only when selecting an outlet, extracting its conventions, or adapting a manuscript to it. `library/journals.jsonl` is a compact outlet registry, not a quality ordering or evidence filter.

## Corpus contract

Freeze the outlet, article type (empirical, theory, structural, review), publication window, search cutoff, sample rule, access route, and output path. Use official author instructions for submission rules and lawfully accessible articles or author manuscripts for observed conventions. Preserve DOI/URL, year, article type, access date, and exact section/page locator. Never bypass access controls or store copyrighted full text in this repository.

Sample across authors, topics, and issues. Do not infer a stable convention from one paper, an editor's article, or a special issue. Separate required rules from recurring patterns and paper-specific choices. Mark sparse or conflicting evidence rather than filling gaps.

## Distill, do not imitate

Following the source-grounded profile pattern used by [Distilly](https://github.com/titanwings/distilly), convert observations into a compact, reusable outlet profile while keeping evidence and inference separate. Record:

- source manifest and coverage limitations;
- article archetypes and recurring section order;
- introduction moves: motivation, question, design or model, findings, contribution, literature placement, roadmap;
- how identification, assumptions, mechanisms, counterfactuals, robustness, limitations, and external validity are surfaced;
- placement and role of propositions, proofs, tables, figures, appendices, data/code statements, and policy discussion;
- paragraph, signposting, terminology, citation, and uncertainty conventions;
- each inferred rule's support count, exceptions, confidence, and source locators.

Store the result as `research/journal-profile-<outlet>.md`; keep raw papers outside the active context. A convention is `high` confidence only when it recurs across independent articles and is consistent with official guidance, `medium` when recurrent but heterogeneous, and `low` when tentative. Update profiles by appending new evidence and revising confidence; preserve contradictions and the prior profile in version control.

Do not reproduce distinctive sentences, metaphors, or an individual author's voice. Paraphrase observations, quote only what is necessary under applicable limits, and use the profile to match genre-level architecture, information order, clarity, and evidentiary discipline.

## Apply and validate

Apply constraints in this order: official submission rules; research validity through the merit gates in [manuscript.md](manuscript.md); verified outlet conventions; author preference. Load only the profile sections needed for the current manuscript stage.

After drafting, map every applied convention to a profile rule, then test whether adaptation hid assumptions, compressed limitations, changed claims, or promoted exploratory findings. If so, restore the defensible statement. An outlet profile improves fit; it never establishes identification, truth, novelty, or acceptance probability.
