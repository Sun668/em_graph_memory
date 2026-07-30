# Next steps

The complete staged execution plan is in
[`PUBLICATION_PLAN.md`](PUBLICATION_PLAN.md). This file keeps the concise
checklist and publication gates; the linked plan defines the full experiment
matrix, execution order, validators, statistics, costs, and paper deliverables.

- [x] Vendor pinned official LoCoMo QA evaluation source.
- [x] Create `common` model-client layer.
- [x] Split `em_graph` into build, recall, and cache packages.
- [x] Group `common`, `em_graph`, and `locomo_eval` under top-level `code/`
      without making `code` a Python package.
- [x] Remove all ten `em_graph` root compatibility modules and migrate active
      callers to `build`, `recall`, and `cache`.
- [x] Add the single `locomo_eval` QA-recall protocol and EM implementation.
- [x] Migrate matched-stack runner and remove active duplicate evaluators.
- [x] Run dependency, vendor-hash, prompt, metric, cache, and context tests.
- [x] Preserve the earlier 199-QA `conv-26` B top-k 5/10/25/50 run as the v09
      historical diagnostic.
- [x] Rerun the `conv-26` A/B wiring preflight after the exact-top-k retrieval
      change from isolated absent directories. Both 199-QA conditions pass the
      external validator, graph and prompt audits, exact context checks, and
      provider-usage checks. Snapshot `v18_conv26_formal_ab_preflight`;
      publication gate `continue`, but the result is not paper-eligible.
- [x] Attempt the official DRAGON Dialog-RAG reproduction through its
      predeclared terminal gate. The dependency-matched corrective retrieval
      still failed Recall@25 tolerance, so the official-stack Reader/O2 work
      stopped before additional API cost. Merely setting
      `EM_GRAPH_EMBED_MODEL=dragon` is not itself an official reproduction:
      the reproduction must preserve the official dialog embedding text,
      DRAGON query/context encoders, unnormalized vectors, and dot-product
      ranking.
- [ ] Run O2-B-25 only as a matched local DRAGON-stack diagnostic. Do not
      describe it as a controlled comparison to the official table.
- [ ] Run structural/input ablations, top-k/fusion/sequence sensitivity,
      significance, and final cost experiments before the final paper review.
- [ ] Snapshot every metric-bearing result before any source edit.
- [x] Freeze the formal experiment foundation at commit `cad7bca`, verify the
      clean frozen evaluator and all 16 vendor hashes, and create recovery
      snapshot `v11_formal_foundation_recovery` before implementing tools.
- [x] Implement and test the external formal-result validator without changing
      `code/locomo_eval/`.
- [x] Validator verification: 9 focused tests,
      25 combined refactor/validator tests, strict all-10 and preflight modes,
      graph/reference audit separation, and structured rejection of invalid
      output directories. Snapshot `v12_formal_validator`.
- [x] Integrate the experiment-local official DRAGON implementation as
      `official_dragon.py` and add upstream parity tests without changing
      `code/locomo_eval/`. Six focused tests and 31 combined tests pass; a
      retrieval-only conv-26 k=25 check returned 25 unique contexts for all
      199 QA rows. Snapshot `v13_official_dragon_runner`.
- [x] Implement and test paired-bootstrap significance, exact ordered-context
      A/B_embed dense control, and strict cold/warm construction / retrieval /
      answer-cost reporting. Empty-evidence recall contributes zero with all
      QA retained in the denominator; 12 focused and 43 combined tests pass.
      Snapshot `v14_analysis_and_cost_tools`.
- [x] Complete formal graph-run orchestration and cost-event instrumentation,
      rerun the full stack, and freeze it before conv-26 A/B preflight.
- [x] Implement isolated formal graph orchestration; clean-source,
      absent-directory, cache-identity, audit, official-stats, and validator
      gates pass 3 focused / 46 combined tests. Publication gate:
      `continue_tooling_only`. Snapshot `v15_formal_graph_orchestration`.
- [x] Add usage/stage telemetry and freeze the stack. Run each subsequent
      metric stage only while the fixed publication stop gates remain green.
- [x] Add default-off provider usage telemetry for chat and embedding without
      changing evaluator behavior; 3 focused / 49 combined tests pass.
      Publication gate: `continue_tooling_only`. Snapshot
      `v16_provider_usage_telemetry`.
- [x] Connect telemetry to identity-bound warm formal measurement and a
      fresh-cache cold/warm probe; preserve zero-request hits, reject missing
      usage, and label overlapping stage walls. 57 combined tests pass.
      Publication gate: `continue_tooling_only`. Snapshot
      `v17_cost_orchestration`.
- [x] Freeze the complete formal stack, then run isolated conv-26 A/B
      preflight and apply the publication stop gates. No blocker was found.
- [x] Run O1 official DRAGON retrieval parity and apply
      the fixed ±1 point recall@25 and ±2 point F1 reproduction gate before
      starting M1. The gate failed on recall; M1 was not started.
- [x] Complete first formal O1-25 all-10 diagnostic from source `9511f94`.
      Validator passes 10/1986/446 and exact k=25; F1 `42.2` is within the
      official `41.0 ± 2` gate, but recall `78.11` exceeds the official
      `76.7 ± 1` gate by `0.41` points. The run is not accepted as an official
      reproduction. Snapshot `v19_o1_dragon_top25_runtime_mismatch`.
- [x] Correct O1 runtime identity outside `code/locomo_eval/`: bind Python,
      PyTorch, Transformers, tokenizers, NumPy, device, Hugging Face revisions,
      and actual Reader model; rebuild from a fresh dependency-matched cache
      and rerun O1 retrieval. The recall tolerance did not pass.
- [x] Implement and test the O1 runtime/cache/Reader identity gates. The source
      milestone passes 19 focused and 61 full tests; the frozen evaluator is
      unchanged. Snapshot `v20_o1_runtime_identity_gate`.
- [x] Create the pinned Python 3.9.18 environment from
      `requirements_o1_official.txt`, delete/recreate only the new corrective
      cache target, and rerun retrieval parity. Reader/formal O1-25 was
      intentionally not launched after the retrieval metric failed.
- [x] Resolve the environment preflight conflict: the first isolated install
      correctly rejected current-only `nltk==3.10.0` under Python 3.9.18.
      Align NLTK, regex, and tqdm to the pinned upstream versions 3.8.1,
      2022.10.31, and 4.64.1 before retrying. Snapshot
      `v21_o1_environment_resolution`.
- [x] Complete dependency-matched O1 retrieval: 10 samples, 1986 QA, exact
      25 unique contexts, official serialized-contribution Recall@25
      `78.113293%`. This is 1.413293 points from official `76.7` and fails the
      fixed ±1 gate. Top-25 sets match v19 on 1986/1986 rows; nine internal
      orders differ. Publication gate `stop`; snapshot
      `v22_o1_corrective_retrieval_stop`.
- [x] Record the user's explicit authorization to waive the v22 O1
      exact-reproduction stop and resume at M1. O1 remains unaccepted and may
      be cited only as an external-reference diagnostic. All remaining
      performance, significance, graph/formal, and dense-control gates stay
      active. Snapshot `v23_user_authorized_o1_waiver`.
- [x] Complete formal all-10 M1-A at top-k 25 from source `3e3a33b`:
      validator passes 10/1986/446, exact ordered top-25 contexts, official
      stats parity, graph constraint, and prompt budget. Official overall F1
      is `42.2642%`, Recall@25 is `79.7468%`, and local Categories 1–4 F1 is
      `50.9979%`. This is the matched baseline, not a method-effectiveness
      conclusion. Snapshot `v24_m1_a_all10`; publication gate `continue`.
- [x] Complete formal all-10 M1-B at top-k 25 from source `484ccf0`:
      validators pass 10/1986/446, exact ordered top-25 contexts, official
      stats parity, graph constraint, and 2,410/5,000 prompt budget. Official
      F1 is `42.6772%`, Recall@25 is `84.3415%`, and local Categories 1–4 F1
      is `52.2448%`. Recall clears 75.7%, but F1 misses the fixed 49.6% floor
      by 6.9228 points. Publication gate `stop`; snapshot
      `v25_m1_b_official_performance_stop`.
- [x] Apply the pre-significance terminal gate. No paired/cluster bootstrap,
      ablation, robustness, O2, or final cost run was launched after the
      failure.
- [x] Correct the v25 decision after direct inspection of the final LoCoMo
      paper: Table 2's `51.6` is `gpt-4-turbo` 128K long-context, while
      Table 3's same-Reader-class RAG reference is DRAGON +
      `gpt-3.5-turbo` Dialog@25 at F1 `41.0` / Recall `76.7`. Retire the
      cross-model `49.6` stop, preserve v25 metrics, and resume the full
      experiment matrix. Snapshot `v26_cross_model_gate_correction`.
- [x] Run the predeclared 10,000-resample paired-QA and
      conversation-cluster B-versus-A significance report from immutable
      v24/v25 formal outputs. Recall improves significantly by 4.5947 points;
      overall F1 improves by 0.4130 points but is not significant. All
      validation and recall-parity checks pass. Snapshot
      `v27_primary_ab_significance`.
- [x] Run all-10 top-25 B_embed and enforce exact per-QA ordered context-id
      equality against formal M1-A. The standalone formal validator passed,
      but the dense-control gate failed on 61/1986 rows. Snapshot
      `v28_m2_embed_dense_control_failure`; the result is diagnostic only.
- [x] Repair the stale whole-file query embedding cache lost-update bug, bind
      a complete cache hash and dataset-question coverage to each formal run,
      and test cache sharing/identity/telemetry without changing the frozen
      evaluator. Locked merge/atomic writes, a strict immutable query
      artifact, runtime usage validation, and the same-artifact dense gate pass
      68 tests. Snapshot `v29_query_embedding_artifact_gate`.
- [x] Commit/push v29, delete only the exact corrupt text cache, and generate
      the all-10 query artifact and build report from absent paths. Snapshot
      `v30_query_embedding_artifact_build`: 1986/1986 ordered QA coverage,
      1974 unique vectors, SHA `bef99a…6f9f`, independent validation pass.
- [x] Run a retrieval-only all-10 A/B_embed check with the exact same artifact
      and require 1986/1986 ordered context equality before formal answer runs.
      The first attempt passed 1,347 QA, then stopped while unnecessarily
      reverse-seeding conflicting historical index vectors into the context
      cache. Snapshot `v31_dense_preflight_context_seed_conflict`; disable
      context-cache writes for strict loaded-index runs and repeat.
      The source repair is complete with 69 tests in
      `v32_strict_run_no_context_seed`; the partial context cache was deleted
      and the repeat from QA 0 passed in v33.
- [x] Repeat corrected all-10 A/B_embed retrieval gate: 1986/1986 ordered
      contexts equal, 3972/3972 artifact hits, zero misses/live requests.
      Snapshot `v33_corrected_dense_retrieval_gate`.
- [x] Rerun matched A and B_embed from absent directories and require exact
      ordered context equality on all 1986 QA rows. Corrected A is complete
      and valid in `v34_corrected_m1_a_all10`: F1 `42.0681%`, Recall@25
      `79.7468%`, 1986/1986 query hits, zero misses/live embedding requests,
      69 tests and 16 vendor hashes passed. Corrected B_embed run02 completed
      in `v36_corrected_b_embed_all10_dense_control`: F1 `42.0677%`,
      Recall@25 `79.7468%`, and all 1986 ordered contexts exactly equal A
      with the same query artifact and zero mismatches. Then rerun B
      and the primary A/B significance analysis under the same bound
      query-vector artifact before continuing B_gate, B_gate_seq, B_entity,
      and B_noseq.
      The first B_embed formal attempt produced zero answers and aborted after
      ten Reader connection errors; it is frozen as non-metric v35. The
      connectivity preflight and fresh run02 subsequently passed.

## Migration pause and resume order

- [x] Freeze v36, save the exact 64-file transfer manifest, and generate/test
      `outputs/migration/graph_memory_locomo_resume_2026_07_28.zip`.
- [x] Stop after committing and pushing v36. Do not launch B on the source
      machine.
- [x] On the target machine, restore the ZIP from the repository root and
      verify its SHA-256, all 64 relative paths, query artifact SHA, 69 tests,
      16 vendor hashes, and absence of the general writable context cache.
- [x] Run corrected all-10 B from a new absent condition directory with the
      exact v36 query artifact and committed parameters.
- [x] Validate B independently, audit graph/prompt/cache identities, and
      freeze immutable snapshot `v37_corrected_m1_b_all10`. Official F1
      `42.5680%`, Recall@25 `84.4842%`, graph constraint and prompt budget
      pass. Commit/push completed at `de14040`.
- [x] Preserve existing corrected A rather than rerun it. Implement a
      fail-closed relocation manifest bound to v34 metric-artifact hashes and
      the immutable query artifact. Without the manifest validation fails; with
      it, the full 10/1986/446 validator passes and remains paper eligible.
      Snapshot `v39_relocation_validation_gate`; 75 tests and 16 vendor hashes
      pass.
- [x] Run corrected A/B paired-QA and conversation-cluster significance with
      10,000 resamples and seed `20260727`. Snapshot v40: Recall@25
      `+4.7374` points with both CIs above zero; overall F1 `+0.4998` points
      with both CIs crossing zero. Independent report reproduction is
      byte-identical.
- [x] Run all-10 B_gate from an absent isolated directory. Snapshot v41:
      official F1 `41.8275%`, Recall@25 `79.2853%`; both validators, 75 tests,
      16 vendor hashes, graph/prompt audits, and exact query artifact pass.
      Full B exceeds B_gate descriptively by `+0.7405` F1 and `+5.1989`
      Recall@25 points.
- [x] Commit/push v41 as `1bb800b`.
- [x] Run all-10 B_gate_seq from an absent isolated directory. Snapshot v42:
      official F1 `41.7666%`, Recall@25 `79.7217%`; sequence versus B_gate is
      `-0.0609` F1 and `+0.4364` Recall@25 points. Both validators, 75 tests,
      16 vendor hashes, graph/prompt audits, and exact query artifact pass.
- [x] Commit/push v42 as `31d8c78`.
- [x] Run all-10 B_entity from an absent isolated directory. Snapshot v43:
      official F1 `37.4899%`, Recall@25 `67.0208%`; Entity-only versus B is
      `-5.0780` F1 and `-17.4634` Recall@25 points. Both validators, 75 tests,
      16 vendor hashes, and graph/prompt audits pass.
- [x] Commit/push v43 as `cabad81`.
- [x] Run all-10 B_noseq from an absent isolated directory. Snapshot v44:
      official F1 `42.0542%`, Recall@25 `82.8114%`; disabling sequence loses
      `0.5137` F1 and `1.6728` Recall@25 points versus B.
- [x] Commit/push v44 as `f92fa51`, lock inference tooling as v45/`6557f83`,
      and run the formal Holm report.
- [x] Component-family result: all four Recall@25 hypotheses pass Holm under
      both estimators; only semantic-signal F1 passes Holm. Independent
      reproduction is byte-identical. Snapshot v46.
- [x] Commit/push v46 as `8fa1820` and begin all-10, top-k-25 input ablations.
- [x] Complete all-10 `A_no_caption` from an absent condition directory.
      Snapshot v47: official F1 `41.6027%`, Recall@25 `79.5545%`; caption
      removal versus A is `-0.4654` F1 and `-0.1923` Recall@25 points. Both
      validators, 76 tests, 16 vendor hashes, graph/prompt audits, and exact
      query-artifact use pass.
- [ ] Commit/push v47, then run all-10 `B_no_caption` from a new absent
      condition directory.
- [ ] Continue remaining input ablations, top-k/fusion sensitivity, O2 diagnostic, and
      cost/final publication audit in the predeclared order.
- [x] Complete fusion sensitivity `0.10/0.90`: valid all-10 F1 `42.2040%`,
      `recall_acc` `82.1780%`; versus primary `0.30/0.70`, F1 is unchanged
      within uncertainty and recall is `2.3062` points lower with both raw
      intervals below zero. Snapshot v61.
- [x] Commit/push v61 and complete fusion `0.50/0.50`: valid all-10 F1
      `42.2440%`, `recall_acc` `84.3280%`; versus primary `0.30/0.70`, all
      overall paired/cluster intervals cross zero. Snapshot v62.
- [x] Commit/push v62 and source-lock the predeclared two-comparison fusion
      family by metric and estimator. Snapshot v63; 19/19 focused and 79/79
      full tests pass.
- [x] Preserve the v64 query-identity audit failure, repair and lock v65, then
      generate a valid byte-identical fusion-family report. `0.10/0.90`
      significantly lowers recall after Holm; `0.50/0.50` and both F1
      contrasts are non-significant. Snapshot v66.
- [ ] Commit/push v66, then freeze and run sequence scales `0.25` and `1.0`
      against primary `0.5`, followed by the predeclared two-comparison Holm
      family.

## Closed publication-readiness standard

No additional change to the frozen LoCoMo prompt, answer generation, F1,
`recall_acc`, rounding, or aggregation logic is currently known to be
necessary. Do not modify `code/locomo_eval/` in anticipation of a possible
difference. A new protocol requirement may be added only when a concrete
comparison against the pinned upstream source demonstrates an actual mismatch.

The experimental package is ready to support paper writing when all of the
following gates pass:

1. **Official comparability**
   - the pinned LoCoMo evaluator and vendor hashes pass;
   - the official DRAGON Dialog-RAG baseline is reproduced, or the official
     paper number is explicitly labeled as an external reference rather than a
     controlled baseline;
   - the official-stack EM-Graph comparison changes retrieval only;
   - reader context, answer protocol, token-F1, `recall_acc`, per-row rounding,
     and official aggregation remain unchanged.
2. **Method effectiveness**
   - all-10 A and B runs complete at the predeclared primary `top_k=25`;
   - B is compared with B_embed, B_gate, B_gate_seq, B_entity, and B_noseq;
   - caption, normalized/time-aware text, and speaker input ablations complete;
   - A and B complete top-k 5/10/25/50 sensitivity;
   - fusion sensitivity and construction/retrieval cost are reported.
3. **Statistical evidence**
   - paired QA bootstrap and conversation-cluster bootstrap confidence
     intervals are reported;
   - if both the B-minus-A recall and F1 95% confidence-interval lower bounds
     are greater than zero, the paper may claim significant retrieval and
     answer-quality improvement;
   - if only recall passes, the paper may claim retrieval improvement only;
   - if both intervals cross zero, the method has not been shown to outperform
     A.
4. **Formal-run acceptance**
   - every condition starts in its own absent or empty output directory and
     never resumes an earlier answer/result;
   - the source commit, exact command, resolved parameters, data, models, and
     run id are recorded;
   - all-10 output contains 1986 QA rows and 446 Category-5 rows;
   - prediction, F1, recall, and context fields are complete;
   - context ids contain no duplicates and each row contains exactly
     `min(top_k, available dialogs)` ids;
   - the conversation-only graph audit and prompt-budget audit pass;
   - every reported result has a matching immutable snapshot.

## Claims allowed after the gates pass

| Evidence | Maximum supported claim |
|---|---|
| Frozen evaluator and valid all-10 output | The result uses the LoCoMo official QA evaluation protocol. |
| Reproduced official DRAGON baseline | The experimental environment is directly calibrated against the official Dialog-RAG result. |
| Matched official-stack EM-Graph beats DRAGON | EM-Graph outperforms the official Dialog-RAG baseline under the matched stack. |
| B-minus-A recall and F1 confidence intervals are both above zero | EM-Graph significantly improves retrieval and final answer quality over the matched dense Memory baseline. |
| Only the recall confidence interval is above zero | EM-Graph significantly improves retrieval; no significant final-answer improvement is claimed. |
| Component ablations degrade as hypothesized | The corresponding Entity gate, score fusion, chronological sequence, or input component has empirical support. |
| Top-k, parameter, and per-conversation results are stable | The improvement is not confined to one cutoff, one parameter point, or a small number of conversations. |

When these gates and their expected statistical signals pass, the experimental
evidence is sufficient to write and submit the paper without another known
LoCoMo-alignment repair cycle. This is a methodological publication-readiness
standard, not a guarantee of peer-review acceptance.

The remaining work is paper production rather than benchmark repair: freeze
tables and figures, describe the method and complexity, report models,
parameters, data hash, source commit and run date, document the official
Category-5 limitation and the paper/code model-name discrepancy, include cost,
limitations and failure cases, and verify every manuscript number against the
archived result files.

## Paused after B_no_caption

- [x] Commit and push v47 as `4b1ff41`.
- [x] Run and independently validate all-10 `B_no_caption` from absent
      isolated directory
      `formal_all10_M3_B_no_caption_top25_4b1ff41_qfrozen_run01`.
- [x] Record official F1 `41.7394%`, Recall@25 `84.3040%`, local Categories
      1–4 F1 `50.6458%`, and local Categories 1–4 Recall@25 `85.0180%`.
- [x] Verify both validators, official aggregation, exact query use, 76/76
      tests, 16/16 hashes, graph constraint, and prompt budget; freeze v48.
- [ ] Do not start `A_raw_text` or another condition until the user explicitly
      asks to resume. Execution is paused after the v48 commit/push.

## Resumed after v48

- [x] Freeze and commit the all-10 `A_raw_text` parameter snapshot before
      cache construction or formal generation.
- [x] Build 10 conversation-only raw-text Memory graphs and 10 new
      identity-bound indexes without deleting old artifacts. Graph files stay
      at 50; indexes increase from 20 to 30.
- [x] Complete and independently validate
      `formal_all10_M3_A_raw_text_top25_57a5f28_qfrozen_run01` from an absent
      directory: official F1 `42.4579%`, Recall@25 `79.2849%`, local
      Categories 1–4 F1 `51.5074%`, and local Categories 1–4 Recall@25
      `82.1492%`.
- [x] Verify both validators, 76/76 tests, 16/16 hashes, exact query use,
      graph constraint, prompt budget, cache preservation, and token/request
      limits; freeze snapshot v49.
- [ ] Commit and push v49.
- [ ] Freeze a new complete parameter snapshot, then run matched all-10
      `B_raw_text` from a new absent output directory. Do not infer raw-text
      family significance until B_raw_text is complete.
- [x] Commit/push v49 as `4965acd`, freeze/commit v50 parameters as
      `ee8255d`, and build 10 new B_raw_text graphs without deleting any old
      cache or creating a new Memory index.
- [x] Complete and independently validate all-10 `B_raw_text`: official F1
      `42.8087%`, Recall@25 `84.2371%`, local Categories 1–4 F1 `52.1546%`,
      and local Categories 1–4 Recall@25 `84.7694%`.
- [x] Run the two predeclared pairwise bootstrap reports. Time annotation
      inside B is not significant; matched raw-text B-over-A Recall@25 is
      significant under paired-QA and conversation-cluster estimators, while
      F1 is not.
- [x] Freeze v50 evidence and v51 input-family Holm tooling; focused analysis
      tests pass 17/17.
- [ ] Commit/push v50-v51, generate the locked input-family Holm report, then
      snapshot/commit it before starting `B_no_speaker`.
- [x] Commit/push v50-v51 as `fff582e`.
- [x] Generate and independently reproduce the v52 input-family report.
      B-over-A raw-text Recall@25 survives Holm under both estimators;
      F1 and the time-annotation effect do not.
- [ ] Commit/push v52, then freeze B_no_speaker parameters before any build
      or formal generation.
- [x] Commit/push v52 as `6bdcaf0` and freeze v53 B_no_speaker parameters.
- [x] Commit/push the v53 parameter freeze as `52a8091`, then build/audit ten
      no-speaker graphs with zero extraction or Memory-embedding requests.
- [x] Complete and independently validate all-10 B_no_speaker: F1 `42.3265%`,
      Recall@25 `83.0021%`, local Categories 1–4 F1 `51.8574%`, and local
      Categories 1–4 Recall@25 `83.0144%`.
- [x] Confirm no cache deletion: graphs `60→70`, indexes remain `30`, and all
      ten canonical Memory indexes are reused read-only.
- [x] Run and byte-identically reproduce the predeclared comparisons. Speaker
      removal causes a significant `-1.4822`-point recall change versus B but
      no significant F1 change; B_no_speaker still has significant
      `+3.2552`-point recall versus corrected A.
- [x] Verify both validators, 77/77 tests, 16/16 hashes, official aggregation,
      graph constraint, prompt budget, and zero query misses/live requests;
      freeze v53.
- [ ] Commit/push completed v53 evidence, then preregister the next top-k
      robustness/sensitivity condition before generating new metrics.
- [x] Commit/push v53 as `c4e3ad2`, freeze v54 A@5 parameters, and commit/push
      the parameter contract as `a464ad5`.
- [x] Complete and independently validate all-10 A@5: official F1 `39.9053%`,
      `recall_acc` `59.3584%`, local Categories 1–4 F1 `46.3974%`, and local
      Categories 1–4 recall `63.1401%`.
- [x] Confirm no cache mutation: graphs remain `70`, Memory indexes remain
      `30`, and build/extraction/embedding/deletion/overwrite counts are zero.
- [x] Verify both validators, 77/77 tests, 16/16 hashes, official aggregation,
      immutable query use, graph constraint, and prompt budget; freeze v54.
- [x] Commit/push completed v54 as `dff9df4`, freeze/commit v55 B@5 parameters
      as `753113f`, and run matched B@5 without deleting or rebuilding shared
      caches.
- [x] Complete and independently validate B@5: official F1 `39.8264%`,
      `recall_acc` `64.1667%`, local Categories 1–4 F1 `46.4255%`, and local
      Categories 1–4 recall `65.2176%`.
- [x] Reproduce the 10,000-resample, seed-`20260727` A@5/B@5 report
      byte-identically. B gains `4.8083` recall points with paired-QA and
      conversation-cluster intervals above zero; F1 differs by `-0.0790`
      points and is not significant.
- [x] Verify both validators, 77/77 tests, 16/16 hashes, official aggregation,
      graph/prompt audits, immutable query use, and cache preservation at
      70 graphs / 30 Memory indexes; freeze v55.
- [x] Commit/push completed v55 as `0eee9b8`, freeze/commit v56 A@10
      parameters as `45bde5d`, and run A@10 from a new absent directory.
- [x] Complete and independently validate A@10: official F1 `41.7607%`,
      `recall_acc` `68.9145%`, local Categories 1–4 F1 `49.5044%`, and local
      Categories 1–4 recall `72.3469%`.
- [x] Verify both validators, 77/77 tests, 16/16 hashes, official aggregation,
      graph/prompt audits, immutable query use, and cache preservation at
      70 graphs / 30 Memory indexes; freeze v56.
- [ ] Commit/push completed v56 evidence, then freeze B@10 parameters before
      starting the matched formal condition.
- [x] Commit/push completed v56 as `54ae6a9`, freeze/commit v57 B@10
      parameters as `35691fb`, and run matched B@10 without deleting or
      rebuilding shared caches.
- [x] Complete and independently validate B@10: official F1 `42.1412%`,
      `recall_acc` `74.4847%`, local Categories 1–4 F1 `50.5795%`, and local
      Categories 1–4 recall `75.2771%`.
- [x] Reproduce the 10,000-resample seed-`20260727` A@10/B@10 report
      byte-identically. B gains `5.5702` recall points with both intervals
      above zero; F1 differs by `+0.3805` points and is not significant.
- [x] Verify both validators, 77/77 tests, 16/16 hashes, official aggregation,
      graph/prompt audits, immutable query use, and cache preservation at
      70 graphs / 30 Memory indexes; freeze v57.
- [ ] Commit/push completed v57 evidence, then freeze A@50 parameters before
      starting the next formal condition.
- [x] Commit/push v57, freeze v58 A@50, pass dual preflight, and complete the
      isolated condition with all old caches preserved.
- [x] Mark v58 diagnostic only because 5,188,935 Reader input tokens exceeded
      the preregistered 3,500,000 maximum despite all validity checks passing.
- [ ] Commit/push v58 failure evidence, then preregister and rerun A@50 under
      an evidence-based ceiling in a new absent output directory.
- [x] Commit/push v58 as `e7a5abf`, freeze/commit v59 as `43d9e2e`, and run
      the scientifically identical A@50 retry with a 6M operational ceiling
      from a different absent output directory.
- [x] Validate v59 as paper-eligible: F1 `42.0782%`, `recall_acc` `86.7148%`,
      local Categories 1–4 F1 `51.9268%`, local Categories 1–4 recall
      `89.4906%`, and 5,188,930 input tokens below the 6M ceiling.
- [x] Confirm no cache deletion, overwrite, or rebuild: 70 graphs, 30 Memory
      indexes, 1,986/1,986 query hits, and zero misses/live requests.
- [ ] Commit/push v59 evidence, then freeze and run matched B@50 from a new
      absent directory while preserving every old cache and result.
- [x] Commit/push v59 as `6afa882`, freeze/commit v60 B@50 as `acb4277`, and
      complete the isolated formal run with all old artifacts preserved.
- [x] Validate B@50 as paper-eligible: F1 `41.7832%`, `recall_acc`
      `90.3306%`, local Categories 1–4 F1 `52.1958%`, local Categories 1–4
      recall `90.9394%`, and 5,251,555 input tokens below the 6M ceiling.
- [x] Reproduce A/B@50 inference byte-identically. Recall gains `3.6159`
      points with both intervals above zero; overall F1 changes `-0.2950`
      points with both intervals crossing zero.
- [x] Close the top-k 5/10/25/50 robustness matrix with significant B-over-A
      recall at every cutoff and no supported overall F1 effect.
- [x] Confirm no cache/result deletion, overwrite, or rebuild: 70 graphs, 30
      Memory indexes, prior v58/v59 present, and zero query misses/live calls.
- [ ] Commit/push v60, then preregister the first fusion-weight or
      sequence-scale sensitivity condition before generating new metrics.

### 2026-07-29 sequence scale 0.25

- v67 completes the first preregistered sequence point from an absent,
  isolated directory: F1 `42.5150%`, `recall_acc` `84.1022%`, local
  Categories 1–4 F1 `52.1005%`, local recall `84.9201%`.
- Against primary scale `0.5`, neither F1 (`-0.0530` points) nor recall
  (`-0.3821` points) has paired or cluster intervals excluding zero.
- Both validators, 80 tests, 16 hashes, graph/prompt/resource gates, exact
  query use, and byte-identical reproduction pass.
- No cache/result was deleted, overwritten, or rebuilt: 70 graphs, 30
  indexes, zero query misses/live requests. Snapshot v67.
- Commit/push v67, then freeze/run scale `1.0` before family correction.

### 2026-07-29 sequence scale 1.0

- v68 completes the second preregistered sequence point: F1 `43.1220%`,
  `recall_acc` `85.1609%`, local Categories 1–4 F1 `52.7534%`, local recall
  `85.2140%`.
- F1 improves descriptively by `+0.5540` points, but paired and cluster
  estimators disagree before correction. Recall changes `+0.6767` points
  with both intervals crossing zero.
- Both validators, 80 tests, 16 hashes, query identity, graph/prompt/resource
  gates, and byte-identical reproduction pass.
- No artifact deletion/overwrite/rebuild: 70 graphs, 30 indexes, zero query
  misses/live requests. Snapshot v68.
- Verify/commit/push v68, then lock and run sequence-family Holm inference.

### 2026-07-29 sequence-family inference

- Locked v69 before analysis and generated the two-comparison family report.
- No F1 or recall comparison survives Holm under paired or cluster
  estimation; scale-1.0 raw cluster-F1 p=`0.0406` adjusts to `0.0812`.
- Report identity contains all ten graph/index records and query SHA
  `bef99a…6f9f`; independent reproduction is byte-identical.
- Supported wording: no adjusted overall-metric sensitivity over scales
  `0.25–1.0`; scale `1.0` is descriptive only, not a significant optimum.
- Freeze/commit/push v70, then complete O2, cost, claim audit, and paper work.

### 2026-07-29 after O2

- [x] Complete v75 O2 on all 1,986 QA and independently validate the isolated
      result.
- [x] Preserve the original 70 graph and 30 Memory-index sets byte-for-byte;
      add only ten identity-isolated raw DRAGON indexes.
- [x] Record the O2 claim boundary: local-stack diagnostic only, not an
      official DRAGON reproduction or controlled comparison.
- [ ] Commit and push the frozen v75 result.
- [ ] Run the preregistered matched cold/warm cost probe without deleting or
      overwriting existing caches or formal outputs.
- [ ] Consolidate cost telemetry and verify request/token/wall-time
      provenance.
- [ ] Run the final publication claim/evidence audit, then generate manuscript
      tables, calibrated claims, limitations, and the paper draft materials.

### 2026-07-29 after v83 failure

- [x] Preserve the 19/128 fail-closed checkpoint, 10 graphs, 9 indexes, TLS
      failure excerpt, and false-zero telemetry audit in snapshot v84.
- [x] Commit/push v84 as `f7e7510` without resuming or deleting v83.
- [x] Connect direct embedding usage to the observer, correctly reduce
      threaded graph chat calls, and require embedding input-token provenance.
- [x] Align the cost runner to the exact formal query artifact with strict
      read-only lookup, no text-cache fallback, and zero live query embeddings.
- [ ] Freeze/verify/commit/push source-only v85 after all regression and
      frozen-evaluator checks pass.
- [x] Freeze/verify/commit/push source-only v85 as `22ba54c`.
- [x] Preserve bounded chat and embedding TLS-EOF diagnostics as a launch
      blocker, not as a partially started experiment.
- [x] Freeze v86 against committed source, exact query/warm identities, and
      four absent paths; parameter SHA `78ab5dd2…a104`.
- [x] Commit/push v86 as `6cda26a`, then rerun the bounded live telemetry
      preflights.
- [x] Preserve the failed chat/embedding/TLS preflight as a not-started v86
      result with all four exact outputs absent and all old caches untouched.
- [ ] While connectivity is unavailable, complete the offline final
      publication claim/evidence audit and prepare the result tables/claim
      boundaries that do not depend on the missing cost report.
- [ ] When connectivity returns, pass minimal chat and embedding telemetry
      checks, including embedding observer/native parity, before initialization.
- [ ] Execute v86 one atomic operation at a time; inspect the first graph and
      index events before authorizing the remaining paid work.
- [ ] Validate/reproduce/freeze/commit/push the complete v86 report and only
      then begin final claim preparation and manuscript drafting.

### 2026-07-29 after v87 publication audit

- [x] Verify 18 frozen result identities and pass the generic claim-evidence
      contract at level `robust`.
- [x] Set the headline boundary to evidence-recall improvement across top-k
      5/10/25/50 with no supported overall F1 improvement.
- [x] Record supported component, speaker, input, fusion, and sequence findings
      and preserve the null and failed-control results.
- [x] Create the evidence ledger, paper tables, and journal-neutral
      Methods/Results/Discussion/Limitations/Conclusion materials.
- [x] Commit and push v87 as `1e71085`.
- [ ] Restore external API connectivity, pass both telemetry preflights, run
      and validate v86, and insert the complete cost table.
- [ ] Select the target journal, create the journal-format record, add verified
      literature positioning, draft the final Abstract, and run the full
      submission gate.

### 2026-07-30 after v93 cold/warm cost

- [x] Complete all 128 staged cold/warm operations over ten conversations and
      1,986 QA.
- [x] Verify 44/44 paired retrieval batches per state, 1,998 read-only query
      hits per state, zero misses, and zero live query embeddings.
- [x] Verify zero new warm conversation-Entity, Memory-embedding, and
      question-Entity requests.
- [x] Strictly validate and independently reproduce the final report
      byte-identically; verify every quarantined cache/checkpoint identity.
- [x] Insert the measured request, token, latency, and storage table into the
      evidence ledger and journal-neutral manuscript materials.
- [ ] Commit/push v97 and the manuscript update, then run the final
      post-cost claim audit and submission-readiness check.
- [x] Commit/push v97 as `e0512a6` and pass the post-cost generic claim
      contract at the unchanged `robust` ceiling.
- [x] Mark the journal-neutral evidence package ready for manuscript drafting;
      keep submission readiness false pending venue and literature work.
- [ ] Select a target journal and add verified literature positioning,
      venue-specific formatting, citations, and the final Abstract.
- [x] Verify six primary literature sources and write the complete
      journal-neutral English manuscript with a 195-word final Abstract.
- [x] Audit all primary, robustness, component, and cost numbers against v98
      evidence; preserve every unsupported-claim exclusion.
- [ ] Replace author placeholders and select a target venue before producing a
      submission-formatted version.
- [x] Produce and verify the seven-page arXiv-style PDF in
      `outputs/paper/entity_memory_graph_retrieval_arxiv.pdf`.
- [x] Collect 20 directly relevant papers in the dedicated Zotero collection,
      verify 20/20 records after write-back, and preserve all pre-existing
      library records.
- [x] Verify every citation against a primary or official source, expand the
      Related Work section, and ensure all 20 bibliography entries are cited.
- [x] Rebuild and inspect the expanded eight-page PDF; freeze v101 without
      changing experiments, caches, metrics, or claim eligibility.
- [ ] Replace the anonymous author, affiliation, acknowledgment, funding, and
      contribution placeholders before uploading an identified arXiv version.
