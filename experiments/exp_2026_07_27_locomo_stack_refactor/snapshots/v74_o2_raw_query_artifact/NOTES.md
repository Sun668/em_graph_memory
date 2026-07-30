# v74 — O2 raw DRAGON query artifact

Date: 2026-07-29 Asia/Shanghai. Builder source commit:
`03a8a6c`.

The immutable O2 raw query artifact was created from absent artifact/report
paths with the pinned local DRAGON query encoder. The build was offline and
used no provider API.

Artifact:
`outputs/em_graph/query_embeddings/locomo10_047d8e25_dragon_raw_v2.npz`

Report:
`outputs/em_graph/query_embeddings/locomo10_047d8e25_dragon_raw_v2_report.json`

## Identity and coverage

- Artifact schema: `query_embedding_artifact_v2`.
- SHA-256:
  `5a8b96c729d802fbf6c1ef1bb9b568c6f15fc16c1d893b79488442b5183ebf81`.
- Dataset SHA-256:
  `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
- Ordered QA digest:
  `21b786753c8e890953c06a6f4738d059504730637b0885a3d47dc4c8ccd5be92`.
- Coverage: all 1,986 ordered QA rows; 1,974 unique questions.
- Dimension: 768.
- Role: `query`.
- Normalization: `none_float32_v1`.
- Encoder: `facebook/dragon-plus-query-encoder`, revision
  `2d3808c087119b953f8494b7638c216c71712cee`.
- Paired context encoder identity: revision
  `68074e7406bb0061b0d049b58592acafae00e9d4`.
- Runtime: Python 3.9.6, PyTorch 2.0.1, Transformers 4.35.0,
  tokenizers 0.14.1, NumPy 1.26.0, CPU, no CUDA runtime.

Independent loading and exact-dataset validation pass. Vector L2 norms span
`9.938947929177438` to `11.18791605812861`; zero rows are unit normalized.

For diagnosis only, every unique question was matched to the earlier O1 raw
query cache. Because O2 uses its own runtime identity and batch size, no row is
byte-identical; the maximum absolute element difference is
`1.9073486328125e-06`. The old O1 cache is not reused or relabeled. O2 will
build context indexes under the same O2 runtime identity as this artifact.

No graph or Memory index changed: counts remain 70 and 30. No formal O2
condition exists yet. No old artifact was deleted, overwritten, or rebuilt.

Publication gate: `continue`; `paper_ready=false`.

