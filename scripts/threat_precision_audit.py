"""Per-pattern audit of the threat / soft-conditional classifier.

The pipeline tags each sentence with `has_threat` (any HARD pattern
matches) and `has_soft_conditional` (any SOFT pattern matches). This
script breaks down which trigger fired for each flagged sentence and
samples N for human review.

Usage::

    python scripts/threat_precision_audit.py
    python scripts/threat_precision_audit.py --sample 50 --seed 0
    python scripts/threat_precision_audit.py --category 'System prompt'
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

# Mirrors prompt_pipeline.THREAT_PATTERNS / SOFT_CONDITIONAL_PATTERNS
# Kept inline so this script is runnable without importing the spaCy-
# dependent pipeline module.
HARD_PATTERNS: dict[str, str] = {
    "will_fail_etc":
        r"\bwill (?:fail|break|crash|error|throw|hang|deadlock|loop|corrupt|delete)\b",
    "or_else":
        r"\bor else\b",
    "or_it_will":
        r"\bor it will\b",
    "is_forbidden":
        r"\bis (?:forbidden|prohibited|not allowed|not permitted)\b",
    "this_will_cause":
        r"\bthis will (?:cause|result in|break|fail|crash)\b",
}

SOFT_PATTERNS: dict[str, str] = {
    "otherwise":      r"\botherwise\b",
    "if_not":         r"\bif not\b",
    "if_you_dont":    r"\bif you (?:don't|do not)\b",
    "modal_cause":    r"\b(?:could|may|might|would) (?:cause|result|lead|"
                      r"break|fail|corrupt|hang|crash|loop|deadlock|delete)\b",
    "risks":          r"\b(?:risks?|risking)\b",
    "leads_to":       r"\bleads? to\b",
    "results_in":     r"\bresults? in\b",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parquet",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sentences_classified.parquet",
        help="Path to sentences_classified.parquet",
    )
    parser.add_argument("--sample", type=int, default=25,
                        help="How many flagged sentences to print for review")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for the sample")
    parser.add_argument("--category", type=str, default=None,
                        help="Restrict the audit to a single category "
                             "(e.g. 'System prompt')")
    args = parser.parse_args()

    df = pd.read_parquet(args.parquet)

    if args.category:
        df = df[df["category"] == args.category]
        if df.empty:
            raise SystemExit(f"No sentences found for category={args.category!r}")

    n_total = len(df)
    n_threat = int(df["has_threat"].sum())
    n_soft = int(df["has_soft_conditional"].sum())

    print(f"Corpus subset: {n_total:,} sentences"
          + (f" (category = {args.category!r})" if args.category else ""))
    print(f"has_threat=True:           {n_threat:,} ({100 * n_threat / max(n_total, 1):.2f}%)")
    print(f"has_soft_conditional=True: {n_soft:,} ({100 * n_soft / max(n_total, 1):.2f}%)")
    print()

    # Per-pattern hit counts on each flagged subset
    threats = df[df["has_threat"]].copy()
    softs = df[df["has_soft_conditional"]].copy()

    print(f"Per-pattern hit counts on the {len(threats)} threat-flagged sentences:")
    for name, pat in HARD_PATTERNS.items():
        h = threats["text"].str.contains(pat, case=False, regex=True)
        print(f"  [HARD] {name:18s}: {int(h.sum())}")
    print()

    print(f"Per-pattern hit counts on the {len(softs)} soft-conditional-flagged sentences:")
    for name, pat in SOFT_PATTERNS.items():
        h = softs["text"].str.contains(pat, case=False, regex=True)
        print(f"  [SOFT] {name:18s}: {int(h.sum())}")
    print()

    if n_threat > 0:
        n_sample = min(args.sample, n_threat)
        sample = threats.sample(n_sample, random_state=args.seed)
        print(f"Random sample of {n_sample} threat-flagged sentences for human review")
        print(f"(seed={args.seed}; classify each as THREAT / NOT-THREAT yourself):")
        print("-" * 72)
        for i, row in enumerate(sample.itertuples(), 1):
            text = re.sub(r"\s+", " ", row.text).strip()
            if len(text) > 220:
                text = text[:217] + "..."
            cat = (row.category or "")[:18]
            print(f"{i:2d}. [{cat:18s}] {text}")


if __name__ == "__main__":
    main()
