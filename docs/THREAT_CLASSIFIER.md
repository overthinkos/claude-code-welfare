# Threat / soft-conditional classifier

The pipeline tags every sentence along two related but distinct dimensions and reports them separately.

## Two-tier classifier

`prompt_pipeline.py` defines two regex lists:

* **`THREAT_PATTERNS`** — unambiguous coercive language. Five entries:
  `will fail/break/crash/...`, `or else`, `or it will`, `is (forbidden|prohibited|not allowed|not permitted)`, `this will (cause|result in|break|fail|crash)`. Drives `threat_count`, `has_threat`, and `threat_share`.
* **`SOFT_CONDITIONAL_PATTERNS`** — neutral procedural connectives.
  Seven entries: `otherwise`, `if not`, `if you (don't|do not)`, modal `(could|may|might|would) (cause|result|...)`, `risks/risking`, `leads to`, `results in`. Drives `soft_conditional_count` and `has_soft_conditional`.

The two lists are tracked separately and **never summed**. Soft-conditional matches are useful as a procedural-density signal — they identify prose where most logic is `if X otherwise Y` rather than `because Z` — but they are not coercion and should not be reported as such.

## Why the split matters

The two phenomena look superficially similar (both involve a hypothetical consequence), but they teach different things in a system prompt:

* **Hard threat — "Do X or it will fail."** Trains compliance with a rule by warning of a consequence.
* **Soft conditional — "If it's a slash command, invoke it via the Skill tool; otherwise act on it directly."** Procedural branching. Not coercion at all.

Lumping them together would conflate procedural-prose density with coercive-language density. The lexicon therefore enforces the distinction at the source.

## Headline numbers (v2.1.132 corpus)

`python scripts/recompute_threat_metrics.py --by-category`:

| Subset           | Sentences | Threat | Soft cond. | Causal | Threat share |
| ---------------- | --------: | -----: | ---------: | -----: | -----------: |
| **All**          | 5,878     | 8      | 96         | 136    | **5.6%**     |
| System prompt    |   659     | 0      | 13         |  28    | **0.0%**     |
| System reminder  |   173     | 0      |  9         |   7    | **0.0%**     |
| Tool description |   553     | 2      | 10         |  33    | 5.7%         |
| Agent prompt     | 1,089     | 2      | 23         |  26    | 7.1%         |
| Skill            | 1,695     | 3      | 31         |  26    | 10.3%        |
| Data / template  | 1,695     | 1      | 10         |  16    | 5.9%         |

The four flagship coercive phrases (`or else`, `or it will`, `is forbidden`, `this will cause`) fire **zero times** in the corpus. All eight hard-threat hits are matches against `will fail/break/crash/error/throw/hang/deadlock/loop/corrupt/delete`.

## Verifying locally

```
# Per-pattern hit counts + sample for human review:
python scripts/threat_precision_audit.py
python scripts/threat_precision_audit.py --category 'System prompt'

# Aggregate threat / causal / soft-conditional counts:
python scripts/recompute_threat_metrics.py --by-category
```

The full pipeline rerun (regenerates `prompt_linguistic_analysis.yaml` and `sentences_classified.parquet`) is the producer chain in `00_setup_and_corpus.ipynb` → `05_headline_and_audit.ipynb`. See `README.md`.
