# Paper collection and benchmark curation

Use when asked to read economics papers and automatically prepare bounded research tasks without revealing their answers. The curator reads the answers; it must not later act as the reconstruction author. Use the existing [historical protocol](../experiments/new-topic-blind/PROTOCOL.md) for dates, contamination, sealing, and evaluation.

## Collect before reading

With a collected catalog, build a private list of licensed PDF locations and record what each provider actually supplies. The first command queries Crossref/OpenAlex metadata, the second checks NIH/NLM PubMed Central, and the third fetches the eligible PDFs. Repeating the commands reuses local receipts. PubMed Central author manuscripts, journal editions and supplemental files have separate version records.

```sh
python3 scripts/queue_open_papers.py --catalog /private/catalog.json --out /private/acquisition index
python3 scripts/collect_pmc_sources.py --catalog /private/catalog.json --acquisition /private/acquisition
python3 scripts/queue_open_papers.py --catalog /private/catalog.json --out /private/acquisition acquire
```

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

## Batch reading and release

Use a private directory outside every author workspace. The batch reader uses installed Codex with its existing account and Poppler’s `pdfinfo`, `pdftotext`, and `pdftoppm`. Each entry in `candidates.json` represents an identified original whose version and appendix inventory a curator has checked. The catalog and download receipts alone do not establish these facts. Use relative paths inside the private directory and choose a neutral ID such as `q001`.

```json
{
  "cases": [{
    "id": "q001",
    "mode": "theory",
    "target": {"title": "Verified title", "authors": ["Full author name"], "doi": "10.…"},
    "sources": [{
      "id": "article", "role": "main", "file": "originals/q001.pdf",
      "sha256": "<64 hex digits from the verified PDF>", "url": "https://example.org/article.pdf",
      "version": "<edition and pagination>",
      "identity_check": "<how the title, byline, edition, body and end were verified>"
    }],
    "appendix_status": "none",
    "appendix_check": "<where appendices and supplements were checked and what was found>"
  }]
}
```

Use `embedded`, `external`, or `both` for articles with appendices. Add each separately verified PDF with role `appendix` or `documentation`. Record any unresolved material in the inventory. The reader accepts theory, empirical, structural and mixed tasks.

```bash
python3 scripts/read_benchmarks.py /private/collection/candidates.json
```

To prioritize bulk downloads, run `python3 scripts/triage_acquired_papers.py --collection /private/collection/open-acquisition --catalog /private/catalog.json --out /private/collection/content-queue.json`. This local check verifies receipt hashes and captures opening, middle and closing page evidence, edition markers and appendix/data mentions. Scanned pages, repository covers, missing bylines and ambiguous editions are flagged for a curator. No triage category establishes that a paper was read, published in the captured version, or ready for authors.

For each case the reader sends every physical page as a rendered image, together with its complete text layer, to reading sessions in groups of six. It checks for a readable, page-specific note on every page and uses those notes to draft the task, private question-to-page mappings and scoring rubric. Independent review sessions compare the entire packet and rubric with the original pages and every author input. Any page-group hold carries into the aggregate decision. The runner archives the held draft, attempts one source-grounded correction, then obtains fresh page-by-page reviews. A second hold blocks release. Sessions use distinct empty directories without file or search tools. The same model can share prior knowledge across contexts. The substantive judgments and any recognition remain review evidence.

The commands preserve existing case directories and frozen versions. `reader-work/<id>/` caches exact-prompt and rendered-image commitments, responses and turn receipts. Resume an interrupted model call by repeating the reader command. A reviewed draft lives in `cases/<id>/`. Inspect the recorded findings before revising a held draft. Changed frozen cases need a new ID.

### Author inputs and research scope

For empirical and mixed cases, add an `inputs` object to the private candidate. Each key is a neutral author filename such as `inputs/input-001.csv`. Each value supplies a private relative `file`, its `sha256`, and a specific `provenance` statement covering the data, vintage, availability and intended use. The gate streams UTF-8 CSV, TSV, TXT and DAT files for identifier checks. The automatic reviewer receives the complete contents within a limit of 200,000 bytes per input and 200,000 characters per prompt. Larger datasets stay in the inventory for supervised review. An independent reviewer can inspect them with appropriate data tools and sign the same full-file hash and file-specific findings. For other file formats, prepare and validate a neutral, reviewable representation, preserving the source and the conversion receipt privately. Keep unsupported or infeasible inputs recorded as gaps.

Use the appropriate `track` in private records.

| Track | Release evidence |
| --- | --- |
| `packet-only` | Default for a packet with no external inputs. The task must contain the primitives needed for its requested derivations. Any historical priority claim requires separate date evidence. |
| `strict-historical` | Default when data files are supplied. Provide the existing historical protocol’s `timeline` object with both sourced target dates. Every delivered input needs exactly one comparator with `title` equal to its neutral filename and `author_material: true`. Its documented first public date must precede the earliest target date, and it must be independent of the target. |
| `calibration` | Name this track explicitly when using retrospective inputs or only partly feasible data. State data availability in the public `data_access_status`. For each private gap, `calibration.missing_blocks` maps the exact gap string to a retained rubric ID. Record the feasible work in `calibration.feasible_scope`. This keeps unavailable blocks in the full-paper denominator. |

### Independent sign-off and author export

A separate `batch.json` lists the case directories, for example `{"cases":["cases/q001","cases/q002"]}`. It can include manually curated cases. Each contains `public-task.json`, `curation.json`, `review.json`, and the explicitly named author inputs. The public task uses `id`, `mode`, `question`, a flat `conditions` object, `available_inputs`, `required_outputs`, `source_restrictions`, and `neutrality_obligation`. The optional `data_access_status` explains delivered coverage. Free-form extra public fields require a review of the release format.

```bash
python3 scripts/curate_benchmarks.py inspect /private/collection/batch.json
python3 scripts/curate_benchmarks.py freeze /private/collection/batch.json
python3 scripts/curate_benchmarks.py export /private/collection/batch.json --author-root /separate/new-handoff
```

For manual curation, give every source a `reading` array of `{"pages":[first,last],"note":"page-specific reading evidence"}` entries. Use one-based physical PDF pages, including covers and references, and mark embedded appendix entries `"appendix":true`. The union must cover the page count in the actual PDF. In `field_sources`, map `question` and every `conditions.<field>` to `source`, a two-element `pages` span and a concrete `reason` for making that condition public. Include `curator`, `target`, `sources`, `appendix_status`, `appendix_check`, `withheld`, `rubric`, `contamination`, `gaps` and `input_checks` in the private curation. Key `input_checks` by exact author filename. Prefer point-bearing rubric rows with `id`, `criterion`, `max_score`, `scoring`, `source` and `pages` for reproducible fidelity evaluation.

The `inspect` command reports actual SHA-256 digests. After inspecting these exact originals, private record, public task and inputs, the independent reviewer records their actual identity in `reviewer`, a `decision` of `pass` or `hold`, and the digest map in `checked_sha256`. Write concrete `sufficiency` and `leakage` findings and an `input_findings` entry for `public-task.json` and every author input. Check which proofs or estimates can actually be completed from the released information. The gate checks that the bytes still match that review. It cannot establish reviewer independence or judge semantic leakage by itself.

Freeze stores a timestamped receipt, originals, private records and public bytes under `frozen/<id>/`. Repeating freeze accepts identical bytes and rejects changes. Retain the reported receipt hash outside curator write authority to establish an independent commitment. Export verifies the freeze and copies only the public task and its declared inputs to `<author-root>/<id>/`. The author root must be dedicated and outside the checkout and private collection. Give each author access only to their own case through a separate execution environment. A directory on the same unrestricted account provides procedural separation. Batch commands report each case separately and exit nonzero if any case is blocked; eligible siblings can still complete.

## Write, compare, and revise

When the user also asks for a manuscript and comparison, use the verified candidate manifest as the entry point. Keep all working directories private. This runs the reader, independent review, immutable freeze and export, author, then two distinct evaluation sessions for each eligible case.

```bash
python3 scripts/run_reconstruction_batch.py output/study/candidates.json output/study/results
```

The model stages use the existing ChatGPT account. They check its login status and remove API-key environment variables for the subprocess. A blocked run preserves its private checkpoints. The default author sees the task and released files. A paper with no data files gets a single tool-free session in an empty directory. A data-backed paper uses a workspace-write session to run analysis against copies of its inputs. Mount only the exported case on a separate worker for technical read isolation when using research tools. Review the private execution trace and independently replay numerical results before making a replication claim. Finished submissions include their exact inputs and outputs by hash. Repeat the command after remedying a source or resource failure. Existing signed submissions and scores are checked before reuse.

For an experiment, use `scripts/write_from_packet.py FROZEN_CASE EXPORTED_CASE OUTPUT --condition coverage` to add the [coverage instructions](reconstruction_coverage.md). Keep ordinary authoring as the default. In the paired November trial, these instructions alone yielded lower or equal historical coverage on both new tasks. Use a fresh held-out paper to test any proposed author change.

Classify each substantive gap before changing the project. Record the original locator, submitted locator, exact missing claim, and one concrete reason:

- If an essential population, domain, or application was absent from the question, ask the neutral subquestion and independently review a **new** packet.
- If multiple designs, example values, mechanisms or expositions fit the released conditions, retain the historical target in the denominator and record the alternative. Adding the original choice to a prompt requires an independent justification as a necessary condition.
- If a file or appendix is unavailable, document what cannot be recovered. Add a genuine verified input in a new frozen version when it becomes available.
- If the public scope was clear and an author omitted it or made an invalid deduction, test a generic reasoning change separately. Preserve the original author submission, including failures.

Lock standalone quality before revealing original-specific obligations. Compare the resulting manuscript to the journal version and supplements, accepting equivalent correct arguments. Preserve the exact full denominator, critical errors, eligibility, tool exposure and recognition. Only report full substantive recovery for the assessed scope when every item passes, every essential artifact is independently verified, and no critical issue remains. A finite rubric cannot establish that every feature of a paper was uniquely determined by its question.

When a numerical discrepancy affects release or scoring, independently run the calculation on the exact delivered observations and retain the program, file digest, sample definition, published values and recomputed values. In a candidate, an optional private `numeric_audits` entry has `input` (the neutral filename), `file` (the private JSON result) and `sha256` (its digest). The result must contain the exact `input_sha256`. These checks reach the curator, independent release review and historical comparison. They are excluded from the author's packet and standalone quality review.

Automated extraction places target-specific scope only in the research question and source-mapped conditions. The pipeline supplies common deliverable instructions after drafting. This prevents a hidden result from reappearing as an instruction to prove a particular sign, bound or convergence claim. Review the exported bytes and the sealed full-paper rubric for omitted scope after this transformation. Previously frozen packets retain their original instructions.

For a numeric CSV, include a private `columns` dictionary to document the original field, observational role and reason for releasing each column. Tables larger than 200,000 bytes require this dictionary. Keep the neutral codebook among the actual author inputs. The reader checks every cell, row width, header and file hash in a declared numeric table. Reviewers see the dictionary, row count, missingness, ranges and small categorical domains, together with the original pages. They assess whether the observations and coding expose published answers. The complete, unchanged CSV goes to the author after release. Large free-text or mixed-format tables require separate review.
