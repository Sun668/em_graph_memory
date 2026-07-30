# v68 — formal sequence-scale sensitivity, scale 1.0

Decision date: 2026-07-29 Asia/Shanghai. Formal source commit
`06a3a2efae7fba9f61995bd102d95379294b866d`, tree
`e00915294899ffab20385f0f4245e0b738219228`. Frozen parameter SHA:
`24b46b36260d14c9dcc37931e674e7a4e46aa4a0f5541cdb3bb9c97c3a018175`;
command SHA:
`049101fb4a253821a6cde393be8ab1714bd7eb236108d281373d85124a0f1847`.

## Outcome and commands

This preregistered point changes only chronological-neighbor secondary scale
from primary B's `0.5` to `1.0`. It keeps top-k 25, Entity/Semantic
`0.30/0.70`, LoCoMo-10 SHA `047d8e…d74`, all 10 conversations, 1,986 QA,
446 Category-5 rows, and the frozen Reader/evaluator.

```bash
RESEARCH_RUN_CLASS=formal RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v68_b_sequence_scale100_all10/parameters.json RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M6_B_seq100_top25_296cbc6_qfrozen_run01 /bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M6_B_seq100_top25_296cbc6_qfrozen_run01 --scope all10 --variant B --top-k 25 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal --sequence-scale 1.0'
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py compare --a-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 --b-dir outputs/locomo_formal/formal_all10_M6_B_seq100_top25_296cbc6_qfrozen_run01 --resamples 10000 --seed 20260727 --output outputs/locomo_analysis/b_sequence_scale100_vs_b_primary_06a3a2e_seed20260727_10000.json
```

Official F1 is `43.1220%`, `recall_acc` `85.1609%`, local Categories 1–4
F1 `52.7534%`, and local Categories 1–4 recall `85.2140%`. Versus primary
B, F1 is `+0.5540` points: paired CI `[-0.3497,+1.4759]`, p=`0.2252`;
conversation-cluster CI `[+0.0210,+1.1683]`, p=`0.0406`. Recall is `+0.6767`
points: paired CI `[-0.0129,+1.3836]`, p=`0.0548`; cluster CI
`[-0.1028,+1.4064]`, p=`0.0864`. The F1 estimators disagree, and both recall
intervals cross zero. No claim is made before family correction.

## Complete behavioral comparison

| Dimension / parameter | Side A: primary B scale 0.5 | Side B: v68 scale 1.0 | Expected impact |
|---|---|---|---|
| Dataset/order | SHA `047d8e…d74`; 10 conversations; 1,986 QA | Exact same bytes, rows, order, denominators | None |
| Graph | 5,882 Memories, 12,808 Entities, 36,227 Entity–Memory and 11,744 sequence edges; conversation-only | Same files/hashes, read-only | No construction confound |
| Memory/query vectors | 10 canonical indexes; query SHA `bef99a…986f9f` | Same artifacts; 1,997 hits, 0 miss/live | No vector confound |
| Retrieval | top-k 25; fusion `0.30/0.70`; sequence scale `0.5`; threshold `0.5`; 20/key; who dampening `0.25`; degree discount on | Only sequence scale is `1.0` | Isolates sequence expansion strength |
| Reader/evaluator | GPT-3.5 Turbo, system, temperature 0, 32 tokens, batch 1; frozen F1/recall | Exact same | No intended protocol effect |
| Output | Isolated validated primary directory | Absent isolated v68 directory; no resume/overwrite | No contamination |

Exactly aligned are dataset, graph/extraction, Memory and query vectors,
fusion/gating/top-k, Reader, evaluator, serialization, and aggregation. The
sole scientific change is sequence scale. No cache, answer, prior result, or
comparison is invalidated.

## End-to-end logic and audits

The reused graph extracts normalized, merged, deduplicated Entity keys from
conversation Memories and links them to Memories; speakers are deterministic
Entities and Memories have chronological edges. Construction uses only
session anchors, dialog ids, speakers, time-annotated dialog text, and
captions. QA answers/evidence/categories, judges, predictions, and ledgers
are excluded.

Recall uses the full question's frozen dense vector and cached question
Entities, graph gating, `0.30/0.70` fusion, degree discount, sequence
expansion at `1.0`, and dense fill to exactly 25 dialog ids. The frozen
Reader answers only from those graph-retrieved Memories. No judge is used;
Categories 1–4 summaries are local diagnostics.

No old cache/result was deleted, overwritten, rebuilt, or rewritten. Graphs
remain `70`, indexes `30`; build, extraction, Memory embedding, and
query-Entity external requests are zero. Retrieval took `28.3138s`.
Answering made 1,986 requests, used 2,733,632 input and 16,173 output tokens,
and took `1941.5774s`, below the 3.5M input ceiling.

Both validators, 80/80 tests, 16/16 hashes, official aggregation, graph
constraint, prompt budget `2410/5000`, isolation, and resource gate pass.
Statistical reproduction is byte-identical. Key hashes: prediction
`366d2efc…bca2`, stats `6515bbc8…e9c8`, audit `0e3b5da6…a3e0`, query usage
`c3b2800b…fc13`, validations `05b20c36…a9df` and `15360159…7688`, report
`0054a99a…8ddd`.

The initial manual project preflight failed closed before the formal launch
because the draft contained an incorrect full base-commit spelling and an
incorrectly computed command digest. Both were corrected in committed
parameter-only commits, and both generic and project preflights then passed.
No output directory, API request, or cache mutation occurred during those
failed checks.

v68 is paper-eligible and graph-claim eligible. Publication gate stays
`continue`, `paper_ready=false`: verify/commit/push v68, then lock and run the
two-comparison sequence-family Holm report.
