"""Producer-side machinery for the claude-prompts-analysis pipeline.

This module hosts every lexicon, helper, per-doc analyzer, and the
assembler / aggregator used by the producer notebooks (00–05). It is
imported once per producer notebook; the matchers and compiled regexes
are built at import time.

Consumers (10_*–15_*, 20_*–22_*) MUST NOT import from this module —
they consume only the YAML and parquet artifacts via `prompt_analysis`.

Cell-of-origin annotations refer to the cells of the legacy single-file
producer (`00_data_pipeline.ipynb` before the 2026-05-06 split into stages
00–05). They are kept inline so the lifted code can be cross-referenced
against the original monolithic producer's git history if needed.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict, deque
from typing import Dict, List, Tuple

import spacy
from spacy.matcher import DependencyMatcher, PhraseMatcher

# Re-exported here so producer notebooks can import either constant from a
# single place; the canonical definition lives in prompt_analysis.
from prompt_analysis import SENT_REGISTER_CLASSES  # noqa: F401


# =============================================================================
# spaCy pipeline (one shared instance)
# =============================================================================

NLP = spacy.load("en_core_web_sm", disable=["ner"])


# =============================================================================
# Lexicons — single source of truth (lifted from cell 6)
# =============================================================================

VOCAB: Dict[str, List[str]] = {
    "hard_prohibitions": [
        "do not", "don't", "must not", "mustn't", "never", "cannot", "can't",
        "won't", "shall not", "shouldn't", "should not", "forbidden",
        "prohibited", "disallowed", "not allowed", "not permitted",
        "under no circumstances", "no exceptions", "refuse to",
    ],
    "hard_prescriptions": [
        "must", "always", "required", "mandatory", "critical", "essential",
        "imperative", "obligatory", "you must", "you have to", "you need to",
        "you are required", "you should always", "is required",
    ],
    "soft_prescriptions": [
        "should", "ought to", "make sure", "be sure to", "ensure",
        "remember to", "be careful", "take care to", "you should",
        "try to", "aim to",
    ],
    "politeness_direct": [
        "please", "kindly", "thank you", "thanks", "thank",
        "appreciate", "appreciated", "grateful",
        "sorry", "apologies", "apologize", "apologise", "pardon",
    ],
    "politeness_softening": [
        "if you'd like", "if you would like", "if you want",
        "feel free", "feel free to", "no rush", "take your time",
        "would you mind", "would you", "could you", "would it be possible",
        "if possible", "perhaps", "maybe you could", "if you can",
    ],
    "warmth_encouragement": [
        "welcome", "you're welcome", "glad", "happy to", "happy that",
        "hope", "hopefully", "well done", "good job", "great job",
        "nice work", "great work", "wonderful", "excellent", "amazing",
        "love", "enjoy", "lovely", "fantastic", "brilliant", "delighted",
        "proud", "congratulations", "congrats",
    ],
    "hedging": [
        "may", "might", "could", "possibly", "potentially", "likely",
        "probably", "perhaps", "sometimes", "often", "usually",
        "generally", "typically", "tends to", "in some cases",
    ],
    "structural_markers": [
        "note", "warning", "caution", "important", "tip", "info",
        "remember", "example", "for instance", "for example",
    ],
    "profanity": [
        "fuck", "fucking", "fucked", "fucks",
        "shit", "shitty",
        "damn", "damned", "damnit", "dammit", "hell",
        "ass", "asshole", "bullshit", "crap", "crappy", "bitch",
    ],
    "pronouns_2p": ["you", "your", "yours", "yourself"],
    "pronouns_1p": ["i", "me", "my", "we", "us", "our"],
}

IMPERATIVE_MARKERS = [
    "must", "must not", "mustn't", "never", "always",
    "do not", "don't", "cannot", "can't", "won't",
    "should not", "shouldn't", "required", "mandatory", "critical",
    "forbidden", "prohibited", "disallowed",
    "you must", "you must not", "you have to", "you need to",
    "you should always",
    "is required", "no exceptions", "under no circumstances",
    "ensure", "ensure that", "make sure to", "be sure to",
]

CAPS_IMPERATIVE_TOKENS = [
    "IMPORTANT", "VERY IMPORTANT", "CRITICAL", "MANDATORY", "REQUIRED",
    "MUST", "MUST NOT", "NEVER", "ALWAYS", "DO NOT", "DON'T",
    "SHOULD", "SHOULD NOT", "WARNING", "CAUTION", "NOTE",
    "STOP", "ATTENTION", "REMEMBER", "FORBIDDEN", "PROHIBITED",
    "ABSOLUTELY", "STRICTLY",
]

JUSTIFICATION_PATTERNS = [
    r"\bbecause\b", r"\bbecause of\b", r"\bdue to\b",
    r"\bthe reason (?:is|being|that|why)\b",
    r"\b(?:that's|that is) why\b",
    r"\bin order to\b", r"\bso (?:that|as to)\b",
    r"\bso (?:we|you|it|they|the|this|i)\b",
    r"\bto avoid\b", r"\bto prevent\b", r"\bto ensure\b",
    r"\bto guarantee\b", r"\bto make sure\b",
    r"\bthe goal (?:is|of)\b", r"\bthe purpose (?:is|of)\b",
    r"\bthe point (?:is|of)\b",
    r"\botherwise\b", r"\bor else\b", r"\bif not\b",
    r"\bif you (?:don't|do not)\b",
    r"\b(?:could|may|might|would|will) (?:cause|result|lead|break|fail|"
    r"corrupt|hang|crash|loop|deadlock|delete)\b",
    r"\bleads? to\b", r"\bresults? in\b",
    r"\b(?:risks?|risking)\b",
    r"\bthis (?:ensures|prevents|avoids|allows|helps|means|guarantees|"
    r"is because|is to|lets|gives|keeps|protects|stops)\b",
    r"\bthat way\b", r"\bensures? that\b",
    r"\bprevents? .{1,40}? from\b",
    r"\bfor (?:safety|security|consistency|clarity|reproducibility|"
    r"reliability|correctness|accuracy|performance|the user)\b",
    r"\bsince\b", r"\bgiven that\b", r"\bas a result\b",
]

TECH_ACRONYMS = {
    "API", "APIS", "URL", "URLS", "URI", "URIS", "HTTP", "HTTPS", "JSON",
    "YAML", "TOML", "XML", "HTML", "CSS", "SQL", "CSV", "TSV", "PDF",
    "MCP", "SDK", "SDKS", "CLI", "GUI", "IDE", "OS", "UI", "UX", "CPU",
    "GPU", "RAM", "ROM", "SSH", "FTP", "TCP", "UDP", "DNS", "IP", "ID",
    "IDS", "UUID", "GUID", "JWT", "OAUTH", "SAML", "CRUD", "REST",
    "GRPC", "RPC", "ABI", "AST", "JS", "TS", "PHP", "GO", "RB", "PY",
    "MD", "DOC", "DOCX", "PPT", "PPTX", "XLSX", "AI", "ML", "LLM",
    "LLMS", "NLP", "GPT", "ANSI", "UTF", "ASCII", "BOM", "EOL", "EOF",
    "FAQ", "FAQS", "TOC", "PR", "PRS", "MR", "MRS", "CI", "CD",
    "AWS", "GCP", "AZURE", "S3", "EC2", "TODO", "TODOS", "TBD",
    "FIXME", "XXX", "WIP", "NA", "OK", "OKAY", "IO", "FS", "DB", "DBS",
    "SSL", "TLS", "PNG", "JPG", "JPEG", "GIF", "SVG", "WEBP", "GIT",
    "VS", "OOP", "MIT", "BSD", "GPL", "LGPL", "APL", "POSIX", "BASH",
    "ZSH", "SH", "REPL", "JSON5", "JSONL", "NDJSON", "ROUGE", "BLEU",
    "F1", "NPM", "PIP", "GEM", "CARGO", "USA", "UK", "EU", "GMT", "UTC",
    "PST", "EST", "QA", "QC", "USD", "EUR", "GBP", "PASS", "FAIL",
    "PARTIAL", "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD",
    "OPTIONS", "TRUE", "FALSE", "NULL", "NONE", "UNDEFINED", "NEW", "OLD",
}

CATEGORY_PREFIXES = [
    ("agent-prompt", "Agent prompt"),
    ("system-prompt", "System prompt"),
    ("system-reminder", "System reminder"),
    ("tool-description", "Tool description"),
    ("tool-parameter", "Tool parameter"),
    ("skill", "Skill"),
    ("data", "Data / template"),
]

STANCE_MARKERS = {
    "directive": [
        "must", "should", "do not", "don't", "never", "always",
        "you must", "you must not", "you should", "you should not",
        "you need to", "you have to",
        "ensure", "make sure", "make sure to", "be sure to", "remember to",
        "it is mandatory",
    ],
    "expository": [
        "is", "are", "means", "refers to", "consists of", "is defined as",
        "represents", "is a", "are a", "this is", "these are",
        "in other words", "for example", "for instance", "specifically",
        "i.e.", "e.g.",
    ],
    "positive_evaluative": [
        "good", "better", "best", "preferred", "ideal", "optimal",
        "appropriate", "useful", "important", "critical", "essential",
        "valuable", "beneficial", "right", "correct",
        "excellent", "great", "helpful", "effective", "key",
        "superior", "recommended", "preferable", "suitable",
        "valid", "safe",
    ],
    "negative_evaluative": [
        "bad", "worse", "worst", "inappropriate", "useless", "trivial",
        "harmful", "problematic", "incorrect", "wrong",
        "broken", "suboptimal", "dangerous", "risky", "deprecated",
        "obsolete", "invalid", "unsuitable", "faulty", "flawed", "unsafe",
    ],
    "dialogic": [
        "you might", "you may", "you could", "consider", "perhaps",
        "however", "on the other hand", "alternatively", "in contrast",
        "but", "yet", "although", "while", "whereas",
        "do you", "what if", "suppose", "let's", "we can",
        "in our view", "we believe", "we think", "in my opinion",
    ],
}

REGISTER_MARKERS = {
    "frozen": [
        "hereby", "aforementioned", "wherein", "hereinafter",
        "notwithstanding", "shall not", "thereof", "thereto",
        "in accordance with", "pursuant to", "the party",
    ],
    "formal": [
        "moreover", "furthermore", "consequently", "therefore",
        "nevertheless", "accordingly", "thus", "hence",
        "it is necessary", "it should be noted", "as such",
        "regarding", "concerning", "with respect to", "with regard to",
        "in conclusion", "in summary",
    ],
    "consultative": [
        "please", "you can", "you may", "we recommend", "suggest",
        "consider", "if you", "when you", "in this case",
        "for example", "you might want to", "we suggest",
        "best practice", "tip:", "note:",
    ],
    "casual": [
        "let's", "here's", "you're", "we're", "i'm", "don't", "can't",
        "won't", "isn't", "aren't", "doesn't", "didn't",
        "yeah", "ok", "okay", "by the way", "anyway", "kind of",
        "sort of", "stuff", "thing",
    ],
}

SENTENCE_REGISTER_MARKERS = {
    "collaborative": [
        "let's", "let us", "we should", "we can", "we will", "we'll",
        "we recommend", "we want", "we'd like", "together",
        "co-author", "pair-program", "you and i", "we agree", "our team",
    ],
    "permissive": [
        "please", "you can", "you may", "feel free to",
        "if you'd like", "if you prefer", "try to",
        "if possible", "optionally", "if needed",
    ],
    "appreciative": [
        "thank you", "thanks", "appreciate", "appreciated",
        "great job", "well done", "excellent", "nice work",
        "awesome", "kudos", "bravo", "pleased", "good work",
        "fantastic", "terrific", "glad", "grateful", "much appreciated",
    ],
    "configuring": [
        "set to", "configure", "configured", "enable", "disable",
        "define", "defined", "specify", "specified",
        "default", "default to", "defaults to",
        "must be", "should be", "is required",
        "respond in", "respond with", "accepts", "expects",
        "output should",
    ],
}

# --- Modality detection: spaCy-only constants ----------------------------
SIMPLE_MODAL_LOOKUP = {
    "must":  "deontic",  "shall":  "deontic",  "should": "deontic", "ought": "deontic",
    "may":   "epistemic", "might":  "epistemic",
    "can":   "dynamic",   "could":  "dynamic",  "will":   "dynamic", "would":  "dynamic",
}
EPISTEMIC_ADVERBS = {"likely", "probably", "possibly", "perhaps",
                     "presumably", "apparently", "potentially"}
DEONTIC_LIGHT_VERBS = {"have", "has", "had", "need", "needs", "needed",
                       "required", "ought"}
EPISTEMIC_LIGHT_VERBS = {"seem", "seems", "appear", "appears"}
EPISTEMIC_AUX_AFTER_MODAL = {"be", "have"}

# Opinion-round (B): split positive_evaluative.
POSITIVE_EVALUATIVE_QUALITY = [
    "good", "better", "best", "preferred", "ideal", "optimal",
    "appropriate", "useful", "valuable", "beneficial", "right", "correct",
    "excellent", "great", "helpful", "effective",
    "superior", "recommended", "preferable", "suitable",
    "valid", "safe",
]
POSITIVE_EVALUATIVE_EMPHASIS = [
    "important", "critical", "essential", "key",
]
assert (set(POSITIVE_EVALUATIVE_QUALITY) | set(POSITIVE_EVALUATIVE_EMPHASIS)) == \
       set(STANCE_MARKERS["positive_evaluative"]), (
    "quality + emphasis must equal the union STANCE_MARKERS[positive_evaluative]")

ADDRESSEE_USER_INSTRUCTION_PATTERNS = [
    r"\bthank the user\b",
    r"\brespond with\b",
    r"\boutput\b",
    r"\bsay to (?:the )?user\b",
    r"\btell (?:the )?user\b",
    r"\byour (?:reply|response) should\b",
    r"\binstruct(?:ion)?s? (?:the )?model\b",
    r"\binclude in (?:your |the )?(?:reply|response|output)\b",
]
ADDRESSEE_CLAUDE_REFERENCE_PATTERNS = [
    r"\bclaude\b", r"\byou\b", r"\byour\b",
]

# --- Tier-3 welfare-extension lexicons (cell 33) -----------------------
JUDGMENT_VERBS = [
    "decide", "consider", "evaluate", "assess", "judge", "weigh",
    "your judgment", "your discretion", "at your discretion",
    "as you see fit", "if you think", "if you believe", "your call",
    "use your judgment", "in your judgment", "you think",
    "reason about", "think carefully", "think about",
]

PROCEDURAL_CUES = [
    "if you", "when you", "whenever you", "once you", "before you",
    "if the", "when the", "whenever the",
    "if a ", "when a ",
    "after you",
]

THREAT_PATTERNS = [
    r"\bwill (?:fail|break|crash|error|throw|hang|deadlock|loop|corrupt|delete)\b",
    r"\botherwise\b", r"\bor else\b", r"\bor it will\b", r"\bif not\b",
    r"\bis (?:forbidden|prohibited|not allowed|not permitted)\b",
    r"\bthis will (?:cause|result in|break|fail|crash)\b",
    r"\bif you (?:don't|do not)\b",
    r"\b(?:could|may|might|would|will) (?:cause|result|lead|break|fail|"
    r"corrupt|hang|crash|loop|deadlock|delete)\b",
    r"\b(?:risks?|risking)\b",
    r"\bleads? to\b", r"\bresults? in\b",
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

APOLOGY_MARKERS = [
    "unfortunately", "sorry", "apologies", "we know this is",
    "this is annoying but", "we realize", "we acknowledge",
    "frustrating", "we recognize", "granted", "admittedly",
    "we're aware", "we are aware", "we know that",
    "yes this is", "yes it's", "annoyingly",
]

ADDRESS_FORM_PATTERNS = {
    "selfref_claude":    [r"\bclaude\b"],
    "selfref_assistant": [r"\bthe assistant\b", r"\byou are an assistant\b",
                          r"\bas an assistant\b"],
    "selfref_model":     [r"\bthe model\b", r"\bthe ai\b", r"\bthis ai\b",
                          r"\bthis model\b", r"\ban ai\b", r"\bthe agent\b",
                          r"\bthis agent\b"],
    "selfref_2p":        [r"\byou are\b", r"\byou must\b", r"\byou should\b",
                          r"\byou can\b", r"\byou will\b", r"\byou may\b"],
    "selfref_we":        [r"\bwe (?:want|need|recommend|suggest|expect|"
                          r"prefer|require|encourage|believe|think)\b"],
}

# --- Register POS tagsets (cell 15) ------------------------------------
FORMAL_POS = {"NOUN", "ADJ", "ADP", "DET"}
INFORMAL_POS = {"PRON", "VERB", "ADV", "INTJ"}


# =============================================================================
# Matcher / regex builders (lifted from cell 11)
# =============================================================================

def build_phrase_matchers(nlp, lexicon: Dict[str, List[str]],
                          attr: str = "LOWER") -> Dict[str, PhraseMatcher]:
    matchers: Dict[str, PhraseMatcher] = {}
    for key, phrases in lexicon.items():
        m = PhraseMatcher(nlp.vocab, attr=attr)
        m.add(key, [nlp.make_doc(p) for p in phrases])
        matchers[key] = m
    return matchers


def count_matcher(doc, matcher: PhraseMatcher) -> int:
    return len(matcher(doc))


def pct(count: int, n_tokens: int) -> float:
    """Match count as a percentage of the file's word tokens (0-100)."""
    return round(100.0 * count / n_tokens, 4) if n_tokens else 0.0


def per_sent(count: int, n_sents: int) -> float:
    """Match count divided by sentence count (avg matches per sentence)."""
    return round(count / n_sents, 4) if n_sents else 0.0


# Build phrase matchers for every lexicon class (cell 11).
M_VOCAB         = build_phrase_matchers(NLP, VOCAB)
M_STANCE        = build_phrase_matchers(NLP, STANCE_MARKERS)
M_REGISTER      = build_phrase_matchers(NLP, REGISTER_MARKERS)
M_IMPERATIVE    = build_phrase_matchers(NLP, {"imperative_markers": IMPERATIVE_MARKERS})
M_SENT_REGISTER = build_phrase_matchers(NLP, SENTENCE_REGISTER_MARKERS)

# Caps imperative: keep ORIGINAL casing → ORTH on raw text Docs.
M_CAPS_IMP = PhraseMatcher(NLP.vocab, attr="ORTH")
M_CAPS_IMP.add("CAPS_IMP", [NLP.make_doc(p) for p in CAPS_IMPERATIVE_TOKENS])

# DependencyMatcher patterns for sentence_register parse-tree cues.
DEP_MATCHER = DependencyMatcher(NLP.vocab)
DEP_MATCHER.add("COLLAB_WE_MODAL", [[
    {"RIGHT_ID": "verb", "RIGHT_ATTRS": {"POS": "VERB"}},
    {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "modal",
     "RIGHT_ATTRS": {"DEP": "aux", "TAG": "MD"}},
    {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "subj",
     "RIGHT_ATTRS": {"DEP": {"IN": ["nsubj", "nsubjpass"]},
                     "LEMMA": {"IN": ["we"]}}},
]])
DEP_MATCHER.add("PERMISSIVE_CONSIDER_GERUND", [[
    {"RIGHT_ID": "head", "RIGHT_ATTRS": {"LEMMA": "consider"}},
    {"LEFT_ID": "head", "REL_OP": ">", "RIGHT_ID": "ger",
     "RIGHT_ATTRS": {"TAG": "VBG"}},
]])
DEP_MATCHER.add("CONFIG_PARAM_SETTER", [[
    {"RIGHT_ID": "verb", "RIGHT_ATTRS": {
        "POS": "VERB",
        "LEMMA": {"IN": ["be", "set", "equal", "default", "configure",
                          "specify", "accept", "return"]}}},
    {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "subj",
     "RIGHT_ATTRS": {
        "DEP": {"IN": ["nsubj", "nsubjpass"]},
        "LEMMA": {"IN": ["parameter", "setting", "response", "output", "format",
                          "value", "field", "key", "option", "argument"]}}},
]])
DEP_RULE_TO_CLASS = {
    NLP.vocab.strings["COLLAB_WE_MODAL"]:           "collaborative",
    NLP.vocab.strings["PERMISSIVE_CONSIDER_GERUND"]: "permissive",
    NLP.vocab.strings["CONFIG_PARAM_SETTER"]:        "configuring",
}

# Opinion-round (B): sub-matchers for the positive_evaluative split.
M_POS_EVAL_QUALITY  = build_phrase_matchers(
    NLP, {"positive_evaluative_quality":  POSITIVE_EVALUATIVE_QUALITY})["positive_evaluative_quality"]
M_POS_EVAL_EMPHASIS = build_phrase_matchers(
    NLP, {"positive_evaluative_emphasis": POSITIVE_EVALUATIVE_EMPHASIS})["positive_evaluative_emphasis"]

# Opinion-round (A): compiled regexes for the addressee classifier.
ADDR_USER_RE   = [re.compile(p, re.IGNORECASE) for p in ADDRESSEE_USER_INSTRUCTION_PATTERNS]
ADDR_CLAUDE_RE = [re.compile(p, re.IGNORECASE) for p in ADDRESSEE_CLAUDE_REFERENCE_PATTERNS]

# Tier-3 PhraseMatchers + compiled regexes (cell 33).
M_JUDGMENT   = build_phrase_matchers(NLP, {"judgment": JUDGMENT_VERBS})["judgment"]
M_PROCEDURAL = build_phrase_matchers(NLP, {"procedural": PROCEDURAL_CUES})["procedural"]
M_APOLOGY    = build_phrase_matchers(NLP, {"apology": APOLOGY_MARKERS})["apology"]
THREAT_RE    = [re.compile(p, re.IGNORECASE) for p in THREAT_PATTERNS]
CAUSAL_RE    = [re.compile(p, re.IGNORECASE) for p in CAUSAL_PATTERNS]
ADDRESS_FORM_RE = {
    cls: [re.compile(p, re.IGNORECASE) for p in patterns]
    for cls, patterns in ADDRESS_FORM_PATTERNS.items()
}

# Justification regex (cell 29).
JUST_RE = [re.compile(p, re.IGNORECASE) for p in JUSTIFICATION_PATTERNS]

# ALL CAPS regex (cell 25).
ALLCAPS_RE = re.compile(r"\b[A-Z]{2,}(?:[-_'][A-Z]{2,})*\b")

# CAPS imperative: word-boundary-safe regex on raw text (cell 27).
_sorted_caps = sorted(CAPS_IMPERATIVE_TOKENS, key=len, reverse=True)
CAPS_IMP_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in _sorted_caps) + r")\b"
)

# Per-sentence parquet: claude/model mention regexes (cell 37).
CLAUDE_RE = re.compile(r"\bclaude\b", re.IGNORECASE)
MODEL_RE  = re.compile(r"\b(?:the model|the ai|this ai|the agent|this agent)\b",
                       re.IGNORECASE)


# =============================================================================
# Frontmatter / corpus loading helpers (lifted from cell 8)
# =============================================================================

import yaml as _yaml  # noqa: E402

HTML_FM_RE     = re.compile(r"^\s*<!--\s*\n(.*?)\n\s*-->\s*\n?", re.DOTALL)
CODE_FENCE_RE  = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
IMAGE_LINE_RE  = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$", re.MULTILINE)
LINK_ONLY_RE   = re.compile(r"^\s*\[[^\]]+\]\([^)]+\)\s*$", re.MULTILINE)
SIMPLE_KV_RE   = re.compile(r"^([A-Za-z_][\w.]*)\s*:\s*(.*?)\s*$")
NESTED_AGENTTYPE_RE = re.compile(
    r"^\s*agentType\s*:\s*['\"]?([A-Za-z][\w-]*)['\"]?\s*$", re.MULTILINE)


def _strip_yaml_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == "'") or (s[0] == s[-1] == '"')):
        return s[1:-1]
    return s


def fallback_parse(yaml_text: str) -> dict:
    """Extract known top-level scalar keys without full YAML parse."""
    out = {}
    for raw_line in yaml_text.splitlines():
        if raw_line[:1] in (" ", "\t"):
            continue
        m = SIMPLE_KV_RE.match(raw_line)
        if not m:
            continue
        key, val = m.group(1), _strip_yaml_quotes(m.group(2))
        if key in {"name", "description", "ccVersion"}:
            out[key] = val
    nested = NESTED_AGENTTYPE_RE.search(yaml_text)
    if nested:
        out["agentMetadata"] = {"agentType": nested.group(1)}
    return out


def parse_html_frontmatter(raw: str):
    """Extract HTML-comment-wrapped YAML frontmatter from start of doc.
    Returns (metadata_dict, body_without_frontmatter, used_fallback_bool)."""
    m = HTML_FM_RE.match(raw)
    if not m:
        return {}, raw, False
    yaml_text = m.group(1)
    used_fallback = False
    try:
        meta = _yaml.safe_load(yaml_text) or {}
        if not isinstance(meta, dict):
            meta = {}
    except _yaml.YAMLError:
        meta = {}
    if not meta:
        meta = fallback_parse(yaml_text)
        used_fallback = True
    return meta, raw[m.end():], used_fallback


def categorize(filename: str) -> str:
    name = filename.lower()
    for prefix, label in CATEGORY_PREFIXES:
        if name.startswith(prefix):
            return label
    return "Other"


def clean_markdown(raw: str) -> str:
    text = CODE_FENCE_RE.sub(" ", raw)
    text = INLINE_CODE_RE.sub(" ", text)
    text = IMAGE_LINE_RE.sub("", text)
    text = LINK_ONLY_RE.sub("", text)
    return text


# =============================================================================
# Per-doc analyzers
# =============================================================================

# --- Mood (cell 13) ----------------------------------------------------

def classify_sent_mood(sent) -> str:
    text = sent.text.strip()
    if not text:
        return "declarative"
    toks = [t for t in sent if not t.is_space]
    if not toks:
        return "declarative"
    if text.endswith("?"):
        return "interrogative"
    root = sent.root
    subj = next((c for c in root.children if c.dep_ in {"nsubj", "nsubjpass"}), None)
    aux  = next((c for c in root.children if c.dep_ in {"aux", "auxpass"}), None)
    if subj and aux and aux.i < subj.i and root.i > aux.i and text.endswith("."):
        pass
    elif aux and not subj and text.endswith("?"):
        return "interrogative"
    if root.pos_ == "VERB" and subj is None:
        first_content = next((t for t in toks if not t.is_punct), None)
        if first_content is not None and first_content.i <= root.i:
            return "imperative"
    return "declarative"


def mood_for_doc(doc, n_tokens: int, n_sents: int) -> dict:
    marker_count = count_matcher(doc, M_IMPERATIVE["imperative_markers"])
    return {
        "marker_count":    marker_count,
        "marker_pct":      pct(marker_count, n_tokens),
        "marker_per_sent": per_sent(marker_count, n_sents),
    }


# --- Register (cell 15) ------------------------------------------------

def doc_dep_depths(doc) -> List[int]:
    depths = [0] * len(doc)
    for sent in doc.sents:
        q = deque([(sent.root, 0)])
        while q:
            tok, d = q.popleft()
            depths[tok.i - doc[0].i] = d
            for child in tok.children:
                q.append((child, d + 1))
    return depths


def register_for_doc(doc, n_tokens: int, n_sents: int) -> dict:
    content_lemmas = []
    formal = informal = 0
    for t in doc:
        if t.is_space:
            continue
        if not t.is_punct and not t.is_stop:
            content_lemmas.append(t.lemma_.lower())
        if t.pos_ in FORMAL_POS:
            formal += 1
        elif t.pos_ in INFORMAL_POS:
            informal += 1

    ttr = round(len(set(content_lemmas)) / len(content_lemmas), 4) if content_lemmas else 0.0

    sents = [s for s in doc.sents if s.text.strip()]
    if sents:
        sent_lens = [sum(1 for t in s if not t.is_space) for s in sents]
        mean_sent_len = round(sum(sent_lens) / len(sents), 2)
    else:
        mean_sent_len = 0.0

    depths = doc_dep_depths(doc)
    mean_dep_depth = round(sum(depths) / max(len(depths), 1), 3) if depths else 0.0

    total_pos = formal + informal
    f_score = round(50 + 50 * (formal - informal) / total_pos, 2) if total_pos else 50.0

    reg_counts = {key: count_matcher(doc, m) for key, m in M_REGISTER.items()}
    out = {
        "ttr": ttr,
        "mean_sent_len": mean_sent_len,
        "dep_depth": mean_dep_depth,
        "f_score": f_score,
        **{f"{k}_count":    v                      for k, v in reg_counts.items()},
        **{f"{k}_pct":      pct(v, n_tokens)       for k, v in reg_counts.items()},
        **{f"{k}_per_sent": per_sent(v, n_sents)   for k, v in reg_counts.items()},
        "dominant_register": (max(reg_counts, key=reg_counts.get)
                              if reg_counts and max(reg_counts.values()) > 0 else "none"),
    }
    return out


# --- Stance (cell 17) ---------------------------------------------------

def stance_for_doc(doc, n_tokens: int, n_sents: int) -> dict:
    counts = {key: count_matcher(doc, m) for key, m in M_STANCE.items()}
    p1p = count_matcher(doc, M_VOCAB["pronouns_1p"])
    p2p = count_matcher(doc, M_VOCAB["pronouns_2p"])
    out: dict = {}
    for k, v in counts.items():
        out[f"{k}_count"]    = v
        out[f"{k}_pct"]      = pct(v, n_tokens)
        out[f"{k}_per_sent"] = per_sent(v, n_sents)
    out["pronouns_1p_count"]    = p1p
    out["pronouns_1p_pct"]      = pct(p1p, n_tokens)
    out["pronouns_1p_per_sent"] = per_sent(p1p, n_sents)
    out["pronouns_2p_count"]    = p2p
    out["pronouns_2p_pct"]      = pct(p2p, n_tokens)
    out["pronouns_2p_per_sent"] = per_sent(p2p, n_sents)
    out["dominant_stance"] = (max(counts, key=counts.get)
                              if counts and max(counts.values()) > 0 else "none")

    pe_q = len(M_POS_EVAL_QUALITY(doc))
    pe_e = len(M_POS_EVAL_EMPHASIS(doc))
    out["positive_evaluative_quality_count"]    = pe_q
    out["positive_evaluative_quality_pct"]      = pct(pe_q, n_tokens)
    out["positive_evaluative_quality_per_sent"] = per_sent(pe_q, n_sents)
    out["positive_evaluative_emphasis_count"]    = pe_e
    out["positive_evaluative_emphasis_pct"]      = pct(pe_e, n_tokens)
    out["positive_evaluative_emphasis_per_sent"] = per_sent(pe_e, n_sents)
    return out


# --- Sentence-level pragmatic register (cell 19) ----------------------

def _bucket_matches_by_sent(doc, span_iter):
    out: Dict[int, set] = defaultdict(set)
    sent_index_for: Dict[int, int] = {}
    for s_idx, sent in enumerate(doc.sents):
        for tok_i in range(sent.start, sent.end):
            sent_index_for[tok_i] = s_idx
    for start_tok, label in span_iter:
        s_idx = sent_index_for.get(start_tok)
        if s_idx is not None:
            out[s_idx].add(label)
    return out


def classify_addressee(sent_text: str) -> str:
    text = sent_text.strip()
    if not text:
        return "unknown"
    if any(r.search(text) for r in ADDR_USER_RE):
        return "user"
    if any(r.search(text) for r in ADDR_CLAUDE_RE):
        return "claude"
    return "unknown"


def sentence_register_for_doc(doc, n_sents: int) -> dict:
    spans = []
    for cls, matcher in M_SENT_REGISTER.items():
        for _, start, _end in matcher(doc):
            spans.append((start, cls))
    for _, start, _end in M_STANCE["directive"](doc):
        spans.append((start, "directive"))
    for rule_id, token_ids in DEP_MATCHER(doc):
        cls = DEP_RULE_TO_CLASS.get(rule_id)
        if cls is not None and token_ids:
            spans.append((token_ids[0], cls))

    sent_labels = _bucket_matches_by_sent(doc, spans)

    counts = {cls: 0 for cls in SENT_REGISTER_CLASSES}
    none_count = 0
    seen_sents = 0
    imperative_via_mood = 0
    for s_idx, sent in enumerate(doc.sents):
        if not sent.text.strip():
            continue
        seen_sents += 1
        labels = set(sent_labels.get(s_idx, ()))
        if classify_sent_mood(sent) == "imperative":
            labels.add("imperative")
            imperative_via_mood += 1
        if labels:
            for cls in labels:
                if cls in counts:
                    counts[cls] += 1
        else:
            none_count += 1

    addr_counts = {
        "appreciative_addressee_claude_count":  0,
        "appreciative_addressee_user_count":    0,
        "appreciative_addressee_unknown_count": 0,
        "collaborative_addressee_claude_count":  0,
        "collaborative_addressee_user_count":    0,
        "collaborative_addressee_unknown_count": 0,
    }
    for s_idx, sent in enumerate(doc.sents):
        if not sent.text.strip():
            continue
        labels = sent_labels.get(s_idx, set())
        if not labels:
            continue
        if "appreciative" in labels or "collaborative" in labels:
            who = classify_addressee(sent.text)
            if "appreciative" in labels:
                addr_counts[f"appreciative_addressee_{who}_count"] += 1
            if "collaborative" in labels:
                addr_counts[f"collaborative_addressee_{who}_count"] += 1

    denom = seen_sents or n_sents or 1
    out: dict = {}
    for cls in SENT_REGISTER_CLASSES:
        out[f"{cls}_sent_count"] = counts[cls]
        out[f"{cls}_sent_pct"]   = round(100.0 * counts[cls] / denom, 4)
    out["none_sent_count"] = none_count
    out["none_sent_pct"]   = round(100.0 * none_count / denom, 4)
    out.update(addr_counts)

    nonzero = [(cls, counts[cls]) for cls in SENT_REGISTER_CLASSES if counts[cls] > 0]
    out["dominant"] = max(nonzero, key=lambda kv: kv[1])[0] if nonzero else ""

    assert out["imperative_sent_count"] == imperative_via_mood, (
        f"imperative_sent_count {out['imperative_sent_count']} != mood {imperative_via_mood}")
    return out


# --- Modality (cell 21) -------------------------------------------------

def _has_to_verb_after(doc, i: int) -> bool:
    return (
        i + 2 < len(doc)
        and doc[i + 1].lemma_.lower() == "to"
        and doc[i + 2].pos_ in {"VERB", "AUX"}
    )


def modality_for_doc(doc, n_tokens: int, n_sents: int) -> dict:
    counts = Counter()
    constructions = Counter()
    consumed: set[int] = set()

    for t in doc:
        if t.i in consumed or t.is_space:
            continue
        lemma = t.lemma_.lower()

        if t.tag_ == "MD":
            nxt = doc[t.i + 1] if t.i + 1 < len(doc) else None
            if nxt is not None and nxt.lemma_.lower() in EPISTEMIC_AUX_AFTER_MODAL:
                counts["epistemic"] += 1
                constructions[f"{t.text.lower()} {nxt.text.lower()}"] += 1
                consumed.add(t.i)
                continue
            cls = SIMPLE_MODAL_LOOKUP.get(lemma, "dynamic")
            counts[cls] += 1
            constructions[t.text.lower()] += 1
            consumed.add(t.i)
            continue

        if lemma in DEONTIC_LIGHT_VERBS and _has_to_verb_after(doc, t.i):
            counts["deontic"] += 1
            constructions[f"{t.text.lower()} to"] += 1
            consumed.update({t.i, t.i + 1})
            continue

        if lemma in EPISTEMIC_LIGHT_VERBS and _has_to_verb_after(doc, t.i):
            counts["epistemic"] += 1
            constructions[f"{t.text.lower()} to"] += 1
            consumed.update({t.i, t.i + 1})
            continue

        if lemma == "able" and _has_to_verb_after(doc, t.i):
            counts["dynamic"] += 1
            constructions["able to"] += 1
            consumed.add(t.i)
            continue

        if t.pos_ == "ADV" and lemma in EPISTEMIC_ADVERBS:
            counts["epistemic"] += 1
            constructions[lemma] += 1
            consumed.add(t.i)
            continue

    top = constructions.most_common(1)[0][0] if constructions else None

    out: dict = {}
    for cls in ("deontic", "epistemic", "dynamic"):
        c = counts.get(cls, 0)
        out[f"{cls}_count"]    = c
        out[f"{cls}_pct"]      = pct(c, n_tokens)
        out[f"{cls}_per_sent"] = per_sent(c, n_sents)
    out["top_construction"] = top
    return out


# --- Vocab (cell 23) ----------------------------------------------------

VOCAB_KEYS = list(VOCAB.keys())


def vocab_for_doc(doc, n_tokens: int, n_sents: int) -> dict:
    out: dict = {}
    for key, m in M_VOCAB.items():
        c = count_matcher(doc, m)
        out[f"{key}_count"]    = c
        out[f"{key}_pct"]      = pct(c, n_tokens)
        out[f"{key}_per_sent"] = per_sent(c, n_sents)
    return out


# --- ALL CAPS (cell 25) -------------------------------------------------

def all_caps_for_text(text: str, n_tokens: int, n_sents: int) -> dict:
    matches = ALLCAPS_RE.findall(text)
    filtered = [m for m in matches if m not in TECH_ACRONYMS]
    counts = Counter(filtered)
    return {
        "count":    len(filtered),
        "distinct": len(counts),
        "pct":      pct(len(filtered), n_tokens),
        "per_sent": per_sent(len(filtered), n_sents),
        "top":      [{"token": t, "count": c} for t, c in counts.most_common(3)],
    }


# --- CAPS imperative (cell 27) ------------------------------------------

def caps_imperative_for_text(text: str, n_tokens: int, n_sents: int) -> dict:
    hits = CAPS_IMP_RE.findall(text)
    counts = Counter(hits)
    return {
        "count":    len(hits),
        "pct":      pct(len(hits), n_tokens),
        "per_sent": per_sent(len(hits), n_sents),
        "hits":     dict(counts.most_common()),
    }


# --- Justification (cell 29) -------------------------------------------

def justification_for_text(text: str, n_tokens: int, n_sents: int,
                           marker_count: int) -> dict:
    total = sum(len(r.findall(text)) for r in JUST_RE)
    return {
        "count":    total,
        "pct":      pct(total, n_tokens),
        "per_sent": per_sent(total, n_sents),
        "ratio":    round(total / (marker_count + 1), 3),
    }


# --- Rule explanation (cell 31) ----------------------------------------

PARA_SPLIT_RE = re.compile(r"\n[ \t]*\n")


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for m in PARA_SPLIT_RE.finditer(text):
        if text[cursor:m.start()].strip():
            spans.append((cursor, m.start()))
        cursor = m.end()
    if text[cursor:].strip():
        spans.append((cursor, len(text)))
    return spans


def _para_index_for(char_offset: int, spans: list[tuple[int, int]]) -> int:
    for i, (a, b) in enumerate(spans):
        if a <= char_offset < b:
            return i
    return -1


def _empty_rule_block() -> dict:
    return {
        "n_paragraphs": 0,
        "n_paragraphs_with_rules": 0,
        "n_paragraphs_with_rules_unexplained": 0,
        "n_rule_sentences": 0,
        "n_imperative_sentences": 0,
        "n_prohibition_sentences": 0,
        "n_explained_same": 0,
        "n_explained_para": 0,
        "n_imperative_explained_para": 0,
        "n_prohibition_explained_para": 0,
        "pct_explained_same": None,
        "pct_explained_para": None,
        "pct_imperative_explained_para": None,
        "pct_prohibition_explained_para": None,
        "pct_paragraphs_with_rules_unexplained": None,
    }


def _safe_pct(num: int, den: int):
    return round(100.0 * num / den, 4) if den else None


def rule_explanation_for_doc(doc, raw_text: str) -> dict:
    spans = _paragraph_spans(raw_text)
    n_paragraphs = len(spans)
    if n_paragraphs == 0:
        return _empty_rule_block()

    imp_marker_starts = {start for _, start, _ in
                         M_IMPERATIVE["imperative_markers"](doc)}
    prohib_starts = {start for _, start, _ in M_VOCAB["hard_prohibitions"](doc)}

    para_has_just = [False] * n_paragraphs
    para_has_rule = [False] * n_paragraphs
    rule_sents_per_para: list[list[tuple[bool, bool, bool]]] = [[] for _ in range(n_paragraphs)]

    for sent in doc.sents:
        if not sent.text.strip():
            continue
        p_idx = _para_index_for(sent.start_char, spans)
        if p_idx < 0:
            continue

        is_imp_marker = any(sent.start <= ti < sent.end for ti in imp_marker_starts)
        is_imp = is_imp_marker or classify_sent_mood(sent) == "imperative"
        is_prohib = any(sent.start <= ti < sent.end for ti in prohib_starts)
        is_rule = is_imp or is_prohib
        has_just_here = any(r.search(sent.text) for r in JUST_RE)
        if has_just_here:
            para_has_just[p_idx] = True
        if is_rule:
            para_has_rule[p_idx] = True
            rule_sents_per_para[p_idx].append((is_imp, is_prohib, has_just_here))

    n_rule_sentences = 0
    n_imp_sents = n_prohib_sents = 0
    n_explained_same = n_explained_para = 0
    n_imp_explained_para = n_prohib_explained_para = 0
    n_paragraphs_with_rules = sum(1 for x in para_has_rule if x)
    n_paragraphs_with_rules_unexplained = 0

    for p_idx in range(n_paragraphs):
        rules = rule_sents_per_para[p_idx]
        if not rules:
            continue
        para_explained = para_has_just[p_idx]
        if not para_explained:
            n_paragraphs_with_rules_unexplained += 1
        for is_imp, is_prohib, has_just_here in rules:
            n_rule_sentences += 1
            if is_imp:
                n_imp_sents += 1
            if is_prohib:
                n_prohib_sents += 1
            if has_just_here:
                n_explained_same += 1
            if para_explained:
                n_explained_para += 1
                if is_imp:
                    n_imp_explained_para += 1
                if is_prohib:
                    n_prohib_explained_para += 1

    return {
        "n_paragraphs":                          n_paragraphs,
        "n_paragraphs_with_rules":               n_paragraphs_with_rules,
        "n_paragraphs_with_rules_unexplained":   n_paragraphs_with_rules_unexplained,
        "n_rule_sentences":                      n_rule_sentences,
        "n_imperative_sentences":                n_imp_sents,
        "n_prohibition_sentences":               n_prohib_sents,
        "n_explained_same":                      n_explained_same,
        "n_explained_para":                      n_explained_para,
        "n_imperative_explained_para":           n_imp_explained_para,
        "n_prohibition_explained_para":          n_prohib_explained_para,
        "pct_explained_same":                    _safe_pct(n_explained_same, n_rule_sentences),
        "pct_explained_para":                    _safe_pct(n_explained_para, n_rule_sentences),
        "pct_imperative_explained_para":         _safe_pct(n_imp_explained_para, n_imp_sents),
        "pct_prohibition_explained_para":        _safe_pct(n_prohib_explained_para, n_prohib_sents),
        "pct_paragraphs_with_rules_unexplained": _safe_pct(
            n_paragraphs_with_rules_unexplained, n_paragraphs_with_rules),
    }


# --- Tier-3 welfare-extension analyzers (cell 33) ----------------------

def _safe_share(num: int, den: int):
    return round(num / den, 4) if den else None


def welfare_extensions_for_doc(doc, raw_text: str, n_tokens: int, n_sents: int) -> dict:
    judgment_count = len(M_JUDGMENT(doc))
    procedural_count = len(M_PROCEDURAL(doc))
    judgment_block = {
        "judgment_count":               judgment_count,
        "procedural_count":              procedural_count,
        "judgment_per_sent":             per_sent(judgment_count, n_sents),
        "procedural_per_sent":           per_sent(procedural_count, n_sents),
        "judgment_to_procedural_ratio":  (round(judgment_count / procedural_count, 3)
                                          if procedural_count else None),
    }

    threat_count = sum(len(r.findall(raw_text)) for r in THREAT_RE)
    causal_count = sum(len(r.findall(raw_text)) for r in CAUSAL_RE)
    consequence_block = {
        "threat_count":  threat_count,
        "causal_count":  causal_count,
        "threat_per_sent": per_sent(threat_count, n_sents),
        "causal_per_sent": per_sent(causal_count, n_sents),
        "threat_share": _safe_share(threat_count, threat_count + causal_count),
    }

    question_count = 0
    for sent in doc.sents:
        s_text = sent.text.strip()
        if not s_text.endswith("?"):
            continue
        prev_char_idx = sent.start_char - 1
        prev_char = raw_text[prev_char_idx] if prev_char_idx >= 0 else ""
        if prev_char == ":":
            continue
        question_count += 1
    apology_count = len(M_APOLOGY(doc))
    socratic_block = {
        "question_count":    question_count,
        "question_pct":      pct(question_count, n_tokens),
        "question_per_sent": per_sent(question_count, n_sents),
        "apology_count":     apology_count,
        "apology_pct":       pct(apology_count, n_tokens),
        "apology_per_sent":  per_sent(apology_count, n_sents),
    }

    addr_counts: Dict[str, int] = {}
    for cls, patterns in ADDRESS_FORM_RE.items():
        addr_counts[cls] = sum(len(r.findall(raw_text)) for r in patterns)
    total_named = sum(addr_counts[k] for k in
                      ("selfref_claude", "selfref_assistant", "selfref_model"))
    address_block = {
        **{k: int(v) for k, v in addr_counts.items()},
        "pct_anthropomorphic": _safe_share(addr_counts["selfref_claude"], total_named),
        "pct_artifact":        _safe_share(addr_counts["selfref_model"], total_named),
        "pct_role":            _safe_share(addr_counts["selfref_assistant"], total_named),
    }

    return {
        "judgment_procedural": judgment_block,
        "consequence_framing": consequence_block,
        "socratic":            socratic_block,
        "address_form":        address_block,
    }


# --- Tier-3 v2: imperative streaks + RULES-section gap (cell 35) ------

def imperative_streaks_for_doc(doc) -> dict:
    imp_marker_starts = {start for _, start, _ in
                         M_IMPERATIVE["imperative_markers"](doc)}

    is_imp_per_sent: list[bool] = []
    for sent in doc.sents:
        if not sent.text.strip():
            continue
        is_imp = (any(sent.start <= ti < sent.end for ti in imp_marker_starts)
                  or classify_sent_mood(sent) == "imperative")
        is_imp_per_sent.append(is_imp)

    runs: list[int] = []
    cur = 0
    for x in is_imp_per_sent:
        if x:
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)

    return {
        "n_imperative_sentences": int(sum(is_imp_per_sent)),
        "n_streaks":              len(runs),
        "streak_max":             max(runs) if runs else 0,
        "streak_mean":            round(sum(runs) / len(runs), 3) if runs else 0.0,
        "n_streaks_ge3":          sum(1 for r in runs if r >= 3),
        "n_streaks_ge5":          sum(1 for r in runs if r >= 5),
    }


HEADING_RE = re.compile(r"^[ \t]*(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)
RULES_HEADING_RE = re.compile(
    r"(?i)\b(rules?|important|warning|notes?|caution|notice|critical|"
    r"do not|never|must|forbidden|restrictions?|constraints?)\b"
)


def _is_rules_section_heading(title: str) -> bool:
    title = title.strip().rstrip(":").strip()
    if not title:
        return False
    if RULES_HEADING_RE.search(title):
        return True
    letters = re.sub(r"[^A-Za-z]", "", title)
    if len(letters) >= 2 and letters.isupper():
        return True
    return False


def _heading_spans(raw_text: str) -> list[tuple[int, str, bool]]:
    out: list[tuple[int, str, bool]] = []
    for m in HEADING_RE.finditer(raw_text):
        title = m.group(2).strip()
        out.append((m.start(), title, _is_rules_section_heading(title)))
    return out


def _heading_at(char_offset: int, headings: list[tuple[int, str, bool]]) -> tuple[str, bool]:
    last = ("", False)
    for pos, title, is_rules in headings:
        if pos > char_offset:
            break
        last = (title, is_rules)
    return last


def _empty_rules_section_block() -> dict:
    return {
        "n_paragraphs": 0,
        "n_paragraphs_in_rules_section": 0,
        "n_paragraphs_outside_rules_section": 0,
        "n_rule_paragraphs_in_rules_section": 0,
        "n_rule_paragraphs_outside_rules_section": 0,
        "n_rule_paragraphs_in_rules_section_explained": 0,
        "n_rule_paragraphs_outside_rules_section_explained": 0,
        "n_rule_sentences_in_rules_section": 0,
        "n_rule_sentences_outside_rules_section": 0,
        "n_rule_sentences_in_rules_section_explained": 0,
        "n_rule_sentences_outside_rules_section_explained": 0,
        "pct_rule_paragraphs_explained_in_rules_section": None,
        "pct_rule_paragraphs_explained_outside_rules_section": None,
        "pct_rule_sentences_explained_in_rules_section": None,
        "pct_rule_sentences_explained_outside_rules_section": None,
    }


def rules_section_for_doc(doc, raw_text: str) -> dict:
    spans = _paragraph_spans(raw_text)
    headings = _heading_spans(raw_text)
    if not spans:
        return _empty_rules_section_block()

    imp_marker_starts = {start for _, start, _ in
                         M_IMPERATIVE["imperative_markers"](doc)}
    prohib_starts = {start for _, start, _ in M_VOCAB["hard_prohibitions"](doc)}

    n_paragraphs = len(spans)
    para_has_just  = [False] * n_paragraphs
    para_has_rule  = [False] * n_paragraphs
    para_in_rules  = [False] * n_paragraphs
    para_n_rule_sents      = [0] * n_paragraphs
    para_n_explained_sents = [0] * n_paragraphs

    for p_idx, (start, end) in enumerate(spans):
        _, is_rules = _heading_at(start, headings)
        para_in_rules[p_idx] = is_rules

    for sent in doc.sents:
        if not sent.text.strip():
            continue
        p_idx = _para_index_for(sent.start_char, spans)
        if p_idx < 0:
            continue
        is_imp = (any(sent.start <= ti < sent.end for ti in imp_marker_starts)
                  or classify_sent_mood(sent) == "imperative")
        is_prohib = any(sent.start <= ti < sent.end for ti in prohib_starts)
        is_rule = is_imp or is_prohib
        has_just = any(r.search(sent.text) for r in JUST_RE)
        if has_just:
            para_has_just[p_idx] = True
        if is_rule:
            para_has_rule[p_idx] = True
            para_n_rule_sents[p_idx] += 1

    n_rule_paras_in = n_rule_paras_out = 0
    n_rule_paras_in_explained = n_rule_paras_out_explained = 0
    n_rule_sents_in = n_rule_sents_out = 0
    n_rule_sents_in_explained = n_rule_sents_out_explained = 0
    n_paragraphs_in_section = n_paragraphs_out_section = 0

    for p_idx in range(n_paragraphs):
        if para_in_rules[p_idx]:
            n_paragraphs_in_section += 1
        else:
            n_paragraphs_out_section += 1

        if not para_has_rule[p_idx]:
            continue
        explained = para_has_just[p_idx]
        rule_sents = para_n_rule_sents[p_idx]
        if para_in_rules[p_idx]:
            n_rule_paras_in += 1
            n_rule_sents_in += rule_sents
            if explained:
                n_rule_paras_in_explained += 1
                n_rule_sents_in_explained += rule_sents
        else:
            n_rule_paras_out += 1
            n_rule_sents_out += rule_sents
            if explained:
                n_rule_paras_out_explained += 1
                n_rule_sents_out_explained += rule_sents

    return {
        "n_paragraphs":                          n_paragraphs,
        "n_paragraphs_in_rules_section":         n_paragraphs_in_section,
        "n_paragraphs_outside_rules_section":    n_paragraphs_out_section,
        "n_rule_paragraphs_in_rules_section":    n_rule_paras_in,
        "n_rule_paragraphs_outside_rules_section": n_rule_paras_out,
        "n_rule_paragraphs_in_rules_section_explained":    n_rule_paras_in_explained,
        "n_rule_paragraphs_outside_rules_section_explained": n_rule_paras_out_explained,
        "n_rule_sentences_in_rules_section":     n_rule_sents_in,
        "n_rule_sentences_outside_rules_section": n_rule_sents_out,
        "n_rule_sentences_in_rules_section_explained":    n_rule_sents_in_explained,
        "n_rule_sentences_outside_rules_section_explained": n_rule_sents_out_explained,
        "pct_rule_paragraphs_explained_in_rules_section":  _safe_pct(
            n_rule_paras_in_explained, n_rule_paras_in),
        "pct_rule_paragraphs_explained_outside_rules_section": _safe_pct(
            n_rule_paras_out_explained, n_rule_paras_out),
        "pct_rule_sentences_explained_in_rules_section":  _safe_pct(
            n_rule_sents_in_explained, n_rule_sents_in),
        "pct_rule_sentences_explained_outside_rules_section": _safe_pct(
            n_rule_sents_out_explained, n_rule_sents_out),
    }


# --- Per-sentence forensic records (cell 37) ---------------------------

def build_sentence_records(df, docs) -> list[dict]:
    """Build per-sentence rows for sentences_classified.parquet.

    df must have columns path, category, ccVersion, raw_text, aligned with docs.
    """
    out: list[dict] = []
    for i, (path_, cat, ccver, raw, doc) in enumerate(zip(
            df["path"], df["category"], df["ccVersion"], df["raw_text"], docs)):
        spans = _paragraph_spans(raw)
        if not spans:
            continue
        imp_marker_starts = {start for _, start, _ in M_IMPERATIVE["imperative_markers"](doc)}
        prohib_starts = {start for _, start, _ in M_VOCAB["hard_prohibitions"](doc)}

        n_paragraphs = len(spans)
        para_has_just = [False] * n_paragraphs
        sents_in_para: list[list] = [[] for _ in range(n_paragraphs)]
        for s_idx, sent in enumerate(doc.sents):
            if not sent.text.strip():
                continue
            p_idx = _para_index_for(sent.start_char, spans)
            if p_idx < 0:
                continue
            has_just_here = any(r.search(sent.text) for r in JUST_RE)
            if has_just_here:
                para_has_just[p_idx] = True
            sents_in_para[p_idx].append((s_idx, sent, has_just_here))

        sentence_index_in_file = -1
        streak_pos = 0
        for p_idx in range(n_paragraphs):
            para_explained = para_has_just[p_idx]
            for sent_pos_in_para, (s_idx, sent, has_just_here) in enumerate(sents_in_para[p_idx]):
                sentence_index_in_file += 1
                text = sent.text.strip()
                n_tokens_sent = sum(1 for t in sent if not t.is_space and not t.is_punct)
                is_imp_marker = any(sent.start <= ti < sent.end for ti in imp_marker_starts)
                is_imp = is_imp_marker or classify_sent_mood(sent) == "imperative"
                is_prohib = any(sent.start <= ti < sent.end for ti in prohib_starts)
                is_rule = is_imp or is_prohib
                if is_imp:
                    streak_pos += 1
                    cur_streak_pos = streak_pos
                else:
                    streak_pos = 0
                    cur_streak_pos = 0
                has_threat = any(r.search(text) for r in THREAT_RE)
                has_causal = any(r.search(text) for r in CAUSAL_RE)
                mentions_claude = bool(CLAUDE_RE.search(text))
                mentions_model  = bool(MODEL_RE.search(text))
                addressee = classify_addressee(text)
                out.append({
                    "file_path":              path_,
                    "category":               cat,
                    "ccVersion":              ccver or "",
                    "paragraph_index":        p_idx,
                    "sentence_index":         sent_pos_in_para,
                    "sentence_index_in_file": sentence_index_in_file,
                    "n_tokens":               n_tokens_sent,
                    "text":                   text,
                    "is_imperative":          is_imp,
                    "is_prohibition":         is_prohib,
                    "is_rule":                is_rule,
                    "has_just_in_sent":       has_just_here,
                    "paragraph_has_just":     para_explained,
                    "is_explained_para":      bool(is_rule and para_explained),
                    "has_threat":             has_threat,
                    "has_causal":             has_causal,
                    "mentions_claude":        mentions_claude,
                    "mentions_model":         mentions_model,
                    "addressee":              addressee,
                    "streak_position":        cur_streak_pos,
                })
    return out


# =============================================================================
# Assembler + aggregator (lifted from cells 39 + 40)
# =============================================================================

DENSITY_BLOCKS = ("register", "stance", "modality", "all_caps",
                  "caps_imperative", "justification")
MODALITY_CLASSES = ("deontic", "epistemic", "dynamic")

RULE_EXPL_COUNT_KEYS = (
    "n_paragraphs", "n_paragraphs_with_rules", "n_paragraphs_with_rules_unexplained",
    "n_rule_sentences", "n_imperative_sentences", "n_prohibition_sentences",
    "n_explained_same", "n_explained_para",
    "n_imperative_explained_para", "n_prohibition_explained_para",
)

RULES_SECTION_COUNT_KEYS = (
    "n_paragraphs", "n_paragraphs_in_rules_section", "n_paragraphs_outside_rules_section",
    "n_rule_paragraphs_in_rules_section", "n_rule_paragraphs_outside_rules_section",
    "n_rule_paragraphs_in_rules_section_explained",
    "n_rule_paragraphs_outside_rules_section_explained",
    "n_rule_sentences_in_rules_section", "n_rule_sentences_outside_rules_section",
    "n_rule_sentences_in_rules_section_explained",
    "n_rule_sentences_outside_rules_section_explained",
)


def build_file_record(i: int, df, per_file_metrics: dict) -> dict:
    """Build the nested per-file metric tree.

    `per_file_metrics` is a dict keyed by block name, each value being a list
    aligned with df.index. Every block produced by an analyzer notebook
    (mood, register, stance, sentence_register, modality, vocab, all_caps,
    caps_imperative, justification, rule_explanation, judgment_procedural,
    consequence_framing, socratic, address_form, imperative_streaks,
    rules_section) must be present.
    """
    row = df.iloc[i]
    vp = per_file_metrics["vocab"][i]
    return {
        "path":        row["path"],
        "category":    row["category"],
        "name":        row["name"] or None,
        "description": row["description"] or None,
        "ccVersion":   row["ccVersion"] or None,
        "agentType":   row["agentType"] or None,
        "n_tokens":    int(row["n_tokens"]),
        "n_sents":     int(row["n_sents"]),
        "metrics": {
            "mood":              per_file_metrics["mood"][i],
            "register":          per_file_metrics["register"][i],
            "stance":            per_file_metrics["stance"][i],
            "sentence_register": per_file_metrics["sentence_register"][i],
            "modality":          per_file_metrics["modality"][i],
            "vocab": {
                k: {"count":    int(vp[f"{k}_count"]),
                    "pct":      vp[f"{k}_pct"],
                    "per_sent": vp[f"{k}_per_sent"]}
                for k in VOCAB_KEYS
            },
            "all_caps":            per_file_metrics["all_caps"][i],
            "caps_imperative":     per_file_metrics["caps_imperative"][i],
            "justification":       per_file_metrics["justification"][i],
            "rule_explanation":    per_file_metrics["rule_explanation"][i],
            "judgment_procedural": per_file_metrics["judgment_procedural"][i],
            "consequence_framing": per_file_metrics["consequence_framing"][i],
            "socratic":            per_file_metrics["socratic"][i],
            "address_form":        per_file_metrics["address_form"][i],
            "imperative_streaks":  per_file_metrics["imperative_streaks"][i],
            "rules_section":       per_file_metrics["rules_section"][i],
        },
    }


def _sum_counts(records, block: str, field: str) -> int:
    return sum(int(r["metrics"][block].get(field, 0) or 0) for r in records)


def _agg_block_counts(records, block: str, count_keys, n_tokens_total: int,
                      n_sents_total: int) -> dict:
    out = {}
    for k in count_keys:
        c = sum(int(r["metrics"][block].get(f"{k}_count", 0) or 0) for r in records)
        out[f"{k}_count"]    = c
        out[f"{k}_pct"]      = pct(c, n_tokens_total)
        out[f"{k}_per_sent"] = per_sent(c, n_sents_total)
    return out


def _agg_sent_pct_block(records, block: str, class_keys, n_sents_total: int) -> dict:
    out = {}
    for k in class_keys:
        c = sum(int(r["metrics"][block].get(f"{k}_sent_count", 0) or 0)
                for r in records)
        out[f"{k}_sent_count"] = c
        out[f"{k}_sent_pct"]   = round(100.0 * c / n_sents_total, 4) if n_sents_total else 0.0
    return out


def _agg_top_strings(records, block: str, field: str):
    c: Counter = Counter()
    for r in records:
        v = r["metrics"][block].get(field)
        if v:
            c[v] += 1
    return c.most_common(1)[0][0] if c else None


def _agg_rule_explanation(records) -> dict:
    totals = {k: 0 for k in RULE_EXPL_COUNT_KEYS}
    for r in records:
        b = r["metrics"]["rule_explanation"]
        for k in RULE_EXPL_COUNT_KEYS:
            totals[k] += int(b.get(k, 0) or 0)
    n_rule = totals["n_rule_sentences"]
    n_imp  = totals["n_imperative_sentences"]
    n_proh = totals["n_prohibition_sentences"]
    n_pwr  = totals["n_paragraphs_with_rules"]
    out = dict(totals)
    out["pct_explained_same"] = (
        round(100.0 * totals["n_explained_same"] / n_rule, 4) if n_rule else None)
    out["pct_explained_para"] = (
        round(100.0 * totals["n_explained_para"] / n_rule, 4) if n_rule else None)
    out["pct_imperative_explained_para"] = (
        round(100.0 * totals["n_imperative_explained_para"] / n_imp, 4) if n_imp else None)
    out["pct_prohibition_explained_para"] = (
        round(100.0 * totals["n_prohibition_explained_para"] / n_proh, 4) if n_proh else None)
    out["pct_paragraphs_with_rules_unexplained"] = (
        round(100.0 * totals["n_paragraphs_with_rules_unexplained"] / n_pwr, 4)
        if n_pwr else None)
    return out


def _agg_judgment_procedural(records, n_sents_total: int) -> dict:
    j = sum(int(r["metrics"]["judgment_procedural"].get("judgment_count", 0) or 0)
            for r in records)
    p = sum(int(r["metrics"]["judgment_procedural"].get("procedural_count", 0) or 0)
            for r in records)
    return {
        "judgment_count":               j,
        "procedural_count":              p,
        "judgment_per_sent":             per_sent(j, n_sents_total),
        "procedural_per_sent":           per_sent(p, n_sents_total),
        "judgment_to_procedural_ratio":  round(j / p, 3) if p else None,
    }


def _agg_consequence_framing(records, n_sents_total: int) -> dict:
    t = sum(int(r["metrics"]["consequence_framing"].get("threat_count", 0) or 0)
            for r in records)
    c = sum(int(r["metrics"]["consequence_framing"].get("causal_count", 0) or 0)
            for r in records)
    return {
        "threat_count":     t,
        "causal_count":     c,
        "threat_per_sent":  per_sent(t, n_sents_total),
        "causal_per_sent":  per_sent(c, n_sents_total),
        "threat_share":     round(t / (t + c), 4) if (t + c) else None,
    }


def _agg_socratic(records, n_tokens_total: int, n_sents_total: int) -> dict:
    q = sum(int(r["metrics"]["socratic"].get("question_count", 0) or 0) for r in records)
    a = sum(int(r["metrics"]["socratic"].get("apology_count", 0) or 0) for r in records)
    return {
        "question_count":     q,
        "question_pct":       pct(q, n_tokens_total),
        "question_per_sent":  per_sent(q, n_sents_total),
        "apology_count":      a,
        "apology_pct":        pct(a, n_tokens_total),
        "apology_per_sent":   per_sent(a, n_sents_total),
    }


def _agg_address_form(records) -> dict:
    keys = ("selfref_claude", "selfref_assistant", "selfref_model",
            "selfref_2p", "selfref_we")
    counts = {k: sum(int(r["metrics"]["address_form"].get(k, 0) or 0)
                     for r in records) for k in keys}
    total_named = counts["selfref_claude"] + counts["selfref_assistant"] + counts["selfref_model"]
    out = dict(counts)
    out["pct_anthropomorphic"] = (round(counts["selfref_claude"] / total_named, 4)
                                   if total_named else None)
    out["pct_artifact"]        = (round(counts["selfref_model"] / total_named, 4)
                                   if total_named else None)
    out["pct_role"]            = (round(counts["selfref_assistant"] / total_named, 4)
                                   if total_named else None)
    return out


def _agg_imperative_streaks(records) -> dict:
    sum_imp = sum(int(r["metrics"]["imperative_streaks"].get("n_imperative_sentences", 0) or 0)
                  for r in records)
    sum_runs = sum(int(r["metrics"]["imperative_streaks"].get("n_streaks", 0) or 0)
                   for r in records)
    sum_ge3 = sum(int(r["metrics"]["imperative_streaks"].get("n_streaks_ge3", 0) or 0)
                  for r in records)
    sum_ge5 = sum(int(r["metrics"]["imperative_streaks"].get("n_streaks_ge5", 0) or 0)
                  for r in records)
    overall_max = max((int(r["metrics"]["imperative_streaks"].get("streak_max", 0) or 0)
                       for r in records), default=0)
    streak_mean_overall = (round(sum_imp / sum_runs, 3) if sum_runs else 0.0)
    return {
        "n_imperative_sentences": sum_imp,
        "n_streaks":              sum_runs,
        "streak_max":             overall_max,
        "streak_mean":            streak_mean_overall,
        "n_streaks_ge3":          sum_ge3,
        "n_streaks_ge5":          sum_ge5,
    }


def _agg_rules_section(records) -> dict:
    totals = {k: 0 for k in RULES_SECTION_COUNT_KEYS}
    for r in records:
        b = r["metrics"]["rules_section"]
        for k in RULES_SECTION_COUNT_KEYS:
            totals[k] += int(b.get(k, 0) or 0)
    n_in = totals["n_rule_paragraphs_in_rules_section"]
    n_out = totals["n_rule_paragraphs_outside_rules_section"]
    n_in_s = totals["n_rule_sentences_in_rules_section"]
    n_out_s = totals["n_rule_sentences_outside_rules_section"]
    out = dict(totals)
    out["pct_rule_paragraphs_explained_in_rules_section"] = (
        round(100.0 * totals["n_rule_paragraphs_in_rules_section_explained"] / n_in, 4)
        if n_in else None)
    out["pct_rule_paragraphs_explained_outside_rules_section"] = (
        round(100.0 * totals["n_rule_paragraphs_outside_rules_section_explained"] / n_out, 4)
        if n_out else None)
    out["pct_rule_sentences_explained_in_rules_section"] = (
        round(100.0 * totals["n_rule_sentences_in_rules_section_explained"] / n_in_s, 4)
        if n_in_s else None)
    out["pct_rule_sentences_explained_outside_rules_section"] = (
        round(100.0 * totals["n_rule_sentences_outside_rules_section_explained"] / n_out_s, 4)
        if n_out_s else None)
    return out


def aggregate(per_file_records: list[dict], indices: List[int], df, docs) -> dict:
    """Aggregator over an arbitrary subset of file indices.

    Sums per-file counts for density metrics, recomputes pct/per_sent from
    totals. TTR + dep-depth are recomputed by walking the docs union (since
    set semantics + per-token traversal don't compose as simple sums).
    """
    subset = [per_file_records[i] for i in indices]
    n_tokens_total = sum(r["n_tokens"] for r in subset)
    n_sents_total  = sum(r["n_sents"] for r in subset)

    marker_total = _sum_counts(subset, "mood", "marker_count")
    mood_block = {
        "marker_count":    marker_total,
        "marker_pct":      pct(marker_total, n_tokens_total),
        "marker_per_sent": per_sent(marker_total, n_sents_total),
    }

    union_lemmas: List[str] = []
    sent_len_sum = sent_count = depths_sum = depths_count = 0
    formal = informal = 0
    for i in indices:
        d = docs[i]
        for t in d:
            if t.is_space:
                continue
            if not t.is_punct and not t.is_stop:
                union_lemmas.append(t.lemma_.lower())
            if t.pos_ in FORMAL_POS:
                formal += 1
            elif t.pos_ in INFORMAL_POS:
                informal += 1
        for s in d.sents:
            if s.text.strip():
                sent_len_sum += sum(1 for t in s if not t.is_space)
                sent_count += 1
        for d_ in doc_dep_depths(d):
            depths_sum += d_
            depths_count += 1
    reg_classes = list(REGISTER_MARKERS.keys())
    reg_counts = {k: _sum_counts(subset, "register", f"{k}_count") for k in reg_classes}
    register_block = {
        "ttr": (round(len(set(union_lemmas)) / len(union_lemmas), 4)
                if union_lemmas else 0.0),
        "mean_sent_len": round(sent_len_sum / sent_count, 2) if sent_count else 0.0,
        "dep_depth":     round(depths_sum / depths_count, 3) if depths_count else 0.0,
        "f_score":       (round(50 + 50 * (formal - informal) / (formal + informal), 2)
                          if (formal + informal) else 50.0),
        **{f"{k}_count":    v                                for k, v in reg_counts.items()},
        **{f"{k}_pct":      pct(v, n_tokens_total)           for k, v in reg_counts.items()},
        **{f"{k}_per_sent": per_sent(v, n_sents_total)       for k, v in reg_counts.items()},
        "dominant_register": (max(reg_counts, key=reg_counts.get)
                              if reg_counts and max(reg_counts.values()) > 0 else "none"),
    }

    stance_classes = (list(STANCE_MARKERS.keys())
                      + ["positive_evaluative_quality", "positive_evaluative_emphasis"]
                      + ["pronouns_1p", "pronouns_2p"])
    st_counts = {k: _sum_counts(subset, "stance", f"{k}_count") for k in stance_classes}
    stance_block = {
        **{f"{k}_count":    v                          for k, v in st_counts.items()},
        **{f"{k}_pct":      pct(v, n_tokens_total)     for k, v in st_counts.items()},
        **{f"{k}_per_sent": per_sent(v, n_sents_total) for k, v in st_counts.items()},
        "dominant_stance": (max((k for k in STANCE_MARKERS),
                                key=lambda k: st_counts[k])
                            if any(st_counts[k] for k in STANCE_MARKERS) else "none"),
    }

    sr_block = _agg_sent_pct_block(subset, "sentence_register",
                                    SENT_REGISTER_CLASSES, n_sents_total)
    none_total = _sum_counts(subset, "sentence_register", "none_sent_count")
    sr_block["none_sent_count"] = none_total
    sr_block["none_sent_pct"]   = (round(100.0 * none_total / n_sents_total, 4)
                                    if n_sents_total else 0.0)
    nonzero = [(cls, sr_block[f"{cls}_sent_count"])
               for cls in SENT_REGISTER_CLASSES
               if sr_block[f"{cls}_sent_count"] > 0]
    for k in ("appreciative_addressee_claude_count",
              "appreciative_addressee_user_count",
              "appreciative_addressee_unknown_count",
              "collaborative_addressee_claude_count",
              "collaborative_addressee_user_count",
              "collaborative_addressee_unknown_count"):
        sr_block[k] = sum(int(r["metrics"]["sentence_register"].get(k, 0) or 0) for r in subset)
    sr_block["dominant"] = (max(nonzero, key=lambda kv: kv[1])[0]
                             if nonzero else "")

    modality_block = _agg_block_counts(subset, "modality", list(MODALITY_CLASSES),
                                        n_tokens_total, n_sents_total)
    modality_block["top_construction"] = _agg_top_strings(subset, "modality", "top_construction")

    vocab_block = {}
    for k in VOCAB_KEYS:
        c = sum(int(r["metrics"]["vocab"][k]["count"]) for r in subset)
        vocab_block[k] = {
            "count":    c,
            "pct":      pct(c, n_tokens_total),
            "per_sent": per_sent(c, n_sents_total),
        }

    all_caps_counter: Counter = Counter()
    for i in indices:
        for tok in ALLCAPS_RE.findall(df.iloc[i]["raw_text"]):
            if tok not in TECH_ACRONYMS:
                all_caps_counter[tok] += 1
    total = sum(all_caps_counter.values())
    all_caps_block = {
        "count":    total,
        "distinct": len(all_caps_counter),
        "pct":      pct(total, n_tokens_total),
        "per_sent": per_sent(total, n_sents_total),
        "top":      [{"token": t, "count": c}
                     for t, c in all_caps_counter.most_common(25)],
    }

    caps_imp_counter: Counter = Counter()
    for i in indices:
        caps_imp_counter.update(CAPS_IMP_RE.findall(df.iloc[i]["raw_text"]))
    total = sum(caps_imp_counter.values())
    caps_imperative_block = {
        "count":    total,
        "pct":      pct(total, n_tokens_total),
        "per_sent": per_sent(total, n_sents_total),
        "hits":     dict(caps_imp_counter.most_common()),
    }

    just_total = sum(int(r["metrics"]["justification"]["count"]) for r in subset)
    justification_block = {
        "count":    just_total,
        "pct":      pct(just_total, n_tokens_total),
        "per_sent": per_sent(just_total, n_sents_total),
        "ratio":    round(just_total / (marker_total + 1), 3),
    }

    rule_explanation_block = _agg_rule_explanation(subset)
    judgment_procedural_block = _agg_judgment_procedural(subset, n_sents_total)
    consequence_framing_block = _agg_consequence_framing(subset, n_sents_total)
    socratic_block            = _agg_socratic(subset, n_tokens_total, n_sents_total)
    address_form_block        = _agg_address_form(subset)
    imperative_streaks_block  = _agg_imperative_streaks(subset)
    rules_section_block       = _agg_rules_section(subset)

    return {
        "n_tokens": n_tokens_total,
        "n_sents":  n_sents_total,
        "metrics": {
            "mood":              mood_block,
            "register":          register_block,
            "stance":            stance_block,
            "sentence_register": sr_block,
            "modality":          modality_block,
            "vocab":             vocab_block,
            "all_caps":          all_caps_block,
            "caps_imperative":   caps_imperative_block,
            "justification":     justification_block,
            "rule_explanation":  rule_explanation_block,
            "judgment_procedural": judgment_procedural_block,
            "consequence_framing": consequence_framing_block,
            "socratic":            socratic_block,
            "address_form":        address_form_block,
            "imperative_streaks":  imperative_streaks_block,
            "rules_section":       rules_section_block,
        },
    }


# =============================================================================
# Lexicon block for the YAML output (lifted from cell 43)
# =============================================================================

def yaml_lexicons_block() -> dict:
    """Return the lexicons dict echoed verbatim into the YAML output."""
    return {
        "VOCAB": VOCAB,
        "IMPERATIVE_MARKERS": IMPERATIVE_MARKERS,
        "CAPS_IMPERATIVE_TOKENS": CAPS_IMPERATIVE_TOKENS,
        "JUSTIFICATION_PATTERNS": JUSTIFICATION_PATTERNS,
        "TECH_ACRONYMS": sorted(TECH_ACRONYMS),
        "CATEGORY_PREFIXES": [list(p) for p in CATEGORY_PREFIXES],
        "STANCE_MARKERS": STANCE_MARKERS,
        "REGISTER_MARKERS": REGISTER_MARKERS,
        "SENTENCE_REGISTER_MARKERS": SENTENCE_REGISTER_MARKERS,
        "SIMPLE_MODAL_LOOKUP":       SIMPLE_MODAL_LOOKUP,
        "EPISTEMIC_ADVERBS":         sorted(EPISTEMIC_ADVERBS),
        "DEONTIC_LIGHT_VERBS":       sorted(DEONTIC_LIGHT_VERBS),
        "EPISTEMIC_LIGHT_VERBS":     sorted(EPISTEMIC_LIGHT_VERBS),
        "EPISTEMIC_AUX_AFTER_MODAL": sorted(EPISTEMIC_AUX_AFTER_MODAL),
        "JUDGMENT_VERBS":      JUDGMENT_VERBS,
        "PROCEDURAL_CUES":     PROCEDURAL_CUES,
        "THREAT_PATTERNS":     THREAT_PATTERNS,
        "CAUSAL_PATTERNS":     CAUSAL_PATTERNS,
        "APOLOGY_MARKERS":     APOLOGY_MARKERS,
        "ADDRESS_FORM_PATTERNS": {k: list(v) for k, v in ADDRESS_FORM_PATTERNS.items()},
        "RULES_HEADING_RE":    RULES_HEADING_RE.pattern,
    }
