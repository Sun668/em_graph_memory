# v48 — all-10 B_no_caption input ablation

Decision date: 2026-07-28 Asia/Shanghai. Source commit/tree:
`4b1ff4160842be70daf284933ad652aff6f6a86f` /
`0903631c57cb9f3967ebf9024ca53f9514da3394`. Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This is the predeclared caption-input ablation for B, not a rerun of A or B.
It started from the absent isolated directory
`outputs/locomo_formal/formal_all10_M3_B_no_caption_top25_4b1ff41_qfrozen_run01/`
with `resume=false` and `overwrite=false`.

## Exact commands and source

The no-caption conversation graphs were built with:

```bash
source ./env_gpt.sh
unset http_proxy https_proxy
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  build-graphs --data-file data/locomo10.json \
  --cache-dir outputs/em_graph --extract-model gpt-3.5-turbo \
  --variants B_no_caption
```

The formal condition then ran with:

```bash
source ./env_gpt.sh
unset http_proxy https_proxy
export EM_GRAPH_EMBED_WAIT=0.05 EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M3_B_no_caption_top25_4b1ff41_qfrozen_run01 \
  --scope all10 --variant B_no_caption --top-k 25 \
  --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph --output-root outputs/locomo_formal
```

The owning experiment sources are `run.py`, `formal_graph.py`, and the active
`code/em_graph/{build,recall,cache}/` implementation at the source commit
above. The frozen `code/locomo_eval/` package owns Reader generation and all
official metric behavior and was not modified. The final run config proves
that the output directory did not exist at start, contained no entries or
prediction, and did not resume or overwrite.

## Complete configuration and graph extraction

All 10 conversations and 1,986 QA rows were used in dataset order; no category
filter or random seed was applied. The sample ids are `conv-26`, `conv-30`,
`conv-41`, `conv-42`, `conv-43`, `conv-44`, `conv-47`, `conv-48`, `conv-49`,
and `conv-50`.

Dialog normalization is `evidence_time_annotations_v1`. Each Memory uses its
session anchor, dialog id, speaker, and normalized dialog text; the resolved
profile has `use_caption=false`, so `blip_caption` is ignored. The
`gpt-3.5-turbo` extraction prompt operates only on normalized conversation
text and emits schema-constrained Entities. The build normalizes, merges,
deduplicates, and filters extracted Entity keys before linking them to
Memories. The fixed non-data extraction scaffold is 2,410 characters,
temperature/token/retry details are those frozen in the source commit, and
the provider's actual versioned model name is unknown.

The resulting bipartite graph contains 5,882 Memory nodes, 12,031 Entity
nodes, 34,416 Entity–Memory edges, and 11,744 stored chronological
NEXT/PREV edges. Graph construction was complete for all 10 conversations.
The exact no-caption Memory embedding indexes are shared with `A_no_caption`
because both profiles produce identical Memory text; B_no_caption adds Entity
nodes, mention edges, gating, fusion, and sequence retrieval over those same
Memory vectors.

## Recall, Reader, and metric logic

The question forms the retrieval query. Warm cached question-Entity
extraction gates the candidate pool at minimum Entity relevance `0.50` with
top 20 candidates per Entity key, who-only dampening `0.25`, and degree
discount enabled. Entity and signed-cosine semantic scores are fused at
`0.30/0.70`, dense semantic fill is enabled, chronological sequence expansion
is enabled at secondary scale `0.50`, and the final cutoff is exactly 25.
Tie-breaking and fallbacks are the committed
`signed_cosine_gated_dense_fill_topk_v2` implementation.

Memory vectors and query vectors use `text-embedding-3-small`. Query vectors
come exclusively from the immutable artifact SHA-256
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.
The formal run recorded 1,986 required queries, 1,996 lookups/hits, zero
misses, and zero live query-embedding calls. Cache identities bind dataset,
normalized Memory text/profile, model, and implementation. Caption changes
invalidate graph and Memory embedding identities, but not the question-vector
artifact.

Retrieved conversation-built Memory evidence is passed to the frozen Reader:
one `system` message, temperature 0, 32 completion tokens, batch size 1, and
requested model `gpt-3.5-turbo`. Category-5 retains the unchanged unseeded
upstream option order. Official per-QA token-F1 and `recall_acc`, rounding,
serialization, category branches, and aggregate denominators are owned by
the frozen package. There is no LLM-as-Judge in this LoCoMo run.

## Behavioral comparison

| Dimension / parameter | Side A: complete B exact behavior | Side B: B_no_caption exact behavior | Expected impact of the difference |
|---|---|---|---|
| Scope and order | All 10 conversations, 1,986 QA, dataset order | Exactly the same | No sampling or order confound |
| Conversation fields | Time anchor, dialog id, speaker, normalized dialog text, and caption when present | Same except caption is ignored | Isolates caption input |
| Graph schema | 5,882 Memories, Entities, mention edges, stored sequence edges | Same node/edge types and retrieval-facing schema; rebuilt Entities and links from no-caption input | Graph counts/content and gated pools may change |
| Memory embeddings | `text-embedding-3-small` over speaker + normalized text + caption | Identity-bound indexes over speaker + normalized text only | Caption removal invalidates B Memory vectors |
| Entity extraction | `gpt-3.5-turbo` over caption-inclusive conversation text | Same extractor/settings over no-caption text | Entity nodes and links may change |
| Retrieval | Gate 0.50, top 20/key, weights 0.30/0.70, sequence 0.50, top-k 25 | Exactly the same | Controlled retrieval parameters |
| Query vectors | Immutable artifact SHA `bef99a…6f9f` | Exactly the same; zero misses/live calls | No question-vector confound |
| Reader and metrics | System role, temperature 0, 32 tokens, batch 1; frozen official F1/recall | Exactly the same | Changed graph contexts propagate to answers and metrics |

Scope, query artifact, retrieval hyperparameters, Reader, and evaluator are
exactly aligned. Graph schema is functionally aligned, while graph contents,
Entity extraction inputs, and Memory vectors intentionally differ. On this
dataset there are no captions on rows where an absent caption could create a
separate missing-value behavior; the effective difference is whether present
caption text is included. The change invalidates B's graph/Memory-vector
cache identities and requires new contexts, answers, and metrics. It does not
invalidate the shared query artifact, the existing B result, or the
`A_no_caption` Memory vectors. No prior metric is overwritten.

## Results

The run completed 10/10 conversations, 1,986/1,986 QA, and all 446
Category-5 rows.

| Metric | Complete B | B_no_caption | B_no_caption − B |
|---|---:|---:|---:|
| Official overall F1 | 42.5680% | 41.7394% | -0.8285 pt |
| Official Recall@25 | 84.4842% | 84.3040% | -0.1803 pt |
| Local Categories 1–4 F1 | 51.9740% | 50.6458% | -1.3282 pt |
| Local Categories 1–4 Recall@25 | 85.0232% | 85.0180% | -0.0052 pt |

Category F1/Recall@25 for `B_no_caption`: C1 `0.401936/0.668372` (282),
C2 `0.384003/0.907579` (321), C3 `0.211885/0.529115` (96), C4
`0.621870/0.925883` (841), and C5 `0.109865/0.818386` (446).

Relative to `A_no_caption`, B_no_caption changes official F1 by `+0.1367`,
Recall@25 by `+4.7495`, local Categories 1–4 F1 by `+0.4360`, and local
Categories 1–4 Recall@25 by `+2.2289` points. Full B-minus-A is `+0.4998`
F1 and `+4.7374` Recall@25 points. Thus removing captions preserves almost
all of B's descriptive retrieval gain over A, while reducing its answer-F1
gain. Caption-family significance has not been computed, so these are
descriptive comparisons only.

## Validation, graph audit, prompt budget, and cost

Both the in-run and independent validators pass. The independent report
SHA-256 is
`280cf51faae2f05ad89ee6a788a86635b89b94509b301654df1a5069aa49b6f6`.
Official aggregation parity, exact top-k context completeness, and exact query
artifact use pass. The full suite passes 76/76; all 16 vendored hashes pass;
`code/locomo_eval/` has no staged, unstaged, or untracked changes.

Graph construction uses conversation data only. Although the generic audit
enumerates `blip_caption` among allowed fields, the resolved
`use_caption=false` profile means it is not consumed. QA questions, answers,
evidence, categories, judge output, previous predictions, and
question-driven ledgers are excluded. Questions are used only at retrieval;
answer recall traverses conversation-built Memory/Entity nodes and edges.
Mandatory graph constraint: **pass**.

The 2,410/5,000-character prompt scaffold budget passes. No oversized,
ineffective, or known harmful prompt component was active. Warm graph
construction, Entity extraction, Memory embedding, and question-Entity
extraction made zero external requests. Retrieval took 23.120 seconds.
Answer generation made 1,986 requests, used 2,578,136 input and 16,098 output
tokens, and took 2,363.064 seconds. The prerequisite cold graph build used
the external extractor, but its request/token/wall telemetry is not recorded
in the warm formal artifact; complete cold/warm cost remains pending.

Publication gate: `continue`, `paper_ready=false`. Per user instruction,
execution is paused after committing and pushing this v48 snapshot. No next
condition is started.
