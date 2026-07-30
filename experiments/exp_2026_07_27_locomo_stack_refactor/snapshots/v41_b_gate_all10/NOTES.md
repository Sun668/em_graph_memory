# v41 — all-10 B_gate component condition

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `faebb2f70007c4146744aa002f986909015b3f77`.
Source tree: `cfc6737a195fcd650bd9315002a55465a92b2c94`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This is the first component condition after the corrected primary A/B
comparison. It isolates Entity-gated candidate selection with signed semantic
ranking while disabling Entity score fusion and sequence expansion. It is not
an A rerun.

The condition started from this absent directory:

```text
outputs/locomo_formal/formal_all10_M2_B_gate_top25_faebb2f_qfrozen_run01/
```

It did not resume or overwrite an answer.

## Exact command and environment

The run sourced `env_gpt.sh`; secrets are excluded. The minimal Reader
connectivity preflight returned a non-empty `OK` response. The exact effective
command and environment were:

```bash
source ./env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M2_B_gate_top25_faebb2f_qfrozen_run01 \
  --scope all10 --variant B_gate --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact \
    outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

The runner, configuration owner, and validator SHA-256 values are recorded in
`result.json`; the full source is recoverable from commit `faebb2f`. Requested
models are `gpt-3.5-turbo` for conversation Entity extraction, retrieval-time
question Entity extraction, and answer generation, plus
`text-embedding-3-small` for Memory and query vectors. Conversation and
question Entity extraction were fully cached in this warm run. The provider's
actual answer-model revision was not recorded and is unknown. There is no judge
model and no random seed override; frozen upstream Category-5 option order
retains its unseeded `random.random()` behavior.

## Exact comparison

The three conditions use the same LoCoMo-10 data and order, 1,986 QA rows,
446 Category-5 rows, Memory embeddings, immutable query vectors, top-k, frozen
Reader, and official metrics. A and B are the accepted v34/v39 and v37
conditions analyzed in v40.

| Dimension / parameter | Side A: exact behavior | Side B: exact behavior | Expected impact of the difference |
|---|---|---|---|
| B_gate versus A graph | B_gate uses 5,882 Memory, 12,808 Entity, 36,227 Entity–Memory, and 11,744 stored sequence edges | A uses 5,882 Memory and 11,744 sequence edges but no Entity nodes/edges | B_gate can form a question-Entity candidate gate; A cannot |
| B_gate versus A candidate pool | Entity-gated pool, threshold `0.50`, top 20/key, who dampening `0.25`, degree discount on, exact dense fill | Full Memory pool | Measures the candidate-gate effect over otherwise semantic-only, no-sequence recall |
| B_gate versus A scoring | Entity weight `0.0`, semantic weight `1.0`, sequence disabled | Exactly the same active scoring weights and sequence state | No active fusion or sequence difference |
| B_gate versus B graph and gate | Same Entity–Memory graph, question Entity extraction, threshold, top-per-key, who dampening, degree discount, and dense fill | Exactly the same | Establishes a matched graph/gate base |
| B_gate versus B fusion | Entity `0.0`, semantic `1.0` | Entity `0.30`, semantic `0.70` | B can reward Entity-linked candidates rather than use Entities only for pool formation |
| B_gate versus B sequence | Disabled; configured scale `0.50` is inactive | Enabled at secondary scale `0.50` | B can add chronological neighbors |
| Dataset / top-k | All 10 conversations, 1,986 QA, top 25 | Same for A and B | No denominator or context-budget difference |
| Query vectors | Immutable artifact SHA `bef99a…986f9f`, L2 float32, 1,986 ordered QA, 1,974 unique questions, 1,536 dimensions | Same for A and B | No semantic-vector confound |
| Answer protocol | One `system` message, temperature 0, 32 completion tokens, batch 1 | Same frozen protocol for A and B | No intended Reader-protocol difference |
| Metric | Frozen official per-row token-F1 and `recall_acc`, official three-decimal serialization and aggregation | Same for A and B | No metric-definition difference |

Exactly aligned with A: semantic weight, inactive Entity score, sequence
disabled, top-k, vectors, Reader, and metric. Functionally similar but
structurally different from A: both rank Memories semantically, while B_gate
first uses conversation-built Entity links to gate candidates. Exactly aligned
with B: graph, gate controls, vectors, Reader, and metric. Intentionally
different from B: Entity/semantic fusion weights and sequence expansion.

The graph and indexes are identical reusable artifacts for B_gate and B. The
retrieval setting changes the condition fingerprint and invalidates contexts,
answers, and metrics, but it does not invalidate graph, conversation Entity,
Memory embedding, immutable query-vector, or question-Entity caches.

## Graph extraction and construction

Each dialog becomes a Memory from session date/time, dialog id, speaker,
normalized dialog text, and optional official `blip_caption`. Extract-v4 sends
normalized dialog text plus caption to the LLM Entity extractor. Entity names
are normalized and deduplicated; speaker Entities are added; Entity mentions
link to Memories. NEXT/PREV Memory edges follow parsed session time with
deterministic session, turn, and dialog fallbacks.

The graph profile is `memory_only=false`, `use_caption=true`,
`use_time_annotations=true`, and `add_speaker_as_entity=true`. The resolved ten
graphs contain 5,882 Memories, 12,808 Entities, 36,227 Entity–Memory edges,
5,872 NEXT edges, and 5,872 PREV edges.

Construction uses conversation fields only. QA questions, answers, evidence,
categories, judge outputs, previous predictions, and question-driven ledgers
are excluded. Query Entities and query vectors remain retrieval-time data in
physically separate caches.

## Recall and answer logic

The question is normalized for the cached extract-v4 question Entity lookup
and separately used to retrieve its immutable vector. Entity matches establish
the candidate pool using relevance threshold `0.50`, at most 20 linked
Memories per key, who-only dampening `0.25`, and degree discount. B_gate then
sorts with signed cosine only (`entity_weight=0.0`,
`semantic_weight=1.0`), performs exact dense fill when needed, disables
sequence expansion, and emits exactly 25 unique ordered Memory ids.

The query artifact records 1,998 lookups and hits, zero misses, and zero live
embedding requests. Twelve non-QA lookups arise from initialization and strict
validation. Question Entity extraction issued zero requests because all 1,986
identity-bound entries were already cached.

Retrieved Memories are formatted as Dialog evidence and passed through the
unchanged `QARecall` interface. The frozen vendored package owns prompt
construction, Category 1–5 answer branches, answer decoding, token-F1,
`recall_acc`, rounding, and aggregation.

## Results

The condition completed all 10 conversations, 1,986 QA rows, and 446
Category-5 rows with zero failures.

| Metric | A | B_gate | B | B_gate − A | B_gate − B |
|---|---:|---:|---:|---:|---:|
| Official overall F1 | 42.0681% | 41.8275% | 42.5680% | -0.2406 pt | -0.7405 pt |
| Official Recall@25 | 79.7468% | 79.2853% | 84.4842% | -0.4615 pt | -5.1989 pt |
| Local Categories 1–4 F1 | 51.2645% | 51.0191% | 51.9740% | -0.2454 pt | -0.9549 pt |
| Local Categories 1–4 Recall@25 | 82.8099% | 82.7017% | 85.0232% | -0.1082 pt | -2.3215 pt |

These component comparisons are descriptive. Inferential component-family
claims wait for all predeclared variants and Holm correction.

Category results:

| Category | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| 1 | 282 | 0.376929 | 0.651603 |
| 2 | 321 | 0.409012 | 0.896676 |
| 3 | 96 | 0.175854 | 0.486323 |
| 4 | 841 | 0.631659 | 0.898138 |
| 5 | 446 | 0.100897 | 0.674888 |

Per-conversation results:

| Conversation | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| conv-26 | 199 | 0.360161 | 0.786437 |
| conv-30 | 105 | 0.412486 | 0.789362 |
| conv-41 | 193 | 0.479446 | 0.882990 |
| conv-42 | 260 | 0.386773 | 0.715758 |
| conv-43 | 242 | 0.400004 | 0.802806 |
| conv-44 | 158 | 0.450728 | 0.759861 |
| conv-47 | 190 | 0.439411 | 0.785963 |
| conv-48 | 239 | 0.426891 | 0.784937 |
| conv-49 | 196 | 0.430811 | 0.810908 |
| conv-50 | 204 | 0.414936 | 0.825980 |

Four rows have empty official evidence. Their serialized recall defaults sum
to 4.0, but official analysis contributes zero for them while retaining all
four in the denominator. The validator confirms exact aggregate parity.

## Judge, validation, prompt budget, and cost

There is no LLM-as-Judge. Formal metrics are frozen official LoCoMo token-F1
and evidence `recall_acc`; Categories 1–4 means are explicitly local
diagnostics.

Both the in-run validator and an independent second invocation pass. The
independent report SHA-256 is
`0fb0af39def06fa175deb6d484f5e7d30e26bf8b85b5a29112c811b87bec8ac6`.
All 75 experiment tests and all 16 vendored hashes pass.
`code/locomo_eval/` has no uncommitted change.

The non-data Entity prompt scaffold is 2,410/5,000 characters and passes.
No oversized, ineffective, or harmful component was introduced; Entity score
fusion and sequence expansion are intentionally disabled for this condition.

Warm telemetry is partial:

- graph construction, conversation Entity extraction, Memory embedding, and
  question Entity extraction: zero provider requests;
- retrieval: 1,986 QA, 29.713 seconds total, 0.01496 seconds/QA mean;
- answer generation: 1,986 requests, 2,694,187 input tokens, 16,425 output
  tokens, 1,980.907 seconds.

A dedicated matched cold/warm probe is still required for the paper cost
table.

## Artifact hashes and decision

The eight formal artifacts have these SHA-256 values:

- `audit.json`: `584821299d9099178015a4f16acf20ded459d9c598244735c716efdc13aa578a`;
- `cost_events_warm.json`: `048d2e30e5c4673d60bfd5af85436b90175afa3d94ed3292cf8cd03daea768bb`;
- `predictions.json`: `f9a8033fc6099f0d57da23a3044df1967d2db251ccf5aaf76ea14b6ff17b752c`;
- `progress.json`: `bee9a40d58df305d1d52551febecee7fbb919e8e3c5a6b6fedf2f463b74aabf1`;
- `query_cache_usage.json`: `30f0d9022ca0bd35494094f356ac6dbf8979bb323c86fce609d499a6876a5c08`;
- `run_config.json`: `011f50427456cc7fcc9f5df9af678ea39e2d94e263419d72f3d92f809d715622`;
- `stats.json`: `6c3f2e53ae534df9ae69f344d377386683a46f5307451055be1656d24cd850e3`;
- `validation.json`: `56dad1df0eb75b59ccff4b1b9be6e436a5e47cd46775e9f6bee066f351068672`.

Mandatory graph constraint: **pass**. Construction is conversation-only and
answer recall uses the conversation-built Entity–Memory graph. Prompts,
extractors, normalization, gating, dense fill, and answer generation are used
only to improve graph density, retrieval, or answering over graph evidence.

Interpretation: the gate alone does not reproduce B's recall gain. B exceeds
B_gate by 5.1989 Recall@25 points, but B_gate_seq and B_entity/B_noseq are
needed before attributing that remainder to Entity fusion, sequence expansion,
or their interaction.

Publication gate: `continue`, `paper_ready=false`. Commit and push v41, then
run B_gate_seq from a new absent condition directory.
