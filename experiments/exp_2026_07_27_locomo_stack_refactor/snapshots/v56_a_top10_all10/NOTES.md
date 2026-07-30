# v56 — formal all-10 A top-k 10 robustness baseline

Decision date: 2026-07-29 Asia/Shanghai.
Formal source commit: `45bde5ddd9219d398f74ab3fdf8546f06660aec0`.
Formal source tree: `501a80e9d6549c490cee5b0cf0906be935cd9922`.
Frozen parameter SHA-256:
`3f0714753be687b0914f29d5c9a2f22c4bb32658beca3c4995df748493f2bec0`.
Frozen command SHA-256:
`70568d328ee634b68cca28691a19e7dabe0f79424dec377dc03cdca0183b4a06`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

## Outcome

The all-10 pure-Memory `A` baseline completed at the preregistered
`top_k=10` cutoff from the absent isolated directory:

```text
outputs/locomo_formal/formal_all10_M4_A_top10_0eee9b8_qfrozen_run01/
```

Across 10 conversations, 1,986 QA rows, and 446 Category-5 rows:

- official serialized-row mean F1: `41.7607%`;
- official evidence `recall_acc`: `68.9145%`;
- local Categories 1–4 subset F1: `49.5044%`;
- local Categories 1–4 subset recall: `72.3469%`.

Relative to corrected A at the primary top-k 25, the descriptive changes are
`-0.3075` F1 points, `-10.8323` recall points, `-1.7601` local Categories
1–4 F1 points, and `-10.4630` local Categories 1–4 recall points.

This is a within-baseline cutoff-sensitivity observation, not an A-versus-B
result. Top-k 25 remains primary and matched B@10 remains pending.

## Exact command

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v56_a_top10_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M4_A_top10_0eee9b8_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M4_A_top10_0eee9b8_qfrozen_run01 --scope all10 --variant A --top-k 10 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

## Complete behavior comparison

| Dimension / parameter | Side A: corrected A@25 | Side B: A@10 | Expected impact of the difference |
|---|---|---|---|
| Dataset / scope | LoCoMo-10 SHA `047d8e…d74`; 10 conversations; 1,986 QA; 446 Category 5 | Exactly the same bytes, order, rows, and denominators | No sampling or aggregation effect |
| Graph inputs | Session date/time, dialog id, speaker, time-annotated text, official caption; QA/judge fields excluded | Exactly the same | No graph-compliance or Memory-content effect |
| Graph structure | Same 5,882 Memory nodes with chronological links; no Entity retrieval | Exact same ten memory-only graph artifacts | No construction effect |
| Memory indexes | Ten canonical `text-embedding-3-small` indexes over identical Memory ids/text | Exact same paths and hashes reused read-only | No Memory-vector effect |
| Query vectors | Artifact SHA `bef99a…986f9f`; ordered 1,986 QA; L2 float32; 1,536 dimensions | Exact same artifact; 1,986 hits, 0 misses, 0 live requests | No query-vector effect |
| Retrieval | Full-pool signed cosine, Entity/semantic weights `0/1`, no sequence, top-k 25 | Identical candidate pool, score, tie-breaking, and order, truncated at top-k 10 | Smaller context budget reduces attainable evidence coverage and can alter answers |
| Reader | Frozen `gpt-3.5-turbo`; system role; temperature 0; 32 tokens; batch 1; upstream Category-5 randomness unchanged | Exactly the same | No intended generation-protocol effect |
| Metrics | Frozen official category-aware F1 and `recall_acc`, three-decimal per-row serialization | Same definitions and aggregation at k=10 | Only cutoff-derived contexts, answers, and metrics change |
| Output | Existing validated corrected-A directory | New absent isolated v56 directory; no resume/overwrite | No cross-condition contamination |

Exactly aligned: dataset/order, construction inputs, Memory graph, Memory text
and vectors, query vectors, candidate pool, ranking function, Reader protocol,
official evaluator, serialization, and aggregation. The only intentional
difference is top-k 25 versus 10.

Both are exactly the same retrieval implementation before truncation, not
merely functionally similar. No difference is treated as no-effect by
assumption: the shorter list changes contexts and observed recall.

No prior graph, index, query vector, answer, metric, or comparison is
invalidated. Only new k=10 contexts, answers, metrics, and telemetry were
created. The minimal next run is matched B@10; A/B@50 remains necessary for
the declared cutoff-range matrix.

## Graph, recall, answer, and metric logic

The memory-only graph was originally constructed from conversation session
anchors, dialog ids, speakers, normalized/time-annotated dialog text, and
official image captions. It contains Memory nodes and chronological
`NEXT/PREV` edges. QA questions, answers, evidence labels, categories, judge
outputs, previous predictions, and question-driven ledgers were excluded from
construction.

The complete question addresses the frozen dense query vector. Retrieval ranks
the full Memory pool by signed cosine similarity with deterministic
tie-breaking and returns exactly ten unique dialog ids. No Entity extractor,
Entity gate, reranker, validator, sequence expansion, or live embedding
fallback is active. Retrieved conversation-built Memory nodes are formatted as
dialog evidence and passed through the unchanged `QARecall` boundary.

The frozen LoCoMo Reader receives only the current question and graph-retrieved
context, with system role, temperature 0, 32 completion tokens, and batch size
1. The judge is not applicable: this condition uses the frozen official
category-aware F1 and evidence `recall_acc`, not the local EvoEmo
LLM-as-Judge.

## Cache, prompt, and cost audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.

- graph files remained exactly `70`;
- Memory embedding indexes remained exactly `30`;
- all ten corrected-A graphs and indexes were reused read-only;
- graph construction, Entity extraction, Memory embedding, and query-Entity
  request counts were all zero;
- immutable query use was 1,986/1,986 hits, 0 misses, 0 live embedding
  requests;
- answer recall used conversation-built Memory graph nodes;
- non-data Entity prompt scaffold was `0/5,000` characters; no oversized,
  ineffective, or harmful prompt component was introduced.

Warm telemetry records 4.6808 seconds retrieval, 1,986 answer requests,
1,165,180 answer input tokens, 15,083 answer output tokens, and 2,235.3189
seconds answer-generation wall time. Provider-resolved model revision,
hardware identity, and monetary price remain unknown.

## Validation and reproducibility

Both in-run and independent validators pass with
`paper_metric_eligible=true`, `graph_claim_eligible=true`, exact official
aggregation, complete contexts, and expected counts. The directory did not
exist at start; `resume=false`, `overwrite=false`.

Verification:

- prediction SHA:
  `b37a92b412383f9224f4d9417ae028017d0bd24defbfa82d914395e81cbaffa9`;
- stats SHA:
  `eb1295f8cb6381000ef110c796fe7fdf5b4303ad51bb57b5c4b37382d4fd7a27`;
- audit SHA:
  `7a8b81693e5bdc75bbb084cf1557275b5d339e05529951b6f1a52b59430704a9`;
- query-usage SHA:
  `d94d1765f07ca06326b5949a3108bf456635210307cfec770b6ff3f717d10d74`;
- in-run validation SHA:
  `7180cf40087457fe3113ae702c1dac651cb1e33b6497f24f86f3b4ba6dd74a30`;
- independent validation SHA:
  `50630668f24cd796b4d52790291a7f0da5cef28183b7ff1f8f34a9510ba3e407`;
- 77/77 tests pass;
- 16/16 frozen vendor hashes pass;
- `code/locomo_eval/` has no diff.

Source hashes: `formal_graph.py` `20eabf21…a10af`, `run.py`
`6624d995…68d7`, `validate_formal_result.py` `c0cf9c0e…d5ff`,
`code/em_graph/build/builder.py` `a35cd8fa…be80`, and
`code/em_graph/recall/retrieval.py` `ca19ff96…94ff`.

## Publication decision

This result is valid, reproducible, conversation-only, graph-claim eligible,
and counts as A@10 in the paper robustness matrix. It supports only the
descriptive statement that reducing A's context budget from 25 to 10 lowers
evidence recall by `10.8323` points while changing overall F1 by `-0.3075`
points.

Publication gate remains `continue`, `paper_ready=false`. Commit and push v56,
then preregister matched B@10 without modifying shared caches.
