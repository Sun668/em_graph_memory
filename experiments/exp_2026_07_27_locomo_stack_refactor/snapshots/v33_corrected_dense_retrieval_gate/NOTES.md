# v33 — corrected all-10 A/B_embed retrieval gate passes

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `f8757e1`.

The all-10 retrieval-only gate was repeated from QA 0 after deleting the exact
partial context cache. Both A and B_embed loaded the same ten hash-bound Memory
index paths, disabled all writable context-cache use, and shared immutable
query artifact SHA `bef99a…6f9f`.

Result:

- conversations: 10/10;
- paired QA: 1,986/1,986;
- ordered context-id mismatches: 0;
- identical Memory index paths: 10/10;
- query artifact lookups/hits: 3,972/3,972;
- query misses: 0;
- live query embedding requests: 0;
- answer calls and metrics: 0.

Graph construction and prompts were unchanged, and `code/locomo_eval/` was not
used or modified. Publication gate: `continue`, `paper_ready=false`. The
corrected dense control is now valid; proceed to formal corrected A and
B_embed, then rerun B and significance.
