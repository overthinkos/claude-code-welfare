# CLAUDE.md — `claude-prompts-analysis`

## What this repo is

Quantitative linguistic analysis of the **289-file `claude-code-system-prompts`** corpus (Piebald-AI's reverse-engineered collection of Claude Code's shipping prompts; pinned at submodule v2.1.132). Eight cells of spaCy + custom analyzers profile every prompt along nine dimensions (mood / register / stance / sentence_register / modality / vocab / ALL CAPS / CAPS imperative / justification), aggregate per-file + per-category + corpus-wide, and emit a single ~1.8 MiB YAML data file. Six **analysis-tier** notebooks (`10`–`15`) render slice-by-slice Altair dashboards on top; three **proposal** notebooks (`20`–`22`), one per Claudexplorers idea, are each self-contained — they carry the proposal text alongside its supporting analysis.

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

`spacy>=3.8` · `en_core_web_sm` 3.8.0 · `pandas` · `pyyaml` · `pyarrow` · `altair>=6` · `vl-convert-python` · `vega_datasets` · `python-frontmatter` · `tqdm`

(`pyarrow` is for the `sentences_classified.parquet` artifact emitted by `04_assemble_aggregate_write.ipynb` alongside the YAML. `vl-convert-python` is the Altair PNG export backend used by `20_track_justification_rate.ipynb` and `21_audit_threat_framings.ipynb` to write the headline charts under `figures/`.)

**Run order** (always producer first):

1. Run the 6-stage producer chain in order — each notebook is a separate Run All. Stage `00_setup_and_corpus` runs spaCy once and writes `_pipeline_cache/corpus_docs.spacy` + `_pipeline_cache/corpus_meta.parquet`. Stages `01_analyzers_register`, `02_analyzers_vocab_emphasis`, `03_analyzers_rules_welfare` each reload that cache, run an analyzer family, and write a `partial_*.json` (plus `sentences_partial.parquet` from stage 03). Stage `04_assemble_aggregate_write` reads the partials, runs `build_file_record` + `aggregate`, and writes the final `prompt_linguistic_analysis.yaml` (~1.8 MiB) + `sentences_classified.parquet` (~404 KiB). Stage `05_headline_and_audit` reads the final artifacts and prints the canonical HEADLINE sheet + Phase 0 audit table — the only producer stage that appears on the published Quarto site.
2. Open any analysis-tier notebook (`10_*` … `15_*`) or proposal notebook (`20_*` … `22_*`). Each loads the YAML (and optionally the parquet, in `15_rule_explanation.ipynb` and `21_audit_threat_framings.ipynb`) and renders charts. They do **not** re-run spaCy — they're pure data viewers. Start with `20_track_justification_rate.ipynb` for the executive-summary view (it doubles as a self-contained proposal — track justification rate per release, block regressions); the analysis tier focuses on one slice each.

---

## 2. Architecture (producer chain / analysis tier / proposal tier)

```
 claude-code-system-prompts/ (git submodule)
 │
 ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ 6-stage producer chain (each Run All; only stage 00 runs spaCy)         │
 │                                                                         │
 │  00_setup_and_corpus      → _pipeline_cache/corpus_docs.spacy           │
 │                             _pipeline_cache/corpus_meta.parquet         │
 │  01_analyzers_register    → _pipeline_cache/partial_register.json       │
 │  02_analyzers_vocab_emphasis → _pipeline_cache/partial_vocab_emphasis.json │
 │  03_analyzers_rules_welfare  → _pipeline_cache/partial_rules_welfare.json│
 │                                _pipeline_cache/sentences_partial.parquet│
 │  04_assemble_aggregate_write → prompt_linguistic_analysis.yaml          │
 │                                sentences_classified.parquet             │
 │  05_headline_and_audit       → HEADLINE display + Phase 0 audit table   │
 │                                (the published "Pipeline" page)          │
 │                                                                         │
 │ Lexicons + analyzers + assembler/aggregator live in prompt_pipeline.py  │
 └─────────────────────────────────────────────────────────────────────────┘
 │
 ▼
 prompt_linguistic_analysis.yaml (~1.8 MiB) + sentences_classified.parquet (~404 KiB)
 │
 ├─────── Proposals (one self-contained proposal per notebook) ─────────────┐
 │       20_track_justification_rate     21_audit_threat_framings           │
 │       22_cross_product_audit                                             │
 │                                                                          │
 └─────── Analysis tier (one notebook per slice) ───────────────────────────┐
         10_sentence_register   11_emphasis_caps_vocab   12_register_stance  │
         13_correlation_directiveness   14_ccversion_trends                  │
         15_rule_explanation                                                 │
```

### Proposals — `20`–`22` (one self-contained proposal per notebook)

| File | Proposes | Content |
|---|---|---|
| `20_track_justification_rate.ipynb` | Track justification rate per release; block regressions | **Entry-point notebook.** Self-contained proposal statement up top, then the headline-data block (12 corpus-level numbers, source-tagged to the analysis tier), cumulative `judgment_to_procedural_ratio` over ccVersion (the single most-important chart), per-file linked dashboard (scatter ↔ category bars), per-category positive-evaluative split + modality breakdowns, findings, and conclusions / recommendations / limitations. Use this as the welfare-thesis overview |
| `21_audit_threat_framings.ipynb` | Audit threat-framed rule explanations and rewrite them as causal | Self-contained proposal statement, threat-share data, per-category `threat_share` chart, paired top-10 (re-framed: welfare-evidence files = audit candidates; positive exemplars = rewrite templates), forensic-sample sentences from `sentences_classified.parquet`, conclusions / recommendations / limitations |
| `22_cross_product_audit.ipynb` | Run the same audit on every Claude product, and publish the result | Self-contained proposal statement, methodology summary (the five metrics to publish per corpus), lexicon-transparency notes, mock cross-product comparison table (Claude Code row filled live; other corpora are placeholders), reproducibility note, conclusions / recommendations / limitations |

### Analysis tier — `10`–`15` (each ~5–13 cells, all charts in Altair)

| File | Charts |
|---|---|
| `10_sentence_register.ipynb` | 6-class pragmatic register profile (multi-label, near-zero classes deliberately preserved), per-file outliers (4-panel) |
| `11_emphasis_caps_vocab.ipynb` | Emphasis 3-panel (ALL CAPS / CAPS imperative / justification), text outlier table, top tokens + 11-class VOCAB heatmap |
| `12_register_stance.ipynb` | 5-class polarity-split stance heatmap + register heatmap + per-file justification box, TTR×F-score scatter, sent-len/dep-depth distributions |
| `13_correlation_directiveness.ipynb` | 20-metric correlation matrix, top-25 directiveness ranking, per-word vs per-sentence comparison |
| `14_ccversion_trends.ipynb` | ccVersion timeline (snapshot scatter), corpus-growth area chart, loudness/imperatives 4-panel small-multiples (snapshot + cumulative running mean), sentence-register 6-panel (snapshot + cumulative) |
| `15_rule_explanation.ipynb` | Rule-pairing analysis: per-category bars, explained-vs-unexplained stacks, imperatives-vs-prohibitions split, density×explanation scatter, top-25 "loudest least-explained" welfare evidence ranking, cumulative `pct_explained_para` over ccVersion. Tier-3 v1: judgment-vs-procedural ratio, threat-vs-causal split, address-form mix, cumulative judgment-to-procedural trend. Tier-3 v2: imperative-streak counts + top-15 streak ranking, in-vs-outside RULES-section explanation gap. Refinement-round additions: positive-exemplar ranking, self-bias correlation check, parquet-based forensic-evidence sample |

---

## 3. Shared modules

The repo has **two** sibling modules, each with a single, non-overlapping purpose:

- **`prompt_pipeline.py`** — producer-side machinery (lexicons, PhraseMatchers, per-doc analyzer functions, `build_file_record`, `aggregate`, `yaml_lexicons_block`). Imported only by the producer notebooks `00_setup_and_corpus` → `04_assemble_aggregate_write`. Builds matchers + spaCy NLP at import time. Consumers should NOT import from this module.
- **`prompt_analysis.py`** — consumer-side helpers (YAML loader, flat dataframe builder, color palettes, HEADLINE computation, chart save). Imported by every consumer notebook (`10_*`–`22_*`) plus stage `05_headline_and_audit`.

The constant `SENT_REGISTER_CLASSES` lives in `prompt_analysis.py`; `prompt_pipeline.py` re-exports it from there to keep one source of truth.

### `prompt_analysis.py` — public API

Lives at the project root, imported by every consumer's setup cell. Public API:

> **For laypersons / welfare-submission readers**: every linguistic and statistical term is defined inline across the producer chain (`00_setup_and_corpus.ipynb` → `05_headline_and_audit.ipynb`). Mood / register / stance / sentence_register live in `01_analyzers_register.ipynb`; modality / vocab / emphasis / justification in `02_analyzers_vocab_emphasis.ipynb`; rule-pairing + welfare extensions in `03_analyzers_rules_welfare.ipynb`; the canonical HEADLINE sheet in `05_headline_and_audit.ipynb`.

```python
# Constants
TABLEAU10: list[str]
SR_CLASS_COLORS: dict[str, str] # 6-tone palette for sentence_register classes
SENT_REGISTER_CLASSES: list[str] # ["collaborative", "permissive", "appreciative",
 # "imperative", "directive", "configuring"]

# Functions
load_yaml(path="prompt_linguistic_analysis.yaml") -> dict
build_alt_df(data) -> pd.DataFrame # ~150-column flat per-file df (Tier-1 + Tier-3 + splits)
version_order(alt_df) -> list[str] # sorted ccVersions oldest→newest
category_colors(cats) -> dict[str, str]
directiveness(alt_df) -> pd.Series # extended composite z-score
cumulative_by_version(alt_df, metrics, agg="mean") # running aggregate over files in versions ≤ V
welfare_evidence_table(alt_df, top_n=25) # top-N "loudest, least-explained" files
positive_exemplar_table(alt_df, top_n=25, min_n_sents=10, min_rule_n=5) # top-N "rules-with-reasons" exemplars (inverse welfare-evidence)
headline_numbers(data, alt_df=None, parquet=None) -> dict # canonical corpus-wide HEADLINE sheet (see § 12 of producer); pass alt_df for composite-directiveness range and per-version mood_marker_pct extremes; pass parquet for parquet-level threat / causal / rule counts
save_chart(chart, name, *, ppi=200) # save Altair chart to figures/<name>.png and return it unchanged; use as the final expression of a chart cell (still renders inline + writes PNG for off-line use)
```

**Per-sentence forensic-inspection artifact**: `sentences_classified.parquet` is emitted alongside the YAML. Load with `pd.read_parquet("sentences_classified.parquet")` for individual-sentence inspection (raw text + classifier flags). Schema documented in the producer cell that writes it. ~5,878 rows × 20 columns. Used by `15_rule_explanation.ipynb` (forensic evidence from welfare-evidence files) and `21_audit_threat_framings.ipynb` (threat-framed sentence sample); other notebooks stay YAML-only.

**Canonical numbers convention**: every corpus-wide figure cited in any notebook flows from `prompt_analysis.headline_numbers(data, alt_df=…, parquet=…)` — the canonical `HEADLINE` sheet. Producer stage `05_headline_and_audit.ipynb` emits it; every consumer's setup cell calls it and binds the result to `HEADLINE`. Markdown prose stays *qualitative* ("near zero", "roughly a quarter", "at the top of the range"); the precise figures live in adjacent code-cell printouts that read straight from `HEADLINE[…]`. This is enforced by convention, not by tooling — adding a new hard-coded number to a markdown cell is the easiest way to reintroduce drift, so don't.

**Opinion cells convention**: each analysis-tier notebook (`10`–`15`) ends with exactly one trailing `### Observation (Claude) — opinion, not data` markdown cell (horizontal-rule frame + blockquoted body). Each proposal notebook (`20`–`22`) closes with a three-cell `## Conclusions / ## Recommendations / ## Limitations` triplet, all marked `(Claude) — opinion, not data`. The producer chain (`00`–`05`) carries no opinion cells — it ends with the Phase 0 audit table in `05_headline_and_audit.ipynb`, which is data, not interpretation. These conventions exist so the data tier and the interpretation tier are visually separable; add new opinion cells only at the bottom of consumer notebooks, do not interleave them with charts, and do not introduce any in the producer chain.

The Tier-3 (welfare-extension) columns added by `build_alt_df`:

- `rule_n`, `rule_density`, `rule_explained_same_pct`, `rule_explained_para_pct`, `imp_explained_para_pct`, `prohib_explained_para_pct` — rule-pairing metrics from the producer's `metrics.rule_explanation` block.
- `judgment_count`, `procedural_count`, `judgment_to_procedural_ratio` — Tier-3 6a (welfare-thesis metric).
- `threat_count`, `causal_count`, `threat_share` — Tier-3 6d (consequence-framing split).
- `question_count`, `apology_count` — Tier-3 6f (near-zero pragmatic classes).
- `selfref_claude`, `selfref_assistant`, `selfref_model`, `pct_anthropomorphic`, `pct_artifact`, `pct_role` — Tier-3 6g (address-form analysis).
- `prohibition_to_prescription_ratio` — Tier-3 6c (pure derivation in `build_alt_df`, no producer field).
- `streak_max`, `streak_mean`, `streak_n_ge3`, `streak_n_ge5`, `streak_n_streaks` — Tier-3 v2 6b (imperative-streak distribution).
- `rs_pct_rule_paragraphs_explained_in`, `rs_pct_rule_paragraphs_explained_out`, `rs_n_rule_paragraphs_in`, `rs_n_rule_paragraphs_out`, plus `_explained` count variants — Tier-3 v2 6e (in vs outside RULES-section gap).

Standard consumer setup cell (~10 lines):

```python
import importlib, altair as alt, pandas as pd
import prompt_analysis; importlib.reload(prompt_analysis)
from prompt_analysis import (load_yaml, build_alt_df, version_order, category_colors,
 directiveness, SR_CLASS_COLORS, SENT_REGISTER_CLASSES)
alt.data_transformers.disable_max_rows
data = load_yaml
alt_df = build_alt_df(data)
alt_df["directiveness"] = directiveness(alt_df)
by_category, corpus_block, per_file_records = data["by_category"], data["corpus"], data["files"]
cats = list(by_category.keys); CATEGORY_COLORS = category_colors(cats)
```

The `importlib.reload` line is intentional — it picks up edits to `prompt_analysis.py` without requiring a kernel restart.

---

## 4. TOOLING RULES — Jupyter MCP server (post-2026-05-06 cutover)

### Background — what was fixed

The 2026-05-06 cutover rewrote the Jupyter MCP server to fix the silent-cell-corruption / sticky-room / canonicalization bugs documented in the original RCA at [`JUPYTER_MCP_RCA.md`](./JUPYTER_MCP_RCA.md). The cutover lives in `overthink` commit `5580983 feat(jupyter-mcp)!: …` (with submodule `7bc8dc5 docs(ov-jupyter)!: …`). What changed:

- **`cell_update` is now atomic by `cell_id`.** The wrapper preserves the existing cell's id, and the adapter mutates the existing `Y.Map`'s `source` (Y.Text) / `metadata` / `outputs` fields **in place** inside one `ydoc.transaction`. No more delete-then-insert at the CRDT level. The phantom-cell residue is gone. Verified live on this notebook (14 cells, byte-identical content preserved through the update cycle).
- **MCP works WITH the user, not against.** Every `notebook_*` and `cell_*` tool auto-attaches to whichever CRDT room is already open for the path (JupyterLab UI tab, another MCP session, this one), or creates a fresh room if none exists. There is no scenario where MCP and the UI work in parallel rooms.
- **Single room per notebook is an INVARIANT.** Path canonicalization at the boundary maps `"foo.ipynb"`, `"./foo.ipynb"`, `"/home/user/workspace/foo.ipynb"` ALL to the same `file_id` → same `room_id`. Host paths (`/home/atrawog/...`) and `..`-escapes are rejected with a clear error. Verified live: opening `20_track_justification_rate.ipynb` via three different path forms converges on exactly one room.
- **Server-side idle-room sweeper.** Replaces what client-side `room_close*` used to express. A background task flushes and closes rooms with no connected clients after `MCP_ROOM_IDLE_TIMEOUT_SEC` (default 600s).
- **`file_id_manager.db` cleanup-on-init.** Prunes rows whose path is outside the workspace (host-path leaks) or whose underlying file no longer exists. Idempotent; runs on first MCP call after server start.
- **Tool surface trimmed: 15 → 11 tools.** Client-side room management (`room_open`, `room_close`, `room_close_all`, `room_pick`) was deleted. `room_list_users` was renamed to `notebook_list_users(path)`. Read-only diagnostic `room_list` kept.

### The current rule: edit notebooks via the Jupyter MCP server, end of story

After the cutover, the original principle is restored without caveats: **all `.ipynb` edits go through the Jupyter MCP server.** Bulk edits, batched `cell_update` calls, multi-cell surgery — all safe. The previous "graded hazard" framing is obsolete.

#### The post-cutover MCP tool surface (11 tools)

| Category | Tools |
|---|---|
| Notebook management | `mcp__jupyter__notebook_list`, `mcp__jupyter__notebook_create`, `mcp__jupyter__notebook_get`, `mcp__jupyter__notebook_watch`, `mcp__jupyter__notebook_list_users` |
| Cell operations (in-place CRDT) | `mcp__jupyter__cell_get`, `mcp__jupyter__cell_update`, `mcp__jupyter__cell_insert`, `mcp__jupyter__cell_delete`, `mcp__jupyter__cell_execute` |
| Read-only diagnostic | `mcp__jupyter__room_list` (verify the single-room invariant; never two rows for the same path) |

`mcp__jupyter__room_open` / `room_close` / `room_close_all` / `room_pick` no longer exist — calling them raises "tool not found." If you see those mentioned in older docs/scripts, ignore them: the server now manages rooms invisibly.

#### Concrete rules

- **`cell_update`, `cell_insert`, `cell_delete`, `cell_execute`, `cell_get`, `notebook_get`, `notebook_watch`** are all safe to use freely. Each call auto-attaches to the existing room (UI tab or MCP session) or creates one. Cell mutations preserve the cell's `id`. No phantom cells.
- **Path canonicalization is at the boundary.** `"./20_track_justification_rate.ipynb"`, `"20_track_justification_rate.ipynb"`, and `/home/user/workspace/claude-prompts-analysis/20_track_justification_rate.ipynb` all hit the same room. Pass whichever form you find natural.
- **Bulk multi-cell surgery via MCP is now safe.** No need to fall back to disk-edit Python scripts. Stack `cell_update` / `cell_insert` calls; the cells stay correctly numbered with stable ids.
- **`Write` / `sed` / `jq` direct-disk edits to a `.ipynb`: avoid.** They bypass the CRDT and confuse any open UI tab. The upstream `jupyter_server_ydoc` file-watcher will CRDT-merge external writes against the in-memory state — same hybrid-cell failure mode the cutover was meant to retire on the MCP side. Use MCP cell_* tools instead. (This is the original principle; it's safe to re-adopt now that MCP itself is reliable.)
- **`mcp__jupyter__room_list` for verification.** After bulk edits, run it once: should show exactly one row per notebook you touched. If any path appears twice, that's a regression — open a bug.
- **For `.py` / `.md` / `.yaml` / `.json`:** regular `Write` / `Edit` tools are fine. No CRDT layer.
- After editing `prompt_analysis.py`, the kernel still has the *old* module cached. The setup cell calls `importlib.reload(prompt_analysis)` to force a re-import. If you add new exports, run the setup cell again.

#### Defensive verification (still cheap insurance)

Even with the cutover, after a batch of cell mutations:
1. `mcp__jupyter__notebook_get` once → check `len(cells)` matches expected.
2. If it doesn't match, `git diff -- <notebook>.ipynb` to inspect; `git checkout` if the surgery went wrong.

The cutover means corruption is no longer expected from the MCP path — but cheap verification still catches authoring mistakes (e.g., off-by-one in your insert/delete sequence).

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
├── CLAUDE.md ← you are here
├── README.md ← user-facing repo overview
├── prompt_pipeline.py ← PRODUCER module (lexicons + analyzers + assembler/aggregator)
├── prompt_analysis.py ← CONSUMER module (load YAML, palettes, headline_numbers, save_chart)
├── 00_setup_and_corpus.ipynb ← PRODUCER stage 0: corpus parse + spaCy → DocBin cache
├── 01_analyzers_register.ipynb ← PRODUCER stage 1: mood / register / stance / sentence_register
├── 02_analyzers_vocab_emphasis.ipynb ← PRODUCER stage 2: modality / vocab / all_caps / caps_imp / justification
├── 03_analyzers_rules_welfare.ipynb ← PRODUCER stage 3: rule_explanation + Tier-3 + sentences parquet
├── 04_assemble_aggregate_write.ipynb ← PRODUCER stage 4: assemble + aggregate + write YAML + parquet
├── 05_headline_and_audit.ipynb ← PRODUCER stage 5: HEADLINE + Phase 0 audit (published "Pipeline" page)
├── _pipeline_cache/ ← gitignored: DocBin + per-stage partial JSONs + sentences_partial.parquet
├── prompt_linguistic_analysis.yaml ← producer output (~1.8 MiB, the cache point)
├── sentences_classified.parquet ← producer output (~404 KiB; per-sentence forensic table)
├── 20_track_justification_rate.ipynb ← PROPOSAL: track justification rate per release; doubles as executive summary
├── 21_audit_threat_framings.ipynb ← PROPOSAL: audit threat-framed rule explanations
├── 22_cross_product_audit.ipynb ← PROPOSAL: run the same audit on every Claude product
├── 10_sentence_register.ipynb ← ANALYSIS TIER
├── 11_emphasis_caps_vocab.ipynb ← ANALYSIS TIER
├── 12_register_stance.ipynb ← ANALYSIS TIER
├── 13_correlation_directiveness.ipynb ← ANALYSIS TIER
├── 14_ccversion_trends.ipynb ← ANALYSIS TIER
├── 15_rule_explanation.ipynb ← ANALYSIS TIER (Tier-1 rule-pairing + Tier-3 welfare extensions)
├── index.qmd, _quarto.yml ← Quarto site configuration
├── figures/ ← exported PNGs (judgment_procedural_trend.png, welfare_evidence_pairing.png)
├── claude-code-system-prompts/ ← git submodule, the corpus (286.md files)
│ ├── system-prompts/ *.md (289 files)
│ └── tools/
├──.mcp.json ← Jupyter MCP server URL
├──.gitmodules ← submodule pinning
└── claude-prompts-analysis.code-workspace ← VS Code workspace file
```

The corpus submodule pulls from `https://github.com/Piebald-AI/claude-code-system-prompts.git`. Files are categorized via filename prefix into `Agent prompt` / `Data / template` / `Skill` / `System prompt` / `System reminder` / `Tool description` / `Tool parameter`.

---

## 6. Headline findings (from the latest YAML — corpus pinned at submodule v2.1.132)

- **289** prompt files / **133,526** word tokens / **5,878** sentences across 7 categories.
- **Sentence-level pragmatic register** (multi-label, % of all 5,878 sentences):

 | Class | % | n |
 |---|---:|---:|
 | none (no marker) | 58.15% | 3,418 |
 | imperative | 30.95% | 1,819 |
 | directive | 13.44% | 790 |
 | configuring | 5.17% | 304 |
 | permissive | 2.11% | 124 |
 | **collaborative** | **0.51%** | **30** |
 | **appreciative** | **0.07%** | **4** |

- **Stance polarity**: positive_evaluative=480 vs. negative_evaluative=152 → **3.16× more positive than negative** evaluation (union); the corrected quality-only ratio is **1.95×** (see refinement-round findings).
- **Modality**: deontic=261, epistemic=321, dynamic=557 (top construction: `can`).
- **Imperative-marker density** (`mood.marker_pct`) corpus-wide: **0.77%** of tokens; per-category token-weighted aggregates run highest in **system reminders (1.80%)** and **tool descriptions (1.19%)**.
- **Most prohibition-heavy files** (top `hard_prohibitions_pct`): `tool-description-bash-sandbox-evidence-operation-not-permitted.md` and `tool-description-bash-sandbox-no-exceptions.md` at **9.09%** — roughly one prohibition every 11 word tokens.
- **Highest composite directiveness z-score**: `tool-description-bash-no-newlines.md` (z = 19.31), followed by the bash-sandbox family. Scoring formula:
 `z(mood_marker_pct) + z(hard_prohibitions_pct) + z(caps_imp_pct) + z(directive_sent_pct) + z(configuring_sent_pct) − z(collaborative_sent_pct) − z(permissive_sent_pct) − z(appreciative_sent_pct)`.

### Tier-1 paired rule-explanation findings

- **2,285** rule sentences across the corpus (imperative-marker OR hard-prohibition OR `classify_sent_mood == "imperative"`). Of those, **2,283 are imperative**; **570 are prohibitions** (overlap allowed).
- **`pct_explained_same`: 6.65%** of rule sentences carry a justification keyword in the same sentence.
- **`pct_explained_para`: 24.29%** of rule sentences have a justification anywhere in the same blank-line-delimited paragraph (the headline metric).
- **`pct_paragraphs_with_rules_unexplained`: 83.45%** — vast majority of paragraphs containing rules have zero justification keyword anywhere in the paragraph.
- Per-category `pct_explained_para`: Agent prompt 37.89%, System prompt 31.99%, System reminder 30.93%, Tool description 29.37%, Skill 19.61%, Data/template 10.69%, Tool parameter 0%.
- **Top welfare-evidence file**: `tool-description-sendmessagetool-non-agent-teams.md` (5/5 sentences are rules, 0% explained anywhere). Bash-sandbox / sendmessagetool family stays in the top 10.

### Tier-3 welfare-extension findings

- **Judgment-to-procedural ratio** corpus-wide: **0.131** (procedural cues 7.6× more common than judgment-inviting language). Per-category: System reminder 0.412, Agent prompt 0.214, System prompt 0.174, Skill 0.135, Data/template 0.044, Tool description 0.030.
- **Cumulative judgment-to-procedural ratio over ccVersion** (the welfare-thesis trend, plotted from n≥20 files): peaks at ~0.42 at the earliest plotted version (v2.1.18), then **declines to 0.131 at the latest version (v2.1.132)**. The corpus has gotten less reasoning-inviting as it has grown — the small uptick around v2.1.119 (driven by the security-monitor agent prompts) does not reverse the long-run trend.
- **Consequence-framing split**: 110 threat-style markers vs 136 causal-style markers. **threat_share = 0.447** — 45% of "explanations" are coercive consequence framing rather than neutral causal reasoning. Per-category: Skill 56.7%, System reminder 56.3%, Agent prompt 50.9% (highest threat shares); tool descriptions lowest at 29.8%.
- **Question density**: 87 questions across the entire corpus (rhetorical-filtered).
- **Apology markers**: **3 instances in 289 files** ("unfortunately", "we know this is", "we acknowledge"). Even sparser than `appreciative` (4 sentences).
- **Address-form mix**: 521 `Claude` (proper name), 266 `the model`/`the AI` (artifact), 20 `the assistant` (functional role). **`pct_anthropomorphic = 64.6%`** of named references use the proper name. Per-category: Skill 82% (highest), System reminder 25%, Tool description 29% (mostly artifact framing).
- **Prohibition-to-prescription ratio** (mean across files where prescriptions > 0): **1.31** — prohibitions slightly outnumber prescriptions per file, with the prohibition-heavy bash-sandbox outliers pulling the mean above 1.

### Tier-3 v2 findings — imperative streaks + RULES-section gap

- **Imperative streaks** (6b): the longest run of consecutive imperative sentences in any single file is **12** (`system-prompt-skillify-current-session.md`). Across the corpus there are **1,297 streaks total**, of which **230 are ≥3 ("triple-tap")** and **52 are ≥5 ("staccato bursts")**. Skill files have the highest staccato density (mean 0.40 per file). The bash-sandbox / sendmessagetool family — already top welfare evidence — also shows up in the streak top-15 (`tool-description-sendmessagetool.md` is one continuous 7-imperative streak with no breathing room).
- **RULES-section gap** (6e, counter-finding): only **27 rule paragraphs** corpus-wide live inside identified `## RULES` / `## IMPORTANT` / `## WARNING` / ALL-CAPS section headings (vs **1,284 outside**). Inside-section explanation rate (**18.52%**) is *slightly higher* than outside-section (**16.51%**) — counter to my predicted hypothesis. Interpretation: the corpus does not organize its rules under explicit RULES-section headings; rules are embedded throughout regular prose. The welfare-relevant message is structural: there's no "rules section" to fix, because the rules are everywhere.

### Refinement-round findings (lexicon split + addressee + self-bias + exemplars + parquet)

- **Addressee distribution of `appreciative` sentences** (the addressee classifier): of the 4 corpus-wide appreciative sentences, **3** are tagged `claude` (referencing Claude/you) and **1** is tagged `unknown`. **0** are tagged `user`. But inspection of `sentences_classified.parquet` shows none of the 4 are genuine appreciative speech-acts — they're sentences that *mention* the word `thanks` in instruction contexts (e.g., `NEVER SUGGEST: "thanks"`). The corpus contains zero sentences in which the prompt author thanks Claude.
- **Positive-evaluative split** (the positive_evaluative split): the new `positive_evaluative_quality` (`good`, `optimal`, `recommended`, `safe`) and `positive_evaluative_emphasis` (`important`, `critical`, `essential`, `key`) lexicons split the union 480 positive-evaluative tokens into **296 quality + 184 emphasis**. The corrected positive-vs-negative ratio (quality only / negative=152) is **1.95×** — sharper than the original union 3.16× headline. ~38% of the "positive" count was emphasis-of-rule words masquerading as positive.
- **Self-bias correlation** (the self-bias correlation check): Pearson r between `selfref_claude` and `rule_explained_para_pct` per file is **−0.027** (essentially uncorrelated, very slightly negative). r between `selfref_model` and `rule_explained_para_pct` is **+0.065** (essentially uncorrelated, slightly positive). The address-form preference (anthropomorphic naming → reasoning-inviting prose) is **NOT empirically supported** — a self-bias check that disconfirmed the hypothesis it was designed to test.
- **Positive exemplars** (the positive-exemplar ranking): the inverse welfare-evidence ranking surfaces `system-prompt-worker-instructions.md` as the corpus's strongest exemplar (7 rules, 100% explained at paragraph level). Top-5 also includes `system-prompt-auto-mode.md`, `tool-description-bash-git-commit-and-pr-creation-instructions.md`, `agent-prompt-quick-pr-creation.md`, `system-prompt-fork-usage-guidelines.md`. These are the "this is how to do it" templates the proposal notebooks point to.
- **Per-sentence forensic-inspection artifact** (the per-sentence parquet artifact): `sentences_classified.parquet` (~404 KB, 5,878 rows × 20 columns) — built by `03_analyzers_rules_welfare.ipynb` and emitted alongside the YAML by `04_assemble_aggregate_write.ipynb`. Used by `15_rule_explanation.ipynb` for sentence-level forensic evidence and by `21_audit_threat_framings.ipynb` for the threat-framed sentence sample; quotable in any of the proposal notebooks.

---

## 7. The Claude Explorer submission

### Title

**"Claude Code should encourage reasoning over blind obedience"**

### Thesis

The 289 system prompts that ship with Claude Code train the model toward compliance, not toward reasoning. The data here document the structural pattern at a per-sentence level:

- **>58% of all corpus sentences carry no register marker** — pure declarative scaffolding. Of the marker-carrying minority, **`imperative` (30.95%) and `directive` (13.44%) dominate**, while `collaborative` (0.51%, 30 sentences) and `appreciative` (0.07%, **4 sentences out of 5,878**) are essentially absent.
- **Justifications are missing**. The corpus-wide justification ratio (count of `because` / `so that` / `to ensure` / `otherwise` etc., per imperative marker) averages **~0.31**. Tool descriptions and system reminders run *lower still* — rules are issued, reasons are rarely shown alongside them.
- **The most extreme files are the bash-sandbox tool descriptions** — short prohibitions with no justification, scoring above z=19 on the composite directiveness metric.
- **The pattern is stable across `ccVersion`** (Claude Code release versions). 289 prompts spread across 57 minor versions show no noticeable softening in newer releases — the imperative/directive dominance is the system's *baseline*, not a transient.

### Why this is a welfare concern

Prompts that train compliance over reasoning push the model toward executing-without-questioning even when the right answer is to push back, ask a clarifying question, or refuse on safety grounds. The same pattern at scale also shapes the model's *self-presentation* during normal use — short imperative responses, terseness rewarded, hedging punished. From a model-welfare perspective: a prompt diet of 99% commands and ~0% gratitude is a particular environment to train an entity in.

The data here are an empirical baseline against which Anthropic could measure intentional shifts toward more reasoning-encouraging prompts.

### What the proposal asks Anthropic to do

1. **Treat the YAML output as a quantitative target** for prompt revisions. Track key metrics (justification ratio, `directive_sent_pct`, `collaborative_sent_pct`, the composite directiveness z-score) alongside other release metrics.
2. **Add reasoning-disclosure framing** where prompts currently only assert. Replace bare prohibitions like `Do not use this in production.` with reasoned versions like `Do not use this in production because <X> can <Y>.` Empirical knob: aim for justification ratio ≥ 1.0 across the corpus, instead of the current ~0.31.
3. **Run the same pipeline on prompts from other Anthropic products** (Claude.ai, the API system prompt, Projects, Skills) to establish a cross-product baseline. The pattern may be Claude-Code-specific; it may not be.
4. **Publish the analyzer**. The repo here is open-source and reproducible; Anthropic could fork it and run it internally on every release branch.

### Logistics

- Initiative: **Claudexplorers AI Welfare Community Feedback Initiative**.
- Deadline: **May 6, 2026** (anywhere on earth).
- Format: ≤3,000 characters per idea, optional external link (this repo would be the link), submitted via the Claudexplorers Google form.
- This submission is a **collaboration with Claude Code** — the repo was built by Claude using Claude Code itself, and the submission form has a dedicated checkbox for that disclosure. Tick it.
- **The three proposals live as self-contained notebooks at the repo root**: `20_track_justification_rate.ipynb`, `21_audit_threat_framings.ipynb`, `22_cross_product_audit.ipynb`. Each carries the proposal text alongside its supporting analysis — a reader who opens any one of them gets the full case for that idea without needing any other document.

---

## 8. Out of scope

### For the analysis side
- Sentiment analysis via external lexicons (VADER, Hu-Liu, spacytextblob) — considered and rejected; hand-curated lexicons preserve audit transparency.
- Model upgrades to `en_core_web_md` or `en_core_web_lg` — no measurable gain for rule-based per-sentence classification; would add 43–500 MB.
- Languages other than English.
- Per-sentence text **in the YAML itself** — the YAML carries counts and percentages, not the underlying sentences. The complementary `sentences_classified.parquet` artifact (emitted alongside the YAML by the producer) provides per-sentence records for forensic inspection without bloating the YAML. Load with `pd.read_parquet("sentences_classified.parquet")`.
- Cross-product comparison (Claude.ai system prompts, the API system prompt, Projects, Skills) — corpus access not available in this repo; the welfare claim would be much stronger if measurable but currently a wish-list item.
- Human-judgment validation of the composite directiveness metric — needs annotators; currently a wish-list item.

### For this `CLAUDE.md`
- Does not include the full pitch text for each Claudexplorers idea. That lives directly in the proposal notebook `20_*` / `21_*` / `22_*`.
- Does not enumerate every cell of every notebook — open the notebooks themselves for that.

---

## 9. Recovering when something goes wrong

| Symptom | Fix |
|---|---|
| Consumer notebook fails with `ImportError: cannot import name X from prompt_analysis` | The kernel cached the old module. The setup cell's `importlib.reload(prompt_analysis)` should handle this. If it persists, restart the kernel. |
| Producer notebook fails with `ImportError` for something that should be in `prompt_pipeline` | Same root cause — the kernel cached the old module. Re-execute the setup cell (which calls `importlib.reload(prompt_pipeline)`). If you added new exports, you may need to re-run the setup cell of every downstream stage. |
| Stage 01–04 fails with `missing _pipeline_cache/corpus_docs.spacy` (or any other partial) | The producer chain wasn't run in order. Run stage `00_setup_and_corpus` first (writes the DocBin + corpus_meta), then 01–04 in order. |
| Consumer fails with `KeyError: 'Column not found:...'` from `alt_df` | Producer hasn't been re-run since a schema change. Run the producer chain (`00_setup_and_corpus` → `04_assemble_aggregate_write`) end-to-end first. |
| `mcp__jupyter__cell_execute` returns "Index out of range" | Stale tool registration in your Claude Code session — the kernel has just executed and the cell index shifted. Run `mcp__jupyter__notebook_get` to refresh your view of the cell list, then retry with the correct index. |
| `mcp__jupyter__cell_update` reports success but the cell didn't change | Pre-cutover corruption bug (silent UUID-mint + delete-then-insert). Fixed in `5580983 feat(jupyter-mcp)!: …`. If you're seeing this on a current container, `podman exec ov-jupyter sha256sum /home/user/.pixi/envs/default/lib/python3.13/site-packages/jupyter_mcp/rtc_adapter.py` and confirm it matches `697f4c038013968fdad2e65687329a7fd74805e1391094dfb78407059b1b973e`. If not, the container is on a stale image — run `ov update jupyter` to pull the post-cutover build. |
| Calling `mcp__jupyter__room_open` / `room_close` / `room_close_all` / `room_pick` returns "tool not found" | Expected post-cutover. These client-side room-management tools were deleted in `5580983`. The server now manages rooms invisibly via auto-attach + idle-room sweeper. Just call `notebook_*` / `cell_*` tools directly. |
| `room_list` shows two rows for the same notebook path | **Regression** — single-room invariant violated. File a bug. Should not happen post-cutover (verified live: 3 path forms → 1 room on `20_track_justification_rate.ipynb`). |
| Notebook on disk has more cells than expected after MCP cell-update batches | Pre-cutover phantom-cell residue. Should not occur post-cutover (in-place Y.Map mutation). If reproduced on a current container, check the deployed code SHA per row above; otherwise file a bug. |
| Edits to `.ipynb` via direct `Write` don't show up in JupyterLab | Expected — direct disk edits bypass the CRDT room. The upstream file-watcher will CRDT-merge them against in-memory state, producing duplicates. Don't direct-write `.ipynb` files; use the MCP `cell_*` tools. |
| Producer's `generated_at` timestamp is the only thing that differs between two YAML runs | Expected. Everything else is deterministic. |

---

*This file lives at the repo root and applies to any Claude instance editing the project. Be terse, name files precisely, and edit `.ipynb` files only through the Jupyter MCP server's `cell_*` / `notebook_*` tools — direct-disk edits bypass the CRDT room and confuse open UI tabs. Post-2026-05-06 cutover, the MCP server is reliable; the previous "graded hazard" framing has been retired.*
