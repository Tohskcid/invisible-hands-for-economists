# b03 multi-agent historical reconstruction protocol

This experiment tests whether the repo can turn one question from an already-published journal article into a complete, scientifically defensible manuscript. It does not test novelty or actual journal acceptance. The authoring side received only `public-task.json`; the target and five-part, ten-point rubric were sealed and SHA-256-committed in `public-hashes.json` before authoring.

The native agents and non-overlapping roles are:

- `/root/b03_benchmark_curator`: choose a journal-registered published target, obtain its full article and appendix, lock the question and rubric. It does not research or write the submitted paper.
- `/root/b03_literature`: search and verify non-target primary literature; store source hashes, closest-work risk, and a safe citation handoff. Its accidental target search-result exposure is quarantined and may not enter the author handoff.
- `/root/b03_model`: independently formalize the question, prove or flag propositions, test boundary cases, and provide `research/model/handoff.md`.
- `/root/b03_writer`: write the complete LaTeX manuscript and PDF from the public question, safe literature handoff, and model handoff. It may not inspect the target or rubric.
- Independent referee: to be dispatched only after manuscript hashes are frozen; it must not have participated in research or writing and reviews the submission before unsealing.
- `/root` (PI): coordinate, freeze the contract and submission, audit agent handoffs, run repo workflow, ensure rejected or unresolved gates are reported rather than waived.

The wall-clock experiment budget is 1,200 seconds from `run-start.json`. The target is a published article, so any ordinary novelty approval is expected to be blocked when the target is revealed. Author-side blindness is instruction-based on a shared filesystem; it is not a technical access guarantee. The scoring agent will inspect sealed material only after the manuscript and independent review are frozen. All exposures, failures, version changes, and scoring decisions remain in this directory.
