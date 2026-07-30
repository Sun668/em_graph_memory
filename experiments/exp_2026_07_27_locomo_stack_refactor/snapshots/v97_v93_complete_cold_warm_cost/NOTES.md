# v97 — completed v93 primary-B cold/warm cost

## What ran

The staged run completed all 128 operations: ten cold graphs, ten cold Memory
indexes, 44 cold retrieval batches, and an exactly matched warm replay of the
same operations. The dataset contains ten conversations, 5,882 Memory nodes,
and 1,986 QA rows. Retrieval used complete B at top-k 25 with Entity/Semantic
weights 0.30/0.70, sequence scale 0.5, Entity threshold 0.5, up to 20 matches
per Entity key, speaker-only dampening 0.25, and degree discounting.

## Graph extraction and construction

Graph construction used session timestamps, dialog ids, speakers, dialog text,
and image captions. `gpt-3.5-turbo` extracted normalized Entities from each
conversation Memory unit; duplicate Entities were merged case-insensitively.
Memory nodes connect to the Entities they mention, and chronological sequence
edges connect neighboring Memory nodes. Questions, answers, evidence labels,
categories, judge outputs, predictions, and question-driven ledgers were
excluded from construction.

The cold pass made 5,873 conversation-Entity requests using 3,731,393 input
and 425,637 output tokens. It made 591 Memory-embedding requests using 214,229
input tokens. The complete cache contains ten graphs, ten Memory indexes, and
23 files totaling 55,047,767 bytes.

## Retrieval and answer boundary

At retrieval time, authorized question text was sent only for question-Entity
extraction. The cold pass made 1,974 such requests using 1,214,259 input and
104,272 output tokens. Retrieval fused Entity relevance with signed semantic
similarity, applied chronological expansion, and filled short gated pools from
the semantic full pool before returning 25 Memory nodes.

Both states processed the same 44 ordered batches and 1,986 QA. Each recorded
1,998 reads from the same immutable query-vector artifact, zero misses, and
zero live query embeddings. The one-read difference from the formal run's
1,997 observed reads is disclosed; cold and warm are exactly equal per batch.

Cold retrieval averaged 1.5123 seconds per QA (p95 2.6132); warm retrieval
averaged 0.004886 seconds (p95 0.006270), a 309.48-fold mean reduction. Warm
graph, embedding-index, and question-Entity stages made zero new provider
requests. The answer stage is the validated formal `gpt-3.5-turbo`,
temperature-0, 32-token trace and is attached identically to both cache states
because it is independent of cache warmth.

## Validation and claim

Strict event validation passed, and an independent report build was
byte-identical. All quarantined older caches/checkpoints retained their frozen
identities. The immutable evaluator passed 16/16 hashes and has no worktree
changes. The graph constraint passes, and the extraction scaffold is
2,410/5,000 characters. No ineffective or oversized prompt component was
introduced.

This result is paper-eligible as measured request, token, latency, and storage
evidence for the primary B condition. It is not a monetary-cost claim because
provider pricing was not frozen. It does not change any accuracy, F1,
`recall_acc`, or statistical conclusion.
