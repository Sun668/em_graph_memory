# v85 cost telemetry and formal-query alignment

Status: **validated source-only tooling; no cost result**.

This snapshot freezes the source repair made after the diagnostic v83 failure
was preserved and pushed at commit `f7e7510`. No external provider request,
new graph, new index, cost manifest, cost report, answer, prediction, judge
score, or official metric was produced by v85.

## Purpose and governed condition

The repaired runner is intended for a future fresh measurement of the
paper-primary complete-B condition:

- dataset `data/locomo10.json`, SHA-256
  `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`;
- all ten conversations, 5,882 dia and 1,986 ordered QA;
- graph variant B, top-k 25;
- extraction and answer model `gpt-3.5-turbo`;
- Memory embedding model `text-embedding-3-small`;
- Entity/Semantic weights `0.30/0.70`, no semantic score normalization;
- sequence expansion enabled at secondary scale `0.5`;
- Entity minimum relevance `0.5`, top 20 matches per key;
- who-only dampening `0.25`, degree discount enabled;
- exact L2 query artifact
  `outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz`,
  SHA-256
  `bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.

The staged batch size remains 50 QA, giving 128 transactions: 10 graph,
10 Memory-index, and 44 retrieval operations under cold state, followed by
the same operations under warm state. Component-operation timing excludes
interpreter, checkpoint serialization, and repeated Recall-load overhead.

## Graph extraction and construction

The extraction prompt, `gpt-3.5-turbo` call parameters, dialog normalization,
entity schema, normalization, deduplication, graph node/edge types, session
ordering, caption handling, and graph identities are unchanged. Construction
uses only session timestamps, dialog ids, speakers, dialog text, and official
`blip_caption`. It excludes QA questions, answers, evidence annotations,
categories, judge outputs, previous predictions, and question-driven ledgers.

The repair changes observation only. Chat calls made inside the threaded graph
builder inherit the outer telemetry stage name `graph_construction`; the
reducer now explicitly maps those chat events into the publication stage
`entity_extraction` while retaining the separate total graph-operation wall
time.

## Embedding and recall

`MemoryEmbeddingIndex._embed_batch_api()` already retained provider-derived
request and input-token counters but did not notify the shared telemetry
observer. It now publishes the same provider response through the opt-in
observer. The staged runner requires observer request/token totals to equal
the index-native counters and requires embedding input-token provenance in
the strict report.

The old v83 staged path did not bind the formal query artifact and allowed
mutable text-cache fallback. v85 corrects that protocol mismatch. Every
transaction validates the full query artifact identity, passes it as a
read-only `query_cache`, sets `strict_query_cache=True`, and sets
`use_text_cache=False`, matching `formal_graph.py`. Each retrieval batch must
record exactly one artifact hit per QA, zero misses, and zero live query
embedding requests.

Question formation, question Entity extraction, Entity BM25 gating, dense
Memory scoring, fusion, sequence expansion, signed scores, tie behavior,
top-k 25, recalled-context formatting, and answer protocol are unchanged.
The future cold pass will measure fresh question Entity extraction; the warm
pass must make zero new provider calls. The existing validated formal answer
event remains reused for both cache states with explicit disclosure because
answer generation is cache-independent.

## Finalization gates

Checkpoint schema is now `locomo_staged_cost_checkpoint_v2`; a v83 checkpoint
cannot resume under this source. Finalization requires:

- all 128 uniquely bound transactions complete and no `in_progress`;
- exactly ten graph files and ten Memory-index files;
- all six cost stages under cold and warm states;
- provider-derived chat and embedding token usage with no estimates;
- 1,986 ordered question-cache entries and 1,974 unique raw questions;
- 1,986 query-artifact hits per cache state, zero misses/live embeddings;
- positive cold entity, embedding, and question-Entity provider requests;
- zero new warm graph/entity, embedding, or question-Entity requests;
- valid graph/index/entity/query-artifact disk paths;
- the reused 1,986-request answer event from the matched formal B run.

The graph constraint and prompt budget remain unchanged and pass by design.
No judge is applicable: this is a non-metric cost measurement, and the frozen
official LoCoMo evaluator is neither called nor modified.

## Validation

- Python compilation: pass;
- focused cost/telemetry/report tests: 19/19;
- current refactor experiment suite: 101/101;
- historical official-comparison suite: 17/17;
- historical conv-26 official-dialog suite: 3/3;
- frozen evaluator manifest: 16/16;
- exact full query-artifact validation: 1,986 QA, 1,974 unique, zero lookups
  during validation, SHA-256 `bef99a…6f9f`;
- `git diff --check`: pass.

The focused tests include a real threaded `build_em_graph()` path with mocked
provider responses, a real direct embedding-client path with provider usage,
strict artifact-hit retrieval, argument/checkpoint identity, interruption
failure, and strict report token validation.

## Decision and invalidation

v85 supports only the claim that the repaired source satisfies its offline
telemetry and formal-query contracts. It does not restore v83 usage because
v83 discarded raw provider events before persistence. v77, v79, and v83
partial caches remain diagnostic and quarantined.

Changing the observer, embedding usage collection, query artifact, cache
fallback, checkpoint schema, finalization gates, or any scientific parameter
requires a new source/run identity. The next formal cost attempt must use a
new run ID and new absent cache, checkpoint, event, and report paths.

Next: commit/push v85, run one-call live chat and embedding usage preflights,
freeze v86 against the committed source and exact query SHA, then inspect the
first persisted graph and index events before continuing the paid full run.
