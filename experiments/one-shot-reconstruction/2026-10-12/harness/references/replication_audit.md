# Replication Package Audit (AEA Standard)

Read this reference when assembling, auditing, or verifying an empirical replication package. Conforms to the American Economic Association (AEA) Data and Code Availability Policy and standards enforced by top-tier economics journals.

---

## 1. Replication Package Checklist

An evidence package is marked `replication-ready` only if it satisfies all six core verification gates:

```
[ ] 1. Master Script: A single master script runs the entire pipeline end-to-end.
[ ] 2. Relative Paths: Zero machine-specific absolute paths in any code file.
[ ] 3. Environment & Seed: Deterministic random seeds and locked dependency manifests.
[ ] 4. Data Separation: Raw data immutable and separated from generated data.
[ ] 5. Table/Figure Mapping: 1-to-1 mapping from manuscript outputs to code scripts.
[ ] 6. Replication README: Comprehensive documentation following the AEA template.
```

---

## 2. Technical Standards

### A. Single Master Execution Entry
The package must provide a single non-interactive entry point:
- **Bash / Linux / macOS**: `run_all.sh`
- **Stata**: `master.do`
- **R**: `main.R`
- **Python**: `run_all.py`

Running this single command must execute:
1. Data cleaning & verification of raw checksums;
2. Estimation & diagnostic tests;
3. Output generation for all manuscript tables and figures.

### B. Path Hygiene
- Audit every code script using grep to confirm absence of absolute directories (e.g., `grep -rE "(Users/|home/|[A-Z]:\\\\)" .`).
- All scripts must reference files relative to the repository root directory.

### C. Random Seed & Dependency Locking
- Every stochastic procedure (bootstrap, permutation test, cross-fitting in DML, simulated method of moments) must declare a fixed seed before execution.
- Include lockfiles:
  - Python: `requirements.txt` or `uv.lock` / `pyproject.toml`
  - R: `renv.lock`
  - Stata: `setup_stata_packages.do` documenting exact `ssc` or `net` versions.

### D. Data Immutability and Provenance
- `data/raw/`: Store unmodified source data as read-only. Record SHA-256 checksums in `data/raw/checksums.sha256`.
- `data/clean/` or `data/processed/`: Store intermediate derived datasets generated exclusively by code.
- If data is confidential, proprietary, or too large to host, provide a formal Data Availability Statement (DAS) detailing exact acquisition steps, application URLs, and contact info, accompanied by synthetic or mock data that allows the code pipeline to run.

### E. Code-to-Artifact Mapping Table
The replication package must document the origin of every output:

| Exhibit in Paper | Generating Script | Output Artifact | Expected Runtime |
| --- | --- | --- | --- |
| Table 1: Summary Statistics | `scripts/01_clean_data.py` | `output/tables/table1.tex` | ~1 min |
| Table 2: Main Estimates | `scripts/02_estimate_did.R` | `output/tables/table2.tex` | ~5 mins |
| Figure 1: Event Study | `scripts/03_event_study.R` | `output/figures/figure1.pdf` | ~2 mins |
| Table A1: Placebo Tests | `scripts/04_falsifications.R` | `output/tables/tableA1.tex` | ~10 mins |

---

## 3. Standard `README_replication.md` Template

Generate `README_replication.md` in the project root:

```markdown
# Replication Package for: [Paper Title]

## Overview
This package contains code and documentation to replicate the empirical results in [Paper Title].

## Data Availability Statement
- [ ] The data used in this paper are publicly available and included in this repository.
- [ ] The data used in this paper are proprietary/confidential. Access instructions are detailed in section "Data Sources".

## Computational Requirements
- Software: [e.g., R version 4.3.0, Stata version 18, Python 3.11]
- Memory & Hardware: [e.g., standard PC with 16GB RAM]
- Total Estimated Run Time: [e.g., approximately 15 minutes]

## Instructions for Replicators
1. Ensure dependencies are installed (see `renv::restore()` or `pip install -r requirements.txt`).
2. Run `bash run_all.sh` (or `stata -b do master.do`).
3. Replicated tables will be written to `output/tables/` and figures to `output/figures/`.
```
