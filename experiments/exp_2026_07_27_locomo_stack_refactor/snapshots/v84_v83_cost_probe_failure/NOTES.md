# v84 freeze of the v83 cost-probe failure

Status: **failed; diagnostic-only; not paper-eligible**.

This snapshot freezes the failed state of
`v83_primary_b_staged_cold_warm_cost` before any telemetry or runner source is
changed.  The governed parameters remain the immutable file
`../v83_primary_b_staged_cold_warm_cost/parameters.json`, SHA-256
`28777bd9ffbb36abd296739291f5e8c68c6c9b636eb4997036efd1daf58d1e4f`.

The run completed all ten cold graph transactions and nine of ten cold Memory
index transactions.  The next transaction,
`cold:index:conv-50`, failed on its first embedding batch after ten consecutive
`APIConnectionError` retries.  The terminal error was:

```text
httpcore.ConnectError: EOF occurred in violation of protocol (_ssl.c:1129)
openai.APIConnectionError: Connection error.
RuntimeError: Embedding failed after 10 retries
```

The checkpoint intentionally retains
`in_progress = "cold:index:conv-50"`.  Under the frozen v83 interruption rule,
the run cannot resume and a new run ID plus new absent cache/output paths are
required.

## Additional telemetry defect found during the freeze

The persisted checkpoint contains ten completed graph wall-time events but
records zero conversation-entity requests and tokens.  The graph transaction
wraps `build_graph()` in a telemetry stage named `graph_construction`, while
the reducer selects chat events named `entity_extraction`; therefore the
provider events generated during graph construction are filtered out before
the checkpoint is written.

The nine completed Memory-index events likewise record only stage wall time
and zero provider requests.  `MemoryEmbeddingIndex._embed_batch_api()` tracks
request count and input tokens on the index object, but it does not emit to
the `common.llm.observe_model_usage()` observer consumed by
`CostTelemetry`.  The staged reducer therefore cannot see these requests.

This means v83 would remain ineligible as complete publication-cost evidence
even without the connection failure.  Cache files retain extracted entities
and vectors, but they do not retain the discarded per-request chat usage and
wall events, so those totals cannot be reconstructed without estimation.

## Frozen evidence

| Check | Evidence | State |
|---|---|---|
| Source | commit `a4d603634a9dc69a2d49a29c8c98848f8acc7001`, tree `9da45113cf51161e6cca733138b3d2001cbf3313` | pass |
| Worktree before failure freeze | clean | pass |
| v83 parameter identity | SHA-256 `28777bd9…d1e4f` | pass |
| Checkpoint | SHA-256 `dc59769e…ff06`; 19/128 complete | failed/incomplete |
| Persisted operation marker | `cold:index:conv-50` | failed |
| Cold graphs | 10/10 graph files; 5,882 Memory nodes | pass |
| Conversation entity cache | 5,873 unique extraction-text keys | diagnostic |
| Cold Memory indexes | 9/10 index files | incomplete |
| Partial cache identity | 21 files; SHA-256 set `331e29c4…e6f`; 82,896 KiB | frozen |
| Cold retrieval | not started | incomplete |
| Warm pass | not started | incomplete |
| Final event manifest/report | both absent | incomplete |
| Entity provider telemetry | persisted as zero despite live calls | invalid |
| Embedding provider telemetry | persisted as zero despite live calls | invalid |
| Graph constraint | conversation-only construction inputs; no QA used | pass |
| Paper eligibility | no complete or valid cost result | fail |

The partial cache remains quarantined at
`outputs/locomo_cost/primary_b_v83_cache` and must not be resumed, deleted, or
used as a cold-start root.  The checkpoint remains at
`outputs/locomo_cost/primary_b_v83_checkpoint.json`.  No v83 event manifest or
report exists.

## Decision

Freeze v83 as diagnostic-only.  Before any new full cost run:

1. repair graph chat-event aggregation and embedding usage collection without
   changing graph, retrieval, generation, or evaluator behavior;
2. add integration tests that exercise the real threaded entity path and the
   real `MemoryEmbeddingIndex` usage counters rather than injecting synthetic
   telemetry;
3. validate the repair on a fresh, isolated preflight cache;
4. freeze a new parameter snapshot and start from new absent cache, checkpoint,
   event, and report paths.

Maximum defensible claim: v83 demonstrated isolated staged progress through
all cold graphs and nine cold indexes, then exposed both an external
connection failure and incomplete provider telemetry.  It produced no
publication cost result.
