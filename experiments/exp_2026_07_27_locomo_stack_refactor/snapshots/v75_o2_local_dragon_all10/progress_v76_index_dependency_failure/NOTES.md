# v76 progress — O2 index preparation dependency failure

Date: 2026-07-29 Asia/Shanghai. Governing parameter snapshot:
`../parameters.json`.

The cache-only raw DRAGON Memory-index preparation wrote the first of ten new
identity-bound indexes successfully, then stopped before retrieval or formal
output creation when Entity BM25 initialization imported a dependency missing
from the isolated O2 runtime:

```text
ModuleNotFoundError: No module named 'rank_bm25'
```

The valid new file is:

```text
outputs/em_graph/embedding_indexes/
conv-26_149353b173b82704339c5f60b7fa0026da00e1bf70235a46cf56bbe7cd122c5b.npz
```

Its SHA-256 is
`4ec9c30bfc73ef6c270ad41174529af3b73925ded043644188951451bf724c08`.
It is retained; it will not be deleted or rebuilt.

Post-failure state:

- graph count: 70;
- graph-set combined digest:
  `6cc96ee62182999d83f5004c49153abfa4dfef8986a304c0e2e81c498daa1ab3`;
- Memory-index count: 31;
- the original 30-index combined digest remains
  `e8c0c14aa4bee79521cd1c81ebe98ffe31412911c52cc80d00448df227c648b0`;
- formal condition directory: absent;
- answer/provider calls: zero;
- query artifact: unchanged;
- old cache deletion, overwrite, or rebuild: none.

The existing project runtime uses `rank-bm25==0.2.2`. Install exactly that
package into the isolated O2 runtime, verify its version, and resume only the
remaining nine absent index paths. No scientific parameter changes.

Publication gate: `continue_after_runtime_dependency_repair`;
`paper_ready=false`.

