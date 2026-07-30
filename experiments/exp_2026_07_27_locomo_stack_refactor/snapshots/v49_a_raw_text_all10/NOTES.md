# v49 — all-10 A_raw_text input ablation

Decision date: 2026-07-28 Asia/Shanghai. Source commit/tree:
`8ff50fb974bca83292ab019556a42f62a4e5ea38` /
`0786d4adbe793ff950a4ca8913235316ce897b04`. Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
The frozen parameter snapshot is `parameters.json`, SHA-256
`35991406bcc043f0e97126be02a8ec8bb0b517362e08f244a64ef182456fded9`;
its bound command SHA-256 is
`2edd9c30d014be5512b4e85fd0868721fa217fe3ddf6596028b6e00976577e07`.

This is the predeclared raw-dialog-text ablation for A, not a replacement for
the accepted corrected A result. It started from the absent isolated directory
`outputs/locomo_formal/formal_all10_M3_A_raw_text_top25_57a5f28_qfrozen_run01/`
with `resume=false` and `overwrite=false`.

## Exact commands and attempts

The new conversation-only Memory graphs were built with:

```bash
source ./env_gpt.sh
unset http_proxy https_proxy
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  build-graphs --data-file data/locomo10.json \
  --cache-dir outputs/em_graph --extract-model gpt-3.5-turbo \
  --variants A_raw_text
```

The ten identity-bound Memory indexes were then prebuilt with
`text-embedding-3-small`. The first sandboxed attempt failed on DNS before
creating any index or making a successful request; its diagnostic report is
`outputs/em_graph/a_raw_text_index_build_report_sandbox_abort.json`. The
authorized retry completed all ten indexes and wrote
`outputs/em_graph/a_raw_text_index_build_report.json`.

The formal condition used the parameter-bound command:

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v49_a_raw_text_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M3_A_raw_text_top25_57a5f28_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M3_A_raw_text_top25_57a5f28_qfrozen_run01 --scope all10 --variant A_raw_text --top-k 25 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

The owning sources are `run.py`, `formal_graph.py`, and the active
`code/em_graph/{build,recall,cache}/` implementation at the source commit
above. The frozen `code/locomo_eval/` package owns Reader generation and all
official metric behavior and was not modified.

## Complete configuration and graph logic

All 10 conversations and all 1,986 QA rows were used in immutable dataset
order, including 446 Category-5 rows. There was no category filter, sampling,
or random-seed override. Conversation construction consumed session anchors,
dialog ids, speakers, raw dialog text, and official `blip_caption`. The sole
intended change from corrected A is `use_time_annotations=true` to `false`;
therefore relative-time phrases remain in their raw utterance form.

The graph contains 5,882 Memory nodes, zero Entity nodes, zero Entity–Memory
edges, and 11,744 stored chronological NEXT/PREV edges. `gpt-3.5-turbo`
extraction is inactive because this condition is memory-only. There is no
normalization-driven Entity generation, merge, deduplication, or filtering.
The Entity prompt scaffold is therefore 0 characters.

Memory search text is speaker plus raw dialog text and caption when present.
The ten new indexes contain 5,882 finite L2-normalized 1,536-dimensional
vectors. Their build used 591 embedding requests and 210,987 input tokens,
below the frozen limits of 700 requests and 500,000 tokens. An independent
reload audit matched every Memory id and text digest.

Old caches were not deleted or overwritten. The graph count remained 50; the
Memory-index count increased from 20 to 30. The build report explicitly records
`old_artifacts_deleted=false`, `old_graphs_preserved=true`, and
`old_indexes_preserved=true`. The raw-text profile has new cache identities
because its Memory text differs; the accepted A caches and result remain valid.

## Recall, Reader, evaluator, and behavioral comparison

The complete QA question forms the query. Retrieval is full-pool signed cosine
over Memory vectors with Entity/semantic weights `0.0/1.0`, no gate, no
sequence expansion, and exact top-k 25. `force_full_pool=true`. The configured
sequence scale `0.50`, Entity threshold `0.50`, Entity top 20/key, who-only
dampening `0.25`, and degree discount are inactive in this condition.

Question vectors come read-only from artifact SHA-256
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`,
using `text-embedding-3-small`, context role, L2 float32 normalization, and
1,536 dimensions. Runtime recorded 1,986 required lookups, 1,986 hits, zero
misses, and zero live query-embedding requests.

The frozen Reader uses requested model `gpt-3.5-turbo`, one `system` message,
temperature 0, 32 completion tokens, and batch size 1. Category-5 retains the
unchanged unseeded upstream option order. Official category-aware per-row
token-F1, `recall_acc`, three-decimal serialization, and aggregation are owned
by the frozen package. There is no LLM-as-Judge.

| Dimension / parameter | Side A: corrected A exact behavior | Side B: A_raw_text exact behavior | Expected impact of the difference |
|---|---|---|---|
| Scope and order | All 10 conversations, 1,986 QA, dataset order | Exactly the same | No sampling or order confound |
| Conversation fields | Session/date, dialog id, speaker, time-annotated dialog text, and caption | Same fields, but raw dialog text without deterministic time annotations | Isolates time annotation in Memory evidence |
| Graph schema | Memory-only; 5,882 Memories, no Entities/mention edges, 11,744 stored sequence edges | Exactly the same counts and schema under a new graph identity | No graph-size or Entity confound |
| Memory embeddings | `text-embedding-3-small` over speaker + annotated text + caption | New indexes over speaker + raw text + caption | Time-text change invalidates only the treatment graph/index identity |
| Retrieval | Full-pool signed cosine, semantic weight 1.0, no sequence, top-k 25 | Exactly the same | Only changed Memory text/vectors can change contexts |
| Query artifact | SHA `bef99a…6f9f` | Exactly the same; 1,986 hits, zero misses/live calls | No query-vector confound |
| Reader and metrics | System role, temperature 0, 32 tokens, batch 1; frozen official F1/recall | Exactly the same | Context/text changes propagate to answers and metrics |

Scope, graph schema, query artifact, retrieval formula, cutoff, Reader, and
evaluator are exactly aligned. The Memory text, graph/index identities,
retrieved contexts, answers, and treatment metrics intentionally differ.
Nothing in this change invalidates corrected A, the shared question artifact,
or unrelated prior conditions.

## Results

The run completed 10/10 conversations, 1,986/1,986 QA, and all 446 Category-5
rows.

| Metric | Corrected A | A_raw_text | A_raw_text − A |
|---|---:|---:|---:|
| Official overall F1 | 42.0681% | 42.4579% | +0.3898 pt |
| Official Recall@25 | 79.7468% | 79.2849% | -0.4619 pt |
| Local Categories 1–4 F1 | 51.2645% | 51.5074% | +0.2429 pt |
| Local Categories 1–4 Recall@25 | 82.8099% | 82.1492% | -0.6606 pt |

Category F1/Recall@25 for `A_raw_text`: C1 `0.382152/0.648028` (282),
C2 `0.429364/0.872274` (321), C3 `0.168365/0.479375` (96), C4
`0.631936/0.899327` (841), and C5 `0.112108/0.693946` (446).

The direction is mixed: deterministic time annotations improve evidence
recall in this A comparison, but raw text produces slightly higher answer F1.
This result is descriptive. The frozen plan reserves paired-QA and
conversation-cluster inference for the complete raw-text input family, after
the matched `B_raw_text` condition is available.

## Validation, graph audit, prompt budget, and cost

Both the in-run and independent validators pass. The independent report
SHA-256 is
`4185e2cf36a409babffacdd38c6870eaed95a4cea7edb370e6d0d54686d725ed`.
Official aggregation parity, exact context completeness, and query-artifact
identity pass. The full suite passes 76/76; all 16 vendored hashes pass;
`code/locomo_eval/` is clean.

Graph construction uses conversation data only. QA questions, answers,
evidence, categories, judge output, previous predictions, and
question-driven ledgers are excluded. Questions and immutable query vectors
are used only at retrieval time; answers use graph retrieval over
conversation-built Memories. Mandatory graph constraint: **pass**.

The 0/5,000-character prompt budget passes. No oversized, ineffective, or
known harmful prompt component was active. Warm retrieval took 4.830 seconds.
Answer generation made 1,986 requests, used 2,656,804 input and 16,217 output
tokens, and took 3,058.533 seconds. The separate cold index build telemetry is
reported above; the matched final cold/warm cost report remains pending.

Publication gate: `continue`, `paper_ready=false`. Freeze, commit, and push
v49 before starting the matched `B_raw_text` condition.
