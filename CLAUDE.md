# CLAUDE.md — `claude-prompts-analysis`

## What this repo is

Quantitative linguistic analysis of the 289-file `claude-code-system-prompts` corpus (submodule, pinned at v2.1.132). A 6-stage producer chain (`00`–`05`) profiles every prompt with spaCy + hand-curated lexicons and emits `prompt_linguistic_analysis.yaml` + `sentences_classified.parquet`. Six analysis-tier notebooks (`10`–`15`) and three proposal notebooks (`20`–`22`) consume those artifacts.

Run order, deps, and rebuild instructions live in `README.md`. The published thesis lives in `index.qmd`. Every notebook self-documents in its first markdown cell.

## Conventions

### Producer vs consumer split

`prompt_pipeline.py` is producer-only — imported only by `00_setup_and_corpus` → `04_assemble_aggregate_write`. `prompt_analysis.py` is consumer-only — imported by `05_headline_and_audit` and every `10_*`–`22_*` notebook. **Consumers MUST NOT import from `prompt_pipeline`.** `SENT_REGISTER_CLASSES` lives in `prompt_analysis.py`; `prompt_pipeline.py` re-exports it to keep one source of truth. The module docstrings spell out the full public API — don't duplicate them here.

### Canonical numbers convention

Every corpus-wide figure cited in any notebook flows from `prompt_analysis.headline_numbers(data, alt_df=…, parquet=…)` — the canonical `HEADLINE` sheet, produced by `05_headline_and_audit.ipynb`. Markdown prose stays *qualitative* ("near zero", "roughly a quarter"); precise figures live in adjacent code-cell printouts that read straight from `HEADLINE[…]`. Hard-coding numbers in markdown is the easiest way to reintroduce drift, so don't.

### Opinion cells convention

Each analysis-tier notebook (`10`–`15`) opens with the four-cell pattern `# Title (intro)` → `### Terms used` → `### Observation (Claude)` → setup code. The Observation cell uses the heading `### Observation (Claude)` (no suffix) and keeps its `***` opener / `>` blockquoted body / `---` closer framing. Each proposal notebook (`20`–`22`) closes with a three-cell `## Conclusions / ## Recommendations / ## Limitations` triplet, all marked `(Claude) — opinion, not data`. The producer chain (`00`–`05`) carries no opinion cells. Keep the data tier and the interpretation tier visually separable.

## Editing notebooks via the Jupyter MCP server

Use the MCP `cell_*` / `notebook_*` tools for every `.ipynb` edit. Direct `Write` / `sed` / `jq` to a notebook bypasses the CRDT room and confuses any open UI tab. For `.py` / `.md` / `.yaml` / `.json`, regular `Write` / `Edit` is fine.

The 11 current tools:

| Category | Tools |
|---|---|
| Notebook | `notebook_list`, `notebook_create`, `notebook_get`, `notebook_watch`, `notebook_list_users` |
| Cell | `cell_get`, `cell_update`, `cell_insert`, `cell_delete`, `cell_execute` |
| Diagnostic | `room_list` (read-only; verify single-room invariant per path) |

Path canonicalization is at the boundary — `"foo.ipynb"`, `"./foo.ipynb"`, and the absolute workspace path all hit the same room. After a batch of cell mutations, call `notebook_get` once and check the cell count matches expectations.

After editing `prompt_analysis.py`, the kernel still has the old module cached; the standard setup cell calls `importlib.reload(prompt_analysis)` to force a re-import. If you add new exports, re-run the setup cell.

The `.mcp.json` in this repo points at `http://localhost:8888/mcp`. Don't change it without reason.

## Local vs Claude Code on the web

The repo is designed to run in two modes:

- **Local** — JupyterLab + the Jupyter MCP server on port 8888. Edits go through `cell_*` tools, the kernel stays alive between cells, and `importlib.reload(prompt_analysis)` in the setup cell handles module re-imports.
- **Claude Code on the web** ([docs](https://code.claude.com/docs/en/claude-code-on-the-web)) — fresh Ubuntu 24.04 sandbox per session, no JupyterLab process, no MCP server. Producer stages run via `jupyter nbconvert --to notebook --execute --inplace <nb>` in strict order `00 → 01 → 02 → 03 → 04 → 05`. Each `nbconvert` invocation is a fresh kernel, so the `importlib.reload` line is a no-op.

`setup.sh` at the repo root is the canonical bootstrap for both modes. It creates a repo-local venv at `.venv/` (gitignored), installs every dependency into it, downloads the spaCy model, and registers an IPython kernel scoped to that venv. No `--break-system-packages`; system Python is never touched. If a venv or conda env is already active when the script runs, it reuses that env instead of creating `.venv/`. Locally: `bash setup.sh` once, then `source .venv/bin/activate` before running notebooks. On the web: configure `bash setup.sh` as the session's environment setup script in the cloud UI — the docs note that setup-script filesystem changes persist across sessions via env caching, so `.venv/` carries over.

Each Bash tool call on Claude Code on the web is a fresh shell — `VIRTUAL_ENV` does not persist between calls. So every `jupyter` / `python` / `nbconvert` invocation in the web sandbox needs to either prefix `source .venv/bin/activate &&` or call the venv binary directly (`.venv/bin/jupyter …`). The `SessionStart` hook in `.claude/settings.json` re-runs only the cheap, idempotent `git submodule update --init --recursive` each session — pip installs are kept out of the hook so local sessions don't reinstall dependencies on every start.

`.mcp.json` (`localhost:8888/mcp`) only resolves locally. On the web, MCP `cell_*` tools are unavailable — drive notebooks via `nbconvert` instead.

## Out of scope

- Sentiment analysis via external lexicons (VADER, Hu-Liu, spacytextblob) — rejected to preserve audit transparency.
- `en_core_web_md` / `en_core_web_lg` — no measurable gain for rule-based per-sentence classification; +43–500 MB.
- Languages other than English.
- Per-sentence text in the YAML itself — `sentences_classified.parquet` carries it instead. Load with `pd.read_parquet("sentences_classified.parquet")`.
- Cross-product comparison (Claude.ai, the API, Projects, Skills) — corpus access not available; proposal `22` is the wish-list version.
- Human-judgment validation of the composite directiveness metric — needs annotators.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Consumer notebook `ImportError` from `prompt_analysis` | Kernel cached the old module. Setup cell's `importlib.reload(prompt_analysis)` handles it; restart the kernel if it persists. |
| Producer `ImportError` from `prompt_pipeline` | Same root cause. Re-execute the setup cell (calls `importlib.reload(prompt_pipeline)`). For new exports, re-run the setup cell of every downstream stage. |
| Stage `01`–`04` fails with missing `_pipeline_cache/*` | Producer chain wasn't run in order. Run `00_setup_and_corpus` first, then `01`–`04`. |
| Consumer `KeyError: 'Column not found'` from `alt_df` | Producer hasn't been re-run since a schema change. Run `00` → `04` end-to-end. |
| `cell_execute` returns "Index out of range" | Cell list shifted (kernel just executed). Run `notebook_get` to refresh, then retry with the correct index. |
| `room_list` shows two rows for the same path | Single-room invariant violated. File a bug. |
| Edits to a `.ipynb` via direct `Write` don't show up in JupyterLab | Expected — disk edits bypass the CRDT room. Use `cell_*` tools instead. |
| Producer's `generated_at` is the only diff between two YAML runs | Expected. Everything else is deterministic. |
| `claude-code-system-prompts/` empty after fresh clone | `git submodule update --init --recursive` (also runs as the `SessionStart` hook). |
| MCP `cell_*` tool fails on Claude Code on the web | Expected — no JupyterLab on the web. Drive notebooks via `jupyter nbconvert --execute --inplace` instead. |

---

*Edit `.ipynb` files via the Jupyter MCP server. Be terse. Name files precisely.*
