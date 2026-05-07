"""Compute the threat / causal / soft-conditional metrics from
``sentences_classified.parquet`` without re-running the spaCy pipeline.

Useful as a quick sanity check after a pipeline rerun — the numbers
this script prints should match the YAML's `consequence_framing` block.

Usage::

    python scripts/recompute_threat_metrics.py
    python scripts/recompute_threat_metrics.py --by-category
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

# Mirrors prompt_pipeline.{THREAT,SOFT_CONDITIONAL,CAUSAL}_PATTERNS so
# this script is runnable standalone.
HARD_PATTERNS = [
    r"\bwill (?:fail|break|crash|error|throw|hang|deadlock|loop|corrupt|delete)\b",
    r"\bor else\b",
    r"\bor it will\b",
    r"\bis (?:forbidden|prohibited|not allowed|not permitted)\b",
    r"\bthis will (?:cause|result in|break|fail|crash)\b",
]

SOFT_PATTERNS = [
    r"\botherwise\b",
    r"\bif not\b",
    r"\bif you (?:don't|do not)\b",
    r"\b(?:could|may|might|would) (?:cause|result|lead|break|fail|"
    r"corrupt|hang|crash|loop|deadlock|delete)\b",
    r"\b(?:risks?|risking)\b",
    r"\bleads? to\b",
    r"\bresults? in\b",
]

CAUSAL_PATTERNS = [
    r"\bbecause\b", r"\bbecause of\b", r"\bdue to\b",
    r"\bthe reason (?:is|being|that|why)\b",
    r"\b(?:that's|that is) why\b",
    r"\bin order to\b", r"\bso (?:that|as to)\b",
    r"\bto avoid\b", r"\bto prevent\b", r"\bto ensure\b",
    r"\bto guarantee\b", r"\bto make sure\b",
    r"\bthe goal (?:is|of)\b", r"\bthe purpose (?:is|of)\b",
    r"\bthe point (?:is|of)\b",
    r"\bthis (?:ensures|prevents|avoids|allows|helps|means|guarantees|"
    r"is because|is to|lets|gives|keeps|protects|stops)\b",
    r"\bthat way\b", r"\bensures? that\b",
    r"\bsince\b", r"\bgiven that\b", r"\bas a result\b",
    r"\bfor (?:safety|security|consistency|clarity|reproducibility|"
    r"reliability|correctness|accuracy|performance|the user)\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _count(texts: pd.Series, regexes: list[re.Pattern]) -> int:
    """Sum of all regex match counts across the joined text -- mirrors
    the pipeline's per-corpus count semantics."""
    joined = "\n".join(texts)
    return sum(len(r.findall(joined)) for r in regexes)


def _share(num: int, denom: int) -> float | None:
    return round(num / denom, 4) if denom else None


def _aggregate(df: pd.DataFrame, label: str) -> dict:
    hard_re = _compile(HARD_PATTERNS)
    soft_re = _compile(SOFT_PATTERNS)
    causal_re = _compile(CAUSAL_PATTERNS)

    threat = _count(df["text"], hard_re)
    soft = _count(df["text"], soft_re)
    causal = _count(df["text"], causal_re)

    return {
        "label":        label,
        "n_sentences":  len(df),
        "threat":       threat,
        "soft_cond":    soft,
        "causal":       causal,
        "threat_share": _share(threat, threat + causal),
    }


def _fmt_row(row: dict) -> str:
    share = row["threat_share"]
    share_s = f"{100 * share:5.1f}%" if share is not None else "  n/a "
    return (f"  {row['label']:18s}  "
            f"n={row['n_sentences']:5d}   "
            f"threat={row['threat']:4d}   "
            f"soft_cond={row['soft_cond']:4d}   "
            f"causal={row['causal']:4d}   "
            f"threat_share={share_s}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parquet",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sentences_classified.parquet",
    )
    parser.add_argument("--by-category", action="store_true",
                        help="Also print per-category breakdown")
    args = parser.parse_args()

    df = pd.read_parquet(args.parquet)

    print("Corpus-wide:")
    overall = _aggregate(df, "ALL")
    print(_fmt_row(overall))

    if args.by_category:
        print()
        print("By category:")
        for cat, sub in sorted(df.groupby("category"), key=lambda kv: -len(kv[1])):
            print(_fmt_row(_aggregate(sub, str(cat)[:18])))

    print()
    print("Notes:")
    print("  * threat       = matches under THREAT_PATTERNS (HARD)")
    print("  * soft_cond    = matches under SOFT_CONDITIONAL_PATTERNS")
    print("                   (procedural connectives, NOT counted as threats)")
    print("  * threat_share = threat / (threat + causal)")


if __name__ == "__main__":
    main()
