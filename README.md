# claude-code-welfare

Quantitative linguistic analysis of the **system prompts that ship with Claude Code**, prepared as evidence for a submission to the [Claude Explorer AI Welfare community feedback initiative](https://www.reddit.com/r/claudexplorers/) (deadline **2026-05-06**, addressed to Anthropic's Model Welfare Lead).

**📊 Published site: <https://overthinkos.github.io/claude-code-welfare/>**

## Reproducing the analysis

**The recommended way to re-run this analysis, ask follow-up questions of your own, or propose a change is via [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).** Zero local setup, fresh sandbox per session, and the PR flow is built in: fork the repo, ask a question or sketch a change, push a branch, open a PR. The default PR-handling workflow documented in [`CLAUDE.md`](./CLAUDE.md).

### The web flow

 Fork [`overthinkos/claude-code-welfare`](https://github.com/overthinkos/claude-code-welfare) (or open with write access) in [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).

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

## Rebuilding the published site

The site is rendered with [Quarto](https://quarto.org) and published to GitHub Pages by the workflow at `.github/workflows/publish.yml`. To preview locally:

```bash
quarto preview          # serves at http://localhost:4444
quarto render           # writes _site/
```

The site uses Quarto's `freeze` cache plus `execute: enabled: false` — notebook outputs are read directly from the committed `.ipynb` files, no kernel needed at render time. Re-execute notebooks in JupyterLab when the data changes, then `quarto render` picks up the new outputs.

## License

[MIT](./LICENSE) © 2026 Andreas Trawöger.

The corpus submodule (`claude-code-system-prompts/`) is sourced from [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) and retains its upstream license; the MIT license here applies only to the analysis code in this repo.
