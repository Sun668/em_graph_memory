# v25 — formal all-10 M1-B at top-k 25; official-performance stop

Source commit: `484ccf0395346cbc7eab0c09f82e91e039a005a8`.
Source tree: `5474be88c45c31f4c05b0d78c594fb27ab047a83`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
Pinned LoCoMo upstream commit:
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

This is the predeclared complete Entity–Memory condition in the formal
matched-stack M1 experiment. The bulky generated artifacts remain under:

```text
outputs/locomo_formal/formal_all10_M1_B_top25_484ccf0_run01/
```

## Exact commands and environment

The graph cache was built first, then the formal answer run sourced
`env_gpt.sh`; secrets are excluded. The condition directory was absent at
start, and the run did not resume or overwrite predictions.

```bash
source env_gpt.sh
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/run.py build-graphs \
  --cache-dir outputs/em_graph --extract-model gpt-3.5-turbo --variants B

source env_gpt.sh
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M1_B_top25_484ccf0_run01 \
  --scope all10 --variant B --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

Resolved requested models were `gpt-3.5-turbo` for conversation-Entity and
query-Entity extraction, `text-embedding-3-small` for Memory embeddings, and
`gpt-3.5-turbo` for answer generation. The provider does not preserve an
actual-model identity per formal response; the separate identity preflight
before M1-A resolved that same requested answer model to
`gpt-3.5-turbo-0125`, but it is not treated as an M1-B metric.

The frozen Reader used one system message, temperature 0, maximum 32 output
tokens, batch size 1, and the unchanged upstream unseeded Category-5 option
ordering.

## Graph extraction and construction

Each dialog produced one Memory from session `date_time`, dialog id, speaker,
raw and normalized dialog text, and optional `blip_caption`. The conversation
Entity extractor received only normalized dialog text and optional caption
under extraction schema v4. The builder also added speaker Entities. Entity
normalization, deduplication, and schema filtering followed the committed
builder; Entity–Memory mention edges joined extracted/speaker Entities to
Memories, and directed NEXT/PREV edges joined Memories in parsed real
`date_time` order with session/turn tie-breaking.

Across the ten conversations the graph contained:

- 5,882 Memory nodes;
- 12,808 Entity nodes;
- 36,227 Entity–Memory mention edges;
- 11,744 directed NEXT/PREV Memory edges.

Graph construction used only conversation fields. QA questions, answers,
evidence, categories, judge outputs, previous predictions, and
question-driven ledgers were excluded. Query-Entity extraction was performed
only at retrieval time into a physically separate question cache.

## Retrieval and answer logic

For each raw QA question, B extracted query Entities, selected/gated related
graph candidates, fused signed cosine semantic score at weight 0.7 with
Entity score at weight 0.3, applied a 0.5 Entity-relative threshold, top 20
Entities per query key, who-only dampening 0.25, degree discount, and
NEXT/PREV sequence expansion at secondary scale 0.5. Dense fill guaranteed
exactly 25 unique dialog ids per QA.

All ten Memory embedding indexes were the exact canonical indexes reused by
M1-A. Retrieved Memory nodes were formatted as the unchanged LoCoMo Dialog
Reader context. The vendored official answer prompt, token-F1, `recall_acc`,
per-row three-decimal serialization, Category-5 branch, and stats aggregation
were used without modification. No LLM-as-Judge was used.

## Formal results

The result covers all 10 conversations, all 1,986 QA rows, and all 446
Category-5 rows.

| Metric | M1-B | M1-A | B − A |
|---|---:|---:|---:|
| Official overall F1 | 0.426772 (42.6772%) | 0.422642 | +0.004130 |
| Official Recall@25 | 0.843415 (84.3415%) | 0.797468 | +0.045947 |
| Local Categories 1–4 F1 | 0.522448 (52.2448%) | 0.509979 | +0.012469 |
| Local Categories 1–4 Recall@25 | 0.848716 (84.8716%) | 0.828099 | +0.020618 |

Official category results:

| Category | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| 1 | 282 | 0.393152 | 0.669752 |
| 2 | 321 | 0.419542 | 0.893040 |
| 3 | 96 | 0.154260 | 0.551938 |
| 4 | 841 | 0.647109 | 0.925685 |
| 5 | 446 | 0.096413 | 0.825112 |

Per-conversation results:

| Conversation | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| conv-26 | 199 | 0.393638 | 0.860975 |
| conv-30 | 105 | 0.416924 | 0.895714 |
| conv-41 | 193 | 0.468155 | 0.898104 |
| conv-42 | 260 | 0.392885 | 0.789904 |
| conv-43 | 242 | 0.410707 | 0.821397 |
| conv-44 | 158 | 0.464342 | 0.833171 |
| conv-47 | 190 | 0.439711 | 0.837721 |
| conv-48 | 239 | 0.446866 | 0.826921 |
| conv-49 | 196 | 0.443276 | 0.847582 |
| conv-50 | 204 | 0.406716 | 0.870510 |

Four QA rows have empty evidence and a raw serialized recall value of 1. For
official/category/per-conversation analysis they each contribute 0 and remain
in the denominator. The aggregate exactly matches the frozen official stats.

## Fixed gate decision

The predeclared M1-B terminal thresholds were:

- official overall F1 `>=0.496`;
- official Recall@25 `>=0.757`.

Recall passes by 0.086415. F1 fails by 0.069228 and is 0.089228 below the
LoCoMo `0.516` best-F1 anchor. Although B has a positive mean retrieval signal
over A, that does not override the independent official-performance gate.
Under the plan, significance, ablations, robustness, O2, and full cost
experiments must not be launched.

No B-versus-A bootstrap was run because the plan explicitly applies this
threshold before significance. Therefore the positive mean differences above
must not be described as statistically supported.

## Validation, prompt, and cost observations

The runner validator and a separate post-run validator invocation both
returned `pass`. They confirmed:

- exact 10 / 1,986 / 446 counts and source order;
- exactly 25 unique valid ordered context ids for every QA;
- complete predictions, F1, recall, and context fields;
- official stats parity;
- absent-directory start, no resume, and one resolved condition;
- conversation-only graph audit and graph-retrieval eligibility;
- Entity prompt scaffold 2,410/5,000 characters.

Warm telemetry records 1,775 query-Entity requests with 1,092,274 input and
95,258 output tokens, plus 1,986 answer requests with 2,743,677 input and
16,207 output tokens. Retrieval has 1,986 latency observations: mean 2.6899 s,
p50 2.9271 s, p95 3.8884 s, p99 6.3691 s, and max 58.5081 s. Stage wall
fields overlap and are not additive. This warm-only event document is not a
complete cost report because the required matched cold/warm six-stage
manifest and disk aggregation were not run after the terminal metric failure.

Post-run verification passed 62/62 combined tests, all 16 vendored source
hashes, and the frozen `code/locomo_eval/` clean check.

## Artifact identity

- condition fingerprint:
  `32fc90680292460a1bc8f88e38cebfc96e2e2fda68ef162f1f11572515791ac2`
- prediction SHA-256:
  `f0fbfa2aff13647eafe34b0604f97e9547ea1dcb90bf06b831d7dc18bb93a04c`
- stats SHA-256:
  `312a6d09bd1f5bf2ceef1cfa4e2c77b87a67f030b6067bdc54678fe37c193854`
- audit SHA-256:
  `f66d7748a5b684619f6f14cc53d2ddc84ce2d11f6aae4e7932af84425fba3e84`
- validation SHA-256:
  `4dcb89440257b4444cdd06ab682c9e4aef62afba075be3597afe65c15f321f79`
- run-config SHA-256:
  `8a3d55264419adc0ac7c062c5b0bd8f551341ed62df99659724f02795b967e16`
- warm-events SHA-256:
  `0a0f5e6e28de49773cab71abc75d0c9384aafadf51f0c411a2b1b8ce24262104`
- `formal_graph.py` SHA-256:
  `ebb369ac9801bb6a18f0b680c46a585448d92be312678645e28def0ff2ce0c51`
- `validate_formal_result.py` SHA-256:
  `b377427f8a14f8db57d2ec3b24e78b5c9554fcfe34882bd017deebf7b511cb63`

## Compliance and publication decision

The mandatory graph constraint passes. Graph construction is
conversation-only; recall uses the conversation-built Entity–Memory graph,
Memory sequence edges, and retrieval-time question only as a query; the
frozen answer generator receives only the question and retrieved graph
evidence. Extraction, normalization, gating, fusion, sequence expansion, and
answer generation are used only to improve graph information density,
retrieval, or answers over retrieved graph evidence.

Prompt budget passes, and no oversized prompt component was active. No source
component was changed after observing this result.

Publication gate: `stop`, `paper_ready=false`. The user-authorized O1 waiver
does not waive this distinct M1-B F1 threshold. The publication experiment
track stops before significance and secondary API spend.
