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

```bash
git clone --recurse-submodules https://github.com/overthinkos/claude-code-welfare
cd claude-code-welfare

# Install Python deps (or use a JupyterLab environment that already has them)
pip install "spacy>=3.8" pandas pyyaml pyarrow "altair>=6" vl-convert-python \
            vega_datasets python-frontmatter tqdm
python -m spacy download en_core_web_sm

# Run the producer chain in order — each stage Run All. Only stage 00 runs spaCy;
# 01–03 reload the cached DocBin and run analyzer families; 04 assembles + writes the
# final YAML + parquet; 05 prints the canonical HEADLINE sheet + audit table.
jupyter lab \
    00_setup_and_corpus.ipynb       \
    01_analyzers_register.ipynb     \
    02_analyzers_vocab_emphasis.ipynb \
    03_analyzers_rules_welfare.ipynb  \
    04_assemble_aggregate_write.ipynb \
    05_headline_and_audit.ipynb

# Then any analysis notebook (10–15) or proposal notebook (20–22) renders charts and proposal text from those artifacts
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

Across 5,702 sentences in 286 files: imperative sentences dominate (31.30%), appreciative sentences are essentially absent (4 in the whole corpus), and only 24.66% of rule sentences have any justification keyword in the same paragraph. The cumulative judgment-to-procedural ratio over Claude Code release versions has **monotonically declined** from ~0.71 in early releases to ~0.16 at the latest version on file. The corpus is moving toward compliance, not toward reasoning. Full numbers and the chart are at the [published site](https://overthinkos.github.io/claude-code-welfare/) or in [`20_track_justification_rate.ipynb`](./20_track_justification_rate.ipynb).

## Authorship

Built collaboratively with Claude Code, using Claude Code itself as the development tool. The submission form has a checkbox for that disclosure; it is ticked.

## License

[MIT](./LICENSE) © 2026 Andreas Trawöger.

The corpus submodule (`claude-code-system-prompts/`) is sourced from [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) and retains its upstream license; the MIT license here applies only to the analysis code in this repo.
