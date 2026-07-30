# v08_no_legacy_em_graph_modules

Complete EM-graph package-layout refactor requested by the user.

## Source structure

`code/em_graph/` now contains only:

```text
README.md
__init__.py
build/
recall/
cache/
```

The ten root compatibility modules (`builder`, `config`, `embedding_index`,
`entity_bm25_index`, `entity_extractor`, `models`, `replace_pronouns`,
`retrieval`, `retrieval_audit`, and `tokenize`) were deleted. Active callers
were migrated to `em_graph.build`, `em_graph.recall`, or `em_graph.cache`.
`em_graph.__init__` remains the sole public convenience facade.

Immutable historical snapshots and the two self-contained experimental
package copies under `exp_2026_07_24_em_bm25_soft_match` and
`exp_2026_07_24_em_embed_seed_expand` were intentionally not rewritten.

This is a breaking import-path cleanup:

- `em_graph` version: `0.5.0`;
- aggregate wheel version: `standalone_graph_memory-0.3.0`;
- wheel SHA-256:
  `9b42b1e33346515aa81ed35993fbaad289170f8dfc1bd3c4b014de9980aa1fc9`.

## Validation

- 15/15 refactor/parity/cache/resume/structure tests pass.
- 17/17 normalization and real-datetime tests pass.
- 71 active source files pass AST syntax parsing.
- all active callers outside the two self-contained experimental copies have
  zero imports from deleted paths.
- public facade plus `build`, `recall`, and `cache` imports pass.
- all ten deleted module paths are absent both locally and in the wheel.
- 16/16 pinned official LoCoMo vendor hashes pass.
- wheel includes all vendor files, contains no `.pyc`/`__pycache__`, and
  passes an isolated import/vendor-runtime smoke test.
- both the new runner and old command compatibility entry point load.
- `git diff --check` passes.

No graph, retrieval, cache, prompt, evaluator, or metric behavior changed.
The mandatory graph constraint remains satisfied. No new QA metric is claimed.
