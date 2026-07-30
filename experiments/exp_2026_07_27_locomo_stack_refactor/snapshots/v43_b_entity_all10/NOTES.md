# v43 — all-10 B_entity component condition

Decision date: 2026-07-28 Asia/Shanghai. Source commit/tree:
`31d8c78dcec13fbf94a5be0e7396a98530f72b7d` /
`30278730659f319b5dba8e3f2135ee347bda3f67`. Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This is the predeclared Entity-only component condition, not an A rerun. It
started from the absent isolated directory
`outputs/locomo_formal/formal_all10_M2_B_entity_top25_31d8c78_qfrozen_run01/`
with `resume=false` and `overwrite=false`.

## Command and resolved settings

```bash
source ./env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05 EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M2_B_entity_top25_31d8c78_qfrozen_run01 \
  --scope all10 --variant B_entity --top-k 25 \
  --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph --output-root outputs/locomo_formal
```

All 10 conversations and 1,986 QA rows were used in dataset order. Graph and
question Entity extraction requested `gpt-3.5-turbo`; the cached Memory index
uses `text-embedding-3-small`; answers requested `gpt-3.5-turbo` (actual
provider revision unknown). Reader settings are one `system` message,
temperature 0, 32 completion tokens, batch 1, with unchanged unseeded upstream
Category-5 ordering. There is no judge and no seed override.

| Dimension / parameter | Side A: B_entity | Side B: complete B | Expected impact |
|---|---|---|---|
| Graph/gate | Same 5,882 Memory, 12,808 Entity, 36,227 Entity–Memory and 11,744 sequence edges; threshold `0.50`, top 20/key, who `0.25`, degree discount | Exactly the same | No construction or candidate-pool confound |
| Fusion | Entity/semantic `1.0/0.0` | Entity/semantic `0.30/0.70` | Isolates removal of semantic score |
| Sequence | Enabled, secondary scale `0.50` | Exactly the same | No sequence confound |
| Top-k/Reader/metric | 25; frozen Reader; official token-F1 and `recall_acc` | Exactly the same | No context budget or evaluation difference |
| Query vectors | Configured artifact remains identity-checked but semantic weight 0 requires zero runtime lookups | B requires all 1,986 lookups | Entity-only avoids semantic-query cost |

Everything except fusion weights and consequent query-vector use is exactly
aligned. The changed retrieval fingerprint invalidates contexts, answers, and
metrics, but not graph, Entity, embedding, or question-Entity caches.

## Graph, recall, and compliance

Each dialog Memory uses only session/date, dialog id, speaker, normalized text,
and optional `blip_caption`. Extract-v4 extracts normalized/deduplicated
Entities from conversation text/captions; speaker Entities are added.
Entity–Memory mention edges and chronological NEXT/PREV edges form the graph.
QA answers, evidence, categories, judge outputs, prior predictions, and
question-driven ledgers are excluded from construction.

The question is used only at retrieval time to obtain cached Entities.
Entity relevance gates and ranks candidates with weight 1.0, dense fill
ensures a complete pool, chronological neighbors expand at scale 0.50, and
exactly 25 unique Memory ids become Reader evidence. Semantic weight 0 means
zero query-vector lookups. Answering and metrics remain owned by frozen
`QARecall`.

## Results

The run completed 10/10 conversations, 1,986/1,986 QA, and 446 Category-5
rows. There is no LLM-as-Judge.

| Metric | B_entity | B | B_entity − B |
|---|---:|---:|---:|
| Official overall F1 | 37.4899% | 42.5680% | -5.0780 pt |
| Official Recall@25 | 67.0208% | 84.4842% | -17.4634 pt |
| Local Categories 1–4 F1 | 44.8409% | 51.9740% | -7.1331 pt |
| Local Categories 1–4 Recall@25 | 65.1320% | 85.0232% | -19.8912 pt |

Category F1/Recall@25: C1 `0.284550/0.406255` (282), C2
`0.410810/0.757012` (321), C3 `0.195365/0.374656` (96), C4
`0.546590/0.724734` (841), C5 `0.121076/0.735426` (446).

Both the in-run and independent validators pass; independent report SHA-256 is
`74b6a5699eea4f02c29582cd74385b7de4ba8572057e644b556bf9512337213f`.
Official aggregation parity, graph constraint, exact top-k contexts, and the
2,410/5,000 prompt budget pass. All 75 tests and 16 vendored hashes pass;
`code/locomo_eval/` is clean. Warm retrieval took 30.374 seconds. Answering
made 1,986 requests, used 2,806,386 input and 15,877 output tokens, and took
2,372.953 seconds. A matched cold/warm cost probe remains pending.

Formal artifact hashes are recorded in `result.json`. Mandatory graph
constraint: **pass**. Interpretation: removing the semantic score causes a
large regression, so semantic relevance is necessary for complete B.
Component-family inference remains descriptive until B_noseq completes and
Holm correction is applied.

Publication gate: `continue`, `paper_ready=false`; commit/push v43, then run
B_noseq from a new absent directory.
