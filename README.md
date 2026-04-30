# claude-code-welfare

Quantitative linguistic analysis of the **287 system prompts that ship with Claude Code**, prepared as evidence for a submission to the [Claude Explorer AI Welfare community feedback initiative](https://www.reddit.com/r/claudexplorers/) (deadline **2026-05-06**, addressed to Anthropic's Model Welfare Lead).

**📊 Published site: <https://overthinkos.github.io/claude-code-welfare/>**

## What's here

| File | Purpose |
| --- | --- |
| [`PROPOSAL.md`](./PROPOSAL.md) | The three-idea ≤3,000-character pitch addressed to Anthropic |
| [`08_summary.ipynb`](./08_summary.ipynb) | Executive summary — twelve corpus-wide numbers, the headline chart, conclusions |
| [`00_data_pipeline.ipynb`](./00_data_pipeline.ipynb) | Producer — spaCy + custom analyzers, writes the YAML + parquet artifacts |
| `01_*` … `07_*.ipynb` | Consumer notebooks, one slice of the analysis each |
| [`GLOSSARY.md`](./GLOSSARY.md) | Plain-English definitions of every linguistic/statistical term used anywhere |
| [`CLAUDE.md`](./CLAUDE.md) | Internal architecture notes (read this if you want to extend the analysis) |
| `prompt_linguistic_analysis.yaml` | Cached output of the producer (~1.8 MiB) |
| `sentences_classified.parquet` | Per-sentence forensic-inspection table (~395 KiB, 5,694 rows) |
| `claude-code-system-prompts/` | Git submodule — the corpus (Piebald-AI's reverse-engineered prompts) |

## Reproducing the analysis

```bash
git clone --recurse-submodules https://github.com/overthinkos/claude-code-welfare
cd claude-code-welfare

# Install Python deps (or use a JupyterLab environment that already has them)
pip install "spacy>=3.8" pandas pyyaml pyarrow "altair>=6" vl-convert-python \
            vega_datasets python-frontmatter tqdm
python -m spacy download en_core_web_sm

# Run the producer (writes prompt_linguistic_analysis.yaml + sentences_classified.parquet)
jupyter lab 00_data_pipeline.ipynb        # → Run All

# Then any consumer notebook (01–08) renders charts from those artifacts
```

For the full architecture (producer/consumer split, the shared `prompt_analysis.py` module, the Jupyter MCP tooling rules) read [`CLAUDE.md`](./CLAUDE.md).

## Rebuilding the published site

The site is rendered with [Quarto](https://quarto.org) and published to GitHub Pages by the workflow at `.github/workflows/publish.yml`. To preview locally:

```bash
quarto preview          # serves at http://localhost:4444
quarto render           # writes _site/
```

The site uses Quarto's `freeze` cache plus `execute: enabled: false` — notebook outputs are read directly from the committed `.ipynb` files, no kernel needed at render time. Re-execute notebooks in JupyterLab when the data changes, then `quarto render` picks up the new outputs.

## Headline findings (one-paragraph version)

Across 5,694 sentences in 287 files: imperative sentences dominate (30.84%), appreciative sentences are essentially absent (4 in the whole corpus), and only 24.28% of rule sentences have any justification keyword in the same paragraph. The cumulative judgment-to-procedural ratio over Claude Code release versions has **monotonically declined** from ~0.65 in early releases to ~0.16 at the latest version on file. The corpus is moving toward compliance, not toward reasoning. Full numbers and the chart are at the [published site](https://overthinkos.github.io/claude-code-welfare/) or in [`08_summary.ipynb`](./08_summary.ipynb).

## Authorship

Built collaboratively with Claude Code, using Claude Code itself as the development tool. The submission form has a checkbox for that disclosure; it is ticked.

## License

[MIT](./LICENSE) © 2026 Andreas Trawöger.

The corpus submodule (`claude-code-system-prompts/`) is sourced from [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) and retains its upstream license; the MIT license here applies only to the analysis code in this repo.
