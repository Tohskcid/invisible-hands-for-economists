# Project layout and literature archive

Read this reference before creating a multi-file deliverable or acquiring cited papers. Reuse a clear existing project convention; otherwise use this compact layout:

```text
paper/                  manuscript sources and bibliography
literature/papers/      lawfully obtained cited PDFs
literature/metadata/    optional source or access records
data/{raw,interim,processed,proxy}/
scripts/{acquire,clean,analyze}/
output/{tables,figures,models}/
research/               contracts, manifests, audits, ledgers, reports
research/sections/      compact evidence-backed manuscript section packets
```

Do not put generated data, PDFs, tables, figures, logs, or draft variants in the project root. Keep one authoritative manuscript path; use version control or immutable run IDs rather than `final`, `final2`, or duplicated copies. Put temporary compilation and extraction files in an ignored build directory or an OS temporary directory. Record the final path of every material artifact in the research manifest or package config. Do not move user files or replace an established layout merely to match these names; map equivalent existing directories to the same categories and keep new outputs consistent.

Before delivery, enforce this rule with:

```bash
python3 scripts/check_project_layout.py --root . --json
```

The research-package gate runs this check automatically whenever `manuscript` or `latex_main` is declared. A failure returns to `artifact_organization`; reorganize or regenerate the files, then rerun the package rather than waiving the failure. Equivalent purpose-named folders such as `docs/`, `figure/`, `src/`, and `latex/` are accepted for established projects.

## Cited-paper archive

Before manuscript delivery, enumerate every BibTeX entry or `\bibitem` key. For each citation, verify metadata against the DOI, publisher, or authoritative repository, then search for a lawful full text in this order: publisher open-access copy, official working-paper or institutional repository, then author-hosted manuscript. Never bypass authentication, paywalls, robots controls, or license restrictions.

Download available PDFs with an actual browser, repository, or HTTP tool call. Reject HTML error pages saved as `.pdf`; verify the PDF signature and open or render at least the first page. Save each file as:

```text
literature/papers/<normalized-citekey>--<normalized-short-title>.pdf
```

Use lowercase ASCII, hyphens, and no spaces. Do not rename two editions as though they were identical; keep the cited edition and record its version. Create `research/literature-archive.json` with one record per bibliography key containing authors, title, year, canonical locator, verification time, license or lawful access basis, access status, and—when downloaded—the download locator, retrieval time, path, and SHA-256. If no lawful copy is available, record `unavailable` or `restricted` plus the verified reason; do not fabricate a PDF or omit the citation from the audit.

Validate coverage, names, file signatures, and checksums with:

```bash
python3 scripts/check_literature_archive.py research/literature-archive.json \
  --bibliography paper/references.bib --root . --require-complete --json
```

Use the manuscript itself as `--bibliography` when it contains `\bibitem` entries. Omit `--require-complete` only when the deliverable explicitly permits a documented access gap; the report will remain valid but `complete: false`. Keep copyrighted PDFs out of Git unless their license permits redistribution; the local archive may be complete even when Git contains only its metadata manifest.
