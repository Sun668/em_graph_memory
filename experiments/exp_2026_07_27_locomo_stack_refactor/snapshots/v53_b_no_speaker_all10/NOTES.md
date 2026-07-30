# v53 — formal all-10 B_no_speaker speaker-Entity ablation

Decision date: 2026-07-29 Asia/Shanghai.
Formal source commit: `52a8091b8dba28c1a1d9050b7517dfedd13a6a6a`.
Formal source tree: `47e9e55e6093d566675c98a11f79ae14992a5612`.
Frozen parameter SHA-256:
`b07aad44124ba15c3477d3899322965b4be725062791253963751526f248aa7b`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

## Outcome

The all-10 `B_no_speaker` condition completed from the absent isolated
directory:

```text
outputs/locomo_formal/formal_all10_M3_B_no_speaker_top25_6bdcaf0_qfrozen_run01/
```

It changes exactly one graph-construction setting relative to complete B:
`add_speaker_as_entity=true` becomes `false`. Caption and time annotation
remain enabled, and retrieval remains Entity/semantic `0.30/0.70`, sequence
expansion scale `0.50`, Entity threshold `0.50`, top 20 Memories per query
Entity, who-only dampening `0.25`, degree discount enabled, and top-k 25.

Across 10 conversations, 1,986 QA rows, and 446 Category-5 rows:

- official serialized-row mean F1: `42.3265%`;
- official evidence `recall_acc`: `83.0021%`;
- local Categories 1–4 subset F1: `51.8574%`;
- local Categories 1–4 subset Recall@25: `83.0144%`.

Relative to complete B, removing speaker Entities changes overall F1 by
`-0.2415` percentage points and recall by `-1.4822` points. The F1 difference
is non-significant under paired-QA and conversation-cluster bootstrap. The
recall loss is significant under both estimators: paired 95% CI
`[-2.3098, -0.6733]` points, p=`0.0006`; cluster 95% CI
`[-2.8158, -0.2410]` points, p=`0.0194`.

Relative to corrected A, B_no_speaker has `+0.2584` F1 points,
non-significant under both estimators, and `+3.2552` recall points,
significant under paired and cluster bootstrap. Speaker injection therefore
accounts for a significant portion of complete B's retrieval advantage, but
the remaining conversation-extracted Entity graph still retains a significant
overall recall advantage over dense Memory retrieval.

## Exact commands

Graph construction:

```bash
source ./env_gpt.sh
unset http_proxy https_proxy
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  build-graphs \
  --data-file data/locomo10.json \
  --cache-dir outputs/em_graph \
  --extract-model gpt-3.5-turbo \
  --variants B_no_speaker
```

Formal condition:

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v53_b_no_speaker_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M3_B_no_speaker_top25_6bdcaf0_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M3_B_no_speaker_top25_6bdcaf0_qfrozen_run01 --scope all10 --variant B_no_speaker --top-k 25 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

The two comparisons use
`significance_report.py compare`, 10,000 resamples, and seed `20260727`.
Corrected A additionally uses the committed v39 relocation manifest. Reports:

```text
outputs/locomo_analysis/b_no_speaker_vs_b_52a8091_seed20260727_10000.json
outputs/locomo_analysis/b_no_speaker_vs_a_52a8091_seed20260727_10000.json
```

## Complete behavior comparison

| Dimension / parameter | Side A: exact behavior | Side B: exact behavior | Expected impact of the difference |
|---|---|---|---|
| Dataset / scope | Complete B; LoCoMo-10 SHA `047d8e…d74`; all 10 conversations; 1,986 QA; 446 Category 5 | B_no_speaker; exactly the same data, order, and denominators | No sampling or metric-denominator effect |
| Conversation inputs | Date/time, dialog ids, speakers, time-annotated text, captions; QA/judge fields excluded | Exactly the same allowed conversation fields and exclusions | No graph-compliance difference |
| Memory nodes | 5,882 | 5,882 with identical ids and search text | No Memory-content effect |
| Entity nodes | 12,808, including deterministic speaker-name injection | 12,808 extracted Entity keys; deterministic speaker injection disabled | The node count happens to remain equal because names already occur in extracted keys; membership/link incidence differs |
| Entity–Memory edges | 36,227 | 30,348 | B_no_speaker loses 5,879 speaker-incidence links, reducing person-query connectivity |
| Sequence edges | 11,744 stored NEXT/PREV edges | Exactly 11,744 | No chronology-storage effect |
| Conversation extractor | Cached extract-v4, `gpt-3.5-turbo`, normalized/merged/deduplicated | Identical cache keys and extractor; 5,882/5,882 cache hits and zero external extraction requests | No model-generation confound |
| Memory embedding | `text-embedding-3-small`, canonical caption/time-annotated Memory text | Exact same ten canonical indexes reused read-only | No Memory-vector confound |
| Query artifact | SHA `bef99a…986f9f`, 1,986 ordered QA, 1,536 dimensions, read-only | Exact same artifact; 1,997 hits, 0 misses, 0 live requests | No semantic query-vector confound |
| Retrieval | Entity/semantic `0.30/0.70`; gated dense fill; threshold `0.50`; top 20/key; who damp `0.25`; degree discount | Exactly the same retrieval parameters | Differences arise from speaker graph links only |
| Sequence / top-k | Expansion enabled, secondary scale `0.50`, top-k 25 | Exactly the same | No context-budget effect |
| Reader | Frozen `gpt-3.5-turbo`, system role, temperature 0, 32 tokens, batch 1, unseeded upstream Category-5 option order | Exactly the same | No intended Reader-protocol effect; backend variance remains |
| Metric / inference | Frozen official F1 and `recall_acc`; 10,000 paired/cluster resamples, seed `20260727` | Joint comparison | Quantifies uncertainty without recalculating official row metrics |
| Output isolation | Existing validated complete-B condition | New absent B_no_speaker directory; no resume/overwrite | No cross-condition contamination |

Exactly aligned: dataset and QA order, allowed graph inputs, Memory nodes and
text, Memory indexes, immutable question vectors, extraction protocol,
retrieval parameters, top-k, Reader, evaluator, and aggregation. Functionally
similar: both use conversation-extracted Entity–Memory retrieval. Intentionally
different: deterministic speaker Entity–Memory incidence. Nothing in this
condition invalidates complete B, corrected A, old graphs, old indexes,
query vectors, answers, or prior metrics.

## Cache and construction audit

No old cache or result was deleted, overwritten, or rewritten.

- graph files increased from `60` to `70`;
- Memory embedding indexes remained exactly `30`;
- the ten new graph profiles are caption-on, time-annotation-on,
  speaker-Entity-off;
- all 5,882 conversation extraction lookups reused existing cache entries;
- the ten complete-B/A Memory indexes were reused exactly and read-only;
- no external Entity extraction request and no Memory embedding request was
  made;
- the shared extraction cache retained 7,450 entries;
- graph totals are 5,882 Memory nodes, 12,808 Entity nodes, 30,348
  Entity–Memory edges, and 11,744 stored sequence edges.

The very short local graph build and unchanged extraction-cache entry count
corroborate zero external graph-extraction calls. The formal telemetry records
zero graph, extraction, embedding, and query-Entity requests in the warm
condition.

## Validation, cost, and reproducibility

Both in-run and independent validators pass with
`paper_metric_eligible=true`, `graph_claim_eligible=true`, exact official
aggregation, complete contexts, and the expected counts. The output directory
did not exist at start; `resume=false`, `overwrite=false`.

The immutable query artifact produced 1,997 hits, 0 misses, and 0 live
embedding requests. The graph audit passes and the only non-data prompt
scaffold is 2,410/5,000 characters. Oversized, ineffective, or harmful prompt
components were not introduced.

Warm telemetry records 27.57 seconds retrieval, 1,986 answer requests,
2,803,169 answer input tokens, 16,395 answer output tokens, and 2,529.30
seconds answer-generation wall time. Provider-resolved model revisions,
hardware identity, and monetary prices remain unknown.

Verification:

- independent validation SHA:
  `42cff9e47c7d438945add67656d6cd08073b66cffa93cd5212ef0f86e3121068`;
- prediction SHA:
  `a56d87b7241ed897adff11f7f823d8f49b5fa785e48b38628ad959c8c0f3f5bb`;
- stats SHA:
  `9d2d9ac30f61dbf2cdc6afc2ab959fef546f2669b4ea91f399671d1524aec8cb`;
- B comparison report SHA:
  `191334b649bbb13b4afd2c23f2c4ecb50296b476db676ff87382c3d4c1ccbbf5`;
- A comparison report SHA:
  `ea6b4907bf132c1ea2373c4e710db6235ef3916de93ff6b0322a4af52e87e95d`;
- both significance reports reproduced byte-identically;
- 77/77 tests pass;
- 16/16 frozen vendor hashes pass;
- `code/locomo_eval/` has no diff.

Source identity is the formal commit above plus these exact file hashes:
`formal_graph.py` `20eabf21…a10af`, `run.py` `6624d995…68d7`,
`significance_report.py` `98c8b8db…a2fa`,
`validate_formal_result.py` `c0cf9c0e…5ff`,
`code/em_graph/build/builder.py` `a35cd8fa…be80`, and
`code/em_graph/recall/retrieval.py` `ca19ff96…9ff`.

## Publication decision

This result is valid, reproducible, conversation-only, graph-claim eligible,
and counts toward the paper matrix. It supports the calibrated claim that
speaker Entity links significantly improve evidence recall within B; it does
not support a significant F1 claim. B_no_speaker still significantly improves
overall recall over corrected A, so B's retrieval benefit does not depend
entirely on deterministic speaker injection.

Publication gate remains `continue`, `paper_ready=false`. Commit and push v53,
then proceed to the predeclared top-k robustness/sensitivity work before the
final claim audit.
