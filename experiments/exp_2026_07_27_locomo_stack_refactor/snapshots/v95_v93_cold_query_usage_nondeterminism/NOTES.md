# v95 — v93 cold query-usage nondeterminism

## Observation

v93 completed its entire cold phase: 64/128 transactions, including 44
retrieval batches over all 1,986 QA. Every batch passed strict read-only query
artifact checks, with zero misses, zero live query embeddings, and zero outer
provider-recovery retries.

The measured query-vector lookup total is 1,998 rather than the matched formal
B@25 run's 1,997. Both totals include one required lookup per QA plus a small
number of legitimate second reads when an Entity-gated pool contains fewer
than 25 Memories and semantic full-pool fill is needed.

## Root cause

Question Entity extraction uses `gpt-3.5-turbo` at temperature 0.3. Fresh
extraction is therefore not byte-deterministic. v93's complete ordered
question-Entity cache differs from the current shared cache on 336/1,986 rows.
The formal run configuration binds graph, Memory-index, and query-vector
identities, but it does not bind a question-Entity cache SHA. Its 1,997 lookup
count is an observed retrieval trace, not an immutable experiment input.

Consequently, requiring every fresh cold-cost realization to reproduce exactly
1,997 internal reads is not a valid cache-integrity gate. Repeating the entire
cold run would neither guarantee 1,997 nor improve scientific validity.

## Predeclared amendment before warm replay

No warm transaction has run. Before observing warm behavior, the corrected
terminal gate is:

1. cold and warm each cover the same 44 ordered batches and 1,986 QA;
2. every paired batch has identical QA count, query-hit count, miss count, and
   live-query-request count;
3. both states have zero misses and zero live query embeddings;
4. each state has at least one immutable query-vector hit per QA;
5. the formal 1,997-hit artifact remains SHA-bound as a reference, and the
   measured delta is disclosed rather than treated as equality.

This amendment changes only terminal validation and reporting. It does not
change graph construction, question extraction, query vectors, retrieval
scores, ranking, context, provider accounting, latency, or any completed cold
artifact. Warm measurement will continue using the original frozen ccb9c6a
runner; a separately committed validator/report repair will finalize it.

## Compliance

Graph construction remains conversation-only. Questions were used only for
retrieval-time Entity extraction under the user's explicit authorization.
Answers, evidence annotations, categories, judge output, and prior predictions
were excluded. Prompt scaffold length remains 2,410 characters. No answer
generation, judging, F1, or `recall_acc` evaluation ran.

v93 is valid cold cost evidence but is not yet paper-eligible until the
amendment is implemented and tested, warm batchwise parity passes, and the
final report is independently reproduced.
