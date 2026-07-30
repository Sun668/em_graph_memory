# LoCoMo publication execution plan

## 1. Objective

The remaining work must establish three separate claims:

1. **Official protocol comparability**: the reported outputs use the pinned
   LoCoMo prompt, answer generation, token-F1, `recall_acc`, rounding, and
   aggregation logic.
2. **Method effectiveness**: EM-Graph outperforms a matched pure-Memory dense
   baseline when all non-method conditions are held constant.
3. **Official baseline contextualization**: the LoCoMo DRAGON Dialog-RAG
   number is retained as an external reference because the local O1 run did
   not meet the exact-reproduction tolerance. A matched local DRAGON-stack
   EM-Graph run may be reported only as a local diagnostic, not as a controlled
   comparison to the official table.

No active file under `code/locomo_eval/` may be modified while executing this
plan. All DRAGON adapters, validators, statistical analysis, cost reporting,
and experiment orchestration must remain outside the frozen evaluator.

### Execution status — resumed after O1 waiver and cross-model gate correction

The corrective O1 retrieval run from source `d570275` matched Python 3.9.18,
PyTorch 2.0.1, Transformers 4.35.0, tokenizers 0.14.1, NumPy 1.26.0, and
pinned Hugging Face revisions. It passed 10/1986 exact-top-25 checks but
produced official serialized-contribution Recall@25 `78.1133`, still 1.4133
points from the official `76.7`. This exceeds the fixed ±1 point tolerance.

The new and v19 top-25 sets were identical for all 1986 QA rows; only nine
within-set orders changed. The only remaining runtime difference is CPU versus
the upstream CUDA 11.7 environment, which is unavailable on the current
machine. Snapshot: `v22_o1_corrective_retrieval_stop`.

On 2026-07-27, the user explicitly authorized continuing despite this O1
tolerance failure, conditional on later formal experiments proving the method
better. O1 remains `o1_accepted=false`; the official `76.7`/`41.0` values are
external references, and no exact-reproduction or controlled-official-baseline
claim is permitted. Execution resumes at M1. The M1-B official-performance
thresholds, B-versus-A significance gate, graph/formal validator gates, and
A/B_embed exact ordered-context gate remain mandatory. Snapshot:
`v23_user_authorized_o1_waiver`.

Formal all-10 M1-A then completed from source `3e3a33b`. Both the in-run and
independent validators pass exact 10/1986/446 counts, per-QA ordered top-25
contexts, official stats parity, isolated output, graph/no-test audit, and
prompt budget. The matched pure-Memory baseline is overall F1 `42.2642%` and
Recall@25 `79.7468%`; local Categories 1–4 F1 is `50.9979%`. Four
empty-evidence rows retain raw serialized recall for audit but contribute zero
to every official recall analysis while all QA remain in the denominator.
This baseline does not by itself establish method effectiveness or paper
readiness. Snapshot: `v24_m1_a_all10`. Execution continues to M1-B, where the
non-waived official-performance thresholds apply.

Formal all-10 M1-B then completed from source `484ccf0`. Both validators pass
exact 10/1986/446 counts, ordered top-25 contexts, official stats parity,
isolated output, graph/no-test audit, and the 2,410/5,000-character prompt
budget. Overall F1 is `42.6772%`, Recall@25 is `84.3415%`, and local
Categories 1–4 F1 is `52.2448%`. Relative to A, the untested mean differences
are +0.4130 F1 points and +4.5947 recall points. Recall passes the fixed 75.7%
floor, but F1 misses the fixed 49.6% floor by 6.9228 points and therefore
activates terminal condition 3 before significance. Snapshot:
`v25_m1_b_official_performance_stop`. Publication gate: `stop`,
`paper_ready=false`; no secondary experiment may start under this plan.

On 2026-07-28, direct inspection of page 7 of the final upstream LoCoMo PDF
established that `51.6` is Table 2's `gpt-4-turbo` 128K long-context result,
whereas the official matched Reader class for RAG is Table 3's
DRAGON + `gpt-3.5-turbo` Dialog@25 result (`41.0` F1, `76.7` Recall@25).
The `49.6 = 51.6 - 2` gate therefore mixed different Reader models and
inference settings and is invalid for M1. The v25 metrics remain immutable,
but its stop decision is superseded by
`v26_cross_model_gate_correction`.

The user directed the track to complete the planned experiment matrix before
revisiting performance and paper interpretation. Intermediate metrics and
significance are recorded, not used for early stopping. Protocol, mandatory
graph, formal-output, prompt-budget, snapshot, and A/B_embed exact-equality
validity gates remain active. Publication gate: `continue`,
`paper_ready=false`.

The predeclared v27 primary significance analysis then completed with 10,000
paired-QA and whole-conversation cluster resamples. B minus A Recall@25 is
`+4.5947` points and both 95% intervals exclude zero (`p=0.0002` each).
Overall F1 is `+0.4130` points, but both intervals cross zero (paired
`p=0.4524`, cluster `p=0.3008`). The result supports a significant retrieval
claim but not a significant overall final-answer F1 claim. Both formal inputs,
official no-evidence recall aggregation, mandatory graph constraint, frozen
evaluator, and prompt budgets pass. Per the user instruction, execution
continues to structural ablations. Snapshot:
`v27_primary_ab_significance`. Publication gate: `continue`,
`paper_ready=false`.

Formal all-10 B_embed then passed the standalone output validator but failed
the mandatory dense-control gate: 61/1986 ordered context lists differ from
historical M1-A, including 10 top-25 set differences. The Memory indexes are
identical. Ten independently loaded whole-file text embedding cache objects
overwrote one another's query-vector additions; the surviving cache covers
only 838/1986 question lookups, and its recoverable vectors reproduce
B_embed's order. The formal config did not bind query-cache content or
coverage. Snapshot: `v28_m2_embed_dense_control_failure`.

Publication gate: `stop_for_control_repair`, `paper_ready=false`. B_embed is
diagnostic only. No dependent ablation may start until a complete immutable
query-vector artifact is shared and hash-bound, corrected A/B_embed passes
exact equality, and corrected A/B significance is rerun.

The v29 source milestone implements that repair without changing the frozen
evaluator. Whole-file text caches now merge only pending additions under
path/file locks and replace atomically. Formal graph conditions require a
read-only dataset/model/role/ordered-QA/hash-bound query artifact, fail on any
miss, record runtime hit/miss/live-request counts, and require A/B_embed to
share the artifact SHA before exact ordered-context comparison. The complete
68-test suite and all 16 vendor hashes pass. Snapshot:
`v29_query_embedding_artifact_gate`.

Publication gate: `continue_tooling_only`, `paper_ready=false`. No metric is
restored until the artifact is built from an absent path and corrected
A/B_embed and A/B are rerun.

The v30 build then explicitly deleted only the proven corrupt text cache and
created the immutable query artifact from absent artifact/report paths. It
covers all 1,986 ordered QA rows with 1,974 unique, 1,536-dimensional vectors.
Independent identity, order, finite-value, and L2-norm validation passes.
Artifact SHA-256 is
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.
The build used 198 embedding requests and 23,936 provider input tokens.
Snapshot: `v30_query_embedding_artifact_build`.

Publication gate: `continue`, `paper_ready=false`. No answer or metric was
generated. Proceed to retrieval-only A/B_embed exact equality before paid
formal reruns.

The corrected retrieval-only A/B_embed gate passed 1,986/1,986 exact ordered
context lists with 3,972/3,972 artifact hits and zero misses/live requests
(`v33`). Corrected formal M1-A then completed from source `76fcf5b` and an
absent condition directory. Both validators pass 10/1,986/446, official stats,
graph/prompt, artifact identity, and zero-fallback runtime gates. Its official
F1 is `42.0681%`, Recall@25 is `79.7468%`, and local Categories 1–4 F1 is
`51.2645%`. Recall is exactly unchanged from historical v24 A; Reader variance
changed F1, so the corrected claim will use only newly rerun conditions.
Snapshot: `v34_corrected_m1_a_all10`.

Publication gate: `continue`, `paper_ready=false`. Corrected B_embed is next
and must use the same artifact SHA and exactly match all ordered context ids
before corrected B and significance are run.

The first corrected B_embed formal attempt (`run01`) then aborted before its
first successful answer after ten external Reader connection errors. It
generated no prediction or metric and did not change graph, index, query
artifact, evaluator, or general cache state. Snapshot:
`v35_b_embed_reader_connection_abort`.

Publication gate: `continue_after_connectivity_preflight`,
`paper_ready=false`. This external availability failure does not waive any
gate. Retry from a new absent condition only after a successful minimal Reader
connectivity preflight.

The connectivity preflight and corrected B_embed run02 subsequently
completed. The formal result covers 1,986 QA rows with F1 `42.0677%` and
Recall@25 `79.7468%`; both validators, official aggregation, graph/prompt,
query-artifact, and zero-fallback checks pass. Against corrected A, the same
query-artifact SHA is bound and all 1,986 ordered top-25 context-id lists are
exactly equal with zero mismatches. Snapshot:
`v36_corrected_b_embed_all10_dense_control`.

Publication gate remains `continue`, `paper_ready=false`: the corrected dense
control is now closed, but corrected B, corrected A/B significance, structural
and input ablations, sensitivity, O2/cost, and the final audit remain. Per user
instruction, execution pauses after the v36 commit/push for migration to
another computer. The transfer ZIP and exhaustive 64-path manifest are stored
with the v36 record; no post-v36 B experiment has started.

### 1.1 Mandatory publication go/no-go after every step

Every source milestone, preflight, and metric result must end with one explicit
publication-readiness decision:

- `continue`: protocol comparability, graph compliance, reproducibility, and
  the prospect of a publishable result all remain intact;
- `stop`: do not launch the next experiment and do not claim that the current
  evidence is sufficient to write the paper.

Stop immediately if any of the following occurs:

1. the official metric, generation, dataset, or retrieval protocol cannot be
   matched closely enough for the planned comparison;
2. the official O1 DRAGON reproduction misses the predeclared tolerance and
   the mismatch cannot be corrected without changing the frozen protocol.
   This condition is waived only for the already recorded v22 O1 result by
   explicit user authorization; O1 must remain labeled non-reproduced and
   external-reference-only;
3. the mandatory graph constraint, exact output validation, snapshot
   reproducibility, or A/B_embed dense-control gate fails.

The former M1-B `49.6` F1 stop is retired: `51.6` belongs to a different
`gpt-4-turbo` 128K long-context condition. The primary B-versus-A significance
result must still be reported and will constrain the final paper claim, but
under the user's 2026-07-28 instruction it is not an intermediate early-stop
condition. Complete the matrix, then make one final performance decision.

Source-only steps may return `continue_tooling_only`: this means no blocker has
yet been found, not that the paper is ready. No response, note, or conclusion
may say “ready to write/submit” until all planned formal results have passed
these terminal gates.

## 2. Phase 0: freeze the experiment foundation

### 2.1 Freeze the current state

Before implementing another experiment feature:

- commit this plan and the updated `next_steps.md`;
- verify that the worktree contains no unrelated changes;
- verify that `code/locomo_eval/` has no uncommitted difference;
- verify every vendored upstream file against
  `code/locomo_eval/vendor/MANIFEST.sha256`;
- record the source commit used as the base of the formal experiment stack;
- create a recovery snapshot before changing a runner, retriever, validator,
  or reporting implementation.

### 2.2 Add external formal-result tools

Implement the following files inside this experiment directory:

```text
validate_formal_result.py
significance_report.py
cost_report.py
official_dragon.py
```

These tools must not reimplement or change an official LoCoMo metric.

#### `validate_formal_result.py`

For every formal output, verify:

- exactly 10 conversations;
- exactly 1986 QA rows;
- exactly 446 Category-5 rows;
- sample ids and QA order match the pinned dataset;
- prediction, F1, recall, and context fields are present for every QA;
- each context-id list has no duplicate;
- each list contains exactly `min(top_k, available dialogs)` ids;
- the official stats file corresponds to the same prediction key;
- the graph/no-test audit passes;
- prompt-scaffold budgets pass;
- the output directory contains exactly one resolved experiment condition;
- the run did not resume a previous answer or result.

#### `significance_report.py`

Use official per-row F1 and recall values as immutable inputs and compute:

- paired QA bootstrap with 10,000 resamples;
- conversation-cluster bootstrap with 10,000 resamples;
- a fixed external-analysis seed of `20260727`;
- mean B-minus-A difference and 95% confidence interval;
- for recall mean/bootstrap/category/per-conversation analysis, define each
  official recall contribution as the serialized per-QA recall when evidence
  is non-empty and `0` when evidence is empty, while retaining every QA row in
  the denominator; preserve raw serialized recall separately for audit;
- Category 1–5 breakdown;
- Categories 1–4 subset diagnostics, explicitly labeled non-official;
- per-conversation differences.

The predeclared primary hypothesis test is B versus A. Component ablations may
report confidence intervals. If the paper claims simultaneous significance for
multiple components, apply a Holm correction across those component tests.

#### `cost_report.py`

Record, at minimum:

- graph-construction wall time;
- entity-extraction request count and input/output tokens;
- embedding request count and wall time;
- query-entity request count, tokens, and latency;
- mean and percentile retrieval latency per QA;
- answer-generation request count and tokens;
- graph, embedding-index, and cache disk usage;
- cold-cache and warm-cache measurements.

## 3. Phase 1: official DRAGON experiment track

This phase establishes direct comparability with the LoCoMo Dialog-RAG
baseline.

### 3.1 Reproduce official DRAGON behavior

Setting `EM_GRAPH_EMBED_MODEL=dragon` alone is not an official reproduction.
The reproduction path in `official_dragon.py` must preserve all of the
following upstream behavior:

| Component | Required behavior |
|---|---|
| Dialog embedding text | `speaker said, "raw text"` plus ` and shared blip_caption` when present |
| Date/time | Excluded from embedding text; added only to the Reader context wrapper |
| Query text | Raw QA question |
| Query encoder | `facebook/dragon-plus-query-encoder` |
| Context encoder | `facebook/dragon-plus-context-encoder` |
| Vectors | No L2 normalization |
| Similarity | Raw query/context dot product |
| Ranking | Descending `np.argsort` behavior |
| Reader | Frozen LoCoMo GPT-3.5 batch-size-1 protocol |
| Metrics | Frozen official F1, recall, rounding, and aggregation |

The implementation must be tested against the pinned upstream code for input
text, encoders, vector normalization, scoring, ranking, and Reader context
format.

The formal O1 cache must additionally bind the exact Python, PyTorch,
Transformers, tokenizers, NumPy, device, and Hugging Face model revisions used
to create the vectors. Loading under any different identity must fail. Formal
Reader telemetry must contain one provider response per QA, a single actual
model identity, and an actual model in the requested GPT-3.5 Turbo family.
Missing telemetry, mixed models, or provider substitution fails official
comparability.

### 3.2 Official experiment matrix

| Experiment | Retriever | top-k | Purpose |
|---|---|---:|---|
| O1-5 | Official Dialog DRAGON | 5 | Official reproduction |
| O1-10 | Official Dialog DRAGON | 10 | Official reproduction |
| O1-25 | Official Dialog DRAGON | 25 | Primary official reproduction |
| O1-50 | Official Dialog DRAGON | 50 | Official reproduction |
| O2-B-25 | EM-Graph with DRAGON semantic signal | 25 | Matched official-stack method comparison |

For O2-B-25:

- use the identical DRAGON query and context encoders;
- preserve the DRAGON dot-product semantic ranking;
- predeclare the cross-signal calibration before observing results;
- use query-local min-max normalization of the DRAGON dot-product score before
  combining it with the Entity score at the predeclared `0.3/0.7` weights;
- disclose this calibration as part of the official-stack EM-Graph variant;
- do not tune the calibration after seeing the final score.

O1 continues to rank raw DRAGON dot products without this fusion calibration.

### 3.3 Official reproduction gate

Use the following predeclared practical tolerance:

- Recall@25 absolute difference from the official table: at most 1 percentage
  point;
- F1 absolute difference: at most 2 percentage points;
- category-level direction and magnitude must remain broadly consistent.

If the reproduction fails, inspect:

1. Dialog embedding text;
2. accidental vector normalization;
3. query/context encoder selection;
4. dot-product and sorting behavior;
5. actual Reader model request;
6. dataset version.

If the difference cannot be resolved, stop the publication experiment track.
The value may still be cited as an external reference in diagnostic notes, but
the plan must not continue toward a controlled-comparison paper claim.

## 4. Phase 2: matched-stack method experiments

This phase tests the EM-Graph method under one internally controlled stack.

### 4.1 Wiring preflight

Rerun `conv-26` for:

- A at top-k 25;
- B at top-k 25.

The preflight checks API wiring, graph construction, exact top-k, Reader
format, output isolation, required fields, and the external validator. It is
not a paper metric and must not be used for parameter selection.

Create a result snapshot immediately after a successful preflight. Any
subsequent source change requires another preflight.

### 4.2 Predeclared primary configuration

```text
dataset: LoCoMo all-10
QA count: 1986
primary top-k: 25
answer model: gpt-3.5-turbo
embedding model: text-embedding-3-small
entity weight: 0.3
semantic weight: 0.7
sequence secondary scale: 0.5
entity minimum relative score: 0.5
entity top-k per question key: 20
who-only dampening: 0.25
degree discount: enabled
```

These settings are frozen before the all-10 result is observed.

### 4.3 Primary A/B experiment

| Experiment | Condition | Purpose |
|---|---|---|
| M1-A-25 | Pure Memory full-pool dense retrieval | Matched no-graph baseline |
| M1-B-25 | Complete Entity–Memory graph retrieval | Complete proposed method |

This is the primary test used for the B-minus-A confidence interval.

### 4.4 Structural ablations

All structural ablations use all-10 and top-k 25.

| Experiment | Variant | Isolated question |
|---|---|---|
| M2-embed | B_embed | Does graph packaging itself change the dense baseline? |
| M2-gate | B_gate | What is the contribution of the Entity gate? |
| M2-gate-seq | B_gate_seq | What is the contribution of sequence expansion over the gate? |
| M2-entity | B_entity | Is the semantic signal necessary? |
| M2-noseq | B_noseq | What is the sequence contribution inside complete B? |

Required interpretation:

- A and B_embed must have exactly equal ordered context-id lists for every
  paired QA row; any id difference or ordering difference fails the
  dense-control gate and is treated as an implementation/control problem;
- both conditions must bind the exact same complete query-embedding artifact
  by content hash and prove coverage for every ordered dataset QA row; Memory
  index equality alone is insufficient;
- B versus B_noseq tests sequence contribution;
- B versus B_gate_seq tests explicit Entity-score fusion;
- B_gate_seq versus B_gate tests sequence expansion over a gated semantic
  retriever;
- B versus B_entity tests the need for the semantic score.

### 4.5 Input ablations

All input ablations use all-10 and top-k 25.

| Experiment | Variant | Isolated input |
|---|---|---|
| M3-A-caption | A_no_caption | Caption contribution to A |
| M3-B-caption | B_no_caption | Caption contribution to B |
| M3-A-raw | A_raw_text | Normalized/time-aware text contribution to A |
| M3-B-raw | B_raw_text | Normalized/time-aware text contribution to B |
| M3-B-speaker | B_no_speaker | Speaker Entity contribution to B |

Report both the within-method ablation and whether the B-over-A improvement
survives under matched input availability.

### 4.6 Top-k robustness

Run both A and B at:

```text
top-k = 5, 10, 25, 50
```

Top-k 25 remains the primary setting. Do not select a new primary cutoff after
observing the results.

### 4.7 Fusion and sequence sensitivity

Hold every other condition fixed and run:

| Condition | Entity weight | Semantic weight |
|---|---:|---:|
| Semantic-heavy | 0.1 | 0.9 |
| Primary | 0.3 | 0.7 |
| Balanced | 0.5 | 0.5 |
| Entity-only | 1.0 | 0.0 |

`B_entity` supplies the Entity-only endpoint.

For sequence scale, compare:

| Condition | Sequence scale |
|---|---:|
| B_noseq | 0.0 |
| B primary | 0.5 |
| B_seq10 | 1.0 |

If improvement appears only at one narrow parameter point, reduce the
robustness claim.

## 5. Phase 3: formal-run organization

### 5.1 One condition per empty directory

Use:

```text
outputs/locomo_formal/<run-id>/
```

Example:

```text
tes_B_top25_e03_s07_seq05_thr05_etk20_text3small_run01
```

Every condition directory must:

- be absent or empty at run start;
- contain exactly one resolved condition;
- never be the shared legacy `outputs/locomo_eval/` directory;
- be deleted exactly and recreated before a rerun;
- never rely on `--overwrite` as a substitute for deletion;
- include a `run_config.json` with the complete command, source commit, data
  hash, models, graph profile, recall parameters, run id, and time.

Graph, Entity, question-Entity, and embedding caches are separate from
answer/result output. They may be reused only when their complete existing
identities match the current inputs and implementation.

### 5.2 Cost-aware execution order

Run in this order:

1. Conv-26 A/B wiring preflight;
2. O1 DRAGON retrieval-only parity check;
3. O1 all-10 official reproduction;
4. M1 all-10 A/B primary experiment;
5. immediate primary B-minus-A significance analysis;
6. structural ablations;
7. input ablations;
8. A/B top-k robustness;
9. fusion and sequence sensitivity;
10. O2-B official-stack EM-Graph;
11. cost aggregation;
12. final cross-result validation.

If the primary A/B result has no positive retrieval signal, stop before
spending answer-generation cost on every secondary condition and diagnose the
method first.

Do not apply the retired cross-model `49.6` threshold. Record the primary
significance result, then continue the planned structural/input ablations,
robustness sweeps, O2, and cost aggregation. Revisit the paper claim only
after final cross-result validation. A validity-gate failure must still be
corrected before dependent experiments proceed.

### 5.3 Result lifecycle

After every metric-bearing result:

1. run `validate_formal_result.py`;
2. preserve the exact resolved configuration;
3. preserve the graph audit and prompt-budget audit;
4. write a concise machine-readable and human-readable result summary;
5. create an immutable result/source snapshot;
6. update the experiment README, conclusion, and next steps;
7. commit and push;
8. only then modify source or proceed to another experiment version.

## 6. Phase 4: metrics and statistical decision

### 6.1 Required reporting

Report:

- official overall F1;
- official `recall_acc`;
- official Category 1–5 breakdown;
- Categories 1–4 subset F1 as an explicitly local diagnostic;
- per-conversation F1 and recall;
- paired-QA B-minus-A confidence intervals;
- conversation-cluster B-minus-A confidence intervals;
- construction, retrieval, and answer-generation cost.

Preserve the unchanged official Category-5 random two-choice behavior.

### 6.2 Green signals

The complete method-effectiveness claim is supported when:

- both paired-QA and conversation-cluster recall confidence-interval lower
  bounds are greater than zero;
- both paired-QA and conversation-cluster F1 confidence-interval lower bounds
  are greater than zero;
- most conversations move in the same direction and the mean is not dominated
  by one or two conversations;
- improvement is reasonably stable across top-k 5/10/25/50;
- parameter sensitivity does not show a single isolated successful point;
- A and B_embed pass the dense-control sanity check;
- component ablations support the proposed mechanism;
- the measured cost increase is reported and defensible.

### 6.3 Yellow signals

| Evidence | Maximum defensible claim |
|---|---|
| Recall is significant but F1 crosses zero | Retrieval improves significantly; final answer quality does not |
| Overall F1 is not significant but Categories 1–4 improve | Local non-Category-5 diagnostic only |
| QA bootstrap passes but cluster bootstrap crosses zero | QA-level evidence without strong conversation-level generalization |
| Only top-k 25 improves | Improvement at the predeclared primary cutoff, not cutoff robustness |
| An ablation does not degrade | No independent contribution claim for that component |

### 6.4 Red signals

Do not make a strong paper claim if:

- both recall and F1 confidence intervals cross zero;
- improvement is driven by only one or two conversations;
- A and B_embed differ materially without an explanation;
- the official DRAGON reproduction fails but the paper claims a controlled
  win over the official baseline;
- context lists are shorter than the required top-k or contain duplicates;
- a result resumed previous predictions;
- graph construction consumed QA answer, evidence, category, or judge data;
- a formal result lacks a matching immutable snapshot;
- a manuscript number cannot be recomputed from archived result JSON.

## 7. Phase 5: paper production

Once the experimental gates pass, freeze the experiment stack and move to
paper production.

### 7.1 Minimum tables

1. Official DRAGON reproduction and matched official-stack EM-Graph;
2. matched-stack A/B primary results with category breakdown;
3. structural and input ablations;
4. top-k and parameter sensitivity;
5. construction/retrieval/answer cost.

### 7.2 Recommended figures

- EM-Graph construction and retrieval architecture;
- top-k recall/F1 curves;
- per-conversation B-minus-A differences;
- paired and cluster confidence intervals;
- effectiveness-versus-cost plot.

### 7.3 Required disclosure

The paper and appendix must state:

- dataset hash and QA counts;
- source commit and run date;
- extraction, embedding, answer, and judge model names;
- actual model requested by the API;
- every primary retrieval parameter;
- frozen official evaluator source and commit;
- unchanged Category-5 two-choice limitation;
- the LoCoMo paper/code model-name discrepancy;
- confirmation that graph construction excludes all QA/test annotations;
- statistical method and external-analysis random seed;
- cost, limitations, and failure cases;
- reproduction commands and output/snapshot locations.

Before submission, verify every table and figure value against the archived
machine-readable result.

## 8. Immediate next actions

The formal tooling, immutable query artifact, corrected A/B_embed dense
control, migration, corrected all-10 A/B, primary significance, and all
component conditions have been completed. The current execution order is:

1. Commit and push snapshot `v46_component_family_significance`. All four
   Recall@25 component hypotheses pass Holm under both estimators; only the
   semantic-signal F1 hypothesis passes Holm.
2. Run the predeclared all-10, top-k-25 input ablations.
3. Complete input ablations, top-k and fusion sensitivity, O2 diagnostic,
   cold/warm cost measurement, and the final publication audit.

When all formal outputs pass validation and the green statistical signals
hold, the experimental evidence is sufficient to write and submit the paper
without another currently known LoCoMo-alignment repair cycle. This does not
guarantee peer-review acceptance.
