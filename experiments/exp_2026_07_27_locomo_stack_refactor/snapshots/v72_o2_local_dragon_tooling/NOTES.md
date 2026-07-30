# v72 — O2 local DRAGON tooling lock

Decision date: 2026-07-29 Asia/Shanghai. Exact source commit:
`a32fbee7259fb138ecaa2b558e085ea3d364af62`.

This source-only snapshot freezes the implemented O2 protocol before installing
its isolated runtime, loading DRAGON weights, building the raw query artifact,
building raw Memory indexes, retrieving contexts, or generating answers.

## Locked implementation

- Existing L2 behavior remains the default. Existing v1 L2 query artifacts
  and v2 Memory indexes load under their historical identities.
- Raw DRAGON uses a new v2 query-artifact schema and v3 Memory-index format.
  Raw identities bind normalization, query/context encoder ids and revisions,
  tokenizer, CLS pooling, max length, raw dot product, Python/package versions,
  and CPU/CUDA state.
- Raw artifacts cannot use the shared L2 text cache.
- Any existing-path identity mismatch fails closed; the implementation never
  silently rebuilds or overwrites an index.
- Retrieval supports the locked query-local min–max semantic calibration.
  Equal semantic scores map to zero. The default `none` mode preserves the
  historical ranking path.
- `formal_graph.py --o2-local-dragon-diagnostic` accepts only all-10 B@25,
  raw DRAGON, 0.30/0.70 fusion, sequence scale 0.5, threshold 0.5,
  entity-top-k 20, who-only dampening 0.25, and degree discount enabled.
- Formal configuration labels the result
  `local_dragon_stack_diagnostic` and
  `official_comparison_eligible=false`.

## Verification

- Related test suite: 105/105 pass.
- Frozen evaluator manifest: 16/16 pass.
- `code/locomo_eval/`: no source difference.
- Historical primary B independently revalidates with the current external
  validator, including the unchanged v1 query-artifact identity.
- Existing artifacts: 70 graph files, 30 Memory indexes, one existing
  two-file L2 query-artifact pair, and no O2 output directory.
- No external model/API call or cache mutation occurred during implementation.

## Locked source SHA-256

- `code/em_graph/cache/query_embeddings.py`:
  `e2336426e0872949a248b00185624987b56fc16474d9d0cd8f85c84e03b5c20a`
- `code/em_graph/recall/embedding_index.py`:
  `80a309584d3370322fb4e2bc70a1d587a821fa62dcceb8c38b65292831912b7a`
- `code/em_graph/recall/retrieval.py`:
  `31544dc1aa21f5f200e91c3a2db14dc0aeede27419562dbb1c31b342ec4c1908`
- `code/em_graph/recall/retrieval_audit.py`:
  `e8d2d9af7eb3331b87ccebae8b360e56623d1dbe6cd726ec0548f054e83395e3`
- `code/em_graph/recall/service.py`:
  `04813f29956dac97dbfc227786ea702f2f27c0e027ea90ee9a64ff5352b6d3e3`
- `formal_graph.py`:
  `3bee184d19bd0a193ab8650efd94440fc685984b04ef90292d9d468a097a64b6`
- `prepare_query_embeddings.py`:
  `00c198f787753ef731edcad3ba1a940d0bc9dd44479fe0e066457fe6841020be`
- `run.py`:
  `6c9cab2629697a082f50949a4e011fcd089fb6eaa82b46cffbad64be6416a5e7`
- `validate_formal_result.py`:
  `a73db185734ffd16e87307e601a59541c87f0b1774a83e508abe10110bf9bf04`
- `test_refactor.py`:
  `127c92734a37b34dc223ffc8e509fe5d3a64277ead2a6f1a5e9c92f63a6f799f`
- `test_formal_graph.py`:
  `60228a325a329cd898262886e74c538a7301da2876544eaf879ee649e3efb3f7`

Publication gate: `tooling_locked`; `paper_ready=false`.

