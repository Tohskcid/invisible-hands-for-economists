# Reproduction and interpretation

Authoritative source: `paper/manuscript/main.tex`. Bibliography: `paper/references/references.bib`. Fixed harness scripts remain outside the attempt at `../harness/scripts`.

Run `python3 scripts/verify_and_package.py` from any directory for exact rational falsification checks and hash-bound claim/coverage metadata. It only writes within this attempt; it adds source-only claim comments for the unchanged strict-numbers checker. The finite checks are not proofs. Do not rerun it after independent review without refreshing that review's hashes.

The successful local compile used the actual unchanged checker with `--engine pdflatex`, build `build/latex-build`, render `build/latex-pages`, report `research/latex-report.json`. Child-process environment: `openout_any=r`, `SOURCE_DATE_EPOCH=1791763200`, `FORCE_SOURCE_DATE=1`. The first setting permits BibTeX to write its own absolute `.blg` path selected by the harness; no global TeX setting was edited. The date settings make output metadata reproducible. `lmodern` was already installed. There were no installs, downloads requiring payment, or changes to the fixed harness.

The as-is `openout_any=p` build failed and is retained in `research/latex-as-is-failure.json`; the earlier observed failures are in `research/latex-build-history.json`. A compatibility-assisted pass does not erase those observations. There is no overfull-limit waiver.

Run `python3 scripts/run_gates.py` to preserve actual manifest, claim, coverage, layout, literature and survey reports. Once fresh referee files exist, it additionally runs hash-bound logic and visual finalization and the complete package checker. Package failure caused by missing/forbidden literature is an observed gate result, not a reason to fabricate evidence.

Lean/lake are unavailable and no externally locked theorem task was supplied. The document is human-readable mathematics only. Proof completeness is subject to the actual independent review; graph, checksum and finite numeric passes alone do not validate a theorem.
