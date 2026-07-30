# v62 — formal fusion sensitivity, Entity/Semantic 0.50/0.50

Decision date: 2026-07-29 Asia/Shanghai. Formal source commit:
`cc41883b008d2893ef8a1ba1a355c1579a45280b`; source tree
`25fcc1ab020d50690f404160f6a4e522ed21d9a8`. Frozen parameter SHA:
`f6a91d0ea729896468924bcae87cd49de2ac066b866d0c89f2224e7511b8e0e2`.
Frozen command SHA:
`d30c6f978e923a78bdddefe48d6a6ed7bf504c8b9a87933fe31e6ac6e6888cee`.

## Outcome and exact commands

The second preregistered new fusion point used the complete
conversation-built Entity–Memory graph at top-k 25, Entity/Semantic weights
`0.50/0.50`, and sequence scale `0.5`. It ran over LoCoMo-10 SHA
`047d8e…d74`, all ten conversations, 1,986 QA rows, all categories, and 446
Category-5 rows from the absent isolated directory
`outputs/locomo_formal/formal_all10_M5_B_e50_s50_top25_0eb464c_qfrozen_run01`.

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v62_b_fusion_e50_s50_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M5_B_e50_s50_top25_0eb464c_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M5_B_e50_s50_top25_0eb464c_qfrozen_run01 --scope all10 --variant B --top-k 25 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal --entity-weight 0.5 --semantic-weight 0.5'
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py compare \
  --a-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 \
  --b-dir outputs/locomo_formal/formal_all10_M5_B_e50_s50_top25_0eb464c_qfrozen_run01 \
  --resamples 10000 --seed 20260727 \
  --output outputs/locomo_analysis/b_fusion_e50_s50_vs_b_primary_cc41883_seed20260727_10000.json
```

The condition reaches official F1 `42.2440%`, official `recall_acc`
`84.3280%`, local Categories 1–4 F1 `52.1406%`, and local Categories 1–4
recall `83.9126%`.

Relative to the preregistered primary B point `0.30/0.70`, F1 changes by
`-0.3240` points. Its paired-QA CI is `[-1.3474, +0.6937]` with raw
p=`0.5465`; its conversation-cluster CI is `[-1.0298, +0.4773]` with raw
p=`0.4190`. Recall changes by `-0.1562` points. Its paired-QA CI is
`[-0.9930, +0.7001]` with raw p=`0.7017`; its conversation-cluster CI is
`[-1.5314, +1.0403]` with raw p=`0.8233`. All four overall intervals cross
zero. Family-adjusted decisions are deferred to the separately locked
two-comparison fusion report.

## Complete behavioral comparison

| Dimension / parameter | Side A: primary B 0.30/0.70 | Side B: v62 B 0.50/0.50 | Expected impact of the difference |
|---|---|---|---|
| Dataset / order | SHA `047d8e…d74`; 10 conversations; 1,986 QA; 446 Category 5 | Exact same bytes, rows, order, and denominators | No sampling or aggregation effect |
| Graph and construction inputs | 5,882 Memories, 12,808 Entities, 36,227 Entity–Memory edges; conversation fields only | Exact same graph files and hashes, reused read-only | No extraction or graph-structure confound |
| Memory indexes | Ten canonical `text-embedding-3-small` indexes | Exact same paths and hashes, reused read-only | No Memory-vector effect |
| Query vectors | SHA `bef99a…986f9f`; ordered 1,986 QA; L2 float32; 1,536 dimensions | Exact same artifact; 1,997 hits, 0 misses, 0 live requests | No query-vector effect |
| Retrieval | top-k 25; Entity/Semantic `0.30/0.70`; sequence scale `0.5`; threshold `0.5`; top 20/key; who dampening `0.25`; degree discount on | Only Entity/Semantic weights change to `0.50/0.50`; every other retrieval parameter is identical | Isolates fusion-weight sensitivity |
| Reader | `gpt-3.5-turbo`; system role; temperature 0; 32 tokens; batch 1 | Exactly the same | No intended generation-protocol effect |
| Metrics | Frozen official F1 and `recall_acc`; three-decimal rows | Exactly the same definitions and aggregation | Differences arise downstream of retrieval |
| Output | Validated isolated primary-B directory | New absent isolated v62 directory; resume/overwrite false | No cross-condition contamination |

Exactly aligned are dataset/order, extraction and graph structure, Memory and
query vectors, query-Entity cache, top-k, sequence behavior, all non-weight
retrieval parameters, Reader, evaluator, serialization, and aggregation. The
only scientific change is fusion from `0.30/0.70` to `0.50/0.50`. No cache,
answer, metric, or prior comparison is invalidated.

## Extraction, construction, recall, answer, and judge logic

The reused graph was extracted one normalized conversation Memory at a time
with the bounded `gpt-3.5-turbo` Entity prompt. Entity keys were normalized,
merged, deduplicated, filtered, and linked to Memory nodes; speakers were
deterministic Entities. Memories also have chronological links. Construction
used only session anchors, dialog ids, speakers, normalized/time-annotated
dialog text, and captions. QA questions, answers, evidence, categories, judge
outputs, previous predictions, and question-driven ledgers were excluded.

At recall, the full question supplies the immutable dense vector and existing
question-Entity keys. The retriever gates through graph Entities, fuses Entity
and signed-cosine scores at `0.50/0.50`, applies degree discount, expands
chronological neighbors at secondary scale `0.5`, and uses dense fill to
return exactly 25 unique dialog ids. Those graph Memories become Reader
evidence.

The frozen Reader uses `gpt-3.5-turbo`, system role, temperature `0`, 32
completion tokens, and batch size `1`, with unchanged category branches.
Metrics are frozen official F1 and evidence `recall_acc`; Categories 1–4
summaries are local diagnostics. No judge was used.

## Cache, resource, validation, and reproducibility audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.
Graphs remained `70`, Memory indexes remained `30`, and v61 plus all prior
formal result directories remain present. All graphs, indexes, cached question
Entities, and immutable query vectors were reused read-only. Graph
construction, Entity extraction, Memory embedding, and query-Entity external
requests were zero. Query use was 1,997 hits, 0 misses, and 0 live requests.

Retrieval took 27.7963 seconds. Answer generation made 1,986 requests, used
2,776,004 input and 15,995 output tokens, and took 2,024.8886 seconds. The
input usage passed the frozen 3.5M ceiling. Provider revision, hardware, and
monetary price remain unknown.

Both validators, 77/77 tests, 16/16 frozen hashes, official aggregation,
graph constraint, 2,410/5,000 prompt budget, output isolation, and resource
gate pass. Statistical reproduction is byte-identical. Hashes: prediction
`1b8d5ca0…1430`, stats `6545847b…e316`, audit `c04dfb8e…9b49`, query usage
`c3b2800b…fc13`, in-run validation `83d66313…5374`, independent validation
`c2ff480b…bdcb`, and significance `7c2deadb…f000`.

## Publication decision

v62 is valid, reproducible, conversation-only, graph-claim eligible, and
counts as the `0.50/0.50` fusion sensitivity point. It shows no supported
overall F1 or evidence-recall change relative to `0.30/0.70`. Together with
v61 it completes the two new preregistered fusion points, but the family claim
requires a source-locked Holm report.

Publication gate remains `continue`, `paper_ready=false`: lock and generate
the fusion-family report, then continue sequence sensitivity, O2 diagnostic,
cost consolidation, and the final claim audit.
