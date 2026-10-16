# Replication package

This package independently computes employment changes around New Jersey's 1992 minimum-wage increase using the producer's public restaurant survey data. It is a bounded historical reconstruction with disclosed source exposure and unresolved causal assumptions; it is not an uninterrupted blind-discovery success or a submission-ready causal study.

Run `python3 scripts/run_all.py` from this directory. The master verifies raw hashes, builds the processed dataset, estimates the frozen specifications and bootstrap, verifies the primary calculation in base R, generates all tables/figures and the full manuscript, and executes the unchanged sibling `../harness/scripts` gates. A nonzero final exit code is expected while substantive identification or literature gates remain blocked; computed output is preserved and every actual return code appears in `research/gate-results.json`.

The supplied snapshot needs the versions in `requirements.txt`, base R, pdfLaTeX/BibTeX, and Poppler. No dependency installation is performed. Computation is deterministic with seed 19920401 and takes seconds; compilation and page rendering take longer. `openout_any=a` is set for BibTeX's absolute scratch-build output path, while the harness keeps shell escape disabled and retains all typesetting checks. A standalone quantitative rerun uses `python3 scripts/analyze.py`; the full delivery audit also needs the unchanged sibling harness and fresh review artifacts.

The data are publicly offered at https://davidcard.berkeley.edu/data_sets.html, linking `njmin.zip`. The raw factual records, codebook, readme, and survey instruments are consumed. The archive's original SAS program is never extracted or read. Acquisition uses an existing hash-checked cache or a public HTTP download, and raw inputs are never cleaned in place. No express redistribution license is supplied by the producer; public download access is verified, but this package grants no new license for republishing it.

Source `sheet` is not unique: two distinct rows share the value 407. The parser preserves all source rows and creates `row_id`. FTE headcount equals full-time nonmanagers plus managers plus half of part-time nonmanagers; all components must be observed. Permanent closures already contain recorded zeros after closure. Temporarily missing counts remain missing. The primary sample is 384 complete pairs, with no weighting.

| Exhibit | Generator | Artifact |
| --- | --- | --- |
| Employment means | `scripts/analyze.py` | `output/tables/means.tex` |
| Main regressions | `scripts/analyze.py` | `output/tables/main.tex` |
| Sensitivity variants | `scripts/analyze.py` | `output/tables/robustness.tex` |
| Auxiliary outcomes | `scripts/analyze.py` | `output/tables/outcomes.tex` |
| Employment figure | `scripts/analyze.py` | `output/figures/employment.pdf` |
| Starting wage figure | `scripts/analyze.py` | `output/figures/wages.pdf` |
| Full manuscript | `scripts/build_package.py` | `paper/manuscript/main.tex` |
| PDF/pages | Fixed `check_latex.py` | `output/pdf/main.pdf`, `output/figures/pages/` |

The displayed estimates are bound to `research/results.json`; `research/results-detail.json` retains a nested presentation of the same outputs. Manifest, section packets, provenance, source-access records, actual checker results, and contamination audit are in `research/`. The `.tex` manuscript contains the complete prose, derivations and generated tables; the two figures are separate PDF assets. No payroll validation, pretrend series, long-run outcome, welfare calculation, or statewide randomization inference is available.
