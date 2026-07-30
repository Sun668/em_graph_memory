# v54 — formal all-10 A top-k 5 robustness baseline

Decision date: 2026-07-29 Asia/Shanghai.
Formal source commit: `a464ad51ff4bbbf7d7d205a734c72e30f0c93e88`.
Formal source tree: `daa7688c91319ddff29baccbc5c65f21c2e1bd5f`.
Frozen parameter SHA-256:
`81cac3f2deb982f3b6c8082d4af7c859452642f1f50bd06204cdc462741831dd`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

## Outcome

The all-10 pure-Memory `A` baseline completed at the preregistered
`top_k=5` cutoff from the absent isolated directory:

```text
outputs/locomo_formal/formal_all10_M4_A_top5_c4e3ad2_qfrozen_run01/
```

Across 10 conversations, 1,986 QA rows, and 446 Category-5 rows:

- official serialized-row mean F1: `39.9053%`;
- official evidence `recall_acc`: `59.3584%`;
- local Categories 1–4 subset F1: `46.3974%`;
- local Categories 1–4 subset recall: `63.1401%`.

Relative to corrected A at the primary top-k 25, the descriptive changes are
`-2.1628` F1 points and `-20.3884` recall points. This establishes that the
pure-Memory baseline is sensitive to the smaller context budget. It is not an
A-versus-B method comparison: the matched B@5 condition remains pending, and
top-k 25 remains the preregistered primary cutoff.

## Exact command

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v54_a_top5_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M4_A_top5_c4e3ad2_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M4_A_top5_c4e3ad2_qfrozen_run01 --scope all10 --variant A --top-k 5 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

## Complete behavior comparison

| Dimension / parameter | Side A: corrected A@25 | Side B: A@5 | Expected impact of the difference |
|---|---|---|---|
| Dataset / scope | LoCoMo-10 SHA `047d8e…d74`; 10 conversations; 1,986 QA; 446 Category 5 | Exactly the same data, order, and denominators | No sampling or aggregation effect |
| Graph inputs | Conversation date/time, dialog id, speaker, time-annotated text, caption; QA/judge fields excluded | Exactly the same | No graph-compliance or Memory-content effect |
| Graph structure | 5,882 Memory nodes, no Entity nodes used for retrieval | Exactly the same ten memory-only graphs | No construction effect |
| Memory indexes | Ten canonical `text-embedding-3-small` indexes over identical Memory ids/text | Exact same index paths and hashes reused read-only | No Memory-vector effect |
| Query vectors | Artifact SHA `bef99a…986f9f`; 1,986 ordered QA; 1,536 dimensions | Exact same artifact; 1,986 hits, 0 misses, 0 live requests | No query-vector effect |
| Retrieval | Full-pool signed cosine, Entity/semantic `0/1`, no sequence, top-k 25 | Identical scoring and ordering, truncated at top-k 5 | Smaller evidence budget can reduce recall and alter answers |
| Reader | Frozen `gpt-3.5-turbo`, system role, temperature 0, 32 tokens, batch 1 | Exactly the same | No intended protocol effect; provider/backend and Category-5 randomness remain |
| Metrics | Frozen official F1 and `recall_acc` at k=25 | Same definitions at k=5 | Cutoff-specific contexts, answers, and metrics differ |
| Output | Existing validated corrected-A directory | New absent isolated directory; no resume/overwrite | No cross-condition contamination |

Exactly aligned: dataset/order, construction inputs, graphs, Memory text and
vectors, query vectors, ranking function, Reader protocol, evaluator, and
aggregation. The only intentional difference is `top_k=25` versus `5`.
Nothing in this run invalidates old graphs, indexes, query vectors, answers,
metrics, or comparisons. Only new k=5 contexts, answers, and metrics were
created.

## Cache, graph, prompt, and cost audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.

- graph files remained exactly `70`;
- Memory embedding indexes remained exactly `30`;
- all ten corrected-A graphs and indexes were reused read-only;
- graph construction, Entity extraction, Memory embedding, and query-Entity
  request counts were all zero;
- immutable query use was 1,986/1,986 hits, 0 misses, 0 live embedding
  requests;
- graph construction used conversation fields only and excluded every QA,
  answer, evidence, category, judge, and prediction field;
- recall operated over conversation-built Memory graph nodes;
- non-data Entity prompt scaffold was `0/5000` characters; no oversized,
  ineffective, or harmful prompt component was introduced.

Warm telemetry records 4.7434 seconds retrieval, 1,986 answer requests,
645,355 answer input tokens, 14,251 answer output tokens, and 2,203.2184
seconds answer-generation wall time. Provider-resolved model revision,
hardware identity, and monetary price remain unknown.

## Validation and reproducibility

Both the in-run and independent validators pass with
`paper_metric_eligible=true`, `graph_claim_eligible=true`, exact official
aggregation, complete contexts, and the expected counts. The output directory
did not exist at start; `resume=false`, `overwrite=false`.

Verification:

- prediction SHA:
  `bad42e270b3bab4634b0abe60b4e94a0b2fd94cd2b29a4275047f88cde4f6d0e`;
- stats SHA:
  `3f58618bf8c92f1b828415da507240669c226b3a3d699f9e38eeb0f00026f5aa`;
- in-run validation SHA:
  `b6e9b027b7d5f726c1b84323a3f330c459af362e8aecc4f396ada5b812b3b04f`;
- independent validation SHA:
  `0332d3f1904dd93683a2c3f0def4a8f0b86779e06b3d21fc07331d3c905622aa`;
- 77/77 tests pass;
- 16/16 frozen vendor hashes pass;
- `code/locomo_eval/` has no diff.

Source hashes: `formal_graph.py` `20eabf21…a10af`, `run.py`
`6624d995…68d7`, `validate_formal_result.py` `c0cf9c0e…d5ff`,
`code/em_graph/build/builder.py` `a35cd8fa…be80`, and
`code/em_graph/recall/retrieval.py` `ca19ff96…94ff`.

## Publication decision

This result is valid, reproducible, conversation-only, graph-claim eligible,
and counts as the A@5 point in the paper robustness matrix. It supports only a
cutoff-sensitivity statement for A. It does not support an A/B robustness
claim until B@5 is separately frozen, run, validated, and compared.

Publication gate remains `continue`, `paper_ready=false`. Commit and push v54,
then preregister B@5 without changing or deleting the shared caches.
