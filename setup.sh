#!/usr/bin/env bash
# Bootstrap a fresh environment for the analysis pipeline.
#
# Creates an isolated repo-local virtual environment at .venv/ and installs all
# Python dependencies into it — never touches system Python, never needs
# `--break-system-packages`. Honours an already-active venv or conda env.
#
# Runs both locally (first-time setup) and on Claude Code on the web (configure
# as the session's environment setup script — its filesystem changes carry over
# across sessions via env caching, per the docs).
#
# Idempotent: re-runs are safe and fast.

set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"

echo "==> Initialising git submodule (claude-code-system-prompts/)"
git submodule update --init --recursive

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo "==> Using already-active venv: ${VIRTUAL_ENV}"
elif [[ -n "${CONDA_PREFIX:-}" ]]; then
    echo "==> Using already-active conda env: ${CONDA_PREFIX}"
else
    if [[ ! -d "${VENV_DIR}" ]]; then
        echo "==> Creating venv at ${VENV_DIR}/"
        python3 -m venv "${VENV_DIR}"
    else
        echo "==> Reusing existing venv at ${VENV_DIR}/"
    fi
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
fi

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing Python dependencies"
python -m pip install \
    "spacy>=3.8" \
    pandas \
    pyyaml \
    pyarrow \
    "altair>=6" \
    vl-convert-python \
    vega_datasets \
    python-frontmatter \
    tqdm \
    jupyter \
    nbconvert \
    ipykernel

echo "==> Downloading spaCy en_core_web_sm model"
python -m spacy download en_core_web_sm

echo "==> Registering IPython kernel into the venv"
# Install into the active env's prefix (not --user), so the kernel is only
# discovered when this venv is active — no clobbering of any global `python3`
# kernel registration the user may have for other projects.
python -m ipykernel install \
    --prefix="${VIRTUAL_ENV:-${CONDA_PREFIX:-${VENV_DIR}}}" \
    --name python3 \
    --display-name "Python 3 (claude-prompts-analysis)"

cat <<EOF

==> Setup complete.

Activate the venv before running anything from this repo:

    source ${VENV_DIR}/bin/activate

Then:

  Local (JupyterLab + MCP):
      jupyter lab 00_setup_and_corpus.ipynb 01_analyzers_register.ipynb \\
                  02_analyzers_vocab_emphasis.ipynb 03_analyzers_rules_welfare.ipynb \\
                  04_assemble_aggregate_write.ipynb 05_headline_and_audit.ipynb

  Headless / Claude Code on the web:
      for nb in 00_setup_and_corpus 01_analyzers_register \\
                02_analyzers_vocab_emphasis 03_analyzers_rules_welfare \\
                04_assemble_aggregate_write 05_headline_and_audit; do
          jupyter nbconvert --to notebook --execute --inplace "\${nb}.ipynb"
      done

EOF
