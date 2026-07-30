# v30 — rebuilt all-10 immutable query embedding artifact

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `ae12238`.

This snapshot records the clean rebuild and independent validation of the
query-vector artifact required by the v29 formal gate. It is a retrieval-input
build milestone, not a metric result.

## Destructive target and clean start

Before the build, the exact invalid cache was rechecked:

```text
outputs/em_graph/text_embeddings/text-embedding-3-small.npz
size: 34,153,773 bytes
SHA-256: 98767be5304a9acdf16295ceb4b3b73c52cc2c0eedba4e728fe780372a077cd9
```

Only that file was deleted. Graphs, Entity caches, question-Entity caches, and
all Memory embedding indexes were retained. Both new artifact/report paths
were confirmed absent before execution. No cache schema was silently skipped.

## Exact command

```text
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/prepare_query_embeddings.py --data-file data/locomo10.json --embedding-model text-embedding-3-small --role context --output outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --report outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1_report.json
```

The build had zero old-vector hits and embedded all 1,974 unique questions
from scratch in 198 successful requests.

## Artifact identity and validation

- Dataset SHA-256:
  `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`
- Model: `text-embedding-3-small`
- Role: `context`
- Normalization: `l2_float32_v1`
- Ordered QA coverage: `1,986/1,986`
- Unique question vectors: `1,974`
- Dimension: `1,536`
- Ordered-QA digest:
  `21b786753c8e890953c06a6f4738d059504730637b0885a3d47dc4c8ccd5be92`
- Artifact SHA-256:
  `bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`
- Artifact size: `10,212,440` bytes
- Build report SHA-256:
  `dee4b5695c1c9f1f13d220867235195e471a72473ecf03d02d5b1ecf968d3224`
- Embedding requests: `198`
- Provider input tokens: `23,936`

An independent reload checked the artifact schema, full dataset/model/role
identity, ordered sample/QA/question digests, matrix shape, finite values, and
L2 norms. Norms range from `0.9999998838` to `1.0000001180`.

The complete binary artifact remains under `outputs/` and is not committed.
Its content hash and compact build report identity are committed here.

## Compliance and decision

- Mandatory graph constraint: pass. QA questions are used only to build a
  retrieval-time query-vector artifact and are never graph-construction
  inputs.
- Graph construction inputs and artifacts: unchanged.
- Frozen evaluator: unchanged.
- Prompt budget: no prompt scaffold is introduced by this embedding build.
- Oversized, ineffective, or harmful prompts: not applicable.
- Answer generation and judging: not run.
- Formal metric claim: none.

Publication gate: `continue`, `paper_ready=false`. The next step is a
retrieval-only corrected A/B_embed all-10 exact-equality check using this same
artifact SHA, before any paid answer-generation rerun.
