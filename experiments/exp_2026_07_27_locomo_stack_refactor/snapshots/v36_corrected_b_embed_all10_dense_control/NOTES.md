# v36 — corrected all-10 B_embed and exact dense control

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `1fe232fd6fe2ad5555ca6dc7c971271dd13a80ca`.
Source tree: `5d418e5498cc56af454c0b1d3764761343344672`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

The corrected B_embed run completed from a new absent condition directory:

```text
outputs/locomo_formal/formal_all10_M2_B_embed_top25_1fe232f_qfrozen_run02/
```

The first run01 connection abort remains immutable and was not resumed. A
minimal Reader preflight succeeded outside the restricted network sandbox, so
run02 used the same external network context and completed without a retry or
failed answer.

## Exact command and environment

The run sourced `env_gpt.sh`; secrets are excluded. It used
`EM_GRAPH_EMBED_WAIT=0.05` and `EM_GRAPH_MAX_WORKERS=8`.

```bash
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M2_B_embed_top25_1fe232f_qfrozen_run02 \
  --scope all10 --variant B_embed --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact \
    outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

Resolved models were `gpt-3.5-turbo` for the previously cached conversation
Entity extraction, `text-embedding-3-small` for Memory/query embeddings, and
requested `gpt-3.5-turbo` for answer generation. The provider's actual
per-response answer-model revision was not recorded and is unknown. No judge
model was used. The frozen Reader used one system message, temperature 0,
maximum 32 output tokens, batch size 1, and the unchanged upstream unseeded
Category-5 option ordering.

## Graph extraction and construction

B_embed loads the complete conversation-built Entity–Memory graph even though
its retrieval configuration disables Entity scoring. Each dialog creates one
Memory node from session `date_time`, dialog id, speaker, normalized dialog
text, and optional `blip_caption`. The cached LLM extractor operates only on
normalized conversation text plus caption; speaker Entity nodes are added by
the builder. Normalization/deduplication use the committed extract-v4,
`evidence_time_annotations_v1`, and exact canonical Memory-text protocols.

Across ten conversations the graphs contain 5,882 Memory nodes, 12,808 Entity
nodes, 36,227 Entity–Memory edges, and 11,744 directed NEXT/PREV Memory edges.
Sequence edges follow parsed real `date_time`, with deterministic
session/turn/dialog fallbacks.

Graph construction used conversation fields only. It excluded QA questions,
answers, evidence annotations, categories, judge results, previous
predictions, and question-driven ledgers. The immutable query artifact is used
only at retrieval time and never changes graph nodes or edges.

## Retrieval and answer logic

B_embed intentionally makes the complete graph retrieval-equivalent to A:
Entity weight 0, semantic weight 1, no Entity gate, no sequence expansion,
full-pool signed-cosine ranking, and exactly 25 unique ordered Memory ids. Its
ten Memory embedding indexes are the exact same files used by corrected A.
The shared immutable query artifact has SHA-256
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`,
1,986 ordered QA rows, 1,974 unique questions, 1,536 dimensions, and ordered
QA SHA-256
`21b786753c8e890953c06a6f4738d059504730637b0885a3d47dc4c8ccd5be92`.

Runtime use was 1,986 lookups, 1,986 hits, zero misses, and zero live query
embedding requests. Strict mode did not create or seed the general writable
context cache.

Retrieved Memories enter the unchanged vendored LoCoMo Dialog Reader. The
official prompt, per-row three-decimal token-F1 and `recall_acc`
serialization, Category-5 branch, and official stats aggregation are
unchanged. For analysis, an empty-evidence row contributes zero recall while
remaining in the denominator; raw serialized recall is retained for audit.

## Results and dense-control decision

The run covers 10 conversations, 1,986 QA rows, and 446 Category-5 rows.

| Metric | B_embed |
|---|---:|
| Official overall F1 | 0.420677 (42.0677%) |
| Official Recall@25 | 0.797468 (79.7468%) |
| Local Categories 1–4 F1 | 0.512640 (51.2640%) |
| Local Categories 1–4 Recall@25 | 0.828099 (82.8099%) |

Official category results:

| Category | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| 1 | 282 | 0.386184 | 0.651603 |
| 2 | 321 | 0.418673 | 0.896676 |
| 3 | 96 | 0.163552 | 0.482844 |
| 4 | 841 | 0.630756 | 0.900516 |
| 5 | 446 | 0.103139 | 0.691704 |

Per-conversation results:

| Conversation | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| conv-26 | 199 | 0.365548 | 0.796487 |
| conv-30 | 105 | 0.394952 | 0.798886 |
| conv-41 | 193 | 0.465617 | 0.882990 |
| conv-42 | 260 | 0.384496 | 0.719604 |
| conv-43 | 242 | 0.404649 | 0.807624 |
| conv-44 | 158 | 0.462051 | 0.772519 |
| conv-47 | 190 | 0.456916 | 0.796489 |
| conv-48 | 239 | 0.434460 | 0.784937 |
| conv-49 | 196 | 0.436776 | 0.810908 |
| conv-50 | 204 | 0.412897 | 0.825980 |

The mandatory cross-condition dense-control gate passed:

- A and B_embed use the same query-artifact SHA;
- all 1,986 samples/QA rows occur in the same order;
- every ordered top-25 context-id list is exactly equal;
- mismatches: 0/1,986;
- both runs' no-evidence recall contribution matches official stats.

Answer text is not part of this retrieval-control gate. Despite identical
contexts, 446 predictions and 146 serialized F1 rows differ because the
external Reader and the upstream Category-5 choice ordering are not fully
deterministic. Aggregate B_embed-minus-A F1 is only about -0.0004 percentage
points; no method-effect claim is made from that noise. Recall is exactly
equal, as required.

## Validation, prompt budget, and telemetry

The in-run and independent formal validators both passed. Dense-control report
fingerprint:
`8223b9da8328adcbe35e136733faa95dfdd6506c051242cbad0831bfcac0e8df`.
Post-run checks passed 69/69 tests and all 16 vendored source hashes.
`code/locomo_eval/` has no diff, and
`outputs/em_graph/text_embeddings/text-embedding-3-small.npz` is absent.

The non-data Entity extraction scaffold is 2,410/5,000 characters. No
oversized, ineffective, or harmful runtime prompt component was active.
Warm telemetry records 1,986 answer requests, 2,694,203 input tokens, 16,453
output tokens, 1,986 retrieval observations, 4.374 seconds of retrieval-stage
wall time, and 1,713.170 seconds of answer-stage wall time. This is partial
warm telemetry, not a complete cold/warm cost report.

Artifact SHA-256 values:

- prediction:
  `c71bede8899ff749b34c3c5bc6c203e17db6b45e0cfb46225289eac556e0c33c`;
- stats:
  `90ad221eb79d049815a937c85770cef2101025405e8b60d325fb84fa521aea0e`;
- audit:
  `1646265d6a5f987a22caf17303368c05ec657f8a5cef098c1383333b7d791cbe`;
- validation:
  `622f87f6ed75eb0c40a6c45402415d1ed4f2942b51ceef54c2654d4423814840`;
- run config:
  `24c577e38c21d52e6fd421d6f25652d83e43fc3e49a53051d9d2d076370744da`;
- query usage:
  `d94d1765f07ca06326b5949a3108bf456635210307cfec770b6ff3f717d10d74`;
- warm events:
  `1e817a678ec0ce2ceee23fcde0442087e43d106108ae3f15076f31a29546576e`;
- dense-control report:
  `2e61645efa2c505a656bbc79c5b6897349900820c6fd4ce12db88a379c97a0b2`.

## Compliance, migration, and next action

Mandatory graph constraint: **pass**. Recall uses graph retrieval over
conversation-built nodes/edges; retrieval-time questions/vectors never enter
construction; prompts and extractors are used only for graph density,
retrieval, or answering over retrieved graph evidence.

The migration archive and exact 64-file relative-path manifest are documented
in `CACHE_TRANSFER.md` and `CACHE_TRANSFER_PATHS.txt`. The archive is generated
under `outputs/` and is intentionally not committed.

Publication gate: `continue`, `paper_ready=false`. Per user instruction, pause
after committing/pushing this snapshot. On the migrated machine, the next
formal experiment is corrected all-10 B from a new absent directory with the
same query artifact, followed by validation, snapshot/commit, and corrected
A/B significance. Do not start B before migration.
