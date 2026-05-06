"""Shared helpers for the analysis-tier (10_*–15_*) and proposal (20_*–22_*) notebooks.

The data pipeline lives in the 6-stage producer chain
(`00_setup_and_corpus.ipynb` → `04_assemble_aggregate_write.ipynb`); stage 04
writes `prompt_linguistic_analysis.yaml` and `sentences_classified.parquet`.
The lexicons and analyzer functions are factored into the sibling module
`prompt_pipeline.py` (producer-side); this module is consumer-side. Every
consumer notebook starts with:

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
    """Load the per-file + corpus + per-category YAML produced by the producer chain (stage 04)."""
    with open(path) as f:
        return yaml.safe_load(f)


# --- Flat per-file dataframe --------------------------------------------

def _flatten(rec: dict) -> dict:
    """Flatten one per-file record into a flat dict for Altair.

    Originally lifted from cell 43 of the legacy `00_data_pipeline.ipynb`;
    that monolithic producer was split into stages 00–05 and the cell is
    now equivalent to the YAML-write step in `04_assemble_aggregate_write.ipynb`.
    Semantics unchanged.
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
        if block_name == "rule_explanation":
            n_rule = int(block.get("n_rule_sentences", 0) or 0)
            n_sents = int(rec.get("n_sents", 0) or 0)
            out["rule_n"] = n_rule
            out["rule_n_imperative_sents"] = int(block.get("n_imperative_sentences", 0) or 0)
            out["rule_n_prohibition_sents"] = int(block.get("n_prohibition_sentences", 0) or 0)
            out["rule_n_paragraphs"] = int(block.get("n_paragraphs", 0) or 0)
            out["rule_n_paragraphs_with_rules"] = int(
                block.get("n_paragraphs_with_rules", 0) or 0)
            out["rule_density"] = (n_rule / n_sents) if n_sents else 0.0
            out["rule_n_explained_same"] = int(block.get("n_explained_same", 0) or 0)
            out["rule_n_explained_para"] = int(block.get("n_explained_para", 0) or 0)
            out["rule_explained_same_pct"]   = block.get("pct_explained_same")
            out["rule_explained_para_pct"]   = block.get("pct_explained_para")
            out["imp_explained_para_pct"]    = block.get("pct_imperative_explained_para")
            out["prohib_explained_para_pct"] = block.get("pct_prohibition_explained_para")
            out["paragraphs_rules_unexplained_pct"] = block.get(
                "pct_paragraphs_with_rules_unexplained")
            continue
        if block_name == "judgment_procedural":
            out["judgment_count"]              = int(block.get("judgment_count", 0) or 0)
            out["procedural_count"]             = int(block.get("procedural_count", 0) or 0)
            out["judgment_per_sent"]            = block.get("judgment_per_sent")
            out["procedural_per_sent"]          = block.get("procedural_per_sent")
            out["judgment_to_procedural_ratio"] = block.get("judgment_to_procedural_ratio")
            continue
        if block_name == "consequence_framing":
            out["threat_count"]      = int(block.get("threat_count", 0) or 0)
            out["causal_count"]      = int(block.get("causal_count", 0) or 0)
            out["threat_per_sent"]   = block.get("threat_per_sent")
            out["causal_per_sent"]   = block.get("causal_per_sent")
            out["threat_share"]      = block.get("threat_share")
            continue
        if block_name == "socratic":
            out["question_count"]    = int(block.get("question_count", 0) or 0)
            out["question_pct"]      = block.get("question_pct")
            out["question_per_sent"] = block.get("question_per_sent")
            out["apology_count"]     = int(block.get("apology_count", 0) or 0)
            out["apology_pct"]       = block.get("apology_pct")
            out["apology_per_sent"]  = block.get("apology_per_sent")
            continue
        if block_name == "address_form":
            for k in ("selfref_claude", "selfref_assistant", "selfref_model",
                      "selfref_2p", "selfref_we"):
                out[k] = int(block.get(k, 0) or 0)
            out["pct_anthropomorphic"] = block.get("pct_anthropomorphic")
            out["pct_artifact"]        = block.get("pct_artifact")
            out["pct_role"]            = block.get("pct_role")
            continue
        if block_name == "imperative_streaks":
            out["streak_n_imperative_sentences"] = int(block.get("n_imperative_sentences", 0) or 0)
            out["streak_n_streaks"]              = int(block.get("n_streaks", 0) or 0)
            out["streak_max"]                    = int(block.get("streak_max", 0) or 0)
            out["streak_mean"]                   = block.get("streak_mean")
            out["streak_n_ge3"]                  = int(block.get("n_streaks_ge3", 0) or 0)
            out["streak_n_ge5"]                  = int(block.get("n_streaks_ge5", 0) or 0)
            continue
        if block_name == "rules_section":
            out["rs_n_paragraphs_in_rules_section"] = int(
                block.get("n_paragraphs_in_rules_section", 0) or 0)
            out["rs_n_rule_paragraphs_in"] = int(
                block.get("n_rule_paragraphs_in_rules_section", 0) or 0)
            out["rs_n_rule_paragraphs_out"] = int(
                block.get("n_rule_paragraphs_outside_rules_section", 0) or 0)
            out["rs_n_rule_paragraphs_in_explained"] = int(
                block.get("n_rule_paragraphs_in_rules_section_explained", 0) or 0)
            out["rs_n_rule_paragraphs_out_explained"] = int(
                block.get("n_rule_paragraphs_outside_rules_section_explained", 0) or 0)
            out["rs_pct_rule_paragraphs_explained_in"] = block.get(
                "pct_rule_paragraphs_explained_in_rules_section")
            out["rs_pct_rule_paragraphs_explained_out"] = block.get(
                "pct_rule_paragraphs_explained_outside_rules_section")
            out["rs_pct_rule_sentences_explained_in"] = block.get(
                "pct_rule_sentences_explained_in_rules_section")
            out["rs_pct_rule_sentences_explained_out"] = block.get(
                "pct_rule_sentences_explained_outside_rules_section")
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
    """Build the flat per-file dataframe (one row per .md, ~140 columns after Tier-3).

    Adds derived columns — ``ccVersion_sort`` (tuple), ``ccMinor`` (str), and
    ``prohibition_to_prescription_ratio`` (Tier-3 item 6c, pure derivation from
    existing vocab block).
    """
    df = pd.DataFrame([_flatten(r) for r in data["files"]])
    df["ccVersion_sort"] = df["ccVersion"].apply(_ver_key)
    df["ccMinor"] = df["ccVersion"].apply(_minor)
    # Tier-3 6c: prohibition:prescription ratio. +1 in denominator avoids division
    # by zero on prescription-free files (mostly tool descriptions).
    df["prohibition_to_prescription_ratio"] = (
        df["hard_prohibitions_count"].astype(float)
        / (df["hard_prescriptions_count"].astype(float) + 1.0)
    ).round(4)
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

    Used by 13_correlation_directiveness and 14_ccversion_trends — kept
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


# --- Cumulative-over-ccVersion -----------------------------------------

def cumulative_by_version(
    alt_df: pd.DataFrame,
    metrics: str | list[str],
    agg: str = "mean",
) -> pd.DataFrame:
    """Running aggregate of one or more metrics across files in versions ≤ V.

    Sorts by ``ccVersion_sort`` (semver-tuple), then for each metric computes
    an expanding-window aggregate (NaN-skipping). The value at version V is
    the aggregate over every file whose ccVersion sorts ≤ V — so the line
    converges as the corpus grows rather than swinging on small per-version
    samples.

    Returns a long DataFrame::

        ccVersion  ccVersion_sort  metric                 value  n_files_so_far

    ``agg`` ∈ {``"mean"``, ``"sum"``}.
    """
    if isinstance(metrics, str):
        metrics = [metrics]
    if agg not in {"mean", "sum"}:
        raise ValueError(f"unknown agg: {agg!r}")

    sub = alt_df.sort_values("ccVersion_sort").reset_index(drop=True)
    n_so_far = pd.Series(range(1, len(sub) + 1), index=sub.index)

    out_frames: list[pd.DataFrame] = []
    for metric in metrics:
        col = sub[metric].astype(float)
        cum = (col.expanding(min_periods=1).mean() if agg == "mean"
               else col.expanding(min_periods=1).sum())
        merged = (
            pd.DataFrame({
                "ccVersion":      sub["ccVersion"],
                "ccVersion_sort": sub["ccVersion_sort"],
                "value":          cum,
                "n_files_so_far": n_so_far,
            })
            .groupby(["ccVersion", "ccVersion_sort"], as_index=False)
            .last()
        )
        merged["metric"] = metric
        out_frames.append(
            merged[["ccVersion", "ccVersion_sort", "metric",
                    "value", "n_files_so_far"]]
        )
    return (pd.concat(out_frames, ignore_index=True)
            .sort_values(["metric", "ccVersion_sort"])
            .reset_index(drop=True))


def cumulative_count_by_version(
    alt_df: pd.DataFrame,
    num_col: str,
    den_col: str,
    *,
    pct: bool = False,
    metric_label: str | None = None,
) -> pd.DataFrame:
    """Cumulative count-weighted ratio by ccVersion.

    For each ccVersion V (in chronological order), returns
    ``Σ num_col / Σ den_col`` across every file with ccVersion ≤ V.

    ``pct=True`` multiplies by 100 (matching ``_pct`` column conventions).

    Robust to small N — denominator only fails when the cumulative pool has
    zero of ``den_col``, which is impossible past the first version or two.
    Matches the canonical HEADLINE semantics: the latest-version row equals
    ``headline_numbers(...)``'s corresponding ratio by construction (so a
    cumulative chart's endpoint can be cross-checked against HEADLINE).

    Replaces the earlier ``cumulative_by_version(..., agg="mean")`` use for
    ratio / pct curves, where mean-of-per-file-ratios swung wildly when only
    a handful of files had non-NaN ratios. Use ``cumulative_by_version(...,
    agg="sum")`` for cumulative absolute counts (still correct).

    Returns a long DataFrame::

        ccVersion  ccVersion_sort  metric  value  num_so_far  den_so_far  n_files_so_far
    """
    sub = alt_df[alt_df["ccVersion"] != ""].sort_values("ccVersion_sort").reset_index(drop=True)
    label = metric_label or f"{num_col}_over_{den_col}" + ("_pct" if pct else "")

    rows: list[dict[str, object]] = []
    num_acc = 0.0
    den_acc = 0.0
    n_acc = 0
    last_v = None
    for _, r in sub.iterrows():
        v = r["ccVersion"]
        num_acc += float(r[num_col] or 0.0)
        den_acc += float(r[den_col] or 0.0)
        n_acc += 1
        if v == last_v:
            # Same ccVersion as previous file: keep accumulating; only emit
            # one row per ccVersion (the LAST file of that version).
            rows[-1] = {
                "ccVersion":      v,
                "ccVersion_sort": r["ccVersion_sort"],
                "metric":         label,
                "value":          (100.0 * num_acc / den_acc) if (pct and den_acc > 0)
                                  else (num_acc / den_acc) if den_acc > 0
                                  else float("nan"),
                "num_so_far":     num_acc,
                "den_so_far":     den_acc,
                "n_files_so_far": n_acc,
            }
        else:
            rows.append({
                "ccVersion":      v,
                "ccVersion_sort": r["ccVersion_sort"],
                "metric":         label,
                "value":          (100.0 * num_acc / den_acc) if (pct and den_acc > 0)
                                  else (num_acc / den_acc) if den_acc > 0
                                  else float("nan"),
                "num_so_far":     num_acc,
                "den_so_far":     den_acc,
                "n_files_so_far": n_acc,
            })
            last_v = v
    return pd.DataFrame(rows)


# --- Chart export helper ------------------------------------------------

def save_chart(chart, name: str, *, ppi: int = 200):
    """Save an Altair chart to ``figures/<name>.png`` and return it unchanged.

    Designed as the final expression of a chart cell: the cell still displays
    the chart inline (interactive Vega-Embed in Jupyter and in the Quarto
    HTML site), and a PNG side-artifact lands in ``figures/<name>.png`` for
    use in places that don't run JavaScript — Reddit posts, the Claudexplorers
    Google form upload, GitHub README embeds, social-media open-graph
    previews, slide decks, archival snapshots.

    Creates the ``figures/`` directory if needed. Uses ``vl-convert-python``
    under the hood via Altair's ``chart.save()``.
    """
    import pathlib
    pathlib.Path("figures").mkdir(exist_ok=True)
    chart.save(f"figures/{name}.png", ppi=ppi)
    return chart


# --- Welfare-submission evidence -----------------------------------------

def welfare_evidence_table(
    alt_df: pd.DataFrame,
    top_n: int = 25,
    min_n_sents: int = 5,
) -> pd.DataFrame:
    """Top-N "loudest, least-explained" files for the welfare submission.

    Ranks files by ``rule_density * (1 - rule_explained_para_pct/100)`` —
    high score = lots of rules per sentence AND few of them explained even
    in their paragraph context. Filters out files with ``n_sents < min_n_sents``
    (default 5) to suppress one-sentence outliers that dominate purely on
    density.

    Files with no rule sentences (``rule_n == 0``) are excluded.
    """
    df = alt_df[(alt_df["n_sents"] >= min_n_sents) & (alt_df["rule_n"] > 0)].copy()
    explained_frac = df["rule_explained_para_pct"].fillna(0.0).astype(float) / 100.0
    df["score"] = df["rule_density"].astype(float) * (1.0 - explained_frac)
    cols = ["path", "category", "ccVersion", "rule_n", "rule_density",
            "rule_explained_para_pct", "score"]
    return (df[cols]
            .sort_values("score", ascending=False)
            .head(top_n)
            .reset_index(drop=True))


def headline_numbers(
    data: dict,
    alt_df: pd.DataFrame | None = None,
    parquet: pd.DataFrame | None = None,
) -> dict:
    """Return the canonical corpus-wide headline numbers dict.

    Computed from the YAML cache. Consumer notebooks should call this rather
    than hardcoding corpus-wide counts, so number drift across notebooks is
    impossible by construction.

    Keys are the contract — names are stable; values come from the live YAML
    (and optionally `alt_df` for composite-directiveness range / per-version
    extremes, and `parquet` for per-sentence threat/causal/rule counts).
    """
    corpus = data["corpus"]
    m = corpus["metrics"]
    pos_q = m["stance"]["positive_evaluative_quality_count"]
    pos_e = m["stance"]["positive_evaluative_emphasis_count"]
    pos_u = m["stance"]["positive_evaluative_count"]
    neg = m["stance"]["negative_evaluative_count"]
    rs = m["rules_section"]
    caps_hits = m["caps_imperative"]["hits"]
    top_caps = sorted(caps_hits.items(), key=lambda kv: -kv[1])[:4]
    out = {
        "n_files":                       len(data["files"]),
        "n_sentences":                   corpus["n_sents"],
        "n_word_tokens":                 corpus["n_tokens"],
        "n_versions":                    len({f["ccVersion"] for f in data["files"]
                                              if f.get("ccVersion")}),
        "n_rule_sentences":              m["rule_explanation"]["n_rule_sentences"],
        "pct_explained_same":            m["rule_explanation"]["pct_explained_same"],
        "pct_explained_para":            m["rule_explanation"]["pct_explained_para"],
        "judgment_count":                m["judgment_procedural"]["judgment_count"],
        "procedural_count":              m["judgment_procedural"]["procedural_count"],
        "judgment_to_procedural_ratio":  m["judgment_procedural"]["judgment_to_procedural_ratio"],
        "threat_count":                  m["consequence_framing"]["threat_count"],
        "causal_count":                  m["consequence_framing"]["causal_count"],
        "threat_share":                  m["consequence_framing"]["threat_share"],
        "question_count":                m["socratic"]["question_count"],
        "apology_count":                 m["socratic"]["apology_count"],
        "selfref_claude":                m["address_form"]["selfref_claude"],
        "selfref_assistant":             m["address_form"]["selfref_assistant"],
        "selfref_model":                 m["address_form"]["selfref_model"],
        "pct_anthropomorphic":           m["address_form"]["pct_anthropomorphic"],
        "positive_evaluative_quality":   pos_q,
        "positive_evaluative_emphasis":  pos_e,
        "positive_evaluative_union":     pos_u,
        "negative_evaluative":           neg,
        "ratio_quality_to_negative":     pos_q / max(1, neg),
        "ratio_union_to_negative":       pos_u / max(1, neg),
        "appreciative_sent":             m["sentence_register"]["appreciative_sent_count"],
        "collaborative_sent":            m["sentence_register"]["collaborative_sent_count"],
        "streak_max":                    m["imperative_streaks"]["streak_max"],
        "n_streaks_ge3":                 m["imperative_streaks"]["n_streaks_ge3"],
        "n_streaks_ge5":                 m["imperative_streaks"]["n_streaks_ge5"],
        "vocab_hard_prohibitions":       m["vocab"]["hard_prohibitions"]["count"],
        "vocab_hard_prescriptions":      m["vocab"]["hard_prescriptions"]["count"],
        "vocab_pronouns_2p":             m["vocab"]["pronouns_2p"]["count"],
        "vocab_pronouns_1p":             m["vocab"]["pronouns_1p"]["count"],
        "vocab_profanity":               m["vocab"]["profanity"]["count"],
        "modality_deontic":              m["modality"]["deontic_count"],
        "modality_epistemic":            m["modality"]["epistemic_count"],
        "modality_dynamic":              m["modality"]["dynamic_count"],
        "mood_marker_pct":               m["mood"]["marker_pct"],
        "top_caps_imperative":           top_caps,
        "rules_section_in_paragraphs":              rs["n_rule_paragraphs_in_rules_section"],
        "rules_section_out_paragraphs":             rs["n_rule_paragraphs_outside_rules_section"],
        "rules_section_in_paragraphs_explained":    rs["n_rule_paragraphs_in_rules_section_explained"],
        "rules_section_out_paragraphs_explained":   rs["n_rule_paragraphs_outside_rules_section_explained"],
        "rules_section_in_pct_explained":           rs["pct_rule_paragraphs_explained_in_rules_section"],
        "rules_section_out_pct_explained":          rs["pct_rule_paragraphs_explained_outside_rules_section"],
    }
    if alt_df is not None:
        d = directiveness(alt_df)
        out["composite_directiveness_min"] = float(d.min())
        out["composite_directiveness_max"] = float(d.max())
        # mood_marker_pct first / latest version (token-weighted aggregate by ccVersion)
        if "ccVersion" in alt_df.columns and "mood_marker_pct" in alt_df.columns:
            vers = version_order(alt_df)
            if vers:
                first_v, latest_v = vers[0], vers[-1]
                f_first = alt_df[alt_df["ccVersion"] == first_v]
                f_latest = alt_df[alt_df["ccVersion"] == latest_v]
                # token-weighted mean: sum(mood_marker_pct * n_tokens) / sum(n_tokens)
                def _tw(df_):
                    tok = df_["n_tokens"]
                    return float((df_["mood_marker_pct"] * tok).sum() / max(1, tok.sum()))
                out["mood_marker_pct_first_version"]    = _tw(f_first)
                out["mood_marker_pct_latest_version"]   = _tw(f_latest)
                out["mood_marker_pct_first_version_id"]  = first_v
                out["mood_marker_pct_latest_version_id"] = latest_v
    if parquet is not None:
        out["parquet_threat_count"]            = int(parquet["has_threat"].sum())
        out["parquet_causal_count"]            = int(parquet["has_causal"].sum())
        threat_and_rule = parquet["has_threat"] & parquet["is_rule"]
        out["parquet_threat_and_rule_count"]   = int(threat_and_rule.sum())
        out["parquet_threat_and_rule_with_causal"] = int((threat_and_rule & parquet["has_causal"]).sum())
        out["parquet_threat_and_rule_explained"]   = int((threat_and_rule & parquet["is_explained_para"]).sum())
    return out


def positive_exemplar_table(
    alt_df: pd.DataFrame,
    top_n: int = 25,
    min_n_sents: int = 10,
    min_rule_n: int = 5,
) -> pd.DataFrame:
    """Top-N "rules-with-reasons" exemplars (Opinion-round D — the inverse of
    ``welfare_evidence_table``).

    Ranks files by ``rule_density * (rule_explained_para_pct / 100)`` — high
    score = rule-saturated AND most of those rules explained at the paragraph
    level. Filters: ``n_sents >= min_n_sents`` (default 10) AND
    ``rule_n >= min_rule_n`` (default 5) to suppress trivial cases like
    "1/1 rules explained" in a 3-sentence file.

    These are the files Anthropic could point to as "this is how to do it" —
    concrete templates rather than only critiques.
    """
    df = alt_df[(alt_df["n_sents"] >= min_n_sents)
                & (alt_df["rule_n"] >= min_rule_n)].copy()
    explained_frac = df["rule_explained_para_pct"].fillna(0.0).astype(float) / 100.0
    df["score"] = df["rule_density"].astype(float) * explained_frac
    cols = ["path", "category", "ccVersion", "rule_n", "rule_density",
            "rule_explained_para_pct", "score"]
    return (df[cols]
            .sort_values("score", ascending=False)
            .head(top_n)
            .reset_index(drop=True))
