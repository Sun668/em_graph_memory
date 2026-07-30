# v39 — fail-closed relocation validation gate

Decision date: 2026-07-28 Asia/Shanghai.
Base commit: `02f27348f0b6461466255019433fcfde3d18bf56`.
Base tree: `f7acca654edae1d687bd5ed5bfc10d54dfd0526d`.

This source milestone makes the accepted corrected A usable after repository
migration without rerunning any answer generation and without editing any
historical formal JSON.

## Behavior

Direct same-path formal validation is unchanged. A configured/actual output
directory mismatch still fails by default. A relocated condition passes only
when the caller explicitly provides an external
`locomo_formal_relocation_v1` manifest.

The manifest must prove:

- exact run id and condition fingerprint;
- exact original output directory from immutable `run_config.json`;
- exact current condition directory;
- exact SHA-256 of a pre-existing experiment snapshot;
- matching source commit and dataset hash between that snapshot and run config;
- three-way SHA equality among manifest, source snapshot, and current files
  for `run_config.json`, predictions, stats, graph audit, and query usage;
- exact original query-artifact path from run config;
- exact SHA equality among manifest, run config, and relocated query artifact.

After those identity checks, the validator still performs its complete normal
validation over the current dataset, sample/QA order, 1,986/446 counts,
top-k context completeness and uniqueness, official stats aggregation,
query-artifact dataset/model/order coverage, runtime query use, graph/no-test
audit, and prompt budget.

The significance loader accepts separate optional relocation manifests for A
and B. Its condition identity records whether relocation was used, the
manifest SHA, and the source snapshot SHA. The dense-control loader has the
same capability.

The CLI refuses to use the condition's own `validation.json` as the default
report destination when relocation is enabled; an external `--report` is
required, so validating a migrated historical result cannot overwrite it.

## Exact validation commands

Default fail-closed check:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
  .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/validate_formal_result.py \
  --condition-dir \
    outputs/locomo_formal/formal_all10_M1_A_top25_76fcf5b_qfrozen_run01 \
  --data-file data/locomo10.json \
  --report /private/tmp/a_without_relocation_manifest_validation.json
```

This correctly failed only the two absolute-path-dependent checks: output
directory identity and query-artifact location. All 10 samples, 1,986 QA rows,
446 Category-5 rows, metrics, contexts, official stats, graph audit, and prompt
checks were otherwise valid.

Verified relocation check:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
  .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/validate_formal_result.py \
  --condition-dir \
    outputs/locomo_formal/formal_all10_M1_A_top25_76fcf5b_qfrozen_run01 \
  --data-file data/locomo10.json \
  --relocation-manifest \
    experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v39_relocation_validation_gate/a_relocation_manifest.json \
  --report /private/tmp/a_with_relocation_manifest_validation.json
```

This passed with `paper_metric_eligible=true`,
`graph_claim_eligible=true`, and directory mode `verified_relocation`.
Manifest SHA-256:
`9c65b3de51b9e80131570196ce499db8459099323acef181d5ccd3417c5b2672`.
The source v34 result SHA and immutable query artifact SHA are respectively
`5e114d1e…58a56` and `bef99a91…986f9f`.

The default-failure and verified-pass report hashes are respectively
`11b9234f…ed4f` and `bfc617f9…1173`.

## Test and compliance audit

The suite passes 75/75 tests. New tests cover:

- relocation rejected without a manifest;
- valid source-snapshot-bound relocation accepted;
- metric artifact byte tampering rejected;
- source snapshot SHA and current path mismatch rejected;
- query-artifact path/hash remap mismatch rejected;
- significance rejected without, then accepted with, explicit relocation
  proof.

All 16 frozen vendor hashes pass and `code/locomo_eval/` has no diff. The
source change adds no prompt, model call, graph input, metric formula, or
evaluator behavior.

Mandatory graph constraint: **pass** for the revalidated A result. The change
only validates copied output and cache identities; it cannot alter graph
construction or retrieval. Prompt budget: **pass**, existing A scaffold
`0/5000`; no new runtime prompt exists.

No metric was recomputed and no external model call occurred in this source
milestone. Publication gate: `continue`, `paper_ready=false`.

Next: commit and push this gate, then use the committed manifest to run the
predeclared corrected A/B significance analysis with seed `20260727` and
10,000 paired-QA plus conversation-cluster bootstrap resamples.
