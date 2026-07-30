# v42 — all-10 B_gate_seq component condition

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `1bb800b113a993d7802159b7f7d849bfefda1d93`.
Source tree: `8c8cf07621f1586174d162d413a683d39d31a1a5`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This formal component condition adds chronological sequence expansion to the
already measured Entity-gated, semantic-only `B_gate` condition. It is not an
A rerun. The condition started from an absent dedicated directory:

```text
outputs/locomo_formal/formal_all10_M2_B_gate_seq_top25_1bb800b_qfrozen_run01/
```

The run did not resume or overwrite any answer.

## Exact command and environment

The run sourced `env_gpt.sh`; secrets are excluded. The Reader connectivity
preflight returned a non-empty `OK` response. The exact effective command and
environment were:

```bash
source ./env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M2_B_gate_seq_top25_1bb800b_qfrozen_run01 \
  --scope all10 --variant B_gate_seq --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact \
    outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

The requested conversation-Entity, question-Entity, and answer model is
`gpt-3.5-turbo`; the embedding model is `text-embedding-3-small`. Conversation
and question Entity extraction were fully cached. The provider's actual answer
model revision is unknown because it was not recorded. There is no judge model
and no seed override. The frozen upstream Category-5 branch retains unseeded
`random.random()` option ordering.

## Exact comparison

All sides use LoCoMo-10 in the same order, 1,986 QA rows, 446 Category-5 rows,
the same graph/index/query artifacts, top-k 25, frozen Reader, and frozen
official metrics.

| Dimension / parameter | Side A: B_gate_seq exact behavior | Side B: B_gate exact behavior | Expected impact of the difference |
|---|---|---|---|
| Graph and candidate gate | 5,882 Memory, 12,808 Entity, 36,227 Entity–Memory edges; threshold `0.50`, top 20/key, who dampening `0.25`, degree discount on, exact dense fill | Exactly the same cached graph and gate | No graph-build, extraction, or initial-pool confound |
| Active scoring | Entity weight `0.0`, semantic weight `1.0`, signed cosine | Exactly the same | No Entity-fusion or semantic-weight difference |
| Sequence | Enabled; chronological NEXT/PREV secondary score scale `0.50` | Disabled; configured `0.50` is inactive | Isolates sequence-neighbor expansion after Entity gating |
| Full A semantic baseline | Unlike A, first applies the conversation-built Entity gate; then uses semantic scoring and sequence expansion | A uses the full Memory pool, semantic-only scoring, and no sequence expansion | B_gate_seq jointly differs from A in gate and sequence |
| Full B method | Same graph, gate, and sequence expansion as B, but Entity/semantic weights are `0.0/1.0` | B uses Entity/semantic weights `0.30/0.70` | Difference to B isolates the missing active Entity-score fusion |
| Query vectors | Immutable artifact SHA `bef99a…986f9f`, L2 float32, 1,986 ordered QA, 1,974 unique questions, 1,536 dimensions | Exactly the same | No semantic-vector confound |
| Reader | One `system` message, temperature 0, 32 completion tokens, batch 1 | Exactly the same | No intended answer-protocol difference |
| Metric | Frozen official per-row token-F1 and evidence `recall_acc`, including official serialization and aggregation | Exactly the same | No metric-definition difference |

Exactly aligned between B_gate_seq and B_gate are graph construction, candidate
gating, active scoring, query vectors, Reader, and metrics. The sole effective
difference is sequence expansion. B_gate_seq is functionally similar to B but
lacks B's active Entity score. It is not structurally aligned with A because A
has no Entity gate.

The retrieval change preserves graph, Entity, embedding, query-vector, and
question-Entity caches, but changes the condition fingerprint and invalidates
contexts, answers, and metrics. Those outputs therefore used a new absent
condition directory.

## Graph extraction and construction

Every normalized dialog becomes a Memory from session date/time, dialog id,
speaker, text, and optional official `blip_caption`. Extract-v4 sends only
normalized conversation text plus caption to the LLM Entity extractor. Entity
names are normalized and deduplicated, speaker Entities are added, and Entity
mentions link to Memories. NEXT/PREV edges follow parsed session time with
deterministic session, turn, and dialog fallbacks.

The graph profile is `memory_only=false`, `use_caption=true`,
`use_time_annotations=true`, and `add_speaker_as_entity=true`. The reused ten
identity-verified graphs contain 5,882 Memories, 12,808 Entities, 36,227
Entity–Memory edges, 5,872 NEXT edges, and 5,872 PREV edges.

Construction uses conversation fields only. QA questions, answers, evidence,
categories, judge results, prior predictions, and question-driven ledgers are
excluded. Retrieval-time question Entities and vectors remain in physically
separate identity-bound caches.

## Recall and answer logic

The normalized question obtains cached extract-v4 Entities and its immutable
query vector. Entity relevance creates a candidate pool at threshold `0.50`,
with at most 20 linked Memories per key, who-only dampening `0.25`, degree
discount, and exact dense fill. Memories are ranked with signed cosine only
(`entity_weight=0.0`, `semantic_weight=1.0`). Chronological NEXT/PREV
neighbors are then expanded with secondary scale `0.50`, and the retriever
returns exactly 25 unique ordered Memory ids.

The query artifact recorded 1,997 lookups and hits, zero misses, and zero live
embedding calls; the 11 lookups beyond the QA denominator come from
initialization/validation. Question-Entity extraction made zero provider
requests because all 1,986 identity-bound entries were cached.

Retrieved Memories are formatted as Dialog evidence and passed through the
unchanged `QARecall` interface. The frozen package owns Category 1–5 prompt
construction and answer branches, decoding, token-F1, `recall_acc`, rounding,
and aggregation.

## Results

The condition completed 10/10 conversations, 1,986/1,986 QA rows, and all 446
Category-5 rows with zero failures.

| Metric | A | B_gate | B_gate_seq | B | seq − gate | seq − A | seq − B |
|---|---:|---:|---:|---:|---:|---:|---:|
| Official overall F1 | 42.0681% | 41.8275% | 41.7666% | 42.5680% | -0.0609 pt | -0.3016 pt | -0.8014 pt |
| Official Recall@25 | 79.7468% | 79.2853% | 79.7217% | 84.4842% | +0.4364 pt | -0.0252 pt | -4.7626 pt |
| Local Categories 1–4 F1 | 51.2645% | 51.0191% | 51.0704% | 51.9740% | +0.0513 pt | -0.1941 pt | -0.9036 pt |
| Local Categories 1–4 Recall@25 | 82.8099% | 82.7017% | 82.7774% | 85.0232% | +0.0757 pt | -0.0325 pt | -2.2458 pt |

These component comparisons are descriptive only. Family-level inference and
Holm correction wait for the remaining predeclared `B_entity` and `B_noseq`
conditions.

| Category | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| 1 | 282 | 0.383652 | 0.649830 |
| 2 | 321 | 0.411237 | 0.896676 |
| 3 | 96 | 0.165833 | 0.482844 |
| 4 | 841 | 0.630639 | 0.900516 |
| 5 | 446 | 0.096413 | 0.691704 |

| Conversation | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| conv-26 | 199 | 0.354457 | 0.796487 |
| conv-30 | 105 | 0.403581 | 0.798886 |
| conv-41 | 193 | 0.464518 | 0.880399 |
| conv-42 | 260 | 0.385065 | 0.719604 |
| conv-43 | 242 | 0.404839 | 0.807624 |
| conv-44 | 158 | 0.465937 | 0.772519 |
| conv-47 | 190 | 0.461584 | 0.796489 |
| conv-48 | 239 | 0.425301 | 0.784937 |
| conv-49 | 196 | 0.429816 | 0.810908 |
| conv-50 | 204 | 0.400103 | 0.825980 |

Four QA rows have empty official evidence. Their raw serialized recall values
sum to 4.0, while official analysis contributes zero and keeps all rows in the
denominator. Exact official-stat aggregation parity passes.

## Judge, validation, prompt budget, and cost

There is no LLM-as-Judge. Formal metrics are frozen official LoCoMo token-F1
and evidence `recall_acc`; Categories 1–4 values are local diagnostics.

Both the in-run and independent validators pass. The independent report
SHA-256 is
`64f6a8e353723683163b3491f7b09e9cccba3b7904e9c6027143d4340a96fd01`.
All 75 experiment tests and 16 vendored hashes pass, and
`code/locomo_eval/` has no uncommitted change.

The non-data Entity prompt scaffold is 2,410/5,000 characters and passes.
No oversized, ineffective, or harmful prompt component was introduced.
Entity-score fusion is intentionally disabled; sequence is the isolated
component under test.

Warm telemetry is partial: cached graph construction, conversation Entity
extraction, Memory embedding, and question-Entity extraction made zero
provider requests; retrieval took 31.507 seconds; answer generation made 1,986
requests, used 2,693,752 input and 16,445 output tokens, and took 1,883.119
seconds. A matched cold/warm probe is still required for the paper cost table.

## Artifact hashes and decision

- `audit.json`: `edf94da0abba5819ff7452b5565616bfac1762d0fb44e9c765e09aadca0188d8`
- `cost_events_warm.json`: `d7250ca37426aa7f4bb63e140c1cb49ebf87f53a91f07b5318f74414003b3a5f`
- `predictions.json`: `82c6fc72eb1ec3e519c9555048a68690bdb824a55cfbc56efee88d6a81162f6d`
- `progress.json`: `bee9a40d58df305d1d52551febecee7fbb919e8e3c5a6b6fedf2f463b74aabf1`
- `query_cache_usage.json`: `c3b2800bc11c157de809415f6d8f64c4727229f5e478f8f1e0b4e1a97ebcfc13`
- `run_config.json`: `c1b9db5987b0298d577ee603808c767765b1ab558d775770ffabf9d014163af6`
- `stats.json`: `177893e47d71f7d41a1f8edbf29501a6812ef75d211fab33c71f62292ff3afed`
- `validation.json`: `1fc9426b7faac9aaf83ee0937ce09e0716fd44d02be7d4018f83524debbbb09d`

Mandatory graph constraint: **pass**. The graph is conversation-only and
answer recall uses its Memory nodes and Entity/sequence edges. Extractors,
normalization, gating, expansion, and answer generation are used only to
improve graph density, retrieval, or answering over graph evidence.

Interpretation: sequence expansion on top of the gate recovers only 0.4364
Recall@25 points and remains 4.7626 points below full B. The full gain cannot
be attributed until `B_entity` and `B_noseq` complete.

Publication gate: `continue`, `paper_ready=false`. Commit and push v42, then
run `B_entity` from a new absent condition directory.
