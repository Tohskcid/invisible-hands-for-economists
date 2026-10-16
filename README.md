# Invisible Hands for Economists

An auditable economics-research skill that turns a research question into an evidence-backed empirical, theoretical, or structural manuscript. It uses tool-acquired literature and data, a provenance graph, design-specific validity checks, competing-mechanism tests, reproducible result bindings, and adversarial review. A failed hard gate returns the research process to the relevant stage instead of allowing unsupported prose.

## Research flow

```mermaid
flowchart TD
    subgraph Scope["1. Research Question and Contribution"]
        Q["One-sentence research question"] --> BL["Baseline literature search"]
        Q --> FL["Frontier search<br/>new and low-citation work"]
        BL --> CP1{"Researcher checkpoint<br/>scope and contribution"}
        FL --> CP1
        CP1 --> RC["Research contract<br/>outlet, estimand, budget, stop rule"]
    end

    subgraph Design["2. Method and Evidence Obligations"]
        RC --> MODE{"Research mode"}
        MODE -->|Empirical| E["Identification design<br/>data and inference"]
        MODE -->|Theory| T["Definitions, assumptions<br/>proof obligations"]
        MODE -->|Structural| S["Moments, solver<br/>identification and holdout"]
        E --> CP2{"Researcher checkpoint<br/>design and data lock"}
        T --> CP2
        S --> CP2
    end

    subgraph Iteration["3. Bounded Research Iteration"]
        CP2 --> ACQ["Tool-acquired evidence<br/>sources, licenses, hashes"]
        ACQ --> RUN["Reproducible analysis<br/>tables, figures, proofs"]
        RUN --> MC["Mechanism challenge<br/>alternatives and falsification"]
        MC --> LEDGER[("Append-only research ledger<br/>provenance and result bindings")]
        LEDGER --> G{"Deterministic audit gates"}
        G -->|fail| FAIL["Classify failure stage"]
        FAIL --> DREAM["Dream-RSI policy<br/>recommend next bounded action"]
        DREAM --> ACQ
        FAIL -->|material scope change| CP2
    end

    subgraph Delivery["4. Delivery and Adversarial Review"]
        G -->|pass| COV["Manuscript coverage<br/>claim-evidence graph"]
        COV --> AR["Adversarial review<br/>identification, mechanism, data"]
        AR --> RA["Replication and layout audit<br/>master script and rendered PDF"]
        RA -->|fail| FAIL
        RA -->|pass| M["Verified manuscript<br/>and replication package"]
    end
```

Core guarantees:

- New and low-citation work remains eligible through separate frontier-search lanes.
- Model memory is not accepted as literature or data evidence.
- Quantitative claims require hash-bound data provenance and generated results.
- Research outputs must be separated into purpose-named folders for manuscripts, references, PDFs, figures, tables, code, data, models, and audit artifacts.
- Identification and economic mechanisms are audited separately.
- Formal claims distinguish paper proofs, proof sketches, and Lean-verified theorems.
- Manuscript delivery requires complete section coverage, central-claim review, and rendered LaTeX inspection.

## Dream-RSI iteration

The optional Dream-RSI loop learns which action kinds most effectively resolve each failed research stage. It uses append-only discovery histories and deterministic package-gate progress as feedback. Coefficients, p-values, effect direction, and agreement with researcher intuition never enter the policy reward.

```bash
# Learn/update a stage-conditioned policy from prior trajectories
python3 scripts/dream_replay_simulator.py \
  --tree research/discovery_tree.jsonl \
  --policy-out research/dream-policy.json

# Run a bounded online loop through an explicit action adapter
python3 scripts/dream_replay_simulator.py --online \
  --tree research/discovery_tree.jsonl \
  --policy research/dream-policy.json \
  --actions research/dream-actions.json \
  --adapter scripts/research_action_adapter.py \
  --root . --config research/package.json \
  --max-steps 10 --max-cost 50
```

See [Dream-RSI research iteration](references/dream_rsi.md) for the action and adapter contracts. Online execution stops on package completion, budget exhaustion, a block, or a researcher checkpoint.

## Skill, MCP, and one-shot execution

The [Agent Skill](SKILL.md) directs the research agent from the initial question through sources, analysis, manuscript, review, and release. The [execution guide](references/workflow_execution.md) defines the frozen contract and repeated `next_tasks` loop. The Python runner checks artifacts; it does not generate scholarly evidence on its own.

For clients that support MCP, install the optional `mcp` dependency (Python 3.11+) and launch a local stdio server bound to one project:

```bash
uv run --no-project --with 'mcp>=2,<3' python scripts/econ_mcp_server.py --root /absolute/path/to/research-project
```

The server exposes `project_status`, `audit_package`, `run_workflow`, and `run_iteration`, plus the `econ://workflow` resource and `research_question` prompt. `run_iteration` executes only declared `research/dream-actions.json` commands. A stopped action retains an in-flight receipt and is not blindly rerun. Configure the MCP host with the absolute path to `scripts/econ_mcp_server.py` and a project-specific `--root`.

Full manuscript profiles now require a PI-accepted [multi-agent handoff report](references/team_workflow.md), an independent substantive review, and a limitations section. Empirical, descriptive, structural, and replication research rejects proxy datasets whenever data is declared. Simulation is reserved for theory validation or isolated engineering tests. A failed workflow returns `rework_plan` with the earliest stage to revisit and the downstream stages to regenerate. These checks verify declared artifacts and reviewer records; the host agent must actually dispatch and supervise the researchers.

## Install

### Codex

```bash
codex plugin marketplace add Tohskcid/invisible-hands-for-economists --ref main
codex plugin add invisible-hands-for-economists@invisible-hands
```

### Claude Code

```bash
claude plugin marketplace add Tohskcid/invisible-hands-for-economists
claude plugin install invisible-hands-for-economists@invisible-hands
```

### Google Antigravity

```bash
agy plugin install https://github.com/Tohskcid/invisible-hands-for-economists
```

Direct skill installations remain supported:

```bash
git clone https://github.com/Tohskcid/invisible-hands-for-economists.git \
  "$HOME/.agents/skills/econ-research-lab"

git clone https://github.com/Tohskcid/invisible-hands-for-economists.git \
  "$HOME/.claude/skills/econ-research-lab"

git clone https://github.com/Tohskcid/invisible-hands-for-economists.git \
  "$HOME/.gemini/config/skills/econ-research-lab"
```

## Core tools

| Tool | Purpose |
|---|---|
| `search_literature.py` / `check_topic_survey.py` | Acquire current literature evidence and gate contribution claims |
| `check_data_provenance.py` | Verify source, license, schema, acquisition, and hashes |
| `check_design_audit.py` / `check_mechanism_audit.py` | Challenge identification and claimed channels |
| `validate_research_manifest.py` / `audit_claims.py` | Validate the provenance and argument graph |
| `check_result_bindings.py` | Bind manuscript numbers to generated results |
| `check_manuscript_coverage.py` / `check_logic_review.py` | Gate section completeness and central claims |
| `check_lean_proof.py` | Verify locked Lean statements, proof terms, and axioms |
| `check_latex.py` | Compile, inspect logs, render, and bind visual review |
| `check_project_layout.py` | Block delivery when research artifacts are mixed or outside purpose-named folders |
| `check_research_package.py` | Run all applicable delivery gates and return failed iteration stages |
| `run_replication.py` / `run_research_workflow.py` | Replay generated results in a temporary copy and orchestrate frozen-contract delivery checks |
| `econ_mcp_server.py` | Expose those checks and bounded iteration through a local MCP server |
| `check_research_team.py` / `check_substantive_review.py` | Check multi-agent handoffs, independent review, and stated limitations |
| `dream_replay_simulator.py` | Learn a safe research-action policy and run bounded online iterations |

## Verify

```bash
python3 -m unittest discover -s tests -q
python3 scripts/validate_library.py --json
uvx --from skills-ref agentskills validate skills/econ-research-lab
uv run --no-project --with 'mcp>=2,<3' python -m unittest tests.test_mcp_server
```

## Research roadmap

See the [harness optimization research plan](docs/research/harness-optimization-plan.md) (Traditional Chinese) for the proposed implementation work packages, controlled evaluation, milestones, and acceptance criteria grounded in the reconstruction pilot.

The [workflow implementation status](docs/research/workflow-implementation-status.md) records the engineering changes, five synthetic experiments, failed research gates, and remaining work toward one-shot paper completion.

MIT Licensed.
