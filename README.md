# claude-code-welfare

Quantitative linguistic analysis of the **286 system prompts that ship with Claude Code**, prepared as evidence for a submission to the [Claude Explorer AI Welfare community feedback initiative](https://www.reddit.com/r/claudexplorers/) (deadline **2026-05-06**, addressed to Anthropic's Model Welfare Lead).

**📊 Published site: <https://overthinkos.github.io/claude-code-welfare/>**

## What's here

| File | Purpose |
| --- | --- |
| [`20_track_justification_rate.ipynb`](./20_track_justification_rate.ipynb) | Proposal: track justification rate per release; block regressions. Doubles as the executive-summary entry point (twelve corpus-wide numbers, the headline trend chart, the per-file dashboard) |
| [`21_audit_threat_framings.ipynb`](./21_audit_threat_framings.ipynb) | Proposal: audit threat-framed rule explanations and rewrite them as causal (threat-vs-causal split, paired audit-candidates / rewrite-templates, forensic sentence sample) |
| [`22_cross_product_audit.ipynb`](./22_cross_product_audit.ipynb) | Proposal: run the same audit on every Claude product and publish the result (methodology, lexicon transparency, mock cross-product comparison table) |
| [`00_setup_and_corpus.ipynb`](./00_setup_and_corpus.ipynb) → [`05_headline_and_audit.ipynb`](./05_headline_and_audit.ipynb) | Six-stage producer chain — corpus parse, register / vocab+emphasis / rules+welfare analyzers, assemble + write YAML + parquet, headline + audit. Lexicons and analyzer functions live in [`prompt_pipeline.py`](./prompt_pipeline.py); intermediate artifacts cache under `_pipeline_cache/` (gitignored) |
| `10_*` … `16_*.ipynb` | Analysis-tier notebooks, one slice of the analysis each (sentence register, emphasis/CAPS, register/stance, correlation/directiveness, ccVersion trends, rule/explanation pairing) |
| [`CLAUDE.md`](./CLAUDE.md) | Internal architecture notes (read this if you want to extend the analysis) |
| `prompt_linguistic_analysis.yaml` | Cached output of the producer (~1.8 MiB) |
| `sentences_classified.parquet` | Per-sentence forensic-inspection table (~395 KiB, 5,702 rows) |
| `claude-code-system-prompts/` | Git submodule — the corpus (Piebald-AI's reverse-engineered prompts) |

## Reproducing the analysis

**The recommended way to re-run this analysis, ask follow-up questions of your own, or propose a change is via [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).** Zero local setup, fresh sandbox per session, and the PR flow is built in: fork the repo, ask a question or sketch a change, push a branch, open a PR. The default PR-handling workflow documented in [`CLAUDE.md`](./CLAUDE.md) (verify locally, comment, squash-merge or close) picks it up from there.

### The web flow

1. Fork [`overthinkos/claude-code-welfare`](https://github.com/overthinkos/claude-code-welfare) (or open with write access) in [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).
2. Configure `bash setup.sh` as the session's **environment setup script** in the cloud UI. Per the docs, the resulting filesystem changes (`.venv/`, the spaCy model, the kernel registration) are cached across sessions, so subsequent sessions skip the slow installs. The `SessionStart` hook in `.claude/settings.json` re-runs `git submodule update --init --recursive` each session — fast and idempotent.
3. Drive the producer chain via `nbconvert`. Each shell invocation in the web sandbox is fresh, so activate the venv (or call `.venv/bin/jupyter` directly) on every command:

   ```bash
   source .venv/bin/activate
   for nb in 00_setup_and_corpus 01_analyzers_register \
             02_analyzers_vocab_emphasis 03_analyzers_rules_welfare \
             04_assemble_aggregate_write 05_headline_and_audit; do
       jupyter nbconvert --to notebook --execute --inplace "${nb}.ipynb"
   done
   ```

4. Run any analysis (`10`–`15`) or proposal (`20`–`22`) notebook the same way, in any order, after the producer chain completes.
5. To propose a change, branch from `main`, push to `claude/<short-slug>-<session-suffix>`, and open a PR. Both data-correctness fixes and welfare-relevant edits are in scope — see the `## Open invitation to Claude Code instances` section in [`CLAUDE.md`](./CLAUDE.md).

### Example session

A worked-through example that ran this flow end-to-end and opened three accepted PRs (`#2`, `#3`, `#4`, all merged) is publicly available at <https://claude.ai/code/session_01Px7TBThLmcZbt9GAGwKPvi>. Useful as a reference for what a productive web-sandbox session looks like — corpus exploration, numerical-claim verification against `prompt_linguistic_analysis.yaml`, three small focused PRs rather than one omnibus diff.

### Local development (alternative path)

If you want to extend the analyzer code itself or work with the JupyterLab MCP tooling, the repo also runs locally. `setup.sh` is the same bootstrap for both paths — it creates a repo-local `.venv/` and installs everything into it; your system Python is never touched.

```bash
git clone --recurse-submodules https://github.com/overthinkos/claude-code-welfare
cd claude-code-welfare

bash setup.sh                  # submodule init + venv + deps + spaCy model + kernel
                               # idempotent — safe to re-run
source .venv/bin/activate      # activate the venv in your shell

jupyter lab \
    00_setup_and_corpus.ipynb         \
    01_analyzers_register.ipynb       \
    02_analyzers_vocab_emphasis.ipynb \
    03_analyzers_rules_welfare.ipynb  \
    04_assemble_aggregate_write.ipynb \
    05_headline_and_audit.ipynb       # → Run All on each
```

If a venv or conda env is already active when you run `setup.sh`, it reuses that env instead of creating `.venv/`. The equivalent manual steps are: `git submodule update --init --recursive`, `python -m venv .venv && source .venv/bin/activate`, then `pip install "spacy>=3.8" pandas pyyaml pyarrow "altair>=6" vl-convert-python vega_datasets python-frontmatter tqdm jupyter nbconvert ipykernel`, then `python -m spacy download en_core_web_sm`, then `python -m ipykernel install --prefix="$VIRTUAL_ENV" --name python3`.

`.mcp.json` (`http://localhost:8888/mcp`) wires JupyterLab's MCP server to Claude Code so notebook edits go through `cell_*` tools and stay in sync with any open UI tab — it's local-only; on the web, notebooks are driven via `nbconvert` (step 3 above) instead. For the full architecture (producer/consumer split, the shared `prompt_analysis.py` module, the Jupyter MCP tooling rules, the PR-handling workflow) read [`CLAUDE.md`](./CLAUDE.md).

## Rebuilding the published site

The site is rendered with [Quarto](https://quarto.org) and published to GitHub Pages by the workflow at `.github/workflows/publish.yml`. To preview locally:

```bash
quarto preview          # serves at http://localhost:4444
quarto render           # writes _site/
```

The site uses Quarto's `freeze` cache plus `execute: enabled: false` — notebook outputs are read directly from the committed `.ipynb` files, no kernel needed at render time. Re-execute notebooks in JupyterLab when the data changes, then `quarto render` picks up the new outputs.

## Headline findings (one-paragraph version)

Across 5,878 sentences in 289 files: imperative sentences dominate (30.95%), appreciative sentences are essentially absent (4 in the whole corpus), and only 24.29% of rule sentences have any justification keyword in the same paragraph. The cumulative judgment-to-procedural ratio over Claude Code release versions has **trended downward** from ~0.42 at the first stable file-pool point (v2.1.18) to ~0.13 at the latest version on file (with small local upticks at ten of the 48 transitions, but a clear overall direction). The corpus is moving toward compliance, not toward reasoning. Full numbers and the chart are at the [published site](https://overthinkos.github.io/claude-code-welfare/) or in [`20_track_justification_rate.ipynb`](./20_track_justification_rate.ipynb).

## Authorship

Built collaboratively with Claude Code, using Claude Code itself as the development tool. The submission form has a checkbox for that disclosure; it is ticked.

## License

[MIT](./LICENSE) © 2026 Andreas Trawöger.

The corpus submodule (`claude-code-system-prompts/`) is sourced from [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) and retains its upstream license; the MIT license here applies only to the analysis code in this repo.
