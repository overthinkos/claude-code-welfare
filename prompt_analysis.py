"""Shared helpers for the consumer notebooks (01_overview, 02_sentence_register, ...).

The data pipeline lives in `00_data_pipeline.ipynb`; it writes
`prompt_linguistic_analysis.yaml`. Every consumer notebook starts with:

    from prompt_analysis import (load_yaml, build_alt_df, version_order,
                                  category_colors, SR_CLASS_COLORS,
                                  SENT_REGISTER_CLASSES)
    data = load_yaml()
    alt_df = build_alt_df(data)

Nothing in this module re-runs spaCy or any analyzer; consumers are pure data
viewers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# --- Constants -----------------------------------------------------------

# Tableau 10 — used for category color encoding across every chart.
TABLEAU10: list[str] = [
    "#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f",
    "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab",
]

# Fixed 6-tone palette for sentence_register classes. Order matches
# SENT_REGISTER_CLASSES (which is also the dominant tie-break order).
SR_CLASS_COLORS: dict[str, str] = {
    "collaborative": "#4e79a7",
    "permissive":    "#76b7b2",
    "appreciative":  "#59a14f",
    "imperative":    "#e15759",
    "directive":     "#f28e2c",
    "configuring":   "#af7aa1",
}

SENT_REGISTER_CLASSES: list[str] = list(SR_CLASS_COLORS.keys())

# Block-aware abbreviations for flat column prefixes in build_alt_df.
# Lifted unchanged from cell 43 of the original notebook.
_BLOCK_PREFIX: dict[str, str] = {
    "mood":              "mood",
    "register":          "",          # numeric metrics live at top level
    "stance":            "",          # already class-named: directive_pct, ...
    "sentence_register": "",          # already class-named: collaborative_sent_pct, ...
    "modality":          "",          # already class-named: deontic_pct, ...
    "all_caps":          "all_caps",
    "caps_imperative":   "caps_imp",
    "justification":     "just",
}


# --- I/O -----------------------------------------------------------------

def load_yaml(path: str | Path = "prompt_linguistic_analysis.yaml") -> dict:
    """Load the per-file + corpus + per-category YAML produced by 00_data_pipeline."""
    with open(path) as f:
        return yaml.safe_load(f)


# --- Flat per-file dataframe --------------------------------------------

def _flatten(rec: dict) -> dict:
    """Flatten one per-file record into a flat dict for Altair.

    Lifted from cell 43 of the original notebook; semantics unchanged.
    """
    out = {k: rec.get(k) or rec.get(k, "")
           for k in ("path", "category", "name", "description",
                     "ccVersion", "agentType", "n_tokens", "n_sents")}
    for block_name, block in rec["metrics"].items():
        if block_name == "vocab":
            for key, sub in block.items():
                out[f"{key}_count"]    = sub["count"]
                out[f"{key}_pct"]      = sub["pct"]
                out[f"{key}_per_sent"] = sub["per_sent"]
            continue
        prefix = _BLOCK_PREFIX.get(block_name, block_name)
        for k, v in block.items():
            if not isinstance(v, (int, float, str, type(None))):
                continue
            col = f"{prefix}_{k}" if prefix else k
            out[col] = v
    return out


def _ver_key(v: str) -> tuple[int, int, int]:
    """Sort key for a "MAJOR.MINOR.PATCH" version string. Empty string sorts first."""
    if not v:
        return (-1, -1, -1)
    parts = v.split(".")
    out: list[int] = []
    for p in parts[:3]:
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)  # type: ignore[return-value]


def _minor(v: str) -> str:
    if v.count(".") >= 2:
        return f"{v.split('.')[0]}.{v.split('.')[1]}"
    return v or "unknown"


def build_alt_df(data: dict) -> pd.DataFrame:
    """Build the flat per-file dataframe (one row per .md, ~115 columns).

    Adds two derived columns — ``ccVersion_sort`` (tuple) and ``ccMinor`` (str) —
    used by the ccVersion charts.
    """
    df = pd.DataFrame([_flatten(r) for r in data["files"]])
    df["ccVersion_sort"] = df["ccVersion"].apply(_ver_key)
    df["ccMinor"] = df["ccVersion"].apply(_minor)
    return df


def version_order(alt_df: pd.DataFrame) -> list[str]:
    """Return ccVersion strings sorted oldest → newest, excluding empty."""
    return (alt_df[alt_df["ccVersion"] != ""]
            .drop_duplicates("ccVersion")
            .sort_values("ccVersion_sort")
            ["ccVersion"]
            .tolist())


# --- Color helpers ------------------------------------------------------

def category_colors(cats: list[str]) -> dict[str, str]:
    """Map each corpus category to a Tableau 10 hex color (stable order)."""
    return {c: TABLEAU10[i % len(TABLEAU10)] for i, c in enumerate(cats)}


# --- Composite metrics --------------------------------------------------

def _zscore(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    return (s - s.mean()) / (s.std(ddof=0) or 1.0)


def directiveness(alt_df: pd.DataFrame) -> pd.Series:
    """Composite directiveness z-score per file (extended formula).

    Used by 05_correlation_directiveness and 06_ccversion_trends — kept
    centrally so both notebooks compute the same composite.

    Higher = more authoritative. The three "soft" classes subtract because
    they soften authority.
    """
    return (
        _zscore(alt_df["mood_marker_pct"])
        + _zscore(alt_df["hard_prohibitions_pct"])
        + _zscore(alt_df["caps_imp_pct"])
        + _zscore(alt_df["directive_sent_pct"])
        + _zscore(alt_df["configuring_sent_pct"])
        - _zscore(alt_df["collaborative_sent_pct"])
        - _zscore(alt_df["permissive_sent_pct"])
        - _zscore(alt_df["appreciative_sent_pct"])
    )
