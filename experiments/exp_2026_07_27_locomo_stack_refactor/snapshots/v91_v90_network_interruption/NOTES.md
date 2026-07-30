# v91 — v90 network interruption

## Outcome

v90 validated the v89 query-hit repair in live execution but did not complete.
It stopped during `cold:retrieve:conv-50:100:150` after one question-Entity
call received ten consecutive connection errors and exhausted the frozen
retry policy. The checkpoint contains that operation in `in_progress`, so v90
is invalid for continuation and final reporting.

The first 61 operations committed successfully: all ten cold conversation
graphs, all ten cold Memory indexes, and 41/44 cold retrieval batches covering
1,882/1,986 QA. The completed retrieval events record 1,894 immutable
query-vector hits, zero misses, and zero live query-embedding requests.

## v89 repair validation

The previously failing conv-26 QA 50–99 batch committed successfully with 52
query-artifact hits over 50 QA, zero misses, and zero live embeddings. This
confirms that the batch-level `hits >= QA` repair correctly accepts the
retriever's legitimate semantic-fill rereads. The eventual v90 failure was an
external chat connection interruption, not a recurrence of the query-counter
bug.

## Artifact and cache decision

The exact v90 checkpoint and 59 MB cache root are quarantined read-only.
Nothing is deleted or overwritten. v77, v79, v83, v86, formal results, and the
immutable query-vector and formal query-usage inputs remain untouched.

The completed values are diagnostic only. They do not prove complete cold
cost, warm zero-provider-request behavior, full 1,997-hit parity, or final
latency and therefore cannot be promoted as paper evidence.

## Compliance

Graph construction used only timestamps, dialog ids, speakers, dialog text,
and captions. QA answers, evidence annotations, categories, judge outputs,
and prior predictions were excluded. Retrieval used the conversation-built
Entity–Memory graph. Prompt scaffold length remained 2,410 characters under
the 5,000-character limit. No answer generation, judging, F1, or
`recall_acc` evaluation ran.

## Next action

Do not launch another expensive all-10 cold run until API connectivity is
stable and the staged runner has a predeclared recovery design for
provider-connection exhaustion. Any new run requires a new source/parameter
snapshot and four absent output paths; it must not reuse v90 graphs, indexes,
question caches, checkpoint events, or partial measurements.
