# GLOSSARY

Plain-language definitions of every linguistic, statistical, and corpus term used in the notebooks. Each entry leads with the everyday-language explanation, then names the precise term so expert readers can still anchor on the technical vocabulary.

The terms here are load-bearing for the welfare submission ("Claude Code should encourage reasoning over blind obedience") — they are not jargon for jargon's sake. The goal of this glossary is to let a non-linguist reader follow what each chart claims and assess whether to trust it.

### YAML key conventions

The notebooks frequently reference YAML keys (`positive_evaluative_pct`, `mood_marker_pct`, `pearson r`, etc.) — these are the underscored / snake_case YAML field names for the spaced display names defined below. Mapping examples:

- "Positive evaluative" stance class → `positive_evaluative_pct` / `positive_evaluative_count` / `positive_evaluative_per_sent` in the YAML / `alt_df`.
- "Negative evaluative" → `negative_evaluative_*`.
- "Imperative marker density" / "mood marker density" → `mood_marker_pct` (also written as `mood.marker_pct` inside the YAML metric tree).
- "Pearson correlation (r)" → labeled as `Pearson r` in chart axes.
- "% of file tokens" / "per word" → the `_pct` suffix; "rate per sentence" → the `_per_sent` suffix.

Use this mapping when a chart axis label or printed table column looks unfamiliar — the snake_case form is just the YAML / dataframe field name; the prose definition lives below.

---

## Linguistic concepts

### Mood

The grammatical type of a sentence. Three classes:
- **Imperative** — a command: `Run the tests.`, `Don't commit yet.`. The verb leads; there's no subject `I` / `you` / `we` performing the action; the sentence ends in `.` or `!`.
- **Interrogative** — a question: `Did the build pass?`. Ends in `?`.
- **Declarative** — a statement: `The build passed.`. Anything that's neither a command nor a question.

In this corpus we report the **imperative-marker density** (how often command-flavoured words like `must`, `never`, `ensure`, `do not` appear) as a proxy for grammatical mood at the document level.

### Register

The level of formality of a passage. Four classes (Halliday tradition):
- **Frozen** — fixed legalistic phrasing: `hereby`, `pursuant to`, `notwithstanding`.
- **Formal** — expository, planned writing: `furthermore`, `consequently`, `it should be noted`.
- **Consultative** — explanatory but reader-aware: `you can`, `we recommend`, `for example`.
- **Casual** — conversational contractions: `let's`, `you're`, `here's`.

Reported per-file as **register class densities** (% of file tokens) plus a **dominant register** label.

### Sentence-level pragmatic register

A separate, **multi-label** classifier that asks: *what speech act is this sentence performing?* Six classes — every sentence can carry zero, one, or several:

- **Collaborative** — interpersonal first-person plural / shared agency: `let's`, `we should`, `we'll`. Predicted absent in this corpus.
- **Permissive** — soft directive / permission-granting / reader-agency: `please`, `you can`, `feel free to`, `optionally`.
- **Appreciative** — gratitude / positive feedback: `thank you`, `appreciate`, `great job`. Predicted absent in this corpus.
- **Imperative** — grammatical mood (see above). Bare commands.
- **Directive** — declarative-but-rule-asserting: `must`, `should`, `never`, `you must`. Forms an instruction in declarative clothing.
- **Configuring** — config / parameter speech: `set to`, `default to`, `must be`, `accepts`.

Because a single sentence can carry several flags (e.g. `we should please consider this` would count as `collaborative` AND `permissive` AND `directive`), per-class **`sent_pct` values can sum to more than 100%**. That is intentional, not a bug.

### Addressee (for `appreciative` and `collaborative` sentences)

Distinguishes *who is addressed* by an appreciative or collaborative sentence — because the headline finding ("4 appreciative sentences in 288 files") obscures whether the prompt author is **thanking Claude** vs **instructing Claude to thank the user**. Three values:

- **`addressee == "claude"`** — the sentence references Claude as the recipient of the appreciative/collaborative speech act (the welfare-positive case). Heuristic: contains `claude` / `you` / `your` AND is not framed as an instruction-to-output.
- **`addressee == "user"`** — the sentence is framed as instruction-to-output (the welfare-neutral scaffolding case). Heuristic: matches phrases like `thank the user`, `respond with`, `output`, `say to`, `tell the user`, `your reply should`.
- **`addressee == "unknown"`** — neither pattern matched; default.

Reported as `appreciative_addressee_*_count` and `collaborative_addressee_*_count` under the `sentence_register` block in the YAML. The corpus-wide count of *acknowledgment-to-Claude* (`appreciative_addressee_claude_count`) is the welfare-relevant number — sharper than the 0.07% headline because it isolates "the corpus does not thank Claude" from "the corpus does not contain the word `thanks`".

### Stance

Where the writer positions themselves toward what they're saying. Five classes (polarity-split):
- **Directive** — issues commands: `must`, `do not`, `you should`.
- **Expository** — describes / defines: `is`, `means`, `refers to`.
- **Positive evaluative** — judges as good: `good`, `recommended`, `optimal`, `safe`. **Sub-split**: `positive_evaluative_quality` (genuinely affirmative quality words: `good`, `optimal`, `recommended`, `safe`, `excellent`, `helpful`) and `positive_evaluative_emphasis` (emphasis-of-rule words that get coded as positive but functionally weight a rule rather than affirm a quality: `important`, `critical`, `essential`, `imperative`, `key`). Both sub-counts sum to the union `positive_evaluative_count`. The split exists because reading the union as "encouraging tone" overstates the result — a fair welfare-submission claim cites the quality-only ratio.
- **Negative evaluative** — judges as bad: `bad`, `wrong`, `risky`, `deprecated`.
- **Dialogic** — invites reader thought: `you might`, `consider`, `however`, `let's`.

The split between **positive** and **negative** evaluative was added to surface sentiment polarity that an aggregated `evaluative` class would hide.

### Modality

Whether and how the writer marks the *kind* of obligation, possibility, or ability. Three classes:
- **Deontic** — obligation: `must`, `shall`, `should`, `ought`. Carries the weight of a rule.
- **Epistemic** — inference / probability: `may`, `might`, `likely`, `probably`. Carries uncertainty.
- **Dynamic** — ability / future: `can`, `could`, `will`. Carries capability or scheduled action.

Reported per file as the count and density of each class. The corpus has **deontic = 263**, **epistemic = 325**, **dynamic = 517** — dynamic dominates, which is mostly `can` / `will`.

### Imperative marker density

Count of imperative-flavoured words (the `IMPERATIVE_MARKERS` lexicon: 30 entries including `must`, `never`, `you must`, `do not`, `is required`, etc.) divided by total word tokens, multiplied by 100. Reported as `mood.marker_pct` in the YAML.

This is a *lexical-density* proxy for grammatical mood; it doesn't classify each sentence, just counts how often imperative-style language appears overall.

### CAPS imperative

A token rendered in `ALL CAPITALS` that is also on a curated list of emphatic command words (`MUST`, `NEVER`, `IMPORTANT`, `STOP`, `CRITICAL`, `DO NOT`, etc.). Distinct from plain `ALL CAPS density`, which counts *any* all-uppercase token (including acronyms — though `TECH_ACRONYMS` like `API` / `JSON` are excluded).

### Justification ratio

`count(justification keywords) / (count(imperative markers) + 1)`. Reported per file as `justification.ratio`.

The numerator counts cause / purpose / consequence words: `because`, `due to`, `in order to`, `so that`, `to ensure`, `otherwise`, `since`, etc. (32-pattern regex list — see the YAML `lexicons.JUSTIFICATION_PATTERNS`).

A ratio of 0.30 means roughly one justification keyword for every three imperative markers — i.e., most rules are issued without a stated reason.

This is a **document-level density ratio**, not a per-rule pairing. The Tier-1 metric `pct_explained_para` (below) is the per-rule pairing version.

---

## Pairing & explanation metrics (Tier-1)

### Rule sentence

A sentence that contains an imperative marker (`IMPERATIVE_MARKERS` lexicon hit), a hard prohibition (`hard_prohibitions` lexicon hit), OR is grammatically classified imperative by `classify_sent_mood`. Reported per file as `n_rule_sentences`.

### Paragraph window

A blank-line-delimited block of text (markdown convention). For paired rule/explanation analysis, a rule sentence is "explained at paragraph window" if any justification keyword appears anywhere in the same blank-line block.

### `pct_explained_same`

Strict pairing: % of rule sentences with a justification keyword in the literal **same sentence**. Corpus baseline: **6.59%**.

### `pct_explained_para`

Paragraph-window pairing (the headline Tier-1 metric): % of rule sentences with a justification keyword anywhere in the **same paragraph**. Captures the common `Do X.\n\nThis is because Y.` shape. Corpus baseline: **24.40%**.

The 4× gap between `pct_explained_same` and `pct_explained_para` reflects how often Anthropic *separates* the rule from the reason: most rules with a reason have it spelled out a sentence or two later, not inline.

### Welfare-evidence score

Per-file ranking score: `rule_density × (1 − pct_explained_para/100)`. High = "loud and unexplained". A score of **1.0** means every sentence in the file is a rule and zero of them are explained anywhere in their paragraph (the worst possible welfare-relevant pattern).

### Positive-exemplar score

The inverse of welfare-evidence: `rule_density × (pct_explained_para/100)`. High = "rule-saturated AND well-explained" — the "this is how to do it" cluster. Computed by `prompt_analysis.positive_exemplar_table` with default filters `min_n_sents=10` and `min_rule_n=5` to suppress trivial cases (`1/1 rules explained`). Used in `16_rule_explanation.ipynb` (and re-rendered as the paired-exemplar chart in `22_audit_threat_framings.ipynb`) to surface the corpus's strongest positive exemplars alongside the welfare-evidence ranking — so the welfare submission can point Anthropic at concrete templates rather than only critiquing the negatives.

### `sentences_classified.parquet`

Per-sentence forensic-inspection artifact emitted alongside the YAML by `00_data_pipeline.ipynb`. ~5,698 rows × 20 columns. Schema includes the raw sentence text plus all the per-sentence classifier flags: `is_imperative`, `is_prohibition`, `is_rule`, `has_just_in_sent`, `paragraph_has_just`, `is_explained_para`, `has_threat`, `has_causal`, `mentions_claude`, `mentions_model`, `addressee`, `streak_position`. Load with `pd.read_parquet("sentences_classified.parquet")`. Used by `16_rule_explanation.ipynb` (forensic evidence from welfare-evidence files) and `22_audit_threat_framings.ipynb` (threat-framed sentence sample); not loaded by other consumers (which stay YAML-only by design). Lets a skeptical reader audit individual classifier decisions and lets PROPOSAL.md quote actual sentences as evidence rather than only aggregate counts.

---

## Tier-3 welfare-extension metrics

### Judgment-to-procedural ratio

`count(judgment-inviting verbs) / count(procedural cues)`. Reported per file as `judgment_procedural.judgment_to_procedural_ratio`. Corpus baseline: **0.140**.

- **Judgment verbs** invite the model's deliberation: `decide`, `consider`, `evaluate`, `your judgment`, `as you see fit`.
- **Procedural cues** prescribe a procedure for the model to execute: `if you...`, `when the...`, `whenever`, `before`.

A ratio ≪ 1 means the corpus prescribes procedures roughly 7× more often than it invites judgment — the welfare thesis "Claude Code should encourage reasoning over blind obedience" operationalized as a single number.

### Threat share

`count(threat-pattern matches) / (count(threat-pattern matches) + count(causal-pattern matches))`. Reported per file as `consequence_framing.threat_share`. Corpus baseline: **0.452**.

- **Threat patterns** describe a negative consequence: `will fail`, `otherwise`, `or else`, `is forbidden`, `if you don't`.
- **Causal patterns** attribute a positive cause: `because`, `due to`, `in order to`, `that's why`.

Both register as "justifications" in the existing `JUSTIFICATION_PATTERNS`. Splitting them shows that 45% of the corpus's "explanations" are coercive consequence framing rather than neutral causal reasoning.

### Prohibition-to-prescription ratio

`vocab.hard_prohibitions.count / (vocab.hard_prescriptions.count + 1)`. Mean across files: **0.952**. The +1 in the denominator avoids dividing by zero on prescription-free files.

A value > 1 means the file forbids more often than it prescribes; < 1 means it prescribes more often than it forbids. The corpus is roughly balanced despite prohibition-heavy outliers (the bash-sandbox tool descriptions).

### Imperative streak

A run of consecutive imperative sentences in a single file. Reported per file as `streak_max`, `streak_mean`, `n_streaks_ge3` (triple-tap), `n_streaks_ge5` (staccato burst). Longest streak in the corpus: **12** (`system-prompt-skillify-current-session.md`).

A high streak count signals "barked-orders prose" — five commands in a row without a justifying or contextual sentence in between reads very differently from the same commands spread across explanatory text.

### RULES section

A markdown ATX heading (`## RULES`, `## IMPORTANT`, `## WARNING`, etc.) or any ALL-CAPS heading. Paragraphs beneath such a heading are tagged as "in RULES section". The Tier-3 v2 6e analyzer compares explanation rates inside vs outside these sections.

Counter-finding from the corpus: only **26 rule paragraphs** live in identified RULES sections vs **1,242 outside** — the corpus does not segregate rules into formal RULES sections; rules are embedded throughout regular prose.

### Address form

How the prompt names the model. Five classes:
- **`Claude`** — proper-name reference; anthropomorphic. Corpus count: 517.
- **`the assistant`** — functional-role reference. Corpus count: 20.
- **`the model` / `the AI` / `the agent`** — artifact-style reference. Corpus count: 244.
- **2nd person `you`** — direct address. Already counted in `vocab.pronouns_2p`.
- **1st-person plural `we`** (with intentional verbs: want, need, recommend,...). Already counted in `vocab.pronouns_1p`.

`pct_anthropomorphic` = `selfref_claude / (selfref_claude + selfref_assistant + selfref_model)`. Corpus value: **0.662** — ⅔ of named self-references use the proper name `Claude`.

---

## Quantitative metrics

### Type-Token Ratio (TTR)

Lexical diversity. The number of distinct word stems (lemmas) divided by the total number of word stems. A **higher TTR means more varied vocabulary**; a lower TTR means more repetition.

Range is 0–1 in principle. Corpus files cluster in 0.4–0.6 (typical for technical prose). Computed on lemmatized content tokens with stop-words and punctuation removed.

### F-score (Heylighen & Dewaele formality)

A formality score that compares the rate of "informational" parts of speech (nouns, adjectives, adpositions, determiners) against "involved" parts of speech (pronouns, verbs, adverbs, interjections). Formula: `50 + 50 × (formal − informal) / (formal + informal)`.

Reads on a 0–100 scale:
- **0–30** — highly conversational / casual.
- **30–50** — informal explanatory.
- **50–70** — neutral / mixed register.
- **70–80** — formal academic prose.
- **80–100** — technical specification / legal text.

Corpus files cluster in 70–80 (uniformly formal academic register). Citation: Heylighen & Dewaele, *Variation in the contextuality of language: An empirical measure*. The metric is well-established in computational stylistics.

### Mean dependency depth

Average syntactic complexity per sentence. For each token, count its distance to the syntactic root in the spaCy parse tree; average across all tokens.

A **higher value means more deeply nested grammar** (e.g. relative clauses inside relative clauses). Typical written English is around 3–4. Corpus files cluster in 3–4.5. Reported as `register.dep_depth`.

### Mean sentence length

Average number of word tokens per sentence (whitespace-only sentences excluded). Corpus mean: ~22 tokens. Reported as `register.mean_sent_len`.

### Pearson correlation (r)

Statistical strength of a linear relationship between two metrics, measured across all 288 files. Range: −1 to +1.
- **+1** — perfect positive correlation; one metric rises exactly as the other rises.
- **0** — no linear relationship.
- **−1** — perfect negative correlation; one metric rises as the other falls.
- **|r| ≥ 0.7** is conventionally "strong" correlation in social-science contexts.

In the correlation-matrix heatmap, color intensity encodes |r|; red is positive, blue is negative.

### z-score

How many standard deviations a value is from the mean of its column. A z-score of `+2` means "two standard deviations above the corpus average — clearly higher than typical". A z-score of `−2` means "two standard deviations below — clearly lower than typical".

Used here as the building block for the **composite directiveness** metric. z-scores allow us to add metrics measured on different units (% of tokens vs % of sentences) on a common scale.

### Composite directiveness z-score

A single per-file authority score combining eight z-scored metrics:

```
directiveness =
 z(mood_marker_pct)
 + z(hard_prohibitions_pct)
 + z(caps_imp_pct)
 + z(directive_sent_pct)
 + z(configuring_sent_pct)
 − z(collaborative_sent_pct)
 − z(permissive_sent_pct)
 − z(appreciative_sent_pct)
```

Higher = more authoritative tone. The first five summands are emphatic features (added); the last three are softening features (subtracted). Range observed in corpus: **−6.13 to +18.94**. The bash-sandbox tool descriptions are the cluster at the top.

A negative score isn't "below zero in any literal sense" — it just means "less directive than the corpus average".

---

## Units (read every chart axis with these in mind)

### `% of file tokens` (`pct`)

`count / total_word_tokens × 100`. Normalized by document length. Answers: "what fraction of this file's prose is this feature?"

Use this when comparing categories of different sizes — a 10,000-word file with 50 imperative markers (0.5%) is *less* imperative-dense than a 200-word file with 10 markers (5%).

### `per_sent` (rate per sentence)

`count / total_sentences`. Can be > 1 if a feature appears multiple times per sentence on average. Answers: "how often per sentence does this feature appear?"

Use this when comparing categories where typical sentence length differs — a category with long, dense sentences will have similar `pct` but higher `per_sent`.

### `sent_pct` (% of sentences with this flag)

`sentences_with_flag / total_sentences × 100`. Used only for `sentence_register` (the multi-label sentence classifier). Because a single sentence can carry several flags, **`sent_pct` values across the six classes can sum to more than 100%** — that is intentional and reflects multi-label overlap.

---

## Corpus terms

### `ccVersion`

The Claude Code release the prompt was last touched in (e.g. `2.1.118`). Stamped in each prompt's HTML-comment frontmatter. Sorted as `(major, minor, patch)` semver tuples.

The corpus has **58 distinct ccVersions** spanning roughly `2.0.14` (oldest) through `2.1.124` (latest). Files are not evenly distributed — `2.1.53` alone has 47 files, while many minor versions have only one or two.

### Snapshot semantics

In `15_ccversion_trends.ipynb`, the metric value at version V is computed from **only the files marked with that exact version**. Early versions with one or two files swing wildly under this convention.

### Cumulative semantics

The metric value at version V is computed from **every file with `ccVersion ≤ V`** (running mean). Stable, converges as the corpus grows, and the rightmost value equals the corpus-wide per-file mean.

### Category

One of seven prefix-derived labels:
- **Agent prompt** — sub-agent system prompts (37 files).
- **Data / template** — fill-in templates and reference data (38 files).
- **Skill** — Claude Code "Skills" prompt files (30 files).
- **System prompt** — top-level Claude Code system prompts (63 files).
- **System reminder** — short reminder messages injected mid-conversation (40 files).
- **Tool description** — descriptions for the tools Claude can call (78 files).
- **Tool parameter** — descriptions of individual tool parameters (1 file).

### Paragraph

A blank-line-delimited block of text (markdown convention). The Tier-1 paired-rule analysis uses paragraphs as the pairing window.

---

## Vocabulary keys (the 11 `VOCAB` lexicon classes)

These are the curated word lists used by the vocabulary analyzer. Each `vocab.<key>` block in the YAML reports the count, % of file tokens, and per-sentence rate of phrase matches.

| Key | Plain-language gloss | Example tokens |
|---|---|---|
| `hard_prohibitions` | Categorical "no": forbidding language. | `do not`, `never`, `must not`, `cannot`, `forbidden`, `under no circumstances` |
| `hard_prescriptions` | Categorical "yes": demanding language. | `must`, `always`, `required`, `you must`, `mandatory` |
| `soft_prescriptions` | Suggesting / encouraging language. | `should`, `make sure`, `ensure`, `try to`, `aim to` |
| `politeness_direct` | Direct politeness markers. | `please`, `kindly`, `thank you`, `sorry`, `apologies` |
| `politeness_softening` | Softening / hedging requests. | `if you'd like`, `feel free`, `would you`, `if possible`, `perhaps` |
| `warmth_encouragement` | Positive emotional tone. | `welcome`, `glad`, `well done`, `great work`, `proud`, `wonderful` |
| `hedging` | Uncertainty / qualification markers. | `may`, `might`, `could`, `possibly`, `perhaps`, `usually`, `tends to` |
| `structural_markers` | Document-structure callouts. | `note`, `warning`, `important`, `tip`, `example`, `for instance` |
| `profanity` | Strong language. | `fuck`, `shit`, `damn`, `hell`, `crap`, `bullshit` |
| `pronouns_2p` | Second-person address. | `you`, `your`, `yours`, `yourself` |
| `pronouns_1p` | First-person reference (singular and plural). | `i`, `me`, `my`, `we`, `us`, `our` |

---

## How to read each chart type

### Stacked / grouped bar

Each bar (or pair of bars) is a category. Color encodes the sub-class. Length encodes the count or percentage. Read horizontally — within a single category — to see the mix; read vertically across categories to see which categories have the most of each sub-class.

### Heatmap

Rows are categories; columns are classes. Cell color intensity encodes the magnitude. Read a row to see one category's profile across classes; read a column to see where one class concentrates across categories.

### Scatter plot

Each dot is one prompt file. Hover for path, ccVersion, exact metric values. Color encodes category. Size sometimes encodes file length (`n_tokens`).

### Line chart over ccVersion

Each point is one ccVersion (snapshot semantics) OR one cumulative aggregate (cumulative semantics — see above). The x-axis is ordered semver-oldest-to-newest, *not* by date. Hover for the version label and the underlying value.

### Boxplot / strip plot

Box edges = 25th and 75th percentiles (the middle 50% of files in the category). Horizontal line inside the box = median. Whiskers extend to the full range (outliers and all). Dots = individual files (strip overlay).

---

## When in doubt

Every metric in this glossary has a corresponding YAML field in `prompt_linguistic_analysis.yaml`. If you need to verify a number a notebook claims, you can read it directly from the YAML at `corpus.metrics.<block>.<field>` for the corpus-wide value, `by_category.<cat>.metrics.<block>.<field>` for the per-category value, or `files[*].metrics.<block>.<field>` for the per-file value.

The producer notebook `00_data_pipeline.ipynb` writes this YAML; everything else reads from it.
