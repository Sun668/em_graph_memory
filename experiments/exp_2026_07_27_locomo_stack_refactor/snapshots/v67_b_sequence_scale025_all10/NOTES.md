# v67 — formal sequence-scale sensitivity, scale 0.25

Decision date: 2026-07-29 Asia/Shanghai. Formal source commit
`73deddcb7341e344698f4e2d80f86d75666d9879`, tree
`5111cc2e9bddac86f4126defc3d2dc3a250c369c`. Parameter SHA:
`5e76502e2729b28f2291078692212e0bcf82287acd280e6fafce7857ed239363`;
command SHA:
`57a4b50d6131490362c89776552f83a87f0f3362fcc6f92d1f2634b515635649`.

## Outcome and commands

This preregistered point changes only chronological-neighbor secondary scale
from primary B's `0.5` to `0.25`. It keeps top-k 25, Entity/Semantic
`0.30/0.70`, LoCoMo-10 SHA `047d8e…d74`, all 10 conversations, 1,986 QA,
446 Category-5 rows, and the frozen Reader/evaluator.

```bash
RESEARCH_RUN_CLASS=formal RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v67_b_sequence_scale025_all10/parameters.json RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M6_B_seq025_top25_73848da_qfrozen_run01 /bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M6_B_seq025_top25_73848da_qfrozen_run01 --scope all10 --variant B --top-k 25 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal --sequence-scale 0.25'
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py compare --a-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 --b-dir outputs/locomo_formal/formal_all10_M6_B_seq025_top25_73848da_qfrozen_run01 --resamples 10000 --seed 20260727 --output outputs/locomo_analysis/b_sequence_scale025_vs_b_primary_73deddc_seed20260727_10000.json
```

Official F1 is `42.5150%`, `recall_acc` `84.1022%`, local Categories 1–4
F1 `52.1005%`, and local Categories 1–4 recall `84.9201%`. Versus primary
B, F1 changes `-0.0530` points (paired CI `[-0.8422,+0.7341]`, cluster CI
`[-0.7100,+0.5920]`) and recall changes `-0.3821` points (paired CI
`[-0.8662,+0.0986]`, cluster CI `[-0.9319,+0.1484]`). Every interval crosses
zero; family inference waits for scale `1.0`.

## Complete behavioral comparison

| Dimension / parameter | Side A: primary B scale 0.5 | Side B: v67 scale 0.25 | Expected impact |
|---|---|---|---|
| Dataset/order | SHA `047d8e…d74`; 10 conversations; 1,986 QA | Exact same bytes, rows, order, and denominators | None |
| Graph | 5,882 Memories, 12,808 Entities, 36,227 Entity–Memory and 11,744 sequence edges; conversation-only | Same files/hashes, read-only | No construction confound |
| Memory/query vectors | 10 canonical indexes; query SHA `bef99a…986f9f` | Same artifacts; 1,997 hits, 0 miss/live | No vector confound |
| Retrieval | top-k 25; fusion `0.30/0.70`; sequence scale `0.5`; threshold `0.5`; 20/key; who dampening `0.25`; degree discount on | Only sequence scale is `0.25` | Isolates sequence expansion strength |
| Reader/evaluator | GPT-3.5 Turbo, system, temperature 0, 32 tokens, batch 1; frozen official F1/recall | Exact same | No intended protocol effect |
| Output | Isolated validated primary directory | Absent isolated v67 directory; no resume/overwrite | No contamination |

Exactly aligned are dataset, graph/extraction, Memory and query vectors,
fusion/gating/top-k, Reader, evaluator, serialization, and aggregation. The
sole scientific change is sequence scale. No existing cache, answer, result,
or comparison is invalidated.

## End-to-end logic and audits

The reused graph extracts normalized, merged, deduplicated Entity keys from
conversation Memories and links them to Memories; speakers are deterministic
Entities and Memories have chronological edges. Construction uses only
session anchors, dialog ids, speakers, time-annotated dialog text, and
captions. QA answers/evidence/categories, judges, predictions, and ledgers
are excluded.

Recall uses the full question's frozen dense vector and cached question
Entities, graph gating, `0.30/0.70` fusion, degree discount, sequence
expansion at `0.25`, and dense fill to exactly 25 dialog ids. The frozen
Reader answers only from those graph-retrieved Memories. No judge is used;
Categories 1–4 summaries are local diagnostics.

No old cache/result was deleted, overwritten, rebuilt, or rewritten. Graphs
remain `70`, indexes `30`; build, extraction, Memory embedding, and
query-Entity external requests are zero. Retrieval took `25.5204s`.
Answering made 1,986 requests, used 2,748,009 input and 16,242 output tokens,
and took `2004.9116s`, below the 3.5M input ceiling.

Both validators, 80/80 tests, 16/16 hashes, official aggregation, graph
constraint, prompt budget `2410/5000`, isolation, and resource gate pass.
Statistical reproduction is byte-identical. Key hashes: prediction
`5b314987…3649`, stats `190cd51c…d6c6`, audit `fe69c23c…6deb9`, query usage
`c3b2800b…fc13`, validations `9d74cc1e…a559` and `c9aaf97f…a4e6`, report
`cfc1ab6c…37b`.

v67 is paper-eligible and graph-claim eligible. It supports no scale effect
before correction. Publication gate stays `continue`, `paper_ready=false`:
commit/push v67, then freeze/run scale `1.0` and generate the sequence-family
Holm report.
