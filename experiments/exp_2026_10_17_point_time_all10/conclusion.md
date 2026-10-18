# Conclusion — all-ten point-time Reader comparison

## Validity and scope

B `pt_all10_B_v02` and treatment `pt_all10_T_v03` were fresh,
dedicated, absent-at-start formal conditions on
`data/locomo10.json` (SHA-256
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`),
all 10 conversations and 1,986 QA in dataset order, no category or
sample filter. Both independent formal validators passed: 1,986/1,986
rows, graph construction/recall constraint, frozen evaluator manifest
(16/16 files), clean evaluator tree, prompt budget, cache coverage
and output isolation. The exact B/T settings and commands are in
`snapshots/pt_all10_B_v02/` and `snapshots/pt_all10_T_v03/`;
their completed source/config/metric/validator snapshots are
`snapshots/v09_b_v02_complete/` and `snapshots/v12_t_v03_complete/`.
The exact paired analysis command was
`PYTHONDONTWRITEBYTECODE=1 /Users/sun/Documents/git/graph_memory/.venv/bin/python experiments/exp_2026_10_17_point_time_all10/compare.py`,
with source/result/independent audit frozen in
`snapshots/v13_all10_paired_result/`. The source commits differ only
because repository rules required closing B before T; the executable
runner and treatment transformer were byte-identical, and the
comparison rejected other executable/input changes.

## Graph, retrieval and answer protocol

Both conditions reused the same conversation-built bipartite
Entity–Memory graphs. Dialog Memory nodes were linked to cached
`gpt-3.5-turbo` extracted Entity nodes; conversation text, speaker,
session/turn sequence, time annotations and official
`blip_caption` were the build inputs. Graph profile enabled captions,
time annotations and speaker entities. No extraction, normalization,
deduplication or graph/index build was repeated in these conditions;
the validated graph/index cache identities are in each
`run_config.json`. QA questions/answers, gold evidence, category
labels, judge outputs, previous predictions and question-driven
ledgers were excluded from graph construction. Recall used the
conversation-built graph nodes and edges.

Questions used cached Entity keys and the identical complete,
read-only `text-embedding-3-small` ordered query-vector artifact
(SHA-256
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`).
Both runs had 1,997 cache hits, zero misses and zero live query
embeddings. Graph scoring used Entity/semantic weights 0.30/0.70,
signed semantic scores without normalization, Entity relative
threshold 0.5 and top20 per key, Who-only dampening 0.25, degree
discount on, sequence expansion on with secondary scale 0.5,
forced full pool off, and Top25 relevance order. T deterministically
converted a supported relative point time in only the first
retrieved Memory's Reader-facing text for `when`/`how long`
questions; `last week` and `last weekend` stayed verbatim.
All other Memory/context text matched B in the no-provider preflight;
99/1,986 questions changed context, of which 98 are Categories 1–4.
All 1,986 formal Top25 ID lists and official `recall_acc` rows
matched exactly. Thus the gain is in answer F1, not Top25 recall.

The frozen upstream LoCoMo `gpt-3.5-turbo` answer path received
the full prompt as a `system` message, temperature 0, batch size 1
and max 32 completion tokens. Vendored commit
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376` supplied
category-specific per-QA F1 and official evidence recall. There was
no local LLM-as-Judge. The non-data Entity scaffold was 2,410
characters, below the 5,000 limit; no oversized/ineffective
component was active. The treatment added no model/embedding calls.

## Paired F1 result

| Measure | B | Treatment | Paired difference |
|---|---:|---:|---:|
| Categories 1–4 subset F1 (1,540 QA) | 0.518458 | 0.538286 | **+0.019827** |
| Category 2 per-QA F1 (321 QA) | 0.413754 | 0.508349 | **+0.094595** |
| Routed Categories 1–4 QA (98) | — | — | +0.287602 |
| Unrouted Categories 1–4 QA (1,442) | — | — | +0.001629 |

The primary +0.019827 is about **+1.98 percentage points**.
The predeclared 10,000-draw conversation-cluster bootstrap
(seed 20261017) gave 95% interval
**[+0.012375,+0.027652]**; its lower bound and the mean are
positive, so the fixed claim gate passes. All 10 conversation
deltas were positive. Routed rows had 58 wins, 11 losses and 29
ties. An independent one-pass recount matched the point estimate;
an independent NumPy cluster bootstrap gave
[+0.012404,+0.027580]. The exact per-conversation and
per-category results are in `result.json` and
`snapshots/v13_all10_paired_result/independent_audit.json`.
Categories 1–4 subset F1 is a repository-defined mean of frozen
official per-QA F1, **not** an official LoCoMo aggregate.
Category 5 results remain descriptive because option order is
unseeded; the official `recall_acc` is unchanged row for row.

## Cost, limitations and decision

B used 2,744,098 answer-input and 16,243 answer-output tokens;
T used 2,744,442 and 16,250 respectively: +344 input and
+7 output tokens over all 1,986 questions. Both stayed below the
frozen 3.5-million-input, 50,000-output and 14,400-second
ceilings; each condition directory occupied about 1.9 MB, below the
2 GB storage ceiling. No provider billing price is available, so no currency
cost is asserted. Generation wall times differed but are not a
treatment target.

Fresh temperature-0 API calls are not byte-deterministic here:
431 of 1,887 inactive answer strings changed even though their
contexts were identical in preflight. The inactive Categories 1–4
F1 delta was +0.001629, and its separate 10-conversation bootstrap
interval crossed zero (about [−0.00372,+0.00661]); the routed-row
delta was much larger. This supports the observed answer benefit
while leaving model-run variability for a future replication.
Conv26, Conv30 and Conv49 informed the preceding small screens;
the all-ten result is an expanded paired test, not a fully unseen
holdout. No result is claimed for Top25 recall improvement.

**Decision:** the predefined all-ten F1 gate passed. This is a
small graph-compliant, deterministic Reader-context improvement
with a positive full-slice paired effect and no additional AI
calls. For a manuscript, report the exact metric name, 10-conversation
interval, unchanged recall, category concentration and generation
variability; a second fresh paired run would strengthen a
reproducibility claim.
