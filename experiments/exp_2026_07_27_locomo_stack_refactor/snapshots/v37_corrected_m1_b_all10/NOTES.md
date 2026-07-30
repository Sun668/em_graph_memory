# v37 — corrected all-10 primary M1-B after migration

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `41a78125d640d5ebb127d1cb817843b4eef35a8b`.
Source tree: `241f8d432693c8849c08458b67f0abbe4b96a03a`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

The migration archive was restored at the repository root before this run.
Its SHA-256 is
`8ab9dc388b64f2758815decf796fc28ab15e8d70e252e8c7bf1fff219617267f`,
its size is 66,190,646 bytes, its ZIP integrity test passed, and its 64
relative paths exactly match the v36 transfer manifest. The immutable query
artifact SHA-256 is
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.

Corrected M1-B started from this absent condition directory and did not resume
or overwrite any answer:

```text
outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01/
```

## Exact command and environment

The run sourced `env_gpt.sh`; secrets are excluded. A minimal Reader
connectivity preflight returned `OK` before the formal run. The effective
command was:

```bash
source ./env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M1_B_top25_41a7812_qfrozen_run01 \
  --scope all10 --variant B --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact \
    outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

The Python environment is the repository `.venv` on Python 3.9.6. Important
installed versions include NumPy 2.0.2, OpenAI 2.48.0, and Torch 2.8.0.
Resolved requested models were `gpt-3.5-turbo` for cached conversation Entity
extraction, retrieval-time question Entity extraction, and answer generation,
plus `text-embedding-3-small` for Memory and query vectors. The provider's
actual answer-model revision was not recorded and is unknown. No judge model
was used.

The frozen Reader uses one `system` message, temperature 0, maximum 32
completion tokens, batch size 1, and unchanged upstream unseeded Category-5
option ordering.

## Graph extraction and construction

The graph is constructed entirely from conversation data. Each dialog becomes
one Memory node using session `date_time`, dialog id, speaker, normalized
dialog text, and optional `blip_caption`. The extract-v4 LLM Entity extractor
receives normalized dialog text plus caption only. The builder normalizes,
deduplicates, and links extracted Entity mentions to Memory nodes; it adds
speaker Entity nodes and bidirectional NEXT/PREV Memory edges ordered by parsed
real session time with deterministic session/turn/dialog fallbacks.

The committed graph profile is:

- `memory_only=false`;
- `use_caption=true`;
- `use_time_annotations=true`;
- `add_speaker_as_entity=true`;
- dialog normalization `evidence_time_annotations_v1`;
- Entity extraction version `v4`.

The ten graph identities recorded by the formal config resolve to 5,882 Memory
nodes, 12,808 Entity nodes, 36,227 Entity–Memory edges, and 11,744 directed
NEXT/PREV Memory edges. All graph and Memory-index hashes are bound in
`run_config.json`.

Graph construction excludes QA questions, QA answers, QA evidence
annotations, QA categories, judge outputs, previous predictions, and
question-driven ledgers. Questions, question Entities, and the immutable query
vectors are used only after construction for retrieval and never alter graph
nodes or edges.

## Recall and answer logic

M1-B uses the full Entity–Memory graph with:

- Entity score weight `0.30`;
- signed-cosine semantic score weight `0.70`;
- Entity relevance threshold `0.50`;
- at most 20 Entity-linked Memories per query key;
- who-only dampening `0.25`;
- degree discount enabled;
- sequence expansion enabled with secondary scale `0.50`;
- gated candidate pool followed by exact dense fill;
- exactly 25 unique ordered Memory contexts.

The question forms both a retrieval-time Entity query and a vector lookup. The
immutable L2-normalized float32 query artifact covers all 1,986 ordered QA
rows, 1,974 unique questions, and 1,536 dimensions. Runtime recorded 1,997
lookups, 1,997 hits, zero misses, and zero live embedding requests. Eleven
extra lookups come from initialization/validation and do not add QA rows.

The migration archive contained only part of the question-Entity cache.
Consequently, retrieval-time question Entity extraction issued 1,671 external
requests. This is query assistance, not graph construction. It used 1,028,452
input tokens and 90,371 output tokens. The completed cache remains physically
separate from the conversation Entity cache.

The ordered retrieved Memories are formatted as Dialog evidence and injected
through the existing `QARecall` boundary into the frozen vendored LoCoMo
Reader. No experiment runner code defines the answer prompt, F1,
`recall_acc`, per-row rounding, or aggregation.

## Results

The condition covers all 10 conversations, 1,986 QA rows, and 446 Category-5
rows with zero answer failures.

| Metric | M1-B |
|---|---:|
| Official overall F1 | 0.425680 (42.5680%) |
| Official Recall@25 | 0.844842 (84.4842%) |
| Local Categories 1–4 F1 | 0.519740 (51.9740%) |
| Local Categories 1–4 Recall@25 | 0.850232 (85.0232%) |

Official category results:

| Category | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| 1 | 282 | 0.399468 | 0.670936 |
| 2 | 321 | 0.410492 | 0.896156 |
| 3 | 96 | 0.173771 | 0.551938 |
| 4 | 841 | 0.641260 | 0.926874 |
| 5 | 446 | 0.100897 | 0.826233 |

Per-conversation results:

| Conversation | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| conv-26 | 199 | 0.396668 | 0.860975 |
| conv-30 | 105 | 0.387886 | 0.895714 |
| conv-41 | 193 | 0.474311 | 0.903285 |
| conv-42 | 260 | 0.392500 | 0.789904 |
| conv-43 | 242 | 0.401682 | 0.826909 |
| conv-44 | 158 | 0.463114 | 0.833171 |
| conv-47 | 190 | 0.452068 | 0.837721 |
| conv-48 | 239 | 0.436791 | 0.822736 |
| conv-49 | 196 | 0.450704 | 0.852684 |
| conv-50 | 204 | 0.407549 | 0.872961 |

Four rows have empty official evidence. Their raw serialized default recall
sums to 4.0, but the official analysis contribution is zero and all four rows
remain in the denominator. The independent validator confirms exact parity
between serialized per-row values and official aggregate stats.

The restored corrected-A artifact was generated under the former absolute
workspace path. Its strict output-directory identity therefore fails on this
machine. A direct row-level diagnostic gives B-minus-relocated-A overall F1
`+0.004998` and Recall@25 `+0.047374`, but this is descriptive only. It is not
the corrected primary significance result. Corrected A must be rerun from a
new local absent condition directory before the 10,000-resample paired-QA and
conversation-cluster analysis.

## Judge and metric protocol

There is no LLM-as-Judge in this LoCoMo experiment. The frozen official LoCoMo
token-F1 and evidence `recall_acc` are used. The Reader prompt, Category 1–5
branches, Category-5 choice behavior, three-decimal per-row serialization,
and official aggregation remain unchanged. “Categories 1–4 subset F1” is
explicitly a repository-local diagnostic and is not called an official LoCoMo
metric.

## Validation, prompt budget, and cost

The in-run validator and a separately executed validator both pass. The
independent report SHA-256 is
`6b22e25ea0080194bb4ac7d59a43370aed3496b09c6ece0e8b3404a0de51573e`.
All 69 experiment tests and all 16 vendor hashes pass after the run.
`code/locomo_eval/` has no uncommitted diff, and the general writable context
cache `outputs/em_graph/text_embeddings/text-embedding-3-small.npz` is absent.

The non-data Entity-extraction scaffold is 2,410/5,000 characters. The budget
passes. No oversized, ineffective, or harmful runtime prompt component was
active.

Warm telemetry is partial, not a complete cold/warm report:

- graph construction, cached conversation Entity extraction, and embeddings:
  zero provider requests;
- question Entity extraction: 1,671 requests, 1,028,452 input tokens, 90,371
  output tokens, 2,478.881 seconds;
- retrieval: 1,986 QA and 2,511.028 seconds including question Entity time, so
  these two wall times are not additive;
- answer generation: 1,986 requests, 2,744,099 input tokens, 16,269 output
  tokens, 2,305.353 seconds.

A dedicated cold/warm cost probe remains required before the paper cost table.

## Artifact hashes and compliance decision

The eight formal artifacts have these SHA-256 values:

- `audit.json`: `c6ae75a9e58516adad8979db8d6925b172d16907bca7fcf3ea5b5597699980e0`;
- `cost_events_warm.json`: `7ea432e10901997a39c51b0711c17e436d6a718bcd53a51991d82885b2c628b4`;
- `predictions.json`: `9dcde0e2f993b1a0199a7e17ccb66a4b307e7355ba7b60aff139ade792c75069`;
- `progress.json`: `bee9a40d58df305d1d52551febecee7fbb919e8e3c5a6b6fedf2f463b74aabf1`;
- `query_cache_usage.json`: `c3b2800bc11c157de809415f6d8f64c4727229f5e478f8f1e0b4e1a97ebcfc13`;
- `run_config.json`: `01e4ff01e361c55fba67c77b87577eadf6b7cde4a6c89a5023098c0fa86ec0f5`;
- `stats.json`: `6a7ae63b72db737353b1c5a2f9ae5171090324ec3efa05ffb3022c2571d8b3de`;
- `validation.json`: `10a2f92257336fb120c6021b586ba3eb4424a7034ce07064cfbaaf4de231cf3f`.

Mandatory graph constraint: **pass**. Graphs use conversation-only inputs;
answer recall traverses conversation-built graph nodes and edges; all prompts,
extractors, scoring, expansion, and answer generation are limited to graph
density, retrieval, and answering over retrieved graph evidence.

Publication gate: `continue`, `paper_ready=false`. Freeze and push this
snapshot, rerun corrected A locally, freeze/push it, and then perform strict
corrected A/B significance before launching dependent ablations.
