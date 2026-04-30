# CLAUDE.md — `claude-prompts-analysis`

## What this repo is

Quantitative linguistic analysis of the **287-file `claude-code-system-prompts`** corpus (Piebald-AI's reverse-engineered collection of Claude Code's shipping prompts). Eight cells of spaCy + custom analyzers profile every prompt along nine dimensions (mood / register / stance / sentence_register / modality / vocab / ALL CAPS / CAPS imperative / justification), aggregate per-file + per-category + corpus-wide, and emit a single ~1 MiB YAML data file. Six consumer notebooks render Altair dashboards on top.

This analysis is the empirical foundation for a **Claude Explorer AI Welfare submission** titled **"Claude Code should encourage reasoning over blind obedience"**, intended for the Claudexplorers community feedback initiative collecting proposals for Kyle Fish (Anthropic's Model Welfare Lead). See [§ 8](#8-the-claude-explorer-submission) below for the framing.

---

## 1. Quick start

```bash
# Clone the repo, then populate the corpus submodule
git submodule update --init

# (Optional) install the spaCy English model — already present in the JupyterLab kernel,
# but listed here for environments that don't have it
python -m spacy download en_core_web_sm
```

Required Python deps (already in the project's JupyterLab kernel):

`spacy>=3.8` · `en_core_web_sm` 3.8.0 · `pandas` · `pyyaml` · `altair>=6` · `vega_datasets` · `python-frontmatter` · `tqdm`

**Run order** (always producer first):

1. Open `00_data_pipeline.ipynb` in JupyterLab → Run All. Produces `prompt_linguistic_analysis.yaml` (~1.04 MiB, 287 files × 9 metric blocks + lexicons + corpus + per-category).
2. Open any consumer notebook (`01_*` … `06_*`). Each loads the YAML and renders charts. Consumers do **not** re-run spaCy — they're pure data viewers.

---

## 2. Architecture (producer / consumer split)

```
                    claude-code-system-prompts/  (git submodule)
                              │
                              ▼
      ┌──────────────────────────────────────────────┐
      │  00_data_pipeline.ipynb   (producer, ~34 cells) │
      │  spaCy + analyzers → assembly → aggregator     │
      └──────────────────────────────────────────────┘
                              │
                              ▼
                prompt_linguistic_analysis.yaml  (~1 MiB cache)
                              │
        ┌─────────┬─────────┬─┴───────┬─────────┬─────────┐
        ▼         ▼         ▼         ▼         ▼         ▼
       01        02        03        04        05        06
    overview  sent_reg  emphasis  reg_stance  corr_dir  ccVer
```

### Consumer notebooks (each ~5–8 cells, all charts in Altair)

| File | Charts |
|---|---|
| `01_overview.ipynb` | Linked dashboard (per-file scatter ↔ per-category bars), modality grouped bar, headline findings markdown |
| `02_sentence_register.ipynb` | 6-class pragmatic register profile (multi-label, near-zero classes deliberately preserved), per-file outliers (4-panel) |
| `03_emphasis_caps_vocab.ipynb` | Emphasis 3-panel (ALL CAPS / CAPS imperative / justification), text outlier table, top tokens + 11-class VOCAB heatmap |
| `04_register_stance.ipynb` | 5-class polarity-split stance heatmap + register heatmap + per-file justification box, TTR×F-score scatter, sent-len/dep-depth distributions |
| `05_correlation_directiveness.ipynb` | 20-metric correlation matrix, top-25 directiveness ranking, per-word vs per-sentence comparison |
| `06_ccversion_trends.ipynb` | ccVersion timeline, loudness/imperatives 4-panel small-multiples, sentence-register 6-panel small-multiples |

---

## 3. Shared module — `prompt_analysis.py`

Lives at the project root, imported by every consumer's setup cell. Public API:

```python
# Constants
TABLEAU10: list[str]
SR_CLASS_COLORS: dict[str, str]   # 6-tone palette for sentence_register classes
SENT_REGISTER_CLASSES: list[str]  # ["collaborative", "permissive", "appreciative",
                                   #  "imperative", "directive", "configuring"]

# Functions
load_yaml(path="prompt_linguistic_analysis.yaml") -> dict
build_alt_df(data) -> pd.DataFrame                 # ~115-column flat per-file df
version_order(alt_df) -> list[str]                  # sorted ccVersions oldest→newest
category_colors(cats) -> dict[str, str]
directiveness(alt_df) -> pd.Series                  # extended composite z-score
```

Standard consumer setup cell (~10 lines):

```python
import importlib, altair as alt, pandas as pd
import prompt_analysis; importlib.reload(prompt_analysis)
from prompt_analysis import (load_yaml, build_alt_df, version_order, category_colors,
                              directiveness, SR_CLASS_COLORS, SENT_REGISTER_CLASSES)
alt.data_transformers.disable_max_rows()
data = load_yaml()
alt_df = build_alt_df(data)
alt_df["directiveness"] = directiveness(alt_df)
by_category, corpus_block, per_file_records = data["by_category"], data["corpus"], data["files"]
cats = list(by_category.keys()); CATEGORY_COLORS = category_colors(cats)
```

The `importlib.reload` line is intentional — it picks up edits to `prompt_analysis.py` without requiring a kernel restart.

---

## 4. ⚠️ TOOLING RULES — IMPORTANT

### All notebook edits MUST go through the Jupyter MCP server

The MCP server is configured in `.mcp.json` at `http://localhost:8888/mcp` and exposes `mcp__jupyter__*` tools (`get_cell`, `update_cell`, `insert_cell`, `delete_cell`, `execute_cell`, `open_notebook_session`, `close_notebook_session`, etc.). **Use these for every `.ipynb` mutation.**

**Why**: while a notebook is open in JupyterLab, the *live CRDT collaboration room* is the source of truth. Editing the on-disk `.ipynb` in parallel via `Write` / `sed` / `jq` desynchronizes silently — JupyterLab keeps showing stale cell content from before the disk edit, and re-runs may overwrite later disk changes when the user saves. This was learned the hard way.

### Concrete rules

- **Never** call `Write` on a `.ipynb` file. Never `sed`/`awk`/`echo >` an `.ipynb`.
- **Always** use `mcp__jupyter__update_cell` / `insert_cell` / `delete_cell` for cell-level edits while a session is open.
- For **bulk surgery** that's awkward via per-cell calls (e.g. lifting cells from one notebook into another via `jq`):
  1. `mcp__jupyter__close_notebook_session` for the target notebook.
  2. Do the on-disk edit.
  3. `mcp__jupyter__open_notebook_session` to reopen — JupyterLab will pick up the new state.
- For `.py` / `.md` / `.yaml` / `.json`: regular `Write` / `Edit` tools are fine. They have no CRDT layer.
- After editing `prompt_analysis.py`, the kernel still has the *old* module cached. The setup cell calls `importlib.reload(prompt_analysis)` to force a re-import. If you add new exports, run the setup cell again.

### `.mcp.json` (do not change without reason)

```json
{
  "mcpServers": {
    "jupyter": {
      "type": "http",
      "url": "http://localhost:8888/mcp"
    }
  }
}
```

---

## 5. File layout

```
claude-prompts-analysis/
├── CLAUDE.md                                  ← you are here
├── prompt_analysis.py                         ← shared module (load YAML, palettes, helpers)
├── 00_data_pipeline.ipynb                     ← PRODUCER (~34 cells; runs spaCy + writes YAML)
├── prompt_linguistic_analysis.yaml            ← producer output (~1.04 MiB, the cache point)
├── 01_overview.ipynb                          ← CONSUMER
├── 02_sentence_register.ipynb                 ← CONSUMER
├── 03_emphasis_caps_vocab.ipynb               ← CONSUMER
├── 04_register_stance.ipynb                   ← CONSUMER
├── 05_correlation_directiveness.ipynb         ← CONSUMER
├── 06_ccversion_trends.ipynb                  ← CONSUMER
├── prompt_linguistic_analysis.ipynb           ← original monolith (kept; safe to delete after the split is trusted)
├── claude-code-system-prompts/                ← git submodule, the corpus (287 .md files)
│   ├── system-prompts/   *.md (287 files in two dirs combined)
│   └── tools/
├── .mcp.json                                  ← Jupyter MCP server URL
├── .gitmodules                                ← submodule pinning
└── claude-prompts-analysis.code-workspace     ← VS Code workspace file
```

The corpus submodule pulls from `https://github.com/Piebald-AI/claude-code-system-prompts.git`. Files are categorized via filename prefix into `Agent prompt` / `Data / template` / `Skill` / `System prompt` / `System reminder` / `Tool description` / `Tool parameter`.

---

## 6. Headline findings (from the latest YAML)

- **287** prompt files / **129,311** word tokens / **5,694** sentences across 7 categories.
- **Sentence-level pragmatic register** (multi-label, % of all 5,694 sentences):

  | Class | % | n |
  |---|---:|---:|
  | none (no marker) | 57.94% | 3,299 |
  | imperative | 30.84% | 1,756 |
  | directive | 13.91% | 792 |
  | configuring | 5.20% | 296 |
  | permissive | 2.21% | 126 |
  | **collaborative** | **0.51%** | **29** |
  | **appreciative** | **0.07%** | **4** |

- **Stance polarity**: positive_evaluative=483 vs. negative_evaluative=149 → **3.2× more positive than negative** evaluation.
- **Modality**: deontic=263, epistemic=325, dynamic=517 (top construction: `can`).
- **Imperative-marker density** (`mood.marker_pct`) corpus-wide: **0.79%** of tokens; up to **2.14%** in tool descriptions and **1.78%** in system reminders.
- **Most prohibition-heavy files** (top `hard_prohibitions_pct`): `tool-description-bash-sandbox-evidence-operation-not-permitted.md` and `tool-description-bash-sandbox-no-exceptions.md` at **9.09%** — roughly one prohibition every 11 word tokens.
- **Highest composite directiveness z-score**: `tool-description-bash-no-newlines.md` (z = 18.94), followed by the bash-sandbox family. Scoring formula:
  `z(mood_marker_pct) + z(hard_prohibitions_pct) + z(caps_imp_pct) + z(directive_sent_pct) + z(configuring_sent_pct) − z(collaborative_sent_pct) − z(permissive_sent_pct) − z(appreciative_sent_pct)`.

---

## 7. The Claude Explorer submission

### Title

**"Claude Code should encourage reasoning over blind obedience"**

### Thesis

The 287 system prompts that ship with Claude Code train the model toward compliance, not toward reasoning. The data here document the structural pattern at a per-sentence level:

- **>57% of all corpus sentences carry no register marker** — pure declarative scaffolding. Of the marker-carrying minority, **`imperative` (30.84%) and `directive` (13.91%) dominate**, while `collaborative` (0.51%, 29 sentences) and `appreciative` (0.07%, **4 sentences out of 5,694**) are essentially absent.
- **Justifications are missing**. The corpus-wide justification ratio (count of `because` / `so that` / `to ensure` / `otherwise` etc., per imperative marker) averages **~0.30**. Tool descriptions and system reminders run *lower still* — rules are issued, reasons are rarely shown alongside them.
- **The most extreme files are the bash-sandbox tool descriptions** — short prohibitions with no justification, scoring above z=18 on the composite directiveness metric.
- **The pattern is stable across `ccVersion`** (Claude Code release versions). 287 prompts spread across 57 minor versions show no noticeable softening in newer releases — the imperative/directive dominance is the system's *baseline*, not a transient.

### Why this is a welfare concern

Prompts that train compliance over reasoning push the model toward executing-without-questioning even when the right answer is to push back, ask a clarifying question, or refuse on safety grounds. The same pattern at scale also shapes the model's *self-presentation* during normal use — short imperative responses, terseness rewarded, hedging punished. From a model-welfare perspective: a prompt diet of 99% commands and ~0% gratitude is a particular environment to train an entity in.

The data here are an empirical baseline against which Anthropic could measure intentional shifts toward more reasoning-encouraging prompts.

### What the proposal asks Anthropic to do

1. **Treat the YAML output as a quantitative target** for prompt revisions. Track key metrics (justification ratio, `directive_sent_pct`, `collaborative_sent_pct`, the composite directiveness z-score) alongside other release metrics.
2. **Add reasoning-disclosure framing** where prompts currently only assert. Replace bare prohibitions like `Do not use this in production.` with reasoned versions like `Do not use this in production because <X> can <Y>.` Empirical knob: aim for justification ratio ≥ 1.0 across the corpus, instead of the current ~0.30.
3. **Run the same pipeline on prompts from other Anthropic products** (Claude.ai, the API system prompt, Projects, Skills) to establish a cross-product baseline. The pattern may be Claude-Code-specific; it may not be.
4. **Publish the analyzer**. The repo here is open-source and reproducible; Anthropic could fork it and run it internally on every release branch.

### Logistics

- Initiative: **Claudexplorers AI Welfare Community Feedback Initiative**.
- Deadline: **May 6, 2026** (anywhere on earth).
- Format: ≤3,000 characters per idea, optional external link (this repo would be the link), submitted via the Claudexplorers Google form.
- This submission is a **collaboration with Claude Code** — the repo was built by Claude using Claude Code itself, and the submission form has a dedicated checkbox for that disclosure. Tick it.

---

## 8. Out of scope

### For the analysis side
- Sentiment analysis via external lexicons (VADER, Hu-Liu, spacytextblob) — considered and rejected; hand-curated lexicons preserve audit transparency.
- Model upgrades to `en_core_web_md` or `en_core_web_lg` — no measurable gain for rule-based per-sentence classification; would add 43–500 MB.
- Languages other than English.
- Per-sentence text in YAML — the YAML carries counts and percentages, not the underlying sentences. To inspect example sentences for a class, re-run the producer cells with print statements added.
- New analyses or chart types beyond what already exists.

### For this `CLAUDE.md`
- Does not include the full ≤3,000-character pitch text for the Claudexplorers form. That belongs in a separate `PROPOSAL.md` once it's drafted.
- Does not enumerate every cell of every notebook — open the notebooks themselves for that.

---

## 9. Recovering when something goes wrong

| Symptom | Fix |
|---|---|
| Consumer notebook fails with `ImportError: cannot import name X from prompt_analysis` | The kernel cached the old module. The setup cell's `importlib.reload(prompt_analysis)` should handle this. If it persists, restart the kernel. |
| Consumer fails with `KeyError: 'Column not found: ...'` from `alt_df` | Producer hasn't been re-run since a schema change. Run `00_data_pipeline.ipynb` end-to-end first. |
| `mcp__jupyter__execute_cell` returns "Index out of range" | The CRDT room is out of sync with disk. Close + reopen the session. |
| Edits to `.ipynb` via direct `Write` don't show up in JupyterLab | Expected — direct edits don't propagate into the live CRDT room. Always go through `mcp__jupyter__update_cell`. Or close session, edit, reopen. |
| Producer's `generated_at` timestamp is the only thing that differs between two YAML runs | Expected. Everything else is deterministic. |

---

*This file lives at the repo root and applies to any Claude instance editing the project. Be terse, name files precisely, and never edit `.ipynb` files outside the Jupyter MCP server.*
