# v24 — formal all-10 M1-A at top-k 25

Source commit: `3e3a33b49c39468dd14b1cead161e1df413332d5`.
Source tree: `99cbd327a0cab169badf2fe530da72f68175e902`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
Pinned LoCoMo upstream commit:
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

This is the first paper-metric-eligible condition in the formal matched-stack
M1 experiment. The bulky generated artifacts remain under:

```text
outputs/locomo_formal/formal_all10_M1_A_top25_3e3a33b_run01/
```

## Exact command and environment

The run sourced `env_gpt.sh`; secrets are excluded. It began from an absent
condition directory and did not resume or overwrite any prediction.

```bash
source env_gpt.sh
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M1_A_top25_3e3a33b_run01 \
  --scope all10 --variant A --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

Resolved models were no extraction model, `text-embedding-3-small` for Memory
embeddings, and requested `gpt-3.5-turbo` for answer generation. A non-metric
identity preflight immediately before M1-A returned actual model
`gpt-3.5-turbo-0125`, response `OK`, and provider usage of 10 input / 2 output
tokens. The formal warm event aggregate records the requested model's exact
request/token totals but not a per-response actual-model list; the preflight
is therefore disclosed separately and is not treated as an M1 metric.

The frozen Reader used one system message, temperature 0, maximum 32 output
tokens, batch size 1, and the unchanged upstream unseeded Category-5 option
ordering.

## Graph extraction and construction

M1-A is the pure-Memory baseline. Each dialog produced one Memory from session
`date_time`, dialog id, speaker, raw and normalized dialog text, and optional
`blip_caption`. It performed no Entity extraction and made no conversation-
Entity or question-Entity model request. Memory sequence edges were built in
parsed real `date_time` order with session/turn tie-breaking.

Across the ten conversations the graph contained:

- 5,882 Memory nodes;
- 0 Entity nodes and 0 Entity–Memory edges;
- 11,744 directed NEXT/PREV Memory edges.

Graph construction used only conversation fields. QA questions, answers,
evidence, categories, judge outputs, previous predictions, and
question-driven ledgers were excluded. The complete graph audit is preserved
in the generated `audit.json`.

## Retrieval and answer logic

For each raw QA question, A performed full-pool dense cosine retrieval over
all Memory nodes for that conversation using semantic weight 1.0, Entity
weight 0.0, no Entity gate, and no sequence expansion. Signed cosine scores
were preserved and dense fill returned exactly 25 unique dialog ids per QA.
The otherwise frozen parameters were sequence secondary scale 0.5, Entity
relative threshold 0.5, Entity top-k 20, who-only dampening 0.25, and degree
discount enabled; these are inactive in A.

Retrieved Memory nodes were formatted as the unchanged LoCoMo Dialog Reader
context. The vendored official answer prompt, token-F1, `recall_acc`,
per-row three-decimal serialization, Category-5 branch, and stats aggregation
were used without modification. No LLM-as-Judge was used.

## Formal results

The result covers all 10 conversations, all 1,986 QA rows, and all 446
Category-5 rows.

| Metric | Value |
|---|---:|
| Official overall F1 | 0.422642 (42.2642%) |
| Official Recall@25 | 0.797468 (79.7468%) |
| Local Categories 1–4 F1 | 0.509979 (50.9979%) |
| Local Categories 1–4 Recall@25 | 0.828099 (82.8099%) |

Official category results:

| Category | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| 1 | 282 | 0.380833 | 0.651603 |
| 2 | 321 | 0.412589 | 0.896676 |
| 3 | 96 | 0.173073 | 0.482844 |
| 4 | 841 | 0.628913 | 0.900516 |
| 5 | 446 | 0.121076 | 0.691704 |

Per-conversation results:

| Conversation | QA | F1 | Recall@25 |
|---|---:|---:|---:|
| conv-26 | 199 | 0.365930 | 0.796487 |
| conv-30 | 105 | 0.405219 | 0.798886 |
| conv-41 | 193 | 0.474482 | 0.882990 |
| conv-42 | 260 | 0.389281 | 0.719604 |
| conv-43 | 242 | 0.403756 | 0.807624 |
| conv-44 | 158 | 0.467133 | 0.772519 |
| conv-47 | 190 | 0.449321 | 0.796489 |
| conv-48 | 239 | 0.427937 | 0.784937 |
| conv-49 | 196 | 0.439408 | 0.810908 |
| conv-50 | 204 | 0.421191 | 0.825980 |

Four QA rows have empty evidence and a raw serialized recall value of 1. For
official/category/per-conversation analysis they each contribute 0 and remain
in the denominator. The resulting aggregate exactly matches the frozen
official stats. Raw serialized recall remains in `predictions.json` for audit.

M1-A alone does not test the primary method claim and is not subject to the
M1-B official-performance terminal threshold. It is the predeclared matched
baseline for the next B run.

## Validation, prompt, and cost observations

The runner validator and a separate post-run validator invocation both
returned `pass`. They independently confirmed:

- exact 10 / 1,986 / 446 counts and source order;
- exactly 25 unique valid ordered context ids for every QA;
- complete predictions, F1, recall, and context fields;
- official stats parity;
- absent-directory start, no resume, and one resolved condition;
- conversation-only graph audit and graph-retrieval eligibility;
- prompt scaffold 0/5000 characters.

Warm telemetry records 1,986 answer requests, 2,694,179 input tokens, 16,350
output tokens, and 1,986 retrieval latency observations. Its stage wall fields
are explicitly non-exclusive. `cost_report.py` correctly rejects this partial
warm-only event document because the final cost report requires a combined
cold/warm six-stage manifest plus graph/index/cache disk artifacts. No complete
cost claim is made in this snapshot.

Post-run verification passed 62/62 combined tests, all 16 vendored source
hashes, and the frozen `code/locomo_eval/` clean check.

## Artifact identity

- condition fingerprint:
  `8dbb51faaeb893e6aa7d411e39985a75e707fe2767d5ee04e461b1cff06813a0`
- prediction SHA-256:
  `c777b8aca86783f6af1fcbea3bd35e2b438e02a9fdda44daef718f212762b431`
- stats SHA-256:
  `8ceb5f6667e2c0498a7f40a79a46a88af5382a4735f5758039abd1d8f9b3ccb1`
- audit SHA-256:
  `0244c7eaae103fc207b12f81a983be1553925df6ef8e351b292b839fc097dc4d`
- validation SHA-256:
  `f2c1ff7a11fe7946f39a5d6b882a04e3acf72736f224d546f7a2c23e68b1c7a7`
- run-config SHA-256:
  `bf672d9d89b5d5e8a5c3f4b8508556fa048c33952c551076c7b02a4cf49f7899`
- warm-events SHA-256:
  `42232582914083b4fecf67081ebef6a8390af5d4ce37086cac830f695786053d`
- `formal_graph.py` SHA-256:
  `ebb369ac9801bb6a18f0b680c46a585448d92be312678645e28def0ff2ce0c51`
- `validate_formal_result.py` SHA-256:
  `b377427f8a14f8db57d2ec3b24e78b5c9554fcfe34882bd017deebf7b511cb63`

## Compliance and publication decision

The mandatory graph constraint passes. Graph construction is
conversation-only, recall uses the conversation-built Memory graph and its
nodes/edges, and the frozen answer generator receives only the question and
retrieved graph evidence. No invalid, redundant, oversized, or measured
harmful prompt component was active; the non-data retrieval scaffold is zero
characters.

The user-authorized O1 waiver remains limited to the v22 reproduction
tolerance. O1 remains external-reference-only. M1-A introduces no new
protocol, graph, metric, validation, or reproducibility blocker.

Publication gate: `continue`, `paper_ready=false`. The next step is a fresh
formal all-10 M1-B run from the committed v24 state. M1-B must pass F1
`>=0.496`, Recall@25 `>=0.757`, and the subsequent paired-QA and
conversation-cluster B-versus-A significance gates before any secondary
experiment starts.
