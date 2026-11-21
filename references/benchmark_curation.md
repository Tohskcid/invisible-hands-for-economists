# Paper collection and benchmark curation

Use when asked to read economics papers and automatically prepare bounded research tasks without revealing their answers. The curator reads the answers; it must not later act as the reconstruction author. Use the existing [historical protocol](../experiments/new-topic-blind/PROTOCOL.md) for dates, contamination, sealing, and evaluation.

## Collect before reading

Start with the five general economics journals in `scripts/collect_papers.py`; do not restrict subject areas or citation counts. This is an initial source list, not a claim to cover all economics journals. Crossref journal-article records include corrections and other non-research items: verify article identity, publication status, and amendments before admitting a benchmark.

```bash
python3 scripts/collect_papers.py --out output/paper-corpus discover \
  --from-year 2024 --to-year 2024 --pages 1 --rows 100
```

Repeat the command to continue saved cursors. Each invocation has a page limit per journal/year. `catalog.json` holds DOI-deduplicated metadata, per-query progress and raw-response hash receipts; `raw/` holds source responses. A lock prevents simultaneous writers. An interrupted request leaves its last checkpoint intact. A remote cursor may expire: start a separate output directory for that query and reconcile by DOI; never silently mark it complete. Historical publication dates can change in the provider; this is a captured candidate inventory, not proof of exhaustive coverage.

Select a public full-text URL after checking the publisher or author source, then acquire it explicitly:

```bash
python3 scripts/collect_papers.py --out output/paper-corpus acquire \
  --doi DOI --url PUBLIC_HTTPS_PDF_URL
```

The downloader rejects HTML, limits response size, hashes PDFs and verifies its cache. It does not certify the PDF's identity, license, completeness or contents. Full-text links in Crossref are discovery candidates, not permission to crawl a publisher. Record inaccessible sources; do not bypass authentication or reuse HPC credentials on publishers. Only public URLs without credentials or access tokens belong in the catalog. Full text remains in ignored `output/` or an external private curator workspace, never in the author's checkout or Git.

The script uses Python's standard library and the existing metadata normalizer. It can run on Linux HPC or macOS without GPUs. Use SSH keys, an interactive SSH prompt, or an existing credential manager for remote execution; never embed credentials in scripts, command arguments, job files, logs or this repository. A university compute account does not establish access or bulk-download rights to journal content. Follow [Crossref's API guidance](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/).

## Meta-analyses for selecting research directions

Search the journal catalog and relevant field journals for quantitative syntheses. Record the DOI, scope and inclusion criteria, empirical units and outcome definition, whether estimates from a single study are dependent, and a concrete question suggested by heterogeneity or missing evidence. Distinguish meta-regressions from narrative reviews and editorial discussions. Date each source against the earliest target version and check whether it cites or reveals the target. Keep later syntheses in the curator’s direction notes. They may motivate future tasks but never supply the target effect, a success threshold, or material for historical authors.

## Read and extract

1. Read the entire main text, relevant appendices, and data documentation using [PDF ingestion](pdf_ingestion.md). Log the exact version, hashes, pages read and missing supplements privately. Abstracts and old benchmark summaries cannot substitute for reading. Missing necessary material makes the task draft or blocked.
2. Extract the actual bounded question: place, time, population, institutional setting, policy exposure, outcomes and available data. For theory, extract primitives, information, feasible actions and the problem to solve. Do not invent geographic or data restrictions when none apply.
3. Separate necessary task boundaries from the author's solution. Keep effect signs, estimates, theorem conclusions, optimal mechanisms, proof strategies and selected estimating specifications private. Data coverage is public context; the final estimation sample or outcome-driven exclusions may reveal the solution. Do not turn a result into an assumption. Retain identifying context essential to the question and record the resulting recognizability risk instead of making the question vague.
4. For every public condition, privately record its source page/label and why it is needed. Distinguish source facts, curator choices and unresolved ambiguity. Do not assume that named data are accessible or that a current data vintage existed before the historical cutoff.

## Two outputs, one handoff

Use a neutral task ID and the existing `public-task.json` convention. Include `question`, `mode`, a `conditions` object (place, period, population, institutions, data or primitives), `available_inputs`, `required_outputs`, `source_restrictions`, and `neutrality_obligation`. Record actual input availability. Add the research budget only when assigned; curation is not authorization to start research. Avoid target title, authors, DOI, answer-bearing filenames or target URLs in the author packet.

Keep `sealed/curation.json` separately: target identity and source receipts; reading coverage; field-to-page mappings; omitted answers; data gaps; evaluation obligations and tolerances; contamination; and review findings. An output folder called `sealed` is only procedural separation, not access control. Store it outside the author's mounted workspace for technical isolation. Hash and timestamp the final public packet and sealed records before dispatch; never overwrite an earlier frozen task.

Before release, independently review both sufficiency and leakage: could another researcher formulate the task from the public packet, and does any sentence supply an answer or a privileged solution step? Use a fresh reviewer when available; that reviewer also must not become the author. Record the review's actual identity and findings. A word filter or JSON validator cannot establish semantic answer-freedom. Do not release a draft as reviewed.

For full-paper reconstruction, keep all required research blocks in the rubric. Missing data can block a block, but does not authorize silently narrowing the target. Report reconstruction fidelity and independent scientific validity separately. Published acceptance is a reference-quality signal, not a certificate that every result is correct.

## Invocation

“Read these papers completely and curate benchmark tasks using benchmark_curation.md. Preserve the concrete research question and resource constraints. Write the public task and private source mappings separately, check sufficiency and answer leakage, and stop before starting an author agent.”

The collector automates acquisition and provenance. Full reading, extraction and semantic review are agent work under this protocol; downloading a PDF does not perform them.
