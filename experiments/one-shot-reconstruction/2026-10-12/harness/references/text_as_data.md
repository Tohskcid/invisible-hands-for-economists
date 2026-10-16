# Text-as-Data & LLM Annotation Audit Protocol

Read this reference when generating, classifying, or extracting economic variables from unstructured text (e.g., SEC 10-K disclosures, central bank minutes, earnings calls, news articles, patent abstracts, or regulatory filings) using Large Language Models (LLMs) or NLP methods.

Do not treat an LLM as an unobservable oracle. Econometric validity requires that text-derived variables satisfy the same transparency, measurement validity, and replication standards as quantitative microdata.

---

## 1. Deterministic Reproducibility Contract

Economics research requires exact computational reproducibility:
1. **Model Snapshot Pinning**:
   - Never use unversioned floating tags (e.g., `gpt-4o`, `claude-3-sonnet`, `gemini-pro`).
   - Always lock the exact dated snapshot identifier (e.g., `gpt-4o-2024-08-06`, `claude-3-5-sonnet-20241022`).
2. **Zero Temperature**:
   - `temperature = 0.0` is strictly required. Any stochasticity in classification introduces measurement error that correlates with batch ordering.
3. **Prompt Template Hash Binding**:
   - System prompt, user prompt template, and few-shot exemplars must be version-controlled in `prompts/`.
   - Record the SHA-256 hash of the exact prompt file in `research/text-audit.json`.

---

## 2. Human Gold-Standard & Inter-Coder Reliability

Never include an LLM-annotated variable in empirical regressions without establishing its inter-coder reliability against trained human domain experts:
1. **Sample Size**:
   - A minimum of **100 randomly sampled text units** (stratified across time and industry) must be independently annotated by human coders.
2. **Substantial Agreement Thresholds**:
   - For categorical/binary labels: **Cohen's Kappa ($\kappa \ge 0.70$)** or **Krippendorff's Alpha ($\alpha \ge 0.70$)** (substantial agreement under Landis & Koch 1977).
   - For continuous scores: Pearson correlation $r \ge 0.85$ and Spearman rank correlation $\rho \ge 0.85$.
   - For extraction tasks: Precision, Recall, and F1-score $\ge 0.85$.
3. **Audit Artifact**:
   - Store the side-by-side human and LLM annotations in `research/text_gold_sample.jsonl` with an immutable SHA-256 checksum.

---

## 3. Mandatory Diagnostics Battery

`research/text-audit.json` must record and pass the following 5 diagnostics:

| Diagnostic ID | Validation Obligation | Rejection Condition |
|---|---|---|
| `inter-coder-reliability` | Human vs. LLM concordance on stratified gold sample | $\kappa < 0.70$ or $\alpha < 0.70$ |
| `prompt-drift-invariance` | Invariance to trivial phrasing variations or exemplar reordering | Classification changes for $> 5\%$ of benchmark queries |
| `deterministic-temperature` | Exact token match across repeat runs on a test subsample | Any non-identical output at $T=0$ |
| `hallucination-rate` | Verification that extracted entities, dates, or numbers exist verbatim in source text | Unsupported entity rate $> 1\%$ |
| `context-window-truncation` | Confirmation that documents do not exceed maximum context length | Silent truncation of long filings |

---

## 4. Text Audit Artifact Schema

Save the audit record to `research/text-audit.json`:

```json
{
  "schema_version": "1",
  "task_description": "Classifying corporate climate risk transition commitments in SEC 10-K Item 1A",
  "model_version": "gpt-4o-2024-08-06",
  "temperature": 0.0,
  "prompt_template": "prompts/climate_risk_extraction_v1.txt",
  "prompt_sha256": "3b2e7a...",
  "human_audit": {
    "sample_size": 250,
    "coder_count": 2,
    "metric": "cohen_kappa",
    "score": 0.84,
    "artifact": "research/climate_gold_audit.jsonl",
    "artifact_sha256": "d4f8a1..."
  },
  "diagnostics": [
    {
      "id": "inter-coder-reliability",
      "status": "pass",
      "finding": "Cohen kappa of 0.84 on 250 stratified 10-K extracts",
      "artifact": "research/climate_gold_audit.jsonl",
      "artifact_sha256": "d4f8a1..."
    },
    {
      "id": "prompt-drift-invariance",
      "status": "pass",
      "finding": "Exemplar permutation check yielded 98.4% label stability",
      "artifact": "research/prompt_drift_check.json",
      "artifact_sha256": "e5c2b9..."
    },
    {
      "id": "deterministic-temperature",
      "status": "pass",
      "finding": "100% token identity across 3 repeated runs at T=0",
      "artifact": "research/determinism_check.json",
      "artifact_sha256": "f6a3c1..."
    },
    {
      "id": "hallucination-rate",
      "status": "pass",
      "finding": "Zero fabricated targets across 250 audited sentences",
      "artifact": "research/hallucination_check.json",
      "artifact_sha256": "7a9b3d..."
    },
    {
      "id": "context-window-truncation",
      "status": "pass",
      "finding": "All Item 1A chunks stayed below 12,000 tokens",
      "artifact": "research/truncation_check.json",
      "artifact_sha256": "8c4d2e..."
    }
  ]
}
```

---

## 5. CLI Verification Gate

Validate the audit record before delivery:

```bash
python3 scripts/check_text_audit.py research/text-audit.json \
  --root . --require-pass --json
```

A failed or missing text audit blocks the quantitative research package whenever LLM-derived variables are used in the manuscript.
