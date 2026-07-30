# v34 — corrected formal all-10 M1-A with frozen query artifact

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `76fcf5b68998622012371a704c703c3004414224`.
Source tree: `3abb9632f6908899ea489a8a789de687445fb6b5`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This is the corrected pure-Memory baseline after the v28 query-cache
control-validity failure. Bulky generated artifacts remain under:

```text
outputs/locomo_formal/formal_all10_M1_A_top25_76fcf5b_qfrozen_run01/
```

## Exact command and environment

The run sourced `env_gpt.sh`; secrets are excluded. It used
`EM_GRAPH_EMBED_WAIT=0.05` and `EM_GRAPH_MAX_WORKERS=8`, began from an absent
condition directory, and did not resume or overwrite an earlier prediction.

```bash
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M1_A_top25_76fcf5b_qfrozen_run01 \
  --scope all10 --variant A --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact \
    outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

Resolved models were no extraction model, `text-embedding-3-small` for Memory
and query embeddings, and requested `gpt-3.5-turbo` for answer generation.
The provider's per-response actual answer-model revision was not recorded, so
it is unknown. No judge model was used.

The frozen Reader used one system message, temperature 0, maximum 32 output
tokens, batch size 1, and the unchanged upstream unseeded Category-5 option
ordering.

## Graph extraction and construction

M1-A creates one Memory node per dialog. Memory inputs are the session
`date_time`, dialog id, speaker, normalized dialog text, and optional
`blip_caption`. It performs no LLM Entity extraction, SVO extraction,
question-Entity extraction, or post-build Entity densification. Text
normalization and the graph/index identities are the previously committed
`evidence_time_annotations_v1` and
`speaker_normalized_caption_v2_exact` protocols.

Across all ten conversations the retained graph has 5,882 Memory nodes, zero
Entity nodes, zero Entity–Memory edges, and 11,744 directed NEXT/PREV edges.
Memory sequence edges use parsed real `date_time` order with deterministic
session/turn fallback.

Graph construction used conversation fields only. QA questions, answers,
evidence, categories, judge outputs, prior predictions, and question-driven
ledgers were excluded. The query artifact is retrieval-time input and is not
used to construct or alter any node or edge.

## Retrieval and answer logic

Each raw QA question is looked up in one immutable, L2-normalized float32 query
artifact. Its identity is:

- SHA-256:
  `bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`;
- 1,986 ordered QA rows and 1,974 unique questions;
- 1,536 dimensions;
- ordered-QA SHA-256:
  `21b786753c8e890953c06a6f4738d059504730637b0885a3d47dc4c8ccd5be92`.

A performs full-pool dense cosine retrieval over the conversation's Memory
nodes with Entity weight 0, semantic weight 1, no Entity gate, no sequence
expansion, and top-k 25. Signed cosine scores are preserved and dense fill
returns exactly 25 unique ordered dialog ids per QA. Inactive shared defaults
are sequence scale 0.5, Entity relative threshold 0.5, Entity top-k 20,
who-only dampening 0.25, and degree discount enabled.

The ten committed Memory indexes were loaded read-only. Strict formal mode did
not open or seed the general writable context embedding cache. Runtime query
usage was 1,986 lookups, 1,986 hits, zero misses, and zero live embedding
requests.

Retrieved Memories are formatted as the unchanged LoCoMo Dialog Reader
context. The vendored official answer prompt, token-F1, `recall_acc`,
per-row three-decimal serialization, Category-5 branch, and stats aggregation
were used without modification. No LLM-as-Judge was used.

## Formal results

The result covers all 10 conversations, all 1,986 QA rows, and all 446
Category-5 rows.

| Metric | Value |
|---|---:|
| Official overall F1 | 0.420681 (42.0681%) |
| Official Recall@25 | 0.797468 (79.7468%) |
| Local Categories 1–4 F1 | 0.512645 (51.2645%) |
| Local Categories 1–4 Recall@25 | 0.828099 (82.8099%) |

Official category results:

| Category | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| 1 | 282 | 0.381794 | 0.651603 |
| 2 | 321 | 0.414891 | 0.896676 |
| 3 | 96 | 0.183073 | 0.482844 |
| 4 | 841 | 0.631453 | 0.900516 |
| 5 | 446 | 0.103139 | 0.691704 |

Per-conversation results:

| Conversation | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| conv-26 | 199 | 0.367357 | 0.796487 |
| conv-30 | 105 | 0.387971 | 0.798886 |
| conv-41 | 193 | 0.478990 | 0.882990 |
| conv-42 | 260 | 0.383646 | 0.719604 |
| conv-43 | 242 | 0.400876 | 0.807624 |
| conv-44 | 158 | 0.454234 | 0.772519 |
| conv-47 | 190 | 0.463763 | 0.796489 |
| conv-48 | 239 | 0.436276 | 0.784937 |
| conv-49 | 196 | 0.429944 | 0.810908 |
| conv-50 | 204 | 0.411784 | 0.825980 |

Four empty-evidence rows retain raw serialized recall 1 for audit, contribute
zero to recall analysis, and remain in the denominator. The aggregate exactly
matches official `stats.json`.

Recall@25 is exactly unchanged from historical v24 A. Overall F1 differs
because the external Reader is not empirically deterministic even at
temperature 0. This run is the new baseline; no A/B effectiveness conclusion
may compare its answer F1 to historical v25 B. Corrected B must be rerun under
the same artifact and then compared.

## Validation, prompts, and telemetry

The in-run validator and an independent post-run invocation both returned
`pass`. They confirmed exact 10/1,986/446 counts and order, 25 unique valid
contexts per QA, official stats parity, absent-directory start, no resume,
conversation-only graph construction, graph retrieval, the bound query
artifact, and zero runtime query misses/live requests.

The non-data prompt scaffold is 0/5,000 characters. No oversized,
ineffective, or harmful prompt component was active. Warm telemetry records
1,986 answer requests, 2,694,202 input tokens, 16,308 output tokens, 1,986
retrieval observations, 4.989 seconds of retrieval-stage wall time, and
1,745.078 seconds of answer-stage wall time. It is a partial warm result, not
a complete cold/warm cost report.

Post-run verification passed 69/69 tests and all 16 vendored source hashes.
`code/locomo_eval/` has no diff. The general
`outputs/em_graph/text_embeddings/text-embedding-3-small.npz` file remains
absent.

## Artifact identity

- condition fingerprint:
  `efd263c3904669977c43dc154197bb942576378d7c2036fb26731d0d5f11739b`;
- prediction SHA-256:
  `0c843b7f921ceea50c07bc6bb14751446f2066909c807df528ee66ff1aa9579c`;
- stats SHA-256:
  `203f30b12406a9c033308757987003c4ef98ad3588cf1f3aadce1127d361663c`;
- audit SHA-256:
  `7a8b81693e5bdc75bbb084cf1557275b5d339e05529951b6f1a52b59430704a9`;
- validation SHA-256:
  `afb857827498f46c58f0ab316bee43ff1a8e0fb43284014bbea8c9e17b8e5c6f`;
- run-config SHA-256:
  `1057173e4ceb72311d6690bac455ff3fc6abd7b3595bcfcc4dfdf0285498343c`;
- query-usage SHA-256:
  `d94d1765f07ca06326b5949a3108bf456635210307cfec770b6ff3f717d10d74`;
- warm-events SHA-256:
  `bd945ba7174445fe72ac3988ebd9cc5a9123be97faf421dbe072627e68908d40`;
- `formal_graph.py` SHA-256:
  `20eabf21fe2a595de3875290bb22d8c27bfcbd733abf7ec6dec3de90726a10af`;
- `validate_formal_result.py` SHA-256:
  `2554c5d519290e8d9574e38d42935cb7599c3751ec1e1bbb6be96be2e5353e77`.

## Compliance and decision

Mandatory graph constraint: **pass**. The graph is conversation-only; answer
recall traverses the conversation-built Memory graph/index; retrieval-time
query vectors do not enter construction; the Reader receives only the
question and retrieved graph evidence.

Publication gate: `continue`, `paper_ready=false`. The next step is corrected
formal all-10 B_embed from a new absent directory, using the exact same query
artifact. Its 1,986 ordered context-id lists must exactly equal this A result
before the dense control is accepted.
