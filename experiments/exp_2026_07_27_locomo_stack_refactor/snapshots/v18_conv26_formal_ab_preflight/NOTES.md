# v18 — conv-26 formal A/B preflight

Source commit: `050c41788d7119a285ebc7623e4cb647d998a73c`.
Source tree: `feb670c58767410056f30b3063d7a3dc01c2df0c`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
Pinned LoCoMo upstream commit:
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

This snapshot records the required post-exact-top-k wiring preflight. It is a
single-conversation, 199-QA diagnostic and is not eligible for a paper metric
or parameter selection. The bulky prediction and telemetry artifacts remain
under:

- `outputs/locomo_formal/preflight_conv26_A_top25_050c417_run02/`
- `outputs/locomo_formal/preflight_conv26_B_top25_050c417_run01/`

The first A attempt, `run01`, failed before producing a QA result because the
first answer request could not connect. Its exact output directory was deleted
instead of resumed. The successful A `run02` and B `run01` each started from
an absent directory and did not use overwrite or a prior prediction.

## Exact commands and environment

Both runs sourced `env_gpt.sh`; secrets are excluded. The resolved models were
`gpt-3.5-turbo` for answer generation and `text-embedding-3-small` for Memory
embeddings. B additionally used `gpt-3.5-turbo` for conversation Entity and
query-Entity extraction; A did not perform Entity extraction.

```bash
source env_gpt.sh
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id preflight_conv26_A_top25_050c417_run02 \
  --scope preflight --samples conv-26 --variant A --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal

source env_gpt.sh
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id preflight_conv26_B_top25_050c417_run01 \
  --scope preflight --samples conv-26 --variant B --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

The frozen Reader used a system message, temperature 0, maximum 32 output
tokens, batch size 1, and the unchanged upstream unseeded Category-5 option
ordering. The retrieval cutoff was exactly 25.

## Graph extraction and construction

Each dialog produced one Memory from dialog id, speaker, raw and normalized
dialog text, optional `blip_caption`, and session `date_time`. B extracted
Entities from normalized dialog text plus caption with the fixed 2410-character
LLM scaffold and added speaker Entities. Extraction used the v4 schema,
normalization, deduplication, and filtering implemented at the source commit.
A intentionally extracted no Entities and had a zero-character extraction
scaffold.

A contained 419 Memory nodes, zero Entity nodes, and 836 bidirectional
NEXT/PREV Memory edges. B contained 419 Memory nodes, 1105 Entity nodes, 2903
Entity–Memory edges, and 836 NEXT/PREV Memory edges. Sequence edges were built
in parsed `date_time` order with session/turn tie-breaking.

Graph construction used only conversation fields: session `date_time`,
`dia_id`, speaker, dialog text, and `blip_caption`. QA questions, answers,
evidence, categories, judge outputs, previous predictions, and
question-driven ledgers were excluded. Question Entities were recall-time
query data in a physically separate cache.

## Retrieval and answer logic

A performed full-pool dense cosine retrieval over all Memory nodes with
semantic weight 1.0 and no Entity or sequence expansion. B formed query
Entities from the question, gated candidates through the Entity–Memory graph,
combined Entity and semantic scores at 0.3/0.7, used Entity relative threshold
0.5, at most 20 Entity matches per question key, who-only dampening 0.25,
degree discounting, and chronological sequence expansion at secondary scale
0.5. Exact-top-k dense fill supplied 25 unique Memory ids when the gated graph
pool was smaller.

Retrieved Memory nodes were formatted as the unchanged LoCoMo Dialog Reader
context and passed to the frozen answer generator. The official vendored
token-F1, `recall_acc`, per-row rounding, Category-5 path, and stats aggregation
were used without modification. No LLM-as-Judge was used.

## Results

| Condition | QA | official overall F1 | official recall@25 | local C1–4 F1 |
|---|---:|---:|---:|---:|
| A | 199 | 0.366 | 0.7965 | 0.4796 |
| B | 199 | 0.390 | 0.8610 | 0.5034 |
| B minus A | 199 paired | +0.024 | +0.0645 | +0.0238 |

These deltas are descriptive preflight signals only. No bootstrap inference or
paper claim is made from one conversation.

Both validators returned `pass`: 199/199 QA rows, 47 Category-5 rows, exact 25
unique valid contexts per row, official-stats parity, clean source, absent
start directory, complete condition identity, graph audit, and prompt budget.
Provider usage was present for exactly 199 answer requests in each run. Warm
answer usage was 270821 input / 1731 output tokens for A and 274770 input /
1817 output tokens for B. These are partial warm observations, not the final
cold/warm cost report.

## Artifact identity

- A prediction SHA-256:
  `71da3717a127303f1b56999c5b86fd4a839a40bbb61c2795a420e70381da479e`
- A stats SHA-256:
  `7b5713d2faa00a35e8c6a8679c0f1998247865b9559e019b1cc6be6ee961c220`
- A audit SHA-256:
  `50f0cc66af0494d6cba2e0e444bbd62fb6f3fe36ccfbee247a914815b7aa83e9`
- B prediction SHA-256:
  `4c42b0025cf861170e407b2c9e7c53d2983ebb0fe6e1bff276e8381787070365`
- B stats SHA-256:
  `c43e61621e662f2a8d1bf14fab68ba870ff366780e1df17d62eb9c130f97f181`
- B audit SHA-256:
  `66ffb3c81332c202ee16c7a4d40618d88a7e43a0f7dbff2a58756117d8c401a2`
- shared embedding-index SHA-256:
  `d3851e488bf733a64320a86edad15d8579fb1fee6b1a2d2c533297dc2fadc2aa`
- `formal_graph.py` SHA-256:
  `ebb369ac9801bb6a18f0b680c46a585448d92be312678645e28def0ff2ce0c51`
- `validate_formal_result.py` SHA-256:
  `6101a83c0632f46cf5acb4dfd32c33bfbf48abac93b18f342623d5496ef8b5b8`

Post-run verification passed 57/57 combined tests, all 16 vendored source
hashes, and the frozen `code/locomo_eval/` clean check.

## Compliance and publication decision

The mandatory graph constraint passes: graph construction is
conversation-only and answer recall traverses conversation-built graph
nodes/edges. Runtime prompts, extractors, normalizers, ranking, and answer
generation operate only on conversation-derived graph evidence and the
recall-time question. Prompt budgets pass at 0/5000 characters for A and
2410/5000 for B. No ineffective prompt component was added in this step.

Publication gate: `continue`. This preflight found no protocol, graph,
validation, snapshot, or engineering blocker. It does not establish paper
readiness. The official DRAGON O1 reproduction, formal all-10 M1 thresholds,
primary significance gates, A/B_embed exact dense control, ablations,
robustness, and full cold/warm cost remain unresolved.
