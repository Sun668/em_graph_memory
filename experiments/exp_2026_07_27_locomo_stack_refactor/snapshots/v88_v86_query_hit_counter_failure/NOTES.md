# v88 — v86 query-hit counter failure

## Outcome

The v86 primary-B cold/warm cost run failed closed at operation 22,
`cold:retrieve:conv-26:50:100`. The preceding 21 operations were committed:
all ten cold conversation graphs, all ten cold Memory indexes, and the first
50-QA cold retrieval batch. The second retrieval batch completed enough work
to persist 100 ordered question-Entity rows and 100 raw question extractions,
but `_retrieval_events` rejected the transaction because the query-artifact
hit counter did not equal the batch's 50 QA rows.

The checkpoint now contains
`in_progress="cold:retrieve:conv-26:50:100"`. Under the frozen v86 protocol,
this permanently invalidates continuation. The exact v86 checkpoint and cache
root are quarantined read-only and must not be resumed, deleted, or copied
into a new formal condition.

## Completed diagnostic evidence

- Graph artifacts: 10/10.
- Memory indexes: 10/10.
- Conversation Entity requests: 5,873; input tokens: 3,731,393; output
  tokens: 427,239.
- Memory embedding requests: 591; input tokens: 214,229.
- First completed retrieval batch: 50 question-Entity requests; 30,635 input
  tokens; 2,181 output tokens; 50/50 query-artifact hits; zero misses; zero
  live query embeddings.
- Failed-batch caches persisted 100 ordered question rows and 100 raw
  questions, which permits a no-new-provider-call diagnosis.

The partial numbers above are diagnostic only. They do not establish complete
cold cost, warm zero-request behavior, or publication-ready latency.

## Integrity and compliance

The run used source commit `22ba54c`, the v86 parameter SHA
`78ab5dd2...a104`, dataset SHA `047d8e25...b4d74`, and immutable query
artifact SHA `bef99a91...6f9f`. Graph construction consumed only session
time, dialog ids, speakers, dialog text, and captions. QA questions were used
only during recall; QA answers, evidence annotations, categories, judge
outputs, and prior predictions were excluded from graph construction. The
2,410-character Entity scaffold remained below the 5,000-character budget.

No answer generation, judge evaluation, F1, or `recall_acc` computation ran.
Old v77/v79/v83 caches and all formal answer/metric artifacts were untouched.

## Next action

Use the persisted v86 question caches only for read-only diagnosis of the
50-row counter mismatch. Snapshot any source repair before launch. A repaired
measurement must use a new absent checkpoint, cache root, event file, report
file, parameter snapshot, and run id; it must rebuild cold graphs and indexes
from scratch rather than reusing v86.
