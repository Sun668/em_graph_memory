# v59 — valid A@50 robustness baseline

Decision date: 2026-07-29 Asia/Shanghai. Formal source commit:
`43d9e2ebe20b8e3c61a1ae285f1376dab706b357`. Source tree:
`7e6e2a2ba49f239e698cf7c5d46ef48c960054d4`. Frozen parameter SHA-256:
`da6e53d272becdae791dcdf70b49384d43e4fef9cb4fa04c7416b1c354ae56ea`.
Frozen command SHA-256:
`639155906c255f14c61f1d4f3cb9431e829da0f8ee071ceb452aeef12bb63ce9`.

## Outcome and exact command

The preregistered all-10 pure-Memory A@50 retry completed from the absent,
isolated directory
`outputs/locomo_formal/formal_all10_M4_A_top50_retry_e7a5abf_qfrozen_run01`.
It covered LoCoMo-10 SHA `047d8e…d74`, 10 conversations, 1,986 QA rows, all
five categories, and 446 Category-5 rows in immutable dataset order.

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v59_a_top50_retry_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M4_A_top50_retry_e7a5abf_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M4_A_top50_retry_e7a5abf_qfrozen_run01 --scope all10 --variant A --top-k 50 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

Official serialized-row mean F1 is `42.0782%`; official evidence
`recall_acc` is `86.7148%`. Local Categories 1–4 subset F1 is `51.9268%`,
and local Categories 1–4 subset recall is `89.4906%`. The condition passed its
6,000,000 answer-input-token ceiling with actual use of 5,188,930.

## Complete behavior and parameter comparison

| Dimension / parameter | Side A: corrected A@25 | Side B: v59 A@50 | Expected impact of the difference |
|---|---|---|---|
| Dataset / order | SHA `047d8e…d74`; 10 conversations; 1,986 QA; 446 Category 5 | Byte-identical dataset, rows, categories, and order | No sampling or denominator effect |
| Construction inputs | Session anchors, dialog ids, speakers, time-annotated dialog text, captions only | Exactly identical conversation-only inputs | No construction confound |
| Graph / index | 5,882 Memory nodes, chronological links, ten canonical `text-embedding-3-small` Memory indexes | Exact same paths and hashes, reused read-only | No graph or Memory-vector effect |
| Query vectors | Artifact SHA `bef99a…986f9f`; 1,986 ordered rows; float32 L2, 1,536 dimensions | Exact same immutable artifact; 1,986 hits, 0 misses, 0 live requests | No query-vector effect |
| Retrieval | Full-pool signed cosine; Entity/semantic weights `0/1`; no sequence; top-k 25 | Same ranking and tie-breaking; top-k 50 | Only the returned evidence budget changes |
| Reader | `gpt-3.5-turbo`; system role; temperature 0; 32 tokens; batch 1 | Exactly identical; upstream Category-5 option randomness remains unseeded | No intended generation-protocol effect |
| Metrics | Frozen official category-aware F1 and `recall_acc`; three-decimal rows | Exactly identical definitions, serialization, and aggregation | No metric-definition effect |
| Resources | Original valid condition budget | 1,986 answer requests; 6M input, 63,552 output token maxima; 7,200 s | Operational ceiling only; no scientific change |
| Output | Prior isolated corrected-A directory | New absent isolated v59 directory; resume/overwrite false | No answer/result contamination |

Exactly aligned are the dataset, graph text and structure, Memory vectors,
query vectors, dense score and tie-breaking, Reader, evaluator, serialization,
and aggregation. Only the top-k evidence cutoff differs scientifically. The
resource ceiling differs operationally and cannot affect answers unless the
run exceeds it; this run did not. No difference invalidates old graph, index,
query, answer, metric, or comparison artifacts. A new B@50 condition is needed
before estimating the graph-method effect at this cutoff.

## Extraction, graph, recall, answer, and judge logic

A uses no Entity extractor at runtime. Its reused Memory graph was built from
conversation session anchors, dialog ids, speakers, normalized and
time-annotated dialog text, and official captions. It contains Memory nodes
and chronological links. QA questions, answers, evidence annotations,
category labels, judge outputs, previous predictions, summaries, and
question-driven ledgers were excluded from graph construction.

The complete question indexes the frozen read-only query vector. Retrieval
ranks the full Memory pool by signed cosine with semantic weight `1.0`, Entity
weight `0.0`, no Entity gate, no sequence expansion, and deterministic
Memory-id/order fallback, returning exactly the top 50 available Memories.
Those conversation-built graph nodes become Reader evidence.

The frozen LoCoMo Reader uses `gpt-3.5-turbo`, system role, temperature `0`,
32 completion tokens, batch size `1`, and the unchanged vendored category
branches. Metrics are frozen official F1 and evidence `recall_acc`; the local
Categories 1–4 summaries are diagnostics. No judge was used.

## Cache, prompt, cost, and validity audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.
Graphs remained `70`; Memory indexes remained `30`; all ten A artifacts were
reused read-only. Graph build, Entity extraction, Memory embedding, and query
Entity requests were all zero. Query use was 1,986 hits, 0 misses, and 0 live
embedding requests. Retrieval took 4.8440 seconds. Answer generation made
1,986 requests, used 5,188,930 input and 17,088 output tokens, and took
2,038.9634 seconds. Provider revision, hardware, and monetary cost are
unknown.

Both validators pass with `paper_metric_eligible=true` and
`graph_claim_eligible=true`; the output was absent at start and
resume/overwrite were false. All 77 tests and 16 vendor hashes pass, and
`code/locomo_eval/` has no diff. The non-data Entity scaffold is `0/5000`;
no oversized, ineffective, or harmful prompt component was active.

Artifact hashes: prediction `4b59a59f…f85628`, stats
`ef51ce22…20753`, audit `7a8b8169…04a9`, query usage
`d94d1765…d10d74`, in-run validation `fe98f819…bfe46`, and independent
validation `f68fd7ef…d88c3`.

## Publication decision

v59 is valid, reproducible, conversation-only, graph-claim eligible, and
counts as A@50 in the paper robustness matrix. It replaces no artifact and
does not retroactively promote diagnostic v58. It supports only the baseline
cutoff result; the A-versus-B@50 claim remains pending matched B@50.
Publication gate remains `continue`, `paper_ready=false`.
