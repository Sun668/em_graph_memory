# Conclusion

The three-layer source refactor is implemented under top-level `code/`:

1. `code/locomo_eval` contains a byte-identical pinned LoCoMo vendor tree and one
   injected QA-recall boundary.
2. `code/em_graph` contains only build, recall, and cache layers.
3. `code/common` is the single active model-client implementation.

Their Python import names remain `locomo_eval`, `em_graph`, and `common`;
`code` is deliberately not a Python package, avoiding a collision with the
standard-library module named `code`.

The ten temporary `em_graph.<legacy_module>` compatibility files have now
been removed. Active callers use `em_graph.build`, `em_graph.recall`, or
`em_graph.cache`; `em_graph.__init__` remains the sole stable convenience
facade. Historical snapshots and self-contained experimental package copies
were not rewritten.

The prior 1044-line matched-stack runner is preserved in
`snapshots/v01_pre_refactor/legacy_matched_stack/`; its active path is now a
small compatibility entry point. The duplicated local LoCoMo prompt and metric
modules were removed from the active experiment.

The strict graph audit passes by construction: graph building consumes
conversation fields only, while QA-derived question entities live in separate
recall caches whose identities include model, extraction protocol, QA index,
and full question SHA-256. `query` and `img_url` were removed from the Memory node schema;
only raw/normalized dialog text and `blip_caption` remain. A no-model all-10
audit verified all 5882 dialogs, 272 dialog-bearing sessions, 288 timestamp
keys, and 11744 directed chronological edges. Prompt scaffold length is 2410,
below the 5000-character limit.

The A baseline retains its original condition: it builds 5882 Memory nodes and
zero Entity nodes, so it incurs no entity-extraction call. B and B_embed use the
complete EM graph. All variants share one canonical per-sample embedding index,
validated by Memory ids and full Memory-text digests.

Unit/parity validation passes. A fresh metric-bearing variant-B preflight was
then run on all 199 `conv-26` QA rows from source commit `23e3a4b`, with no
legacy graph, embedding, question, or answer artifact reused.

Official `recall_acc` at k=5/10/25/50 is
`0.6231/0.7580/0.8610/0.9213`. Official overall F1 at the same cutoffs is
`0.341/0.385/0.391/0.400`. The official stats implementation, rather than a
direct mean of serialized recall fields, is authoritative because it retains
empty-evidence questions in the denominator without accumulating their
row-level default recall.

The graph contains 419 Memory nodes, 1105 Entity nodes, and 2903 total edges,
including 836 chronological Memory edges. Graph construction and recall pass
the mandatory conversation-only graph audit. Official overall F1 remains an
official-compatibility diagnostic because Category 5 exposes both answer
options in its official prompt; the compliant Categories 1–4 subset F1 is
`0.41985/0.49053/0.49905/0.52332`.

This is a single-conversation result. A, B_entity, B_embed, B_noseq, and all-10
regression remain pending; historical A/B numbers must not be relabeled as
results from the new stack.

The formal-result validator is now implemented outside the frozen evaluator.
It validates complete condition identity, empty-directory/no-resume assertions,
all-10 counts and order, exact unique context ids, serialized metric fields,
official stats aggregation, graph/no-test audit, and prompt budget. It does not
recalculate LoCoMo F1 or `recall_acc`.

Nine focused validator tests plus the sixteen existing refactor tests pass
(25 total). The suite includes a synthetic dataset-faithful all-10 result with
10 conversations, 1986 QA, and 446 Category-5 rows, a conv-26 preflight that is
explicitly ineligible for paper metrics, a non-graph official reference, and
negative cases for resume/overwrite, false empty-start claims, QA reorder,
missing metrics, stats mismatch, short/duplicate/unknown contexts, condition
fingerprint drift, unexpected artifacts, graph-audit failure, and prompt-budget
failure.

No metric-bearing run or external model call occurred in this validator stage.
The old isolated conv-26 DRAGON directory is correctly rejected as non-formal
because it predates the required `run_config.json`. Snapshot:
`snapshots/v12_formal_validator/`.

The experiment-local official Dialog DRAGON runner is now implemented without
changing `code/locomo_eval/`. Six focused parity tests verify upstream dialog
and query inputs, distinct query/context model ids, batch size 24, raw CLS
vectors without L2 normalization, raw dot-product ranking, dated reader
context, reference labeling, cache-bound condition fingerprints, all 16 vendor
hashes, and the `em_graph` dependency boundary. Together with the prior suites,
31/31 tests pass.

A fresh retrieval-only conv-26 diagnostic used CPU, PyTorch 2.13.0,
Transformers 5.14.1, 419 dialog vectors, 199 query vectors, and k=25. Every QA
returned exactly 25 unique context ids. Context norms ranged
65.1454–66.3124 and query norms 10.0860–10.8967, confirming that the production
cache is unnormalized. No answer generation, official F1, or `recall_acc` was
run or claimed.

The official Dialog reference intentionally fails the mandatory graph
constraint: its index is built from conversation dialogs, but recall is dense
retrieval over a flat dialog matrix rather than graph retrieval. It may
calibrate official protocol behavior but cannot count as a compliant EM-Graph
result. The runner adds no prompt scaffold and keeps the frozen official
generation/evaluation path unchanged. Snapshot:
`snapshots/v13_official_dragon_runner/`.

The external significance, dense-control, and cost-report tools are now
implemented without touching `code/locomo_eval/`. Significance uses 10,000
paired-QA and conversation-cluster resamples with seed `20260727`; it reports
overall, Category 1–5, local Categories 1–4, and per-conversation differences.
Empty-evidence recall rows contribute zero while remaining in every
denominator, even if their serialized row-level recall is 1. Raw serialized
recall is retained, and computed category recall means must match the frozen
official stats block.

The A/B_embed dense-control gate requires exact per-QA ordered context-id
equality. Tests cover exact formal-condition equality over all 199 conv-26
rows, a changed id, and the same ids in a changed order. The cost reporter
requires all six stages in both cold and warm measurements, provider
request/token data, per-QA retrieval latency, and graph/index/cache sizes; it
does not estimate missing fields.

Twelve focused analysis/cost tests and all earlier suites pass (43/43 total).
No metric-bearing experiment, real-result bootstrap claim, external model
call, or cost measurement occurred in this source-only stage. Snapshot:
`snapshots/v14_analysis_and_cost_tools/`.

Formal EM-Graph orchestration is implemented in `formal_graph.py`. It binds
source commit/tree, pinned data, scope, models, retrieval parameters, graph
profile, answer protocol, and graph/index cache hashes into one condition;
refuses an existing output directory; never resumes or overwrites; writes a
conversation-only graph/prompt audit; and finishes via frozen official stats
and the external validator. Three focused and 46 combined tests pass.

Publication gate: `continue_tooling_only`. This step produced no metric and
therefore cannot establish paper readiness. The plan now mandates immediate
stop on unresolved official-protocol mismatch, clear underperformance against
the fixed LoCoMo anchors, failed primary B/A significance, graph/output
non-compliance, or failed A/B_embed ordered-context equality. Snapshot:
`snapshots/v15_formal_graph_orchestration/`.

Provider-usage telemetry is now available as a default-off shared client hook.
Mocked chat and embedding tests verify unchanged outputs plus exact
requested/actual model, provider token, request, stage, and wall-time records;
nested observers restore cleanly. Three focused and 49 combined tests pass.
No API request or metric occurred. Publication gate remains
`continue_tooling_only`; a cold/warm probe still must consume this hook before
preflight. Snapshot: `snapshots/v16_provider_usage_telemetry/`.

Cold/warm cost orchestration is now complete. Formal conditions capture warm
answer/query/retrieval telemetry; the probe binds to the validated condition
identity, refuses existing outputs or a non-fresh cold cache, rebuilds and
replays the matched graph twice, and produces the strict cost manifest/report.
Warm zero-request hits remain zero, missing provider usage fails, and
overlapping stage walls are labeled non-exclusive. Eight new/updated focused
tests bring the complete suite to 57/57.

No live cost or metric was measured in this source step. Publication gate:
`continue_tooling_only`, `paper_ready=false`. The formal stack is now ready
for the conv-26 A/B wiring preflight, where the next gate is applied.
Snapshot: `snapshots/v17_cost_orchestration/`.

The isolated post-exact-top-k conv-26 A/B wiring preflight is now complete from
source commit `050c417`. The successful A and B conditions each began in an
absent directory, produced all 199 QA rows and 47 Category-5 rows, and passed
the external validator. A returned official overall F1 `0.366` and
`recall_acc` `0.7965`; B returned `0.390` and `0.8610`. The descriptive B
minus A differences are +2.4 F1 points and +6.45 recall points, but one
conversation is not a paper metric or statistical claim.

A contained 419 Memory nodes and 836 parsed-date-time NEXT/PREV edges. B
contained the same Memories plus 1105 Entities, 2903 Entity–Memory edges, and
836 chronological edges. Both graphs were built only from conversation fields;
QA answers, evidence, categories, judge outputs, and predictions were excluded.
Answer recall used graph nodes/edges and the frozen LoCoMo Reader and metrics.
Prompt budgets passed at 0/5000 for A and 2410/5000 for B.

Post-run verification passed 57/57 tests, all 16 vendor hashes, and the frozen
evaluator clean check. Provider usage was complete for exactly 199 answer
requests per condition. Snapshot:
`snapshots/v18_conv26_formal_ab_preflight/`.

Publication gate: `continue`, `paper_ready=false`. No protocol, graph, output,
or reproducibility blocker was found in the preflight. The next terminal gate
is the O1 all-10 official DRAGON reproduction; M1 performance, primary
significance, dense-control, ablation, robustness, cost, and final manuscript
gates remain unresolved.

The first formal all-10 O1-25 run has completed from source `9511f94`.
Validation passes all 10 conversations, 1986 QA rows, 446 Category-5 rows,
official stats parity, exact 25 unique context ids, clean source, and isolated
output. It produced official overall F1 `42.2` and Recall@25 `78.11`.

F1 is 1.2 points above the Table 3 Dialog value `41.0` and passes the ±2 point
gate. Recall is 1.41 points above `76.7` and misses the fixed ±1 point gate by
0.41 points. The result is therefore not accepted as an official reproduction.

The pinned paper Table 3 was visually rechecked. A full-data audit found zero
ordered-ranking mismatches against the upstream NumPy ranking expression, and
confirmed raw Dialog/question inputs, correct separate DRAGON encoders,
unnormalized vectors, raw dot product, and exact-top-k behavior. The remaining
identified difference is the runtime: the official requirements use PyTorch
2.0.1/CUDA 11.7, Transformers 4.35.0, tokenizers 0.14.1, and NumPy 1.26.0;
the diagnostic used CPU, PyTorch 2.13.0, Transformers 5.14.1, tokenizers
0.22.2, and NumPy 2.2.6. Its actual provider-resolved Reader model was also
not captured.

Publication gate: `continue` only to correct and rerun O1 with dependency,
device, Hugging Face revision, and actual Reader identity bound outside the
frozen evaluator. `o1_accepted=false`, `paper_ready=false`, and M1 remains
blocked. If that corrective reproduction cannot meet tolerance, the
publication experiment track stops. Snapshot:
`snapshots/v19_o1_dragon_top25_runtime_mismatch/`.

The corrective source gate is now implemented outside the frozen evaluator.
O1 caches bind exact dependencies, platform/device, and pinned Hugging Face
revisions. Formal outputs bind the requested and provider-resolved Reader
identity and exact request count; mixed, substituted, or missing Reader
identity fails validation. Nineteen focused and 61 full experiment tests pass,
the 16-file vendor manifest passes, and `code/locomo_eval/` is unchanged.

Publication gate: `continue_tooling_only`, `paper_ready=false`. This source
milestone fixes the identified audit gap but does not accept O1. The
dependency-matched O1-25 rerun remains the next terminal gate, and M1 remains
blocked until it passes. Snapshot:
`snapshots/v20_o1_runtime_identity_gate/`.

The first Python 3.9.18 dependency preflight stopped before installing any
package because `nltk==3.10.0` requires Python 3.10. The pinned upstream
environment specifies NLTK 3.8.1, regex 2022.10.31, and tqdm 4.64.1; the O1
requirements now use those versions. This is an environment-resolution
correction, not a metric or protocol change.

Publication gate remains `continue_tooling_only`, `paper_ready=false`.
Snapshot: `snapshots/v21_o1_environment_resolution/`.

The corrective O1 retrieval run is complete. Its isolated runtime exactly
matches the declared Python and retrieval-library versions and fixed
Hugging Face revisions. All 10 caches share one CPU identity, and the
retrieval check passes 1986/1986 rows at exactly 25 unique context ids.

Using official per-row three-decimal recall contributions, with empty-evidence
rows contributing zero and all QA retained in the denominator, Recall@25 is
`78.113293%`. The fixed official target is `76.7±1`, so the absolute 1.413293
point difference fails. The top-25 evidence sets are identical to v19 for all
1986 rows; nine rows have only a changed internal order. Reader generation
cannot change recall and was therefore not run.

The only unresolved runtime difference is CPU versus the official CUDA 11.7
stack. CUDA 11.7 is unavailable on this macOS arm64 host. Under the
predeclared rule, this activates terminal stop condition 2.

Publication gate: `stop`, `o1_accepted=false`, `paper_ready=false`. M1,
significance, all secondary/ablation/robustness/O2 experiments, cost
aggregation, and the final paper-ready claim are blocked and were not run.
Snapshot: `snapshots/v22_o1_corrective_retrieval_stop/`.

The user subsequently authorized one explicit protocol decision: ignore the
v22 O1 ±1 reproduction stop if the later formal experiments prove the method
better. O1 remains unaccepted and external-reference-only; this waiver does
not change any metric, prompt, dataset, graph constraint, model setting, or
M1 parameter.

The first new fusion-sensitivity point is now complete. At top-k 25, changing
only Entity/Semantic fusion from the primary `0.30/0.70` to `0.10/0.90`
produces official F1 `42.2040%` and `recall_acc` `82.1780%`. Relative to the
primary B condition, overall F1 changes by `-0.3640` points and is not
significant under either paired-QA or conversation-cluster bootstrap. Evidence
recall falls by `-2.3062` points, with both raw 95% intervals fully below zero.

The run is paper-eligible and graph-claim eligible: both validators, 77/77
tests, 16/16 frozen hashes, immutable-query checks, graph constraint, prompt
budget, resource ceiling, and byte-identical significance reproduction pass.
All 70 graph caches and 30 Memory indexes remain preserved and were reused
read-only. Family-level interpretation remains pending until the preregistered
`0.50/0.50` point is complete and Holm correction is applied. Snapshot:
`snapshots/v61_b_fusion_e10_s90_all10/`.

The second new fusion point is also complete. At `0.50/0.50`, official F1 is
`42.2440%` and `recall_acc` is `84.3280%`. Relative to primary `0.30/0.70`,
overall F1 changes by `-0.3240` points and recall by `-0.1562` points; all
paired-QA and conversation-cluster 95% intervals cross zero. Both validators,
77/77 tests, 16/16 hashes, graph/prompt and resource gates, exact query use,
and byte-identical statistical reproduction pass. No cache was rebuilt or
deleted; 70 graph caches and 30 Memory indexes remain preserved. Snapshot:
`snapshots/v62_b_fusion_e50_s50_all10/`.

The two new fusion points are now complete. A source-locked two-comparison
Holm report is still required before making the family-level conclusion.

The repaired fusion-family report is now complete and byte-identically
reproduced. It explicitly binds all ten graph/index cache records and query
artifact SHA `bef99a…6f9f`. For `0.10/0.90 − 0.30/0.70`, overall F1 changes
by `-0.3640` points without significance, while evidence recall falls
`-2.3062` points and remains significant after Holm under both paired-QA and
conversation-cluster estimators (adjusted p=`0.0004`). For
`0.50/0.50 − 0.30/0.70`, neither F1 nor recall differs significantly.

The supported fusion conclusion is therefore calibrated: strongly reducing
Entity weight harms evidence recall, while the tested equal weighting is
statistically indistinguishable from the primary setting on overall metrics.
The family does not prove that `0.30/0.70` is globally optimal. Snapshot:
`snapshots/v66_fusion_family_significance/`.

Execution therefore resumed at M1 A/B. At v23, the next non-waived terminal
gates were M1-B F1 `49.6`, Recall@25 `75.7`, and positive support for B over A
under the predeclared paired-QA and conversation-cluster analyses. v26 later
retired these performance early-stop gates. The v23 publication gate was
`continue`, `paper_ready=false`. Snapshot:
`snapshots/v23_user_authorized_o1_waiver/`.

Formal all-10 M1-A is now complete from source `3e3a33b`. The pure-Memory
baseline used all 10 conversations, 1,986 QA rows, top-k 25,
`text-embedding-3-small`, and requested `gpt-3.5-turbo` answers. It produced
official overall F1 `42.2642%`, Recall@25 `79.7468%`, and local Categories 1–4
F1 `50.9979%`.

Both formal validations pass exact counts and order, 25 unique valid contexts
per row, official stats parity, isolated/no-resume output, graph/no-test
audit, and prompt budget. Its graph contains 5,882 Memory nodes, zero Entity
nodes, and 11,744 chronological edges, built only from conversation fields.
Four empty-evidence rows retain raw serialized recall 1 but correctly
contribute zero to official recall analysis with all QA in the denominator.
Post-run checks pass 62/62 tests and all 16 vendor hashes; the frozen evaluator
is unchanged.

The v24 publication gate remained `continue`, `paper_ready=false`. M1-A is
only the matched baseline. Under the rule then active, formal all-10 M1-B had
to pass F1 `49.6%`, Recall@25 `75.7%`, and paired-QA plus
conversation-cluster B-over-A significance before secondary experiments. v26
later superseded those performance early-stop conditions. Snapshot:
`snapshots/v24_m1_a_all10/`.

Formal all-10 M1-B is now complete from source `484ccf0`. The complete
Entity–Memory method used all 10 conversations, 1,986 QA rows, top-k 25,
`gpt-3.5-turbo` Entity/query extraction and answers,
`text-embedding-3-small`, Entity/semantic weights 0.3/0.7, and sequence scale
0.5. Its conversation-only graph has 5,882 Memories, 12,808 Entities, 36,227
Entity–Memory edges, and 11,744 chronological edges.

Both validators pass exact counts/order, 25 unique valid contexts per row,
official stats parity, isolated/no-resume output, graph/no-test audit, and a
2,410/5,000-character prompt scaffold. Post-run checks pass 62/62 tests and
all 16 vendor hashes; the frozen evaluator remains unchanged.

Official overall F1 is `42.6772%`, Recall@25 is `84.3415%`, and local
Categories 1–4 F1 is `52.2448%`. The mean B-minus-A changes are +0.4130 F1
points and +4.5947 recall points, but these were not bootstrapped because the
official-performance gate is applied first. Recall passes its 75.7% floor;
F1 misses its 49.6% floor by 6.9228 points.

Publication gate: `stop`, `paper_ready=false`. This is terminal condition 3,
which was not covered by the user's O1-only waiver. Significance, ablations,
robustness, O2, and complete cost aggregation were not launched. Snapshot:
`snapshots/v25_m1_b_official_performance_stop/`.

The v25 stop interpretation was subsequently corrected after direct inspection
of the final upstream LoCoMo paper. Its Table 2 F1 `51.6` is produced by
`gpt-4-turbo` with a 128K long context and no RAG retrieval. The relevant
same-Reader-class Table 3 reference is DRAGON + `gpt-3.5-turbo` Dialog@25,
with F1 `41.0` and Recall@25 `76.7`. Thus `49.6 = 51.6 - 2` was an invalid
cross-model stop gate for M1.

No v25 metric or artifact changes. Only the go/no-go decision is superseded.
Under the user's 2026-07-28 instruction, complete the planned significance,
ablation, robustness, O2, and cost experiments before revisiting the paper
claim. Validity gates remain mandatory throughout.

Publication gate: `continue`, `paper_ready=false`. Snapshot:
`snapshots/v26_cross_model_gate_correction/`.

The predeclared primary M1-B versus M1-A significance analysis is complete.
It used all 1,986 paired QA rows and 10 conversation clusters, seed
`20260727`, and 10,000 bootstrap resamples per estimator. Both formal inputs
passed validation, and the no-evidence-zero recall contribution exactly
matches official stats.

B improves Recall@25 by `+4.5947` points: paired CI
`[+3.5241, +5.7012]`, cluster CI `[+3.2593, +5.9514]`, with `p=0.0002`
for both. B improves overall F1 by only `+0.4130` points: paired CI
`[-0.6824, +1.4990]`, `p=0.4524`; cluster CI
`[-0.3519, +1.2114]`, `p=0.3008`. The evidence supports a significant
retrieval gain but not a significant overall final-answer F1 gain.

The local Categories 1–4 F1 gain is `+1.2469` points with both intervals above
zero. Category-5 recall gains `+13.3408` points while Category-5 F1 loses
`2.4664` points. Recall improves in all 10 conversations; F1 improves in six.
This tradeoff must constrain the final claim but, under the user's instruction,
does not stop the remaining matrix.

All graph, frozen-evaluator, formal-output, prompt-budget, and snapshot checks
remain compliant. No external model calls were needed for the analysis.
Publication gate: `continue`, `paper_ready=false`. Snapshot:
`snapshots/v27_primary_ab_significance/`.

Formal all-10 B_embed subsequently passed the standalone formal validator but
failed its mandatory control comparison with M1-A. Of 1,986 paired QA rows,
61 have different ordered top-25 contexts: 51 are order-only changes and 10
change at least one id. Its F1 `41.5877%` and Recall@25 `79.7468%` are
diagnostic only and cannot be interpreted as a structural ablation.

All ten Memory embedding indexes are byte-identical across A and B_embed. The
failure comes from query embeddings: the runner creates ten independent
whole-file cache objects before evaluation. Each starts from the same snapshot
and can later overwrite query vectors added by another object. The final cache
covers only 838/1986 dataset question lookups. The formal config binds Memory
indexes but not query-cache content or coverage.

Graph construction remains compliant and the 2,410/5,000 prompt budget passes;
`code/locomo_eval/` is unchanged. Nevertheless, exact dense-control validity
fails. Publication gate: `stop_for_control_repair`, `paper_ready=false`.
Snapshot: `snapshots/v28_m2_embed_dense_control_failure/`. Corrected matched
A/B_embed and A/B runs are required before continuing the ablation matrix.

The v29 source milestone implements the repair: shared writable text caches
merge only pending additions under path/file locks and replace atomically;
formal query vectors live in a separate immutable artifact bound to dataset,
model, role, ordered QA digests, normalization, dimension, and file hash.
Formal retrieval fails on any miss, records zero live requests, and
dense-control requires A/B_embed to share the artifact SHA before comparing
all ordered contexts.

No metric or model call is claimed at this source milestone. The full suite
passes 68/68, all 16 vendor hashes pass, and the frozen evaluator is unchanged.
Publication gate: `continue_tooling_only`, `paper_ready=false`. Snapshot:
`snapshots/v29_query_embedding_artifact_gate/`.

The v30 clean build deleted only the exact corrupt text cache and produced the
new artifact from absent paths. It has exact 1986/1986 ordered QA coverage,
1,974 unique 1,536-dimensional vectors, and SHA-256 `bef99a…6f9f`.
Independent identity, ordering, finite-value, and L2-norm checks pass. The
build required 198 embedding requests and 23,936 provider input tokens; no
answer generation or metric was run.

Publication gate: `continue`, `paper_ready=false`. Snapshot:
`snapshots/v30_query_embedding_artifact_build/`. Next is the retrieval-only
A/B_embed exact-equality gate.

The corrected all-10 M1-A run is now complete from source `76fcf5b` and the
immutable query artifact. It covers all 10 conversations, 1,986 QA rows, and
446 Category-5 rows. Both validators pass exact order/count/context checks,
official stats parity, graph/no-test and prompt audits, artifact identity, and
runtime use of 1,986 hits with zero query misses or live embedding requests.
The general writable context cache remains absent.

Official overall F1 is `42.0681%`, Recall@25 is `79.7468%`, and local
Categories 1–4 F1 is `51.2645%`. Recall is exactly unchanged from historical
v24 A; the answer F1 difference is Reader variance and is not a method effect.
Post-run checks pass 69/69 tests and all 16 vendor hashes; the frozen evaluator
is unchanged.

Mandatory graph constraint and prompt budget pass. Publication gate:
`continue`, `paper_ready=false`. Snapshot:
`snapshots/v34_corrected_m1_a_all10/`. Corrected B_embed must now run from an
absent directory with the same artifact and pass exact 1,986-row ordered
context equality.

The first corrected B_embed formal attempt reached the Reader loop but
completed zero answers: ten consecutive external connection errors exhausted
the bounded retry policy. Only run config and graph audit files exist; there
is no prediction, metric, or resumable state. Graph, prompt, frozen-evaluator,
query-artifact, and cache validity remain intact.

Publication gate: `continue_after_connectivity_preflight`,
`paper_ready=false`. Snapshot:
`snapshots/v35_b_embed_reader_connection_abort/`. Retry from a fresh absent
directory after one successful minimal Reader connectivity preflight.

The connectivity preflight succeeded and corrected B_embed run02 completed
from a fresh absent directory. It covers all 10 conversations, 1,986 QA rows,
and 446 Category-5 rows. Official F1 is `42.0677%`, Recall@25 is `79.7468%`,
and local Categories 1–4 F1 is `51.2640%`. Both formal validators, official
stats parity, graph/no-test audit, 2,410/5,000 prompt budget, 1,986/1,986
query hits with zero misses/live requests, 69 tests, and 16 vendor hashes pass.

The A/B_embed dense-control gate passes exactly: the query artifact SHA and QA
order match, and every one of 1,986 ordered top-25 context-id lists is equal.
There are zero mismatches. Answer/F1 variation is external Reader/Category-5
noise and is not interpreted as a retrieval effect. Mandatory graph constraint
passes. Snapshot:
`snapshots/v36_corrected_b_embed_all10_dense_control/`.

Publication gate: `continue`, `paper_ready=false`. Execution is deliberately
paused for migration after commit/push. The next experiment is corrected
all-10 B, followed by its validation/snapshot/commit and corrected A/B
significance. No B run has started.

Migration restoration and corrected all-10 M1-B are now complete on source
`41a7812`. The 64-file archive, archive SHA, query-artifact identity, 69 tests,
16 vendor hashes, frozen evaluator boundary, and absent general writable
context cache all passed before the run.

M1-B covers all 10 conversations, 1,986 QA rows, and 446 Category-5 rows.
Official overall F1 is `42.5680%`, Recall@25 is `84.4842%`, and local
Categories 1–4 subset F1 is `51.9740%`. All formal and independent validation
checks pass. The conversation-only graph has 5,882 Memory nodes, 12,808 Entity
nodes, 36,227 Entity–Memory edges, and 11,744 directed sequence edges.
Mandatory graph constraint and the 2,410/5,000 prompt budget pass.

The immutable query-vector artifact had 1,997 hits, zero misses, and zero live
embedding requests. The restored question-Entity cache was incomplete, so
retrieval made 1,671 query-Entity extraction calls. These calls used only the
current question at retrieval time and did not enter graph construction.

The old corrected-A output is numerically readable but its committed absolute
output and query-artifact paths point to the previous machine. A descriptive
row-level comparison shows B-minus-A `+0.4998` F1 points and `+4.7374`
Recall@25 points, but this is not accepted as the formal post-migration
significance result until relocation proof is applied.

Publication gate: `continue`, `paper_ready=false`. Snapshot:
`snapshots/v37_corrected_m1_b_all10/`.

Snapshot v39 now supplies that proof without rerunning A. The validator remains
fail-closed by default and accepts relocation only with an explicit manifest
whose run identity, old/new paths, v34 snapshot SHA, run config, predictions,
stats, graph audit, query usage, and immutable query artifact all match by
SHA-256. It then repeats every ordinary formal check over the current dataset.

Without the manifest, A fails the two expected absolute-path checks. With the
manifest, A passes as 10 conversations, 1,986 QA rows, 446 Category-5 rows,
`paper_metric_eligible=true`, and `graph_claim_eligible=true`. The suite passes
75/75, vendor hashes 16/16, and the frozen evaluator remains unchanged. No
model call or metric recomputation occurred. Snapshot:
`snapshots/v39_relocation_validation_gate/`.

Publication gate remains `continue`, `paper_ready=false`. The next action is
the predeclared corrected A/B significance analysis with seed `20260727` and
10,000 paired-QA and conversation-cluster resamples.

That corrected primary analysis is now complete. It uses all 1,986 paired QA
rows and 10 conversation clusters. Recall@25 increases by `+4.7374` points,
with paired CI `[+3.6504, +5.8425]` and cluster CI
`[+3.5286, +6.0124]`; both p-values are `0.0002`. Overall F1 increases by
`+0.4998` points, but paired CI `[-0.5745, +1.5514]` and cluster CI
`[-0.1773, +1.2711]` cross zero.

The local Categories 1–4 F1 difference is `+0.7095` points and is also not
significant under either estimator. Categories 1–4 Recall@25 gains `+2.2133`
points with both intervals above zero. Recall improves in all 10
conversations; F1 improves in six and decreases in four.

Both formal inputs validate, A's v39 relocation proof passes, the scoped
A/B run-source diff is empty, official stats parity passes, and an independent
analysis rerun is byte-identical. Supported claim: significant retrieval
improvement only; no significant overall F1 improvement. Snapshot:
`snapshots/v40_corrected_primary_ab_significance/`.

Publication gate: `continue`, `paper_ready=false`. Proceed to B_gate,
B_gate_seq, B_entity, and B_noseq before input ablations.

The first component condition, B_gate, is now complete. It keeps the
conversation-built Entity gate but uses only signed semantic scoring and
disables sequence expansion. It completes all 1,986 QA with official F1
`41.8275%`, Recall@25 `79.2853%`, local Categories 1–4 F1 `51.0191%`, and
local Categories 1–4 Recall@25 `82.7017%`.

B_gate is descriptively close to A: `-0.2406` F1 points and `-0.4615`
Recall@25 points. Full B exceeds B_gate by `+0.7405` F1 points and `+5.1989`
Recall@25 points. The gate alone therefore does not reproduce B's retrieval
gain, but this run cannot separate Entity fusion from sequence expansion or
their interaction.

Both formal validators, official stats parity, graph/prompt audits, immutable
query-vector checks, 75 tests, and 16 vendor hashes pass. Question Entity
extraction is fully warm with zero requests. Snapshot:
`snapshots/v41_b_gate_all10/`.

Publication gate: `continue`, `paper_ready=false`. Run B_gate_seq next, then
B_entity and B_noseq before component-family inference with Holm correction.

B_gate_seq is now complete without rerunning A. It exactly matches B_gate's
graph, Entity gate, signed semantic ranking, dense fill, vectors, Reader, and
metrics, and adds only chronological sequence expansion at scale `0.50`. It
completed all 1,986 QA with official F1 `41.7666%`, Recall@25 `79.7217%`,
local Categories 1–4 F1 `51.0704%`, and local Categories 1–4 Recall@25
`82.7774%`.

Sequence expansion over B_gate changes F1 by `-0.0609` points and Recall@25
by `+0.4364` points. Full B still exceeds B_gate_seq by `+0.8014` F1 and
`+4.7626` Recall@25 points, so the remaining gain is not explained by
sequence over a semantic-only gate. B_entity and B_noseq are still required
before interaction or component attribution.

Both validators, official stats parity, immutable query-vector checks,
graph/prompt audits, 75 tests, and 16 vendor hashes pass. The graph is built
only from conversation data, answer recall uses graph Memories and edges, and
question-Entity extraction is fully warm with zero provider requests.
Snapshot: `snapshots/v42_b_gate_seq_all10/`.

Publication gate: `continue`, `paper_ready=false`. Commit/push v42, then run
B_entity and B_noseq before component-family Holm correction.

B_entity is now complete. It preserves complete B's graph, gate, sequence,
Reader, and metric while removing the semantic score (`1.0/0.0`
Entity/semantic weights). Across all 1,986 QA rows it scores official F1
`37.4899%`, Recall@25 `67.0208%`, local Categories 1–4 F1 `44.8409%`, and
local Categories 1–4 Recall@25 `65.1320%`.

Compared with complete B, Entity-only loses `5.0780` F1 and `17.4634`
Recall@25 points. This is strong descriptive evidence that semantic relevance
is necessary. Both validators, official parity, graph/prompt audits, 75 tests,
and 16 vendor hashes pass. Snapshot: `snapshots/v43_b_entity_all10/`.

Publication gate: `continue`, `paper_ready=false`. Commit/push v43, run
B_noseq, then perform the predeclared component-family Holm correction.

B_noseq is now complete. It holds graph, gate, `0.30/0.70` fusion, Reader,
metric, and top-k constant while disabling sequence expansion. Across 1,986 QA
it scores official F1 `42.0542%`, Recall@25 `82.8114%`, local Categories 1–4
F1 `51.3764%`, and local Categories 1–4 Recall@25 `84.0672%`.

Complete B exceeds B_noseq by `0.5137` F1 and `1.6728` Recall@25 points.
Both validators, official parity, graph/prompt audits, 75 tests, and 16 vendor
hashes pass. Snapshot: `snapshots/v44_b_noseq_all10/`.

All predeclared component conditions are complete. Publication gate remains
`continue`, `paper_ready=false`; component-family Holm correction is next.

The component-family Holm analysis is now complete. Under both paired-QA and
conversation-cluster estimators, all four Recall@25 component gains remain
significant after Holm. For F1, only semantic relevance is significant;
sequence expansion and explicit Entity-score fusion do not have established
F1 gains.

This supports retrieval-component claims while requiring conservative answer
quality wording. The report independently reproduces byte-for-byte and all
formal inputs validate. Snapshot:
`snapshots/v46_component_family_significance/`.

Publication gate remains `continue`, `paper_ready=false`. Proceed to input
ablations.

The first predeclared input ablation, `A_no_caption`, is now complete without
rerunning A. It holds A's memory-only graph shape, query artifact, signed
semantic retrieval, top-k 25, Reader, and metrics constant, while excluding
`blip_caption` from Memory text and using newly identity-bound Memory vectors.

Across 1,986 QA, official F1 is `41.6027%`, Recall@25 `79.5545%`, local
Categories 1–4 F1 `50.2097%`, and local Categories 1–4 Recall@25 `82.7891%`.
Caption removal versus A is `-0.4654`, `-0.1923`, `-1.0547`, and `-0.0208`
points, respectively. Thus caption has a small positive aggregate effect in
A, with the clearest descriptive change in the local Categories 1–4 F1
diagnostic.

Both validators, official aggregation, exact query use, graph/prompt audits,
76 tests, and 16 vendor hashes pass. Snapshot:
`snapshots/v47_a_no_caption_all10/`.

Publication gate remains `continue`, `paper_ready=false`. Commit/push v47,
then run the matched `B_no_caption` condition before drawing a method-wide
caption conclusion.

The matched `B_no_caption` condition is now complete. It holds B's gate,
`0.30/0.70` fusion, sequence scale `0.50`, top-k 25, immutable question
vectors, Reader, and metrics constant while excluding captions from graph
extraction and Memory embeddings.

Across 1,986 QA, official F1 is `41.7394%`, Recall@25 `84.3040%`, local
Categories 1–4 F1 `50.6458%`, and local Categories 1–4 Recall@25
`85.0180%`. Caption removal versus B is `-0.8285`, `-0.1803`, `-1.3282`,
and `-0.0052` points, respectively. Against `A_no_caption`, B_no_caption
retains a `+4.7495`-point Recall@25 gain but only a `+0.1367`-point F1 gain.
This supports the descriptive conclusion that B's retrieval improvement does
not depend on captions, while captions contribute to answer F1. Formal
caption-family inference is still required for significance claims.

Both validators, official aggregation, exact query use, graph/prompt audits,
76 tests, and 16 vendor hashes pass. Snapshot:
`snapshots/v48_b_no_caption_all10/`.

Publication gate remains `continue`, `paper_ready=false`. Execution is paused
after committing and pushing v48, as requested; no next experiment is
started.

The resumed `A_raw_text` condition is now complete. It holds graph schema,
caption use, dense retrieval, query vectors, top-k 25, Reader, and metrics
constant while disabling deterministic relative-time annotations in Memory
text and rebuilding only the newly identity-bound graph/index artifacts.

Across 1,986 QA, official F1 is `42.4579%`, Recall@25 `79.2849%`, local
Categories 1–4 F1 `51.5074%`, and local Categories 1–4 Recall@25
`82.1492%`. Relative to corrected A, the changes are `+0.3898`, `-0.4619`,
`+0.2429`, and `-0.6606` points. Thus time annotations improve retrieval
recall descriptively but do not improve final-answer F1 in this A condition.
No significance claim is made before the matched raw-text family is complete.

Both validators, official aggregation, exact query use, graph/prompt audits,
76 tests, and 16 vendor hashes pass. Old caches were preserved; ten new
indexes were added under new identities. Snapshot:
`snapshots/v49_a_raw_text_all10/`.

Publication gate remains `continue`, `paper_ready=false`. Commit/push v49,
then preregister and run `B_raw_text`.

The matched `B_raw_text` condition is now complete. It keeps complete B's
caption, speaker Entity, gate, fusion, sequence, top-k, query, Reader, and
metric settings fixed while disabling deterministic time annotations.

Across 1,986 QA, official F1 is `42.8087%`, Recall@25 `84.2371%`, local
Categories 1–4 F1 `52.1546%`, and local Categories 1–4 Recall@25
`84.7694%`. Relative to corrected B, differences are small and
non-significant: `+0.2407` F1 and `-0.2472` Recall@25 points. Relative to
`A_raw_text`, B_raw_text gains `+4.9522` Recall@25 points, supported by both
paired-QA and conversation-cluster intervals, while its `+0.3508` F1 gain is
not significant.

Both validators, official aggregation, exact query use, graph/prompt audits,
76 tests, and 16 vendor hashes pass. Historical caches remain intact; ten new
graphs were added and the exact A_raw_text indexes were reused read-only.
Snapshot: `snapshots/v50_b_raw_text_all10/`.

The raw-text input-family Holm procedure is source-locked in v51 with two
predeclared hypotheses, seed `20260727`, 10,000 resamples per estimator, and
17/17 focused tests passing. Publication gate remains `continue`,
`paper_ready=false`; generate the family report after committing the lock.

The locked raw-text input-family Holm report is now complete. Under matched
raw input, B's `+4.9522`-point Recall@25 gain over A survives Holm correction
under both paired-QA and conversation-cluster estimators (adjusted
p=`0.0004`). The F1 difference remains non-significant. Neither F1 nor recall
establishes a deterministic time-annotation effect inside complete B.

Independent generation is byte-identical. Snapshot:
`snapshots/v52_input_family_significance/`. Publication gate remains
`continue`, `paper_ready=false`; preregister B_no_speaker next.

The all-10 `B_no_speaker` speaker-Entity ablation is now complete. It changes
only deterministic speaker Entity injection relative to complete B while
preserving caption/time inputs, extracted Entities, Memory indexes, query
vectors, retrieval weights and gates, sequence expansion, top-k 25, Reader,
and frozen metrics.

Across 1,986 QA, official F1 is `42.3265%`, Recall@25 `83.0021%`, local
Categories 1–4 F1 `51.8574%`, and local Categories 1–4 Recall@25
`83.0144%`. Removing speaker links lowers overall recall by `1.4822` points;
the paired and conversation-cluster confidence intervals are both below zero.
Its `0.2415`-point F1 reduction is not significant. B_no_speaker nevertheless
retains a significant `3.2552`-point recall advantage over corrected A, with
no significant F1 difference.

This supports a narrow paper claim: deterministic speaker links materially
improve evidence retrieval inside B, while the broader conversation-extracted
Entity graph still carries retrieval value without them. It does not support
a speaker-link answer-F1 claim.

Both validators, official aggregation, immutable query use, 77 tests, 16
vendor hashes, graph/prompt audits, and byte-identical statistical
reproduction pass. Old caches remain intact: graphs `60→70`, indexes stay
`30`, and all ten Memory indexes were reused read-only. Snapshot:
`snapshots/v53_b_no_speaker_all10/`.

Publication gate remains `continue`, `paper_ready=false`; top-k robustness,
remaining sensitivities/cost consolidation, and the final claim audit still
precede manuscript drafting.

The all-10 A@5 robustness baseline is complete and valid. With the same
conversation-only Memory graphs, identical Memory indexes and query vectors,
and the same frozen Reader/evaluator, reducing only top-k from 25 to 5 yields
official F1 `39.9053%` and `recall_acc` `59.3584%`. These are descriptive
losses of `2.1628` and `20.3884` points versus corrected A@25.

Both validators, official aggregation, 77 tests, 16 vendor hashes, graph and
prompt audits, and immutable query use pass. Cache preservation is exact:
graphs remain 70, indexes remain 30, and deletion/overwrite/rebuild counts are
zero. Snapshot: `snapshots/v54_a_top5_all10/`.

The supported conclusion is limited to A's sensitivity to context budget.
Whether B's graph retrieval is more robust at top-k 5 remains unknown until
the matched B@5 condition is frozen and completed. Publication gate remains
`continue`, `paper_ready=false`.

The matched B@5 condition is now complete and valid. It preserves the exact
Memory text/indexes, frozen query vectors, top-k budget, Reader, evaluator,
serialization, and aggregation used by A@5, while activating the complete
conversation-derived Entity graph, Entity/semantic fusion, and chronological
sequence expansion.

B@5 reaches official F1 `39.8264%` and `recall_acc` `64.1667%`. Against
A@5, recall improves by `4.8083` points with paired-QA CI
`[3.3450, 6.2808]` and conversation-cluster CI `[2.8809, 6.6134]` points.
F1 changes by `-0.0790` points and both confidence intervals cross zero.

Thus the supported conclusion at top-k 5 is retrieval-only: complete B
retains a statistically supported evidence-recall advantage under a tight
context budget, without a supported final-answer F1 difference. This is
consistent with the primary top-k-25 result but does not establish full
cutoff robustness until matched top-k 10 and 50 pairs complete.

Both validators, official aggregation, 77 tests, 16 vendor hashes,
conversation-only graph and prompt audits, immutable query use, and
byte-identical significance reproduction pass. Cache counts remain 70 graphs
and 30 Memory indexes with zero deletion, overwrite, or rebuild. Snapshot:
`snapshots/v55_b_top5_all10/`.

Publication gate remains `continue`, `paper_ready=false`; preregister A@10
next.

The A@10 robustness baseline is now complete and valid. With the exact same
conversation-only Memory graphs, Memory vectors, frozen query vectors,
signed-cosine ranking, Reader, evaluator, and aggregation as corrected A@25,
reducing only top-k to 10 yields official F1 `41.7607%` and `recall_acc`
`68.9145%`.

Relative to A@25, this is a descriptive `-0.3075`-point F1 change and a
`-10.8323`-point recall change. It shows the expected evidence-budget
sensitivity but does not support an A/B top-k-10 claim before B@10 completes.

Both validators, official aggregation, 77 tests, 16 vendor hashes,
conversation-only graph and prompt audits, and immutable query use pass.
Cache preservation is exact at 70 graphs and 30 Memory indexes with zero
deletion, overwrite, or rebuild. Snapshot: `snapshots/v56_a_top10_all10/`.

Publication gate remains `continue`, `paper_ready=false`; preregister B@10
next.

The matched B@10 condition is now complete and valid. It preserves the exact
Memory text/indexes, frozen query vectors, top-k budget, Reader, evaluator,
serialization, and aggregation used by A@10, while activating the complete
conversation-derived Entity graph, Entity/semantic fusion, and chronological
sequence expansion.

B@10 reaches official F1 `42.1412%` and `recall_acc` `74.4847%`. Against
A@10, recall improves by `5.5702` points with paired-QA CI
`[4.2928, 6.8624]` and conversation-cluster CI `[4.2365, 6.7522]` points.
F1 changes by `+0.3805` points and both confidence intervals cross zero.

Thus the supported conclusion at top-k 10 is retrieval-only: complete B
retains a statistically supported evidence-recall advantage, without a
supported final-answer F1 difference. Combined with top-k 5 and the primary
top-k 25 pair, this is consistent evidence across three cutoffs; top-k 50 is
still required before declaring the full preregistered cutoff range complete.

Both validators, official aggregation, 77 tests, 16 vendor hashes,
conversation-only graph and prompt audits, immutable query use, and
byte-identical significance reproduction pass. Cache counts remain 70 graphs
and 30 Memory indexes with zero deletion, overwrite, or rebuild. Snapshot:
`snapshots/v57_b_top10_all10/`.

Publication gate remains `continue`, `paper_ready=false`; preregister A@50
next.

The first A@50 condition completed technically but failed its preregistered
resource gate. Both validators, official aggregation, 77 tests, 16 vendor
hashes, graph/prompt audits, immutable query use, and cache preservation pass.
Diagnostic F1 is `42.0064%` and `recall_acc` `86.7148%`.

Answer input usage was 5,188,935 tokens against a frozen maximum of 3,500,000.
Accordingly v58 is diagnostic only and contributes no paper metric or
top-k-50 comparison. Its output is preserved, and caches remain exactly 70
graphs and 30 Memory indexes. A newly preregistered A@50 condition with a
justified ceiling and new absent directory is required.

The v59 A@50 retry is now complete and valid. It retained the exact dataset,
conversation-only Memory graphs, Memory vectors, frozen query vectors,
signed-cosine retrieval, top-k 50, Reader, evaluator, serialization, and
aggregation used by v58; only the preregistered operational input-token
ceiling changed from 3.5M to 6M. Actual usage was 5,188,930, so the resource
gate passed.

Official F1 is `42.0782%`, official `recall_acc` is `86.7148%`, local
Categories 1–4 F1 is `51.9268%`, and local Categories 1–4 recall is
`89.4906%`. Both validators, 77 tests, 16 vendor hashes, graph/prompt audits,
official aggregation, immutable query use, and output isolation pass.

All old artifacts are preserved: graphs remain 70, Memory indexes remain 30,
and frozen query use is 1,986 hits with zero misses/live requests. v59 counts
as A@50 in the paper robustness matrix, while v58 remains diagnostic only.
No B-over-A claim at top-k 50 is supported until matched B@50 completes.
Publication gate remains `continue`, `paper_ready=false`.

The matched B@50 condition is now complete and valid. B@50 reaches official
F1 `41.7832%` and `recall_acc` `90.3306%`. Against v59 A@50, recall improves
by `3.6159` points with paired-QA CI `[2.7754, 4.4735]` and
conversation-cluster CI `[2.4603, 4.6426]` points. Overall F1 changes by
`-0.2950` points; both confidence intervals cross zero.

Thus the full preregistered cutoff family now supports the same calibrated
claim at top-k 5, 10, 25, and 50: complete conversation-derived Entity graph
retrieval significantly improves evidence recall over matched pure-Memory A,
but no overall final-answer F1 advantage is established.

Both validators, official aggregation, 77 tests, 16 vendor hashes,
conversation-only graph and prompt audits, resource limits, immutable query
use, and byte-identical significance reproduction pass. All old caches and
results remain preserved at 70 graphs and 30 Memory indexes with zero
deletion, overwrite, or rebuild. Snapshot:
`snapshots/v60_b_top50_all10/`.

Publication gate remains `continue`, `paper_ready=false`; the remaining
fusion-weight/sequence-scale sensitivities, O2 diagnostic, cost consolidation,
and final claim audit must complete before manuscript drafting.

The first sequence-scale sensitivity condition is complete and valid. At
top-k 25 with complete B and Entity/Semantic fusion `0.30/0.70`, reducing
chronological-neighbor scale from `0.5` to `0.25` yields official F1
`42.5150%` and `recall_acc` `84.1022%`. F1 changes `-0.0530` points and
recall `-0.3821` points versus primary B; both paired-QA and
conversation-cluster intervals cross zero for both metrics.

Both validators, official aggregation, 80 tests, 16 hashes, graph/prompt
audits, immutable query use, resources, and byte-identical inference pass.
All old artifacts remain at 70 graphs and 30 Memory indexes with zero
deletion, overwrite, or rebuild. Snapshot v67. Publication gate remains
`continue`, `paper_ready=false`; scale `1.0` and family correction remain.

The second sequence-scale point is complete and valid. Increasing scale from
`0.5` to `1.0` yields official F1 `43.1220%` and `recall_acc` `85.1609%`.
F1 changes `+0.5540` points: its paired-QA interval crosses zero while its
conversation-cluster interval is above zero. Recall changes `+0.6767` points
and both intervals cross zero. This estimator disagreement cannot support a
claim before the preregistered family Holm correction.

Both validators, official aggregation, 80 tests, 16 hashes, graph/prompt
audits, immutable query use, resources, and byte-identical inference pass.
All old artifacts remain at 70 graphs and 30 Memory indexes. Snapshot v68.
Publication gate remains `continue`, `paper_ready=false`; sequence-family
inference is next.

The preregistered sequence-scale family is now complete. After Holm
correction, neither scale `0.25` nor `1.0` differs from primary `0.5` in
overall F1 or `recall_acc` under either paired-QA or conversation-cluster
estimation. Scale `1.0` has the highest descriptive means, but its raw
cluster-F1 p=`0.0406` adjusts to `0.0812`.

Thus the supported conclusion is sensitivity robustness, not optimization:
within the tested `0.25–1.0` range, no family-corrected overall metric
difference is established. The complete identity-bound report is
byte-identically reproducible; caches remain 70 graphs and 30 indexes.
Snapshot v70. Publication gate remains `continue`, `paper_ready=false`.

The preregistered v75 O2 local-DRAGON diagnostic is now complete. It uses the
same conversation-only complete-B graph profile and frozen Reader/evaluator,
but replaces the primary semantic channel with pinned separate DRAGON
query/context encoders, raw vectors and dot products, and query-local min-max
calibration.

Across all 1,986 QA rows, O2 reaches F1 `42.4419%`, `recall_acc` `81.4261%`,
local Categories 1–4 F1 `51.7466%`, and local Categories 1–4 recall
`83.3521%`. Relative to primary local B, F1 is descriptively `-0.1260`
points and recall `-3.0582` points. No inferential or official-reference
claim is supported because O1 failed its reproduction tolerance and the
semantic/query artifacts differ.

Both validators, official aggregation, 109 tests, 16 vendor hashes,
conversation-only graph and prompt audits, immutable raw query use, resource
limits, and output isolation pass. The original 70 graphs and 30 Memory
indexes retain their exact set hashes; ten new protocol-isolated raw indexes
raise the total to 40. No old cache or result was deleted, overwritten, or
rebuilt. Snapshot: `snapshots/v75_o2_local_dragon_all10/`.

The supported O2 conclusion is narrow: under this local stack, raw DRAGON
calibration does not materially change descriptive answer F1 but yields lower
evidence recall than the primary semantic channel. Publication gate remains
`continue_to_cost_and_final_audit`, `paper_ready=false`.

v83 does not provide a cost conclusion. It stopped after all ten cold graphs
and nine of ten cold Memory indexes when the final index exhausted ten TLS
connection retries. More importantly, its persisted entity and embedding
provider totals were false zeros because the telemetry reducer did not match
the actual chat stage and the direct embedding client was not connected to
the observer. No retrieval, warm pass, final manifest, or report exists.

The failed state is preserved as diagnostic snapshot v84 and pushed at
`f7e7510`. The maximum defensible v83 claim is only that staged isolated
construction progressed to 19/128 before exposing connection and telemetry
failures. It contributes no paper cost evidence.

The v85 source repair establishes a stricter measurement contract: exact
provider usage for threaded entity extraction and Memory embedding, mandatory
embedding tokens, agreement between observer and native counters, and exact
read-only use of the same frozen query vectors as the formal primary-B
condition. Any query miss, live query embedding, incomplete question cache, or
new warm provider request fails finalization. This is tooling evidence only;
paper readiness remains false until a fresh isolated run and final claim audit
pass.

v86 remains a not-started condition, not a failed cost measurement. Its
scientific and measurement parameters are frozen, but the hard connectivity
gate failed before checkpoint initialization: chat failed through both the
configured proxy and direct connection, embedding returned no provider usage,
and the listening local proxy accepted CONNECT but could not complete TLS to
`api.openai.com:443`.

All four v86 output targets remain absent. No graph, Memory index, retrieval
batch, Reader call, judge call, or metric was run; no prior cache was deleted,
overwritten, or resumed. Consequently v86 supports no request, token, latency,
cost, or paper claim. The defensible next step is offline final-claim
preparation plus a later bounded connectivity retry, not initialization of a
partially viable paid run.

The v87 audit fixes the paper’s central claim boundary. Complete B improves
official evidence recall over matched A at all four preregistered cutoffs
between top-k 5 and 50. At the primary cutoff, the difference is `+4.7374`
points with both paired-QA and conversation-cluster intervals above zero.
None of the four matched cutoff comparisons supports an overall F1 difference.

The result therefore supports a graph-retrieval contribution within the
evaluated ten-conversation LoCoMo set, not a general final-answer improvement.
Component and speaker ablations provide mechanism-level recall evidence, while
input, fusion, and sequence families define the tested sensitivity limits.
O2 remains diagnostic, and no official-reference or state-of-the-art claim is
allowed.

All 18 frozen inputs match their preregistered SHAs, and the generic evidence
contract passes at level `robust`. Journal-neutral manuscript materials now
exist. At the v87 audit boundary, complete cold/warm cost was still absent.
Publication gate at that time:
`continue_to_cost`, `paper_ready=false`.

The replacement v93 staged cost run is now complete and valid. It executed all
128 cold/warm operations over ten conversations and 1,986 QA without deleting,
overwriting, or resuming any older cache. Cold construction used 5,873
conversation-Entity calls and 591 Memory-embedding calls; cold retrieval used
1,974 question-Entity calls. The matched warm replay made zero new provider
requests in all three cache-sensitive stages.

Cold retrieval averaged `1.5123` seconds per QA (p95 `2.6132`), whereas warm
retrieval averaged `0.004886` seconds (p95 `0.006270`), a `309.48×` mean
reduction. Both states covered the same 44 ordered batches, recorded 1,998
read-only query-vector hits, and had zero misses or live query embeddings.
Strict validation and byte-identical independent report reproduction pass, and
all quarantined artifact identities remain unchanged. Snapshot:
`snapshots/v97_v93_complete_cold_warm_cost/`.

This closes the measured request, token, latency, and storage gap for primary
B. Monetary cost remains intentionally unclaimed because provider price was
not frozen. Accuracy and statistical conclusions are unchanged.

The audited evidence package has now been converted to a seven-page,
two-column arXiv-style PDF. The build has resolved references, no overfull
boxes, and passed page-by-page visual inspection. Snapshot
`snapshots/v100_arxiv_pdf/` binds the LaTeX, bibliography, and PDF identities.
The technical paper is ready for distribution; identified submission still
requires user-supplied author and affiliation metadata.

The final literature expansion increases the verified bibliography from six
to 20 works. A dedicated Zotero collection
`Graph Memory Paper - Verified References` (key `TNDVXSZ8`) contains all 20
records after a successful 20/20 API read-back; no older library item was
deleted or overwritten. Every manuscript citation was checked against a
primary paper page or official proceedings record, and every bibliography
entry is used in the text.

The rebuilt artifact is an eight-page, two-column arXiv-style PDF with zero
final LaTeX warnings, no unresolved citations or references, and no visible
clipping or overlap across eight inspected page renders. The expanded
literature is used only for positioning: it does not introduce cross-system
score rankings, alter any frozen result, or broaden the v87/v98 claim
contract. Snapshot `snapshots/v101_verified_literature_pdf/` binds the Zotero,
source, bibliography, audit, and PDF identities.
