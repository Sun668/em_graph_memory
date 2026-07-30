# v44 — all-10 B_noseq component condition

Decision date: 2026-07-28 Asia/Shanghai. Source commit/tree:
`cabad81fe043b00da8671fb008414aed945637c9` /
`593c67b84a4d94e721bb4a3cf83a7e0709b0f7e2`. Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This final predeclared component condition disables sequence expansion inside
complete B. It is not an A rerun. It started from the absent isolated directory
`outputs/locomo_formal/formal_all10_M2_B_noseq_top25_cabad81_qfrozen_run01/`
with `resume=false` and `overwrite=false`.

## Command and resolved settings

```bash
source ./env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05 EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M2_B_noseq_top25_cabad81_qfrozen_run01 \
  --scope all10 --variant B_noseq --top-k 25 \
  --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph --output-root outputs/locomo_formal
```

The run uses all 10 conversations and 1,986 QA rows in dataset order.
Conversation/question Entity and answer models request `gpt-3.5-turbo`;
Memory/query embeddings use `text-embedding-3-small`; the provider's actual
answer revision is unknown. Reader: one `system` message, temperature 0,
32 completion tokens, batch 1, unchanged unseeded Category-5 option ordering.
There is no judge and no seed override.

| Dimension / parameter | Side A: B_noseq | Side B: complete B | Expected impact |
|---|---|---|---|
| Graph/gate | Same 5,882 Memory, 12,808 Entity, 36,227 Entity–Memory, threshold `0.50`, top 20/key, who `0.25`, degree discount | Exactly the same | No construction or gate confound |
| Fusion | Entity/semantic `0.30/0.70` signed scores | Exactly the same | No ranking-weight confound |
| Sequence | Disabled; configured scale `0.50` inactive | NEXT/PREV expansion enabled at scale `0.50` | Isolates sequence contribution in complete B |
| Query/top-k/Reader/metric | Same immutable query artifact, top 25, frozen Reader and official metrics | Exactly the same | No vector, context budget, or evaluation difference |

The sequence switch is the only effective difference. It changes the condition
fingerprint and therefore invalidates contexts, answers, and metrics, while
preserving graph, Entity, Memory embedding, query-vector, and question-Entity
caches.

## Graph, recall, and compliance

Dialog Memories and extract-v4 Entities use only conversation session/date,
dialog id, speaker, normalized text, and optional `blip_caption`. Normalized
Entities and speakers link to Memories; NEXT/PREV edges follow deterministic
chronology. QA answers/evidence/categories, judges, previous predictions, and
question-driven ledgers are excluded from construction.

At retrieval, cached question Entities gate candidates; Entity relevance and
signed cosine are fused `0.30/0.70`; exact dense fill returns 25 unique ordered
Memories. B_noseq does not add chronological neighbors. Retrieved Memories go
through unchanged `QARecall`; frozen code owns answering, token-F1,
`recall_acc`, rounding, and aggregation.

## Results

The run completed 10/10 conversations, 1,986/1,986 QA, and all 446 Category-5
rows. There is no LLM-as-Judge.

| Metric | B_noseq | B | B_noseq − B |
|---|---:|---:|---:|
| Official overall F1 | 42.0542% | 42.5680% | -0.5137 pt |
| Official Recall@25 | 82.8114% | 84.4842% | -1.6728 pt |
| Local Categories 1–4 F1 | 51.3764% | 51.9740% | -0.5976 pt |
| Local Categories 1–4 Recall@25 | 84.0672% | 85.0232% | -0.9560 pt |

Category F1/Recall@25: C1 `0.394996/0.666014` (282), C2
`0.402850/0.900829` (321), C3 `0.192135/0.529365` (96), C4
`0.632637/0.911812` (841), C5 `0.098655/0.784753` (446).

Both validators pass; independent report SHA-256 is
`28b72e65fa58ae0d2453d7ad5ebaf7b2cd52575c722617a1dc2fa9387ffe5df1`.
Official aggregation parity, exact top-k, graph constraint, and prompt budget
2,410/5,000 pass. All 75 tests and 16 vendored hashes pass; frozen evaluator
is clean. Query artifact: 1,998 hits, zero misses/live calls. Warm retrieval
took 30.108 seconds; answering made 1,986 requests, used 2,750,742 input and
16,173 output tokens, and took 2,373.874 seconds. Matched cold/warm cost remains
pending.

Mandatory graph constraint: **pass**. Sequence expansion produces positive
descriptive F1 and recall changes inside complete B. All component conditions
are now complete; next run the predeclared component-family statistical
analysis and Holm correction.

Publication gate: `continue`, `paper_ready=false`.
