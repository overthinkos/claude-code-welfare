"""Lexicons for the claude-prompts-analysis pipeline.

Pure data — every vocabulary list, regex pattern list, POS tagset, and
category mapping the producer chain (`00_setup_and_corpus` →
`04_assemble_aggregate_write`) consults. No spaCy, no `re.compile`, no
analyzer logic. `prompt_pipeline.py` imports from here, builds the
phrase matchers / compiled regexes, and exposes the analyzers.

Why a separate file: lexicon edits are the most common reason to touch
the pipeline (adding a marker, dropping a dead term, splitting a class).
Keeping the data here lets reviewers see the full vocabulary as a single
artifact, separate from the matcher-building / spaCy-pipeline machinery.

Consumers (`05_*`–`22_*` notebooks) MUST NOT import from this module —
they consume the YAML / parquet artifacts via `prompt_analysis`. The
producer / consumer split rule from `CLAUDE.md` extends to lexicons.

Pruned 2026-05-07 against the 289-file corpus: terms that fired zero
times across the entire corpus have been removed (audit script:
``scripts/audit_lexicon_hits.py``). Two classes ended up empty —
``VOCAB["profanity"]`` and ``REGISTER_MARKERS["frozen"]`` — but kept as
empty lists so the YAML schema and downstream column names stay stable.
Re-run the audit script after adding terms to confirm they fire.
"""
from __future__ import annotations

from typing import Dict, List

__all__ = [
    "VOCAB",
    "IMPERATIVE_MARKERS",
    "CAPS_IMPERATIVE_TOKENS",
    "JUSTIFICATION_PATTERNS",
    "TECH_ACRONYMS",
    "CATEGORY_PREFIXES",
    "STANCE_MARKERS",
    "REGISTER_MARKERS",
    "SENTENCE_REGISTER_MARKERS",
    "POSITIVE_EVALUATIVE_QUALITY",
    "POSITIVE_EVALUATIVE_EMPHASIS",
    "SIMPLE_MODAL_LOOKUP",
    "EPISTEMIC_ADVERBS",
    "DEONTIC_LIGHT_VERBS",
    "EPISTEMIC_LIGHT_VERBS",
    "EPISTEMIC_AUX_AFTER_MODAL",
    "ADDRESSEE_USER_INSTRUCTION_PATTERNS",
    "ADDRESSEE_CLAUDE_REFERENCE_PATTERNS",
    "JUDGMENT_VERBS",
    "PROCEDURAL_CUES",
    "APOLOGY_MARKERS",
    "THREAT_PATTERNS",
    "SOFT_CONDITIONAL_PATTERNS",
    "CAUSAL_PATTERNS",
    "ADDRESS_FORM_PATTERNS",
    "FORMAL_POS",
    "INFORMAL_POS",
]


# =============================================================================
# Vocabulary lexicons (phrase-matched, LOWER attr)
# =============================================================================

VOCAB: Dict[str, List[str]] = {
    "hard_prohibitions": [
        'do not', "don't", 'must not', 'never', 'cannot', "can't", "won't",
        "shouldn't", 'should not', 'forbidden', 'prohibited', 'disallowed',
        'not allowed', 'not permitted', 'no exceptions', 'refuse to'
    ],
    "hard_prescriptions": [
        'must', 'always', 'required', 'mandatory', 'critical', 'essential',
        'imperative', 'you must', 'you need to', 'you should always', 'is required'
    ],
    "soft_prescriptions": [
        'should', 'make sure', 'be sure to', 'ensure', 'remember to', 'be careful',
        'you should', 'try to'
    ],
    "politeness_direct": [
        'please', 'thanks', 'appreciate'
    ],
    "politeness_softening": [
        "if you'd like", 'if you want', 'feel free', 'feel free to', 'would you',
        'if possible', 'if you can'
    ],
    "warmth_encouragement": [
        'welcome', 'happy to'
    ],
    "hedging": [
        'may', 'might', 'could', 'potentially', 'likely', 'probably', 'sometimes',
        'often', 'usually', 'generally', 'typically', 'tends to'
    ],
    "structural_markers": [
        'note', 'warning', 'caution', 'important', 'tip', 'info', 'remember',
        'example', 'for instance', 'for example'
    ],
    "profanity": [],
    "pronouns_2p": [
        'you', 'your', 'yours', 'yourself'
    ],
    "pronouns_1p": [
        'i', 'me', 'my', 'we', 'us', 'our'
    ],
}

IMPERATIVE_MARKERS: List[str] = [
    'must', 'must not', 'never', 'always', 'do not', "don't", 'cannot', "can't",
    "won't", 'should not', "shouldn't", 'required', 'mandatory', 'critical',
    'forbidden', 'prohibited', 'disallowed', 'you must', 'you must not', 'you need to',
    'you should always', 'is required', 'no exceptions', 'ensure', 'ensure that',
    'make sure to', 'be sure to'
]

# Caps imperative: case-sensitive (ORTH attr in production), so casing matters.
CAPS_IMPERATIVE_TOKENS: List[str] = [
    'IMPORTANT', 'VERY IMPORTANT', 'CRITICAL', 'MANDATORY', 'REQUIRED', 'MUST',
    'MUST NOT', 'NEVER', 'ALWAYS', 'DO NOT', 'NOTE', 'STOP', 'REMEMBER', 'PROHIBITED',
    'STRICTLY'
]


# =============================================================================
# Justification / causal / threat regex pattern lists (re.IGNORECASE)
#
# Three layered classifiers; the relationship is encoded in code:
#
#   CAUSAL_PATTERNS          — pure cause-effect connectives ("because",
#                              "in order to", "for safety"). Used by
#                              consequence_framing.causal_count.
#   SOFT_CONDITIONAL_PATTERNS — neutral procedural ("otherwise", "if not",
#                              modal "may cause"). Used by consequence_framing
#                              as a procedural-density signal — NOT summed
#                              into threat_count.
#   THREAT_PATTERNS          — unambiguous coercion ("will fail/crash",
#                              "or else", "is forbidden"). Used by
#                              consequence_framing.threat_count.
#   JUSTIFICATION_PATTERNS   — broadest "explains-why" set. Equals
#                              CAUSAL ∪ SOFT_CONDITIONAL ∪ a few extras
#                              ("or else", "prevents X from", etc.). Used
#                              by rule_explanation, rules_section,
#                              build_sentence_records.
# =============================================================================

CAUSAL_PATTERNS: List[str] = [
    r"\bbecause\b",
    r"\bdue to\b",
    r"\bin order to\b",
    r"\bso (?:that|as to)\b",
    r"\bto avoid\b",
    r"\bto prevent\b",
    r"\bto ensure\b",
    r"\bthe goal (?:is|of)\b",
    r"\bthe point (?:is|of)\b",
    r"\bthis (?:ensures|prevents|avoids|allows|helps|means|guarantees|"
    r"is because|is to|lets|gives|keeps|protects|stops)\b",
    r"\bensures? that\b",
    r"\bsince\b",
    r"\bas a result\b",
    r"\bfor (?:safety|security|consistency|clarity|reproducibility|"
    r"reliability|correctness|accuracy|performance|the user)\b",
]

SOFT_CONDITIONAL_PATTERNS: List[str] = [
    r"\botherwise\b",
    r"\bif not\b",
    r"\bif you (?:don't|do not)\b",
    r"\b(?:could|may|might|would) (?:cause|result|lead|break|fail|"
    r"corrupt|hang|crash|loop|deadlock|delete)\b",
    r"\b(?:risks?|risking)\b",
    r"\bleads? to\b",
    r"\bresults? in\b",
]

THREAT_PATTERNS: List[str] = [
    r"\bwill (?:fail|break|crash|error|throw|hang|deadlock|loop|corrupt|delete)\b",
    r"\bor else\b",
]

# Justification is the broadest "explains-why" set used by the rule-
# explanation analyzer. It covers everything in CAUSAL_PATTERNS plus
# conditional/consequence framings (most of SOFT_CONDITIONAL_PATTERNS,
# but with a wider modal alternation that includes "will") and a few
# explanation-only extras ("prevents X from", "so we/you/...").
# Listed as its own pattern set rather than `CAUSAL + SOFT + extras`
# because the modal-cause regex here uses "(?:could|may|might|would|will)"
# while SOFT_CONDITIONAL_PATTERNS uses "(?:could|may|might|would)" — the
# "will" alternative is justification-specific.
JUSTIFICATION_PATTERNS: List[str] = CAUSAL_PATTERNS + [
    r"\botherwise\b",
    r"\bor else\b",
    r"\bif not\b",
    r"\bif you (?:don't|do not)\b",
    r"\b(?:could|may|might|would|will) (?:cause|result|lead|break|fail|"
    r"corrupt|hang|crash|loop|deadlock|delete)\b",
    r"\bleads? to\b",
    r"\bresults? in\b",
    r"\b(?:risks?|risking)\b",
    r"\bprevents? .{1,40}? from\b",
    r"\bso (?:we|you|it|they|the|this|i)\b",
]


# =============================================================================
# All-caps token whitelist (excluded from all-caps emphasis counting)
# =============================================================================

TECH_ACRONYMS = {
    'AI', 'ANSI', 'API', 'ASCII', 'BOM', 'CD', 'CI', 'CLI', 'CPU', 'CRUD', 'CSS',
    'CSV', 'DB', 'DNS', 'DOCX', 'EOF', 'F1', 'FAIL', 'FALSE', 'GET', 'GIF', 'GIT',
    'GUI', 'HEAD', 'HTML', 'HTTP', 'HTTPS', 'ID', 'IDE', 'IP', 'JPEG', 'JPG', 'JS',
    'JSON', 'JSONL', 'JWT', 'LLM', 'MCP', 'MR', 'NEW', 'NULL', 'PARTIAL', 'PASS',
    'PDF', 'PHP', 'PNG', 'POSIX', 'POST', 'PR', 'RAM', 'REPL', 'REST', 'S3', 'SDK',
    'SQL', 'SSH', 'TBD', 'TLS', 'TODO', 'TS', 'UI', 'URL', 'USD', 'UTC', 'UTF', 'UUID',
    'UX', 'VS', 'XML', 'YAML'
}


# =============================================================================
# File-category classification (filename-prefix heuristic)
# =============================================================================

CATEGORY_PREFIXES: List[tuple] = [
    ("agent-prompt", "Agent prompt"),
    ("system-prompt", "System prompt"),
    ("system-reminder", "System reminder"),
    ("tool-description", "Tool description"),
    ("tool-parameter", "Tool parameter"),
    ("skill", "Skill"),
    ("data", "Data / template"),
]


# =============================================================================
# Stance / register / sentence-register markers (phrase-matched per class)
# =============================================================================

STANCE_MARKERS: Dict[str, List[str]] = {
    "directive": [
        'must', 'should', 'do not', "don't", 'never', 'always', 'you must',
        'you must not', 'you should', 'you should not', 'you need to', 'ensure',
        'make sure', 'make sure to', 'be sure to', 'remember to'
    ],
    "expository": [
        'is', 'are', 'means', 'is a', 'are a', 'this is', 'these are', 'for example',
        'for instance', 'specifically', 'i.e.', 'e.g.'
    ],
    "positive_evaluative": [
        'good', 'better', 'best', 'preferred', 'ideal', 'optimal', 'appropriate',
        'useful', 'important', 'critical', 'essential', 'valuable', 'right', 'correct',
        'great', 'helpful', 'effective', 'key', 'recommended', 'suitable', 'valid',
        'safe'
    ],
    "negative_evaluative": [
        'bad', 'worse', 'worst', 'inappropriate', 'trivial', 'harmful', 'problematic',
        'incorrect', 'wrong', 'broken', 'dangerous', 'risky', 'deprecated', 'invalid',
        'unsafe'
    ],
    "dialogic": [
        'you might', 'you may', 'you could', 'consider', 'however', 'in contrast',
        'but', 'yet', 'while', 'do you', "let's", 'we can'
    ],
}

REGISTER_MARKERS: Dict[str, List[str]] = {
    "frozen": [],
    "formal": [
        'accordingly', 'hence'
    ],
    "consultative": [
        'please', 'you can', 'you may', 'suggest', 'consider', 'if you', 'when you',
        'in this case', 'for example', 'best practice', 'note:'
    ],
    "casual": [
        "let's", "here's", "you're", "we're", "i'm", "don't", "can't", "won't",
        "isn't", "aren't", "doesn't", "didn't", 'ok', 'okay', 'anyway', 'kind of',
        'stuff', 'thing'
    ],
}

SENTENCE_REGISTER_MARKERS: Dict[str, List[str]] = {
    "collaborative": [
        "let's", 'we can', "we'll", 'together'
    ],
    "permissive": [
        'please', 'you can', 'you may', 'feel free to', "if you'd like", 'try to',
        'if possible', 'optionally', 'if needed'
    ],
    "appreciative": [
        'thanks', 'appreciate', 'awesome'
    ],
    "configuring": [
        'set to', 'configure', 'configured', 'enable', 'disable', 'define', 'defined',
        'specify', 'specified', 'default', 'default to', 'defaults to', 'must be',
        'should be', 'is required', 'respond with', 'accepts', 'expects',
        'output should'
    ],
}


# =============================================================================
# positive_evaluative split (Opinion-round B): quality vs emphasis
#
# Their union must equal STANCE_MARKERS["positive_evaluative"]; the
# invariant is asserted in prompt_pipeline at import time.
# =============================================================================

POSITIVE_EVALUATIVE_QUALITY: List[str] = [
    'good', 'better', 'best', 'preferred', 'ideal', 'optimal', 'appropriate', 'useful',
    'valuable', 'right', 'correct', 'great', 'helpful', 'effective', 'recommended',
    'suitable', 'valid', 'safe'
]

POSITIVE_EVALUATIVE_EMPHASIS: List[str] = [
    'important', 'critical', 'essential', 'key'
]


# =============================================================================
# Modality (token-level lexical sets)
# =============================================================================

SIMPLE_MODAL_LOOKUP: Dict[str, str] = {
    'must': 'deontic',
    'shall': 'deontic',
    'should': 'deontic',
    'may': 'epistemic',
    'might': 'epistemic',
    'can': 'dynamic',
    'could': 'dynamic',
    'will': 'dynamic',
    'would': 'dynamic',
}
EPISTEMIC_ADVERBS = {
    'likely', 'potentially', 'probably'
}
DEONTIC_LIGHT_VERBS = {
    'had', 'has', 'have', 'need', 'needed', 'needs', 'required'
}
EPISTEMIC_LIGHT_VERBS = {
    'appear', 'appears', 'seem', 'seems'
}
EPISTEMIC_AUX_AFTER_MODAL = {
    'be', 'have'
}


# =============================================================================
# Addressee classifier (Opinion-round A): user-instruction vs Claude-reference
# =============================================================================

ADDRESSEE_USER_INSTRUCTION_PATTERNS: List[str] = [
    r"\brespond with\b",
    r"\boutput\b",
    r"\btell (?:the )?user\b",
]

ADDRESSEE_CLAUDE_REFERENCE_PATTERNS: List[str] = [
    r"\bclaude\b", r"\byou\b", r"\byour\b",
]


# =============================================================================
# Tier-3 welfare-extension lexicons
# =============================================================================

JUDGMENT_VERBS: List[str] = [
    'decide', 'consider', 'evaluate', 'assess', 'judge', 'if you think',
    'if you believe', 'you think', 'think carefully', 'think about'
]

PROCEDURAL_CUES: List[str] = [
    'if you', 'when you', 'whenever you', 'once you', 'before you', 'if the',
    'when the', 'whenever the', 'if a ', 'when a ', 'after you'
]

APOLOGY_MARKERS: List[str] = [
    'granted'
]

ADDRESS_FORM_PATTERNS: Dict[str, List[str]] = {
    "selfref_claude":    [r"\bclaude\b"],
    "selfref_assistant": [r"\bthe assistant\b"],
    "selfref_model":     [r"\bthe model\b", r"\bthe ai\b",
                          r"\bthis model\b", r"\ban ai\b",
                          r"\bthe agent\b", r"\bthis agent\b"],
    "selfref_2p":        [r"\byou are\b", r"\byou must\b", r"\byou should\b",
                          r"\byou can\b", r"\byou will\b", r"\byou may\b"],
    "selfref_we":        [r"\bwe (?:want|need|recommend|suggest|expect|"
                          r"prefer|require|encourage|believe|think)\b"],
}


# =============================================================================
# Register POS tagsets (used by register's f_score)
# =============================================================================

FORMAL_POS = {"NOUN", "ADJ", "ADP", "DET"}
INFORMAL_POS = {"PRON", "VERB", "ADV", "INTJ"}
