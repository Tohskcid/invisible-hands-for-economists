# One-shot reconstruction experiment

This pilot tests the current working-tree harness against two historical research questions from journals in `library/journals.jsonl`. The two workers receive a research question, the target outlet and a fixed experiment contract. They do not receive the original title, authors, original analysis code or published results. Source discovery is permitted and accidental exposure is logged. Both classic cases are susceptible to model-memory contamination.

The harness is copied without modification to `harness/`; `research/harness-snapshot.json` hashes every copied source. The empirical worker writes only `attempt/`; the theory worker writes only `attempt-theory/`. The evaluator keeps paraphrased publication facts in `holdout/`, which workers are instructed not to read. Isolation is instruction-based because agents share the filesystem. Copyrighted source PDFs are temporary and excluded from Git.

An attempt is not successful merely because the text is polished or the configurable package gate returns valid. Evaluation distinguishes independent execution, fidelity to the publication, complete manuscript coverage, actual gate results, reproducibility, and source/memory leakage.

## Files

- `research/protocol.json`: empirical task and frozen evaluation rules.
- `research/protocol-theory.json`: theoretical task and frozen evaluation rules.
- `research/harness-snapshot.json`: working-tree source hashes.
- `research/run-manifest.json`: agent/context/budget/isolation record.
- `attempt/`: empirical reconstruction artifacts.
- `attempt-theory/`: theoretical reconstruction artifacts.
- `holdout/`: evaluator-only original-paper facts and coverage obligations.

The final [evaluation report](report.md) and [scorecard](research/scorecard.json) record completed outputs and every remaining gate or input gap. Both cases achieved core reconstruction but neither achieved full original-paper recovery or all-gate delivery. The run was interrupted and resumed; no uninterrupted one-shot success is claimed. No general success rate over the ten journals can be estimated from two historical cases.
