# v87 final publication claim audit

## Decision

The formal experiment matrix supports a robust retrieval claim, not a
final-answer quality claim. Complete Entity-Memory retrieval has higher
official evidence recall than the matched dense Memory control at every
preregistered cutoff (`top-k = 5, 10, 25, 50`) under both paired-QA and
whole-conversation bootstrap inference. None of the four matched comparisons
supports an overall F1 difference.

The maximum claim level is `robust` within the evaluated ten-conversation
LoCoMo set. It is not `generalized`, `officially-comparable`, or
`paper-ready`.

## Evidence identity and protocol

The audit read 18 frozen result JSON files named in `parameters.json`; all
SHA-256 values matched. No metric was recalculated, no cache or result was
mutated, and no provider request was made.

All promoted conditions used `data/locomo10.json` (SHA-256
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`),
ten conversations, 1,986 QA rows, and 446 Category-5 rows. Matched embedding
comparisons used the same complete read-only query artifact (SHA-256
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`)
with zero misses and zero live query-embedding requests. A and B_embed
returned the same ordered context ids for all 1,986 QA rows.

The frozen evaluator retained batch size 1, system-role answer prompts,
temperature 0, and 32 requested completion tokens. The requested answer model
was `gpt-3.5-turbo`; the provider did not supply a separately persisted actual
model identity. Official F1 and `recall_acc` were kept distinct from the local
Categories 1–4 subset summaries.

## Graph extraction and construction

Complete B used session timestamps, dialog ids, speakers, dialog text, and
official captions. Entity extraction used the bounded `gpt-3.5-turbo` prompt
over conversation text. Entity values were normalized and deduplicated before
forming Entity nodes. Memory nodes represented 5,882 dialog items and were
linked to extracted Entity nodes; chronological Memory edges linked adjacent
dialog memories.

QA questions, QA answers, evidence annotations, categories, judge output, and
prior predictions were excluded from graph construction. Answer recall used
the conversation-built Entity-Memory graph. All promoted formal snapshots pass
the mandatory graph constraint and prompt-budget checks.

## Retrieval and statistics

Primary B used Entity and semantic weights `0.30/0.70`, sequence scale `0.5`,
Entity threshold `0.5`, top-20 Entity matches per key, who-only dampening
`0.25`, degree discount, and semantic fill to the requested top-k. A used the
same Memory embeddings and ordered query vectors with semantic-only ranking
over the full Memory pool.

Inference used 10,000 paired-QA bootstrap resamples and 10,000 resamples of
whole conversations with seed `20260727`. Component, input, fusion, and
sequence families used Holm step-down correction separately by metric and
estimator.

## Findings and claim boundaries

At primary top-k 25, B raised `recall_acc` from `79.7468%` to `84.4842%`, a
`4.7374`-point difference. The paired-QA 95% interval was
`[3.6504, 5.8425]` points and the conversation-cluster interval was
`[3.5286, 6.0124]`. Overall F1 changed from `42.0681%` to `42.5680%`; both F1
intervals included zero.

The evidence-recall advantage remained supported at top-k 5, 10, and 50, with
differences of `4.8083`, `5.5702`, and `3.6159` points. No cutoff supported an
overall F1 difference. The allowed headline is therefore retrieval coverage
across the tested cutoff range.

Component-family inference supports recall contributions from sequence
expansion, Entity-score fusion, sequence expansion over the Entity gate, and
the semantic channel after Holm correction. Only the semantic-channel
contrast supports an overall F1 difference within that family. The separate
speaker ablation supports a `1.4822`-point recall contribution from
deterministic speaker links but no F1 contribution.

Raw-text input preserved a B-over-A recall advantage after input-family Holm
correction, while time annotation had no supported within-B overall effect.
Reducing the Entity weight to `0.10` lowered recall; `0.50/0.50` did not differ
from primary `0.30/0.70`. No F1 or recall contrast among sequence scales
`0.25`, `0.5`, and `1.0` survived family correction.

The local DRAGON result is descriptive only because its query/context protocol
differs and the official reproduction gate failed. It cannot be reported as an
official baseline reproduction or controlled inferential comparison.

## Remaining gate

The complete corrected cold/warm cost report is absent. v86 stopped at
connectivity preflight before creating a checkpoint or cache. Existing warm
answer and retrieval telemetry may be described only as partial resource
traces, not as complete construction/retrieval cost.

The publication decision is `continue_to_cost`, with `paper_ready=false`.
Journal formatting is also unknown, so the accompanying manuscript materials
are journal-neutral and do not claim compliance with a word limit, citation
style, or submission checklist.
