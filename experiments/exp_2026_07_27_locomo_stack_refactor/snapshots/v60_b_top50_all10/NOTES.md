# v60 — formal B@50 and completed cutoff robustness matrix

Decision date: 2026-07-29 Asia/Shanghai. Formal source commit:
`acb4277c21217daeae6ef20a4f09fa7d7e5f7970`; source tree
`3a904d2ac94063d6d9296c347d75dbe1a28dd2ad`. Frozen parameter SHA:
`2cdc26588d13c34043d49bb8ebe477cee50b54b1f3cd7d02b4ba55f4ca52157c`.
Frozen command SHA:
`ff63690331ebc3146445585f20556838286ca8ee8dcddbea1afe732745aa12f3`.

## Outcome and exact commands

Complete Entity–Memory B@50 ran over LoCoMo-10 SHA `047d8e…d74`, all ten
conversations, 1,986 QA rows, all categories, and 446 Category-5 rows from the
absent isolated directory
`outputs/locomo_formal/formal_all10_M4_B_top50_6afa882_qfrozen_run01`.

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v60_b_top50_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M4_B_top50_6afa882_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M4_B_top50_6afa882_qfrozen_run01 --scope all10 --variant B --top-k 50 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py compare \
  --a-dir outputs/locomo_formal/formal_all10_M4_A_top50_retry_e7a5abf_qfrozen_run01 \
  --b-dir outputs/locomo_formal/formal_all10_M4_B_top50_6afa882_qfrozen_run01 \
  --resamples 10000 --seed 20260727 \
  --output outputs/locomo_analysis/b_top50_vs_a_top50_acb4277_seed20260727_10000.json
```

B@50 reaches official F1 `41.7832%`, official `recall_acc` `90.3306%`,
local Categories 1–4 F1 `52.1958%`, and local Categories 1–4 recall
`90.9394%`.

Against matched A@50, B changes F1 by `-0.2950` points; paired-QA CI
`[-1.3129, +0.7143]` and conversation-cluster CI `[-1.4188, +0.7825]`
both cross zero. Recall increases by `+3.6159` points; paired-QA CI
`[+2.7754, +4.4735]` and conversation-cluster CI
`[+2.4603, +4.6426]` are both above zero (both p=`0.0002`).

## Complete A/B behavior comparison

| Dimension / parameter | Side A: v59 A@50 | Side B: v60 B@50 | Expected impact of the difference |
|---|---|---|---|
| Dataset / order | SHA `047d8e…d74`; 10 conversations; 1,986 QA; 446 Category 5 | Exact same bytes, rows, order, and denominators | No sampling or aggregation effect |
| Construction inputs | Session anchors, dialog ids, speakers, time-annotated text, captions; all QA/judge fields excluded | Exactly the same conversation-only inputs | No input-profile confound |
| Graph | 5,882 Memory nodes and chronology; no Entity retrieval | Same Memories plus 12,808 conversation Entities, 36,227 Entity–Memory edges, and speaker incidence | Tests the complete Entity graph |
| Memory indexes | Ten canonical `text-embedding-3-small` indexes | Exact same paths and hashes reused read-only | No Memory-vector effect |
| Query vectors | SHA `bef99a…986f9f`; ordered 1,986 QA; L2 float32; 1,536 dimensions | Exact same artifact; 1,998 hits, 0 misses, 0 live requests | No query-vector effect |
| Query Entity channel | Disabled | Existing full-question Entity cache; threshold `0.5`, top 20/key, who-only dampening `0.25`, degree discount on; zero live requests | Adds conversation-graph candidates |
| Retrieval | Full-pool signed cosine; weights `0/1`; no sequence; top-k 50 | Gated dense fill; weights `0.30/0.70`; sequence ±1 at scale `0.5`; top-k 50 | Can change ranks, coverage, and answers |
| Reader | `gpt-3.5-turbo`; system role; temperature 0; 32 tokens; batch 1 | Exactly the same | No intended generation-protocol effect |
| Metrics | Frozen official F1 and `recall_acc`; three-decimal rows | Exactly the same definitions and aggregation | Differences arise downstream of retrieval |
| Output | Validated isolated v59 directory | New absent isolated v60 directory; resume/overwrite false | No cross-condition contamination |

Exactly aligned are dataset/order, Memory inputs/text/vectors, immutable query
vectors, top-k, Reader, evaluator, serialization, and aggregation. Both sides
retrieve conversation-built graph Memories, but B additionally uses Entity
incidence, gating, fusion, degree discount, and sequence expansion. Those are
the intended differences. No old cache, answer, metric, or comparison is
invalidated.

## Extraction, construction, recall, answer, and judge logic

The reused B graph was extracted one normalized conversation Memory at a time
with the bounded `gpt-3.5-turbo` Entity prompt. Entity keys were normalized,
merged, deduplicated, filtered, and linked to Memory nodes; speakers were
deterministic Entities. Memories also have chronological links. Inputs were
only session anchors, dialog ids, speakers, normalized/time-annotated dialog
text, and captions. QA questions, answers, evidence, categories, judge
outputs, and predictions were excluded from construction.

At recall, the full question supplies the immutable dense vector and existing
question-Entity keys. B gates through graph Entities, fuses Entity and signed
cosine scores at `0.30/0.70`, applies degree discount, expands chronological
neighbors at secondary scale `0.5`, and uses dense fill to return exactly 50
unique dialog ids. Those graph Memories become Reader evidence.

The frozen Reader uses `gpt-3.5-turbo`, system role, temperature `0`, 32
completion tokens, batch size `1`, and unchanged category branches. Metrics
are frozen official F1 and evidence `recall_acc`; Categories 1–4 summaries
are local diagnostics. No judge was used.

## Cache, resource, validation, and reproducibility audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.
Graphs remained `70`, Memory indexes remained `30`, and the prior v58/v59
directories remain present. All ten B graphs, canonical indexes, cached
question Entities, and immutable query vectors were reused read-only. Graph
construction, Entity extraction, Memory embedding, and query-Entity external
requests were zero. Query use was 1,998 hits, 0 misses, 0 live requests.

Retrieval took 30.5423 seconds. Answer generation made 1,986 requests, used
5,251,555 input and 17,148 output tokens, and took 2,139.9025 seconds. The
input usage passed the frozen 6M ceiling. Provider revision, hardware, and
monetary price remain unknown.

Both validators, 77/77 tests, 16/16 frozen hashes, official aggregation,
graph constraint, 2,410/5,000 prompt budget, and output isolation pass.
Statistical reproduction is byte-identical. Hashes: prediction
`8ca84dec…c3b8e`, stats `8dbd5f62…d1695`, audit `c6ae75a9…9980e0`,
query usage `30f0d902…a5c08`, in-run validation `44846cb1…207af`,
independent validation `34124922…0b983`, and significance
`ec022c63…7b09`.

## Publication decision

v60 is valid, reproducible, conversation-only, graph-claim eligible, and
counts as B@50. Together with matched pairs at top-k 5, 10, and primary 25,
it supports a statistically significant evidence-recall advantage for
complete B at all four preregistered cutoffs. No overall final-answer F1
advantage is established at any cutoff. This is a strong robustness claim,
not proof that every component or parameter choice is optimal.

Publication gate remains `continue`, `paper_ready=false`: fusion-weight and
sequence-scale sensitivity, O2 diagnostic, cost consolidation, and final
claim audit still precede manuscript drafting.
