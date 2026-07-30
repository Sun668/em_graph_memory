# v47 — all-10 A_no_caption input ablation

Decision date: 2026-07-28 Asia/Shanghai. Source commit/tree:
`8fa182093e3f0a55768a853791b52e0df38ad845` /
`c640ea39ccaa9b05807573eac2f3f4cab8d97487`. Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This is the predeclared caption-input ablation for A, not a rerun of the
existing A result. It started from the absent isolated directory
`outputs/locomo_formal/formal_all10_M3_A_no_caption_top25_8fa1820_qfrozen_run01/`
with `resume=false` and `overwrite=false`.

## Attempts and exact commands

The first invocation failed closed before creating the formal directory
because the new graph identity did not exist. The required conversation-only
memory graphs were then built:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/run.py build-graphs \
  --data-file data/locomo10.json --cache-dir outputs/em_graph \
  --extract-model gpt-3.5-turbo --variants A_no_caption
```

A second invocation attempted the new Memory embedding indexes, but ten
connection retries failed because lowercase `http_proxy` / `https_proxy`
from `env_gpt.sh` pointed to an unavailable proxy. It also stopped before the
formal directory or any prediction was created. A direct
`text-embedding-3-small` preflight succeeded after unsetting only those two
proxy variables. The final run used the same still-unused run id:

```bash
source ./env_gpt.sh
unset http_proxy https_proxy
export EM_GRAPH_EMBED_WAIT=0.05 EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M3_A_no_caption_top25_8fa1820_qfrozen_run01 \
  --scope all10 --variant A_no_caption --top-k 25 \
  --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph --output-root outputs/locomo_formal
```

The final run config independently proves the directory did not exist at
start, had no entries or prediction file, and did not resume or overwrite.

## Complete configuration and behavioral comparison

All 10 conversations and 1,986 QA rows were used in dataset order. The
memory-only graph has 5,882 Memory nodes, zero Entity nodes, zero
Entity–Memory edges, and 11,744 stored chronological NEXT/PREV edges.
Dialog normalization is `evidence_time_annotations_v1`. Memory search text is
speaker plus normalized dialog text, with no `blip_caption`. The embedding
model is `text-embedding-3-small`; query vectors come exclusively from the
immutable artifact SHA-256 `bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.

Recall uses signed cosine over the full Memory pool with Entity/semantic
weights `0.0/1.0`, no gate, no sequence expansion, and exact top-k 25.
The configured sequence scale `0.50`, threshold `0.50`, top 20/key,
who-only dampening `0.25`, and degree discount are inactive for this
memory-only full-pool condition. The speaker-Entity flag is also ineffective
because no Entity nodes are constructed.

The frozen Reader uses one `system` message, temperature 0, 32 completion
tokens, batch size 1, requested model `gpt-3.5-turbo`, and unchanged unseeded
upstream Category-5 option order. The provider's actual versioned model name
is unknown. Official token-F1 and `recall_acc` are serialized per row and
aggregated by the frozen package. There is no judge and no random-seed
override for generation.

| Dimension / parameter | Side A: exact behavior | Side B: A_no_caption exact behavior | Expected impact of the difference |
|---|---|---|---|
| Conversation fields | Session/date, dialog id, speaker, normalized dialog text, and `blip_caption` when present | Same except `blip_caption` is ignored | Isolates caption information in Memory text and vectors |
| Graph | Memory-only, 5,882 Memory, no Entity/mention edges, 11,744 stored sequence edges | Exactly the same structure and counts | No graph-size or Entity confound |
| Memory embeddings | `text-embedding-3-small` over speaker + normalized text + caption | New identity-bound indexes over speaker + normalized text only | Caption removal invalidates Memory embedding indexes |
| Retrieval | Full-pool signed cosine, semantic weight 1.0, no sequence, top-k 25 | Exactly the same | Only changed Memory vectors can change contexts |
| Query artifact | SHA `bef99a…6f9f`, L2 float32, 1,986 required lookups | Exactly the same; 1,986 hits, zero misses/live requests | No query-vector confound |
| Reader and metrics | System role, temperature 0, 32 tokens, batch 1; frozen official QA/F1/recall | Exactly the same | Context changes propagate to answers and metrics |

The graph schema, dialog ids, chronological order, query artifact, retrieval
formula, top-k, Reader, and evaluator are exactly aligned. The Memory text and
therefore the Memory embedding indexes are intentionally different. This
invalidates retrieved contexts, answers, and metrics for the ablation, but
does not invalidate A's graph, vectors, answers, metrics, or the shared query
artifact. The two conditions are controlled apart from caption inclusion.

## Results

The run completed 10/10 conversations, 1,986/1,986 QA, and all 446
Category-5 rows. There is no LLM-as-Judge.

| Metric | A | A_no_caption | A_no_caption − A |
|---|---:|---:|---:|
| Official overall F1 | 42.0681% | 41.6027% | -0.4654 pt |
| Official Recall@25 | 79.7468% | 79.5545% | -0.1923 pt |
| Local Categories 1–4 F1 | 51.2645% | 50.2097% | -1.0547 pt |
| Local Categories 1–4 Recall@25 | 82.8099% | 82.7891% | -0.0208 pt |

Category F1/Recall@25 for `A_no_caption`: C1 `0.394606/0.653713` (282),
C2 `0.395053/0.893564` (321), C3 `0.199823/0.487188` (96), C4
`0.613503/0.900120` (841), and C5 `0.118834/0.683857` (446).
The aggregate result is descriptive; no caption-family confidence interval
has yet been computed.

## Validation, graph audit, prompt budget, and cost

Both the in-run and independent validators pass. The independent report
SHA-256 is
`2344d6a80570cbfe689ab9821627c6334b0016a9dcc222fa6b43fb921dfd3dc7`.
Official aggregation parity, graph constraint, exact top-k context
completeness, and the 0/5,000-character Entity prompt budget pass. The full
suite passes 76/76; all 16 vendored hashes pass; `code/locomo_eval/` is clean.

Graph construction uses conversation fields only. Although the generic audit
enumerates `blip_caption` among the allowed conversation fields, the resolved
profile has `use_caption=false`, so captions are not consumed. QA questions,
answers, evidence, categories, judge outputs, prior predictions, and
question-driven ledgers are excluded from graph construction. Questions and
the immutable vectors are used only at retrieval time, and answer recall is
over conversation-built Memory nodes.

Warm retrieval took 6.614 seconds. Answer generation made 1,986 requests,
used 2,539,302 input and 16,083 output tokens, and took 2,112.700 seconds.
The prerequisite cold no-caption index construction completed, but its
request/token/wall telemetry is not represented by the warm formal artifact;
the matched cold/warm cost phase remains pending. No oversized, ineffective,
or harmful prompt component was active.

Mandatory graph constraint: **pass**. Interpretation: captions provide a
small positive aggregate contribution to A, especially on the local
Categories 1–4 F1 diagnostic, while the overall Recall@25 change is small.
This is not yet a general caption claim for B.

Publication gate: `continue`, `paper_ready=false`. Commit/push v47, then run
the predeclared `B_no_caption` condition from a new absent output directory.
