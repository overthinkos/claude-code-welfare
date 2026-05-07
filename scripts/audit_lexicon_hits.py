"""Per-term hit-count audit across every lexicon in prompt_pipeline.

Walks the claude-code-system-prompts/ corpus, parses each markdown file the
same way 00_setup_and_corpus does (parse_html_frontmatter -> clean_markdown
-> NLP.pipe), then for every lexicon entry counts how many times it fires
across the whole corpus. Output is written to lexicon_hits.json plus a
printed summary of zero-hit terms — the input to the Phase-3a cleanup
decision.

Run::

    .venv/bin/python scripts/audit_lexicon_hits.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from spacy.matcher import PhraseMatcher  # noqa: E402

import prompt_pipeline as pp  # noqa: E402

CORPUS = REPO / "claude-code-system-prompts"
OUT = REPO / "lexicon_hits.json"


def load_corpus() -> tuple[list[str], list]:
    """Return (paths, docs) — every .md file under CORPUS, parsed and tokenized.

    Mirrors the 00_setup_and_corpus pipeline exactly: frontmatter split,
    clean_markdown, NLP.pipe.
    """
    paths: list[str] = []
    cleaned: list[str] = []
    for p in sorted(CORPUS.rglob("*.md")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        _meta, body, _used = pp.parse_html_frontmatter(raw)
        cleaned.append(pp.clean_markdown(body))
        paths.append(str(p.relative_to(REPO)))
    docs = list(pp.NLP.pipe(cleaned, batch_size=32))
    return paths, docs


def count_phrase_hits(docs, terms: list[str]) -> dict[str, int]:
    """For each term, count phrase-matcher hits (LOWER attr) across docs."""
    hits: dict[str, int] = {}
    for term in terms:
        m = PhraseMatcher(pp.NLP.vocab, attr="LOWER")
        m.add("X", [pp.NLP.make_doc(term)])
        n = 0
        for d in docs:
            n += len(m(d))
        hits[term] = n
    return hits


def count_phrase_hits_orth(docs_raw_text: list[str], terms: list[str]) -> dict[str, int]:
    """For caps-imperative tokens: case-sensitive (ORTH) match on raw text.

    The caps-imperative matcher in production runs on raw text (not lemmatized
    docs) because it depends on character casing. We replicate via simple
    word-boundary regex per term.
    """
    hits: dict[str, int] = {}
    for term in terms:
        pat = re.compile(r"\b" + re.escape(term) + r"\b")
        n = 0
        for t in docs_raw_text:
            n += len(pat.findall(t))
        hits[term] = n
    return hits


def count_regex_hits(docs_raw_text: list[str], patterns: list[str]) -> dict[str, int]:
    """For each regex pattern, count findall matches across raw texts."""
    hits: dict[str, int] = {}
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        n = 0
        for t in docs_raw_text:
            n += len(rx.findall(t))
        hits[pat] = n
    return hits


def count_token_hits(docs, terms) -> dict[str, int]:
    """For each token-level term (lowercase lemma/text match), count tokens."""
    target = set(terms)
    counts = {t: 0 for t in target}
    for d in docs:
        for tok in d:
            txt = tok.text.lower()
            if txt in target:
                counts[txt] += 1
    return counts


def main() -> None:
    print(f"Loading corpus from {CORPUS} ...")
    paths, docs = load_corpus()
    raw_texts = [d.text for d in docs]
    print(f"  loaded {len(paths)} files, {sum(len(d) for d in docs)} tokens")

    report: dict[str, dict] = {}

    # --- VOCAB (dict[str, list[str]] of phrase terms) ---
    for cls, terms in pp.VOCAB.items():
        report[f"VOCAB.{cls}"] = count_phrase_hits(docs, terms)

    # --- Single-list phrase lexicons (LOWER attr) ---
    report["IMPERATIVE_MARKERS"] = count_phrase_hits(docs, pp.IMPERATIVE_MARKERS)
    report["JUDGMENT_VERBS"]     = count_phrase_hits(docs, pp.JUDGMENT_VERBS)
    report["PROCEDURAL_CUES"]    = count_phrase_hits(docs, pp.PROCEDURAL_CUES)
    report["APOLOGY_MARKERS"]    = count_phrase_hits(docs, pp.APOLOGY_MARKERS)
    report["POSITIVE_EVALUATIVE_QUALITY"]  = count_phrase_hits(docs, pp.POSITIVE_EVALUATIVE_QUALITY)
    report["POSITIVE_EVALUATIVE_EMPHASIS"] = count_phrase_hits(docs, pp.POSITIVE_EVALUATIVE_EMPHASIS)

    # --- Caps-imperative tokens (ORTH attr in production: case-sensitive) ---
    report["CAPS_IMPERATIVE_TOKENS"] = count_phrase_hits_orth(raw_texts, pp.CAPS_IMPERATIVE_TOKENS)

    # --- Multi-class phrase lexicons (dict[str, list[str]]) ---
    for cls, terms in pp.STANCE_MARKERS.items():
        report[f"STANCE_MARKERS.{cls}"] = count_phrase_hits(docs, terms)
    for cls, terms in pp.REGISTER_MARKERS.items():
        report[f"REGISTER_MARKERS.{cls}"] = count_phrase_hits(docs, terms)
    for cls, terms in pp.SENTENCE_REGISTER_MARKERS.items():
        report[f"SENTENCE_REGISTER_MARKERS.{cls}"] = count_phrase_hits(docs, terms)

    # --- Regex pattern lists ---
    report["JUSTIFICATION_PATTERNS"]      = count_regex_hits(raw_texts, pp.JUSTIFICATION_PATTERNS)
    report["THREAT_PATTERNS"]             = count_regex_hits(raw_texts, pp.THREAT_PATTERNS)
    report["CAUSAL_PATTERNS"]             = count_regex_hits(raw_texts, pp.CAUSAL_PATTERNS)
    report["SOFT_CONDITIONAL_PATTERNS"]   = count_regex_hits(raw_texts, pp.SOFT_CONDITIONAL_PATTERNS)
    report["ADDRESSEE_USER_INSTRUCTION_PATTERNS"]  = count_regex_hits(raw_texts, pp.ADDRESSEE_USER_INSTRUCTION_PATTERNS)
    report["ADDRESSEE_CLAUDE_REFERENCE_PATTERNS"]  = count_regex_hits(raw_texts, pp.ADDRESSEE_CLAUDE_REFERENCE_PATTERNS)
    for cls, patterns in pp.ADDRESS_FORM_PATTERNS.items():
        report[f"ADDRESS_FORM_PATTERNS.{cls}"] = count_regex_hits(raw_texts, patterns)

    # --- Token-set lexicons (lemma/text match against token stream) ---
    report["EPISTEMIC_ADVERBS"]         = count_token_hits(docs, pp.EPISTEMIC_ADVERBS)
    report["DEONTIC_LIGHT_VERBS"]       = count_token_hits(docs, pp.DEONTIC_LIGHT_VERBS)
    report["EPISTEMIC_LIGHT_VERBS"]     = count_token_hits(docs, pp.EPISTEMIC_LIGHT_VERBS)
    report["EPISTEMIC_AUX_AFTER_MODAL"] = count_token_hits(docs, pp.EPISTEMIC_AUX_AFTER_MODAL)
    report["SIMPLE_MODAL_LOOKUP"]       = count_token_hits(docs, list(pp.SIMPLE_MODAL_LOOKUP))
    report["TECH_ACRONYMS"]             = count_phrase_hits_orth(raw_texts, sorted(pp.TECH_ACRONYMS))

    OUT.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(f"\nWrote {OUT}")

    # --- Summary -------------------------------------------------------
    print("\n=== Zero-hit terms (slated for removal) ===")
    total_zero = 0
    for lex_name, terms in sorted(report.items()):
        zeros = [t for t, n in terms.items() if n == 0]
        if not zeros:
            continue
        total_zero += len(zeros)
        print(f"\n{lex_name}  ({len(zeros)} of {len(terms)} terms zero-hit):")
        for t in zeros:
            print(f"  · {t!r}")

    print(f"\nTotal zero-hit terms across all lexicons: {total_zero}")

    print("\n=== 1–4 hit terms (low-frequency, review individually) ===")
    for lex_name, terms in sorted(report.items()):
        low = [(t, n) for t, n in terms.items() if 0 < n < 5]
        if not low:
            continue
        print(f"\n{lex_name}:")
        for t, n in low:
            print(f"  · {t!r}: {n}")


if __name__ == "__main__":
    main()
