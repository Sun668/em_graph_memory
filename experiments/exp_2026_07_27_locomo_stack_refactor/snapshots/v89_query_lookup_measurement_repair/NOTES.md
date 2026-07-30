# v89 — query lookup measurement repair

## Root cause

The complete-B retriever may read the same immutable question vector twice for
one QA. It first scores the Entity-gated candidate pool. If that pool contains
fewer than `top_k=25` Memories, semantic fill scores the full Memory pool and
therefore performs a second read-only lookup. This is retrieval behavior
already present in the matched formal B@25 condition; it is not an extra API
call and does not change the query vector.

The failed v86 batch covering conv-26 QA indices 50–99 reproduced 52 artifact
hits over 50 QA. Indices 82 and 98 each performed two legitimate lookups.
There were zero artifact misses, zero live query-embedding requests, and zero
native embedding requests. The matched formal B@25 result records 1,997 hits
over 1,986 QA with zero misses/live requests.

## Repair

`cost_probe_staged.py` now:

1. requires at least one artifact hit per QA inside each retrieval batch;
2. binds a separate formal `query_cache_usage.json` by absolute path and
   SHA-256;
3. verifies that the formal usage document is passing, complete, and has
   `lookup_count == cache_hits >= qa_count`;
4. revalidates that artifact identity on every step and at finalization; and
5. requires both cold and warm retrieval totals to equal the formal B@25
   count of exactly 1,997 hits, with zero misses and zero live requests.

No graph, retrieval ranking, fallback, prompt, model, normalization, answer,
or evaluator behavior changed. The repair only corrects measurement
validation and adds an input identity.

## Validation

- Focused staged-cost tests: 12/12.
- Full current experiment tests: 104/104.
- Frozen evaluator manifest: 16/16.
- New regression cases prove that two read-only hits for one QA are accepted,
  fewer hits than QA rows are rejected, and the formal query-usage document
  binds an exact lookup total.

The exact source is the two changed files listed with SHA-256 values in
`parameters.json`. The reconstructable patch is the diff from base commit
`29e9529` to the commit that introduces this snapshot and those source files.

## Publication and compliance decision

This source-repair snapshot has no cost result and is not paper evidence.
Graph construction logic remains conversation-only and the prompt budget is
unchanged. v86 must not be resumed. A new run must start from absent output
paths and rebuild cold graphs and Memory indexes from scratch.
