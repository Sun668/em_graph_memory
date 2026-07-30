# v50 — all-10 B_raw_text input ablation

Decision date: 2026-07-28 Asia/Shanghai. Formal source commit:
`ee8255dfffcf537e8272b90603f9403e541d590e`. Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
The frozen `parameters.json` SHA-256 is
`42fb206ccd744ed77417a2ffd510650954c282723cfd1b90bc7f6cc41397e9f2`;
its bound command SHA-256 is
`acdf738d6c1b7dc5e8dd67ec06c282680a676e6f274c7e6d0c1a3099ce8944b3`.

This is the predeclared raw-dialog-text ablation for complete B. It is not a
replacement for corrected B. The formal run started from the absent isolated
directory
`outputs/locomo_formal/formal_all10_M3_B_raw_text_top25_4965acd_qfrozen_run01/`
with `resume=false` and `overwrite=false`.

## Commands and complete configuration

The ten new conversation-only Entity–Memory graphs were built with:

```bash
source ./env_gpt.sh
unset http_proxy https_proxy
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  build-graphs --data-file data/locomo10.json \
  --cache-dir outputs/em_graph --extract-model gpt-3.5-turbo \
  --variants B_raw_text
```

The formal condition used:

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v50_b_raw_text_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M3_B_raw_text_top25_4965acd_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M3_B_raw_text_top25_4965acd_qfrozen_run01 --scope all10 --variant B_raw_text --top-k 25 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

Both paired reports use 10,000 bootstrap resamples and seed `20260727`:
`significance_report.py compare`, first with corrected B as side A and then
with A_raw_text as side A.

All 10 conversations and 1,986 QA rows were retained in immutable order,
including 446 Category-5 rows. There is no category filter or subsampling.
Extraction model is `gpt-3.5-turbo`; embedding model is
`text-embedding-3-small`; Reader model is `gpt-3.5-turbo`; no judge applies.

## Extraction and graph construction

Construction consumes only session anchors, dialog ids, speakers, raw dialog
text, and official `blip_caption`. It disables deterministic relative-time
annotations and enables speaker Entities. Entity extraction is one raw
conversation Memory text at a time with a 2,410-character schema scaffold.
Entity keys are schema-constrained, normalized, merged, deduplicated, and
filtered before linking to Memories.

The ten graphs contain 5,882 Memory nodes, 12,733 Entity nodes, 36,144
Entity–Memory mention edges, and 11,744 NEXT/PREV sequence edges. Of 5,882
Memory texts, 352 differ from the time-annotated profile; all 352 exact
extraction keys were absent before and present after construction. The build
path did not record provider token telemetry for these new extraction calls,
so exact extraction request and token counts are unknown; the number of
newly populated exact keys is 352 and no extraction failure was logged.

No historical cache was deleted or overwritten. Graph files increased from
50 to 60. Memory indexes remained 30 because B_raw_text reloaded, read-only,
the exact ten A_raw_text index identities and SHA-256 files. This made zero
new Memory embedding requests. The accepted A/B graphs, indexes, extraction
caches, query artifact, and formal results remain intact.

QA questions, answers, evidence annotations, categories, judge outputs,
previous predictions, and question-driven ledgers are excluded from graph
construction. Questions and the immutable question-vector artifact are used
only at retrieval time. Mandatory graph constraint: **pass**.

## Retrieval, Reader, and metrics

The complete QA question forms the query. Question Entity extraction is held
in its physically separate retrieval cache. Candidates use Entity/semantic
weights `0.30/0.70`, Entity gate threshold `0.50`, top 20 candidates per
Entity key, who-only dampening `0.25`, degree discount enabled, signed dense
fill, sequence expansion enabled at secondary scale `0.50`, and final top-k
25. `force_full_pool=false`; stable committed ordering breaks ties.

Question vectors come read-only from artifact SHA-256
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`,
with 1,536-dimensional L2 float32 context-role vectors. Runtime recorded 1,997
lookups/hits, zero misses, and zero live query-embedding requests.

Retrieved graph Memories become dated Reader context through the frozen
`QARecall` interface. The frozen Reader uses one `system` message,
temperature 0, 32 completion tokens, and batch size 1. Category-5 keeps the
unchanged upstream unseeded option order. Official per-row token-F1,
`recall_acc`, three-decimal serialization, and category-aware aggregation are
unchanged. There is no LLM-as-Judge.

| Dimension / parameter | Side A: corrected B | Side B: B_raw_text | Expected impact of the difference |
|---|---|---|---|
| Scope | 10 conversations, 1,986 QA, dataset order | Exactly the same | No sampling confound |
| Conversation text | Deterministic relative-time annotations enabled | Raw dialog text; annotations disabled | Isolates time annotation |
| Captions and speaker | Caption and speaker Entity enabled | Exactly the same | No caption/speaker confound |
| Graph schema | Entity–Memory plus sequence | Same schema; 75 fewer Entities and 83 fewer mention edges | Extraction content may change retrieval |
| Memory indexes | Annotated Memory search text | Exact A_raw_text raw-text indexes | Treatment-specific identity; old index remains valid |
| Retrieval | Gate 0.50, 0.30/0.70 fusion, sequence 0.50, top-k 25 | Exactly the same | Graph/text change is the retrieval cause |
| Query/Reader/evaluator | Frozen query SHA, Reader, and official metrics | Exactly the same | No query, generation, or metric confound |

The scope, graph schema, retrieval parameters, question vectors, Reader, and
evaluator are exactly aligned. Memory text, graph/index identities, extracted
Entities, contexts, answers, and treatment metrics intentionally differ.

## Results and paired inference

| Metric | Corrected B | B_raw_text | Difference |
|---|---:|---:|---:|
| Official overall F1 | 42.5680% | 42.8087% | +0.2407 pt |
| Official Recall@25 | 84.4842% | 84.2371% | -0.2472 pt |
| Local Categories 1–4 F1 | 51.9740% | 52.1546% | +0.1806 pt |
| Local Categories 1–4 Recall@25 | 85.0232% | 84.7694% | -0.2538 pt |

For B_raw_text minus B, overall F1 paired-QA 95% CI is
`[-0.005843, 0.011051]`, p=`0.5671`; conversation-cluster CI is
`[-0.007105, 0.011670]`, p=`0.6217`. Recall paired-QA CI is
`[-0.008233, 0.003026]`, p=`0.3828`; cluster CI is
`[-0.010286, 0.003117]`, p=`0.5049`. Thus there is no supported
time-annotation effect on either primary outcome.

Under matched raw text, B_raw_text minus A_raw_text is +0.3508 F1 points and
+4.9522 Recall@25 points. F1 is not significant: paired-QA CI
`[-0.007879, 0.014546]`, p=`0.5481`; cluster CI
`[-0.007002, 0.016541]`, p=`0.6183`. Recall is robust: paired-QA CI
`[0.039231, 0.060106]`, p=`0.0002`; cluster CI
`[0.037648, 0.060594]`, p=`0.0002`. The Categories 1–4 recall gain is
+2.6201 points and is also nonzero under both estimators.

These are predeclared pairwise results. Raw-text family Holm correction is
still pending, so the snapshot does not yet make a family-wise claim.

## Validation, prompt budget, and cost

Both in-run and independent validators pass 10/1,986/446, exact top-k context
completeness, official aggregation, graph audit, and query identity. The
independent report SHA-256 is
`23beaed7e29abe656147c5968da7cb55d69a6648859ff2ba8fcf0248ea014af1`.
The suite passes 76/76 tests; all 16 vendored hashes pass; frozen
`code/locomo_eval/` is clean.

The 2,410/5,000-character extraction scaffold passes. No oversized or known
harmful prompt component was active. Warm retrieval took 31.085 seconds.
Answer generation made 1,986 requests, used 2,713,456 input and 16,321 output
tokens, and took 3,075.214 seconds. A complete cold/warm cost report remains
pending because the build did not instrument provider extraction usage.

Publication gate: `continue`, `paper_ready=false`. Freeze raw-text family
Holm inference, then commit and push v50 before starting B_no_speaker.
