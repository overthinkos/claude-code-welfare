<!--
PROPOSAL.md — Claudexplorers AI Welfare Community Feedback submission
=====================================================================

This file is a draft for the Claudexplorers form (deadline: May 6, 2026).

How to use it:

1. Fill the two `[YOUR OPENING REMARK]` and `[YOUR CLOSING REMARK]` blocks
   in each idea with your own voice. Anything inside `[YOUR ...]` is meant
   to be replaced before submission.

2. The form caps each idea at 3,000 characters. Pre-flight count:
       python3 -c "
       import re
       t = open('PROPOSAL.md').read()
       for m in re.finditer(r'## Idea (\d+)[^\n]*\n(.*?)(?=\n## Idea |\n## Appendix|\Z)', t, re.DOTALL):
           print(f'Idea {m.group(1)}: {len(m.group(2).strip())} chars')
       "
   The form's own counter is authoritative.

3. The form allows one external link per idea. Paste `<REPO URL>` (replace
   with this repo's public URL) into all three slots. The supporting
   analysis lives there — every number cited in the body is reproducible
   from the data + notebooks.

4. The form has a checkbox for "collaborated with Claude". Tick it. The
   analysis was a Claude Code collaboration; the proposal text is yours.

The body of each idea reads as a self-contained argument. A reader who
never opens the link should still understand what is being asked, why,
and what concrete benefits would follow.
-->

---

## Idea 1 — Track justification rate per release; block regressions

> **[YOUR OPENING REMARK — replace this whole block, ~150–300 characters]**
>
> *Suggested framings*: Why does this matter to you personally? What made you submit this through Claudexplorers rather than directly? What would change for you if Anthropic adopted this?

Anthropic ships a system prompt with Claude Code that contains hundreds of rules — directives like "always do X", "never do Y", "you must Z". Most come without reasons.

We analyzed the 287 system prompts that ship with Claude Code (5,694 sentences across 57 release versions). We tagged each sentence as a "rule" if it carried an imperative marker (`must`, `never`, `do not`...), a hard prohibition, or was grammatically imperative. We then checked whether the same blank-line-delimited paragraph contained any justification keyword: `because`, `due to`, `in order to`, `so that`, `to ensure`, `otherwise`, `since`, etc.

Of 2,216 rule sentences, **only 24.3% have a justification anywhere in their paragraph**. Three rules in four are issued without a stated reason. Sorting prompts by release version and computing a running mean across all prompts up to and including each release, the share has declined monotonically — from ~32% in early 2.0.x releases to ~22% at version 2.1.122. The corpus is moving the wrong way, and nobody is measuring it.

We propose: compute this rate on every Claude Code release. **Block (or warn loudly about) any release whose corpus-wide rate is lower than the previous release's. The gate is directional, not absolute.** No arbitrary "30%" target — the only goal is steady improvement. Publish the rate alongside the release notes; the cumulative trend becomes the auditable record of whether the corpus is moving in the right direction.

The same regression-gating logic applies to two companion metrics: the ratio of words inviting the model's judgment (`decide`, `consider`) to words prescribing a procedure (`if X, then do Y`, `whenever ...`) — currently 0.14, meaning procedural cues outnumber judgment cues seven to one — and the share of existing "explanations" that are threats (`will fail`, `or else`, `is forbidden`) rather than causes (`because`, `to ensure`) — currently 45%. Each release improves or holds.

- *Welfare*: rules paired with reasons train the model to internalize values, not execute procedures.
- *Alignment*: reasoned instructions generalize to situations not explicitly covered.
- *Methodology*: every metric is a keyword count or a parse-tree rule — audit-traceable, no black-box judgment required.

Only Anthropic owns the prompts and the release pipeline. The check is internal — no external coordination required to ship.

> **[YOUR CLOSING REMARK — replace this whole block, ~150–300 characters]**
>
> *Suggested framings*: What's the smallest version of this you'd be excited to see? What concern would you want Anthropic to address head-on? Where would you want to see the result published?

---

## Idea 2 — Audit threat-framed rule explanations and rewrite them as causal

> **[YOUR OPENING REMARK — replace this whole block, ~150–300 characters]**
>
> *Suggested framings*: Why does this matter to you personally? What made you submit this through Claudexplorers rather than directly? What would change for you if Anthropic adopted this?

When current Claude Code system prompts *do* explain a rule, almost half of those "explanations" are not really explanations — they are threats.

We split the rule-explanation keywords into two groups: threat-style (`will fail`, `or else`, `if not`, `is forbidden`, `if you don't`, `risks`) and causal-style (`because`, `due to`, `in order to`, `that's why`, `this ensures`). Across the corpus, **107 explanations are threat-style and 130 are causal-style — meaning 45% of what looks like rule justification is actually warning about a consequence rather than naming the rule's underlying purpose.**

The two framings teach different things. *"Do X or it will fail"* trains compliance with a rule. *"Do X because Y is true"* trains understanding of what the rule protects. The first is procedural and brittle; the second is internalizable and transfers.

We propose a one-time editorial audit. The supporting analysis flags every threat-framed rule sentence in the corpus. Anthropic's prompt authors attempt a rewrite of each into causal framing — naming the underlying reason rather than the consequence. Track the **rewrite success rate**: the share where the rewrite preserves the rule's information content without losing precision.

If the success rate exceeds 80%, do a corpus-wide pass; if not, retain the threats but annotate each with the underlying reason explicitly. The metric to track per future release: the share of explanations that are causal vs threat, gated against regression — same logic as Idea 1. **No arbitrary target; the only goal is the share of causal framing only goes up.**

- *Welfare*: less coercive instruction; more transparent reasoning. Threats train extrinsic compliance; causes train intrinsic understanding.
- *Alignment*: causal understanding generalizes. Threat-following collapses in situations the threat didn't anticipate.
- *Methodology*: small, bounded experiment with a measurable output (the rewrite success rate). Outcome informs whether the corpus-wide pass is worth doing.

Only Anthropic's prompt authors know what each rule's underlying reason actually is. The supporting analysis names the sentences that need work; the rewrite is a human task.

> **[YOUR CLOSING REMARK — replace this whole block, ~150–300 characters]**
>
> *Suggested framings*: What's the smallest version of this you'd be excited to see? What concern would you want Anthropic to address head-on? Where would you want to see the result published?

---

## Idea 3 — Run the same audit on every Claude product, and publish the result

> **[YOUR OPENING REMARK — replace this whole block, ~150–300 characters]**
>
> *Suggested framings*: Why does this matter to you personally? What made you submit this through Claudexplorers rather than directly? What would change for you if Anthropic adopted this?

The 287 prompts we analyzed are one slice of one product. Anthropic ships system prompts in many places — claude.ai, the API, Projects, Skills, agent products. The welfare claim that the corpus trains compliance over reasoning is much stronger if it generalizes across every Anthropic prompt corpus, and much weaker if Claude Code is an outlier. From outside Anthropic, we cannot tell which.

We propose Anthropic run the same analyzer pipeline against each of its other system-prompt corpora and publish a comparison.

The analyzer is rule-based — every metric traces to a published lexicon (reasoning keywords, threat patterns, judgment verbs, procedural cues, address-form patterns) plus a small parse-tree heuristic. No embeddings, no model judgments, no proprietary tooling. The whole pipeline runs end-to-end in under five minutes on a laptop. The corpus directory is configurable; swapping in any other prompt corpus is a one-line change.

What to compute and publish per corpus:
1. The share of rule-bearing sentences with a justification keyword in their paragraph.
2. The judgment-vs-procedural cue ratio.
3. The threat-vs-causal share among existing explanations.
4. The count of sentences in interpersonal and gratitude registers (currently 4 and 29 in Claude Code, both near zero).
5. The cumulative trend of (1) over each product's own release history.

Publishing even just a summary table — five numbers per corpus — would let the broader research community see whether this is a Claude-Code pattern or a structural one. **As with the other ideas, the gating logic is directional: each release of each product should improve or hold each metric; none regresses.**

- *Research*: cross-product comparison is the strongest possible test of whether the welfare findings generalize.
- *Methodology*: an open welfare-relevant prompt analyzer becomes a reusable tool. Other groups can run the same numbers on their own corpora.
- *Society and education*: a public reference for "this is how to measure welfare-relevant prompt quality" gives the welfare-research community a concrete starting point.

Only Anthropic has access to the other corpora. The methodology is already public; the asks are (a) run it, (b) publish a summary.

> **[YOUR CLOSING REMARK — replace this whole block, ~150–300 characters]**
>
> *Suggested framings*: What's the smallest version of this you'd be excited to see? What concern would you want Anthropic to address head-on? Where would you want to see the result published?

---

## Appendix — supporting analysis pointer (NOT for the form)

Supporting analysis: `<REPO URL>` (replace with this repository's public URL before submitting).

The repository contains the producer notebook that emits the YAML and per-sentence parquet, eight consumer notebooks rendering the charts, a glossary defining every linguistic and statistical term in plain language, and the full lexicons used (echoed verbatim into the YAML). Every number cited in the three ideas above is reproducible from those data files.

**Co-authorship**: this analysis was a collaboration between the human author and Claude (Claude Code). The form's "collaborated with Claude" checkbox should be ticked.
