# v63 — fusion-family inference tooling lock

Decision date: 2026-07-29 Asia/Shanghai. Base commit:
`ee916f712574ac3adb34dd01f8a656ca945ae116`.

This source-only snapshot locks the fusion-family analysis before generating
its family-wise report. Both metric-bearing fusion points were already frozen
as v61 and v62. This step makes no model, embedding, graph-build, Reader, or
judge request.

Locked sources:

- `fusion_family_report.py`, SHA-256
  `d9537c0ca11f10a7a18ed0275dde2b8b37cea42df2c27f5e0c3bdc34a8c78de3`;
- unchanged `significance_report.py`, SHA-256
  `98c8b8dbb5d0f05b1061aa3d1eca5a99efdbb3f7f285a7eb2cc06a77755da2fa`;
- `test_analysis_tools.py`, SHA-256
  `87e358530e1c1035d1ebbce2dca667a103a0b752bc371844e0bbcce53c7282d0`.

The two hypotheses were preregistered before v61:

1. fusion `0.10/0.90 − 0.30/0.70`;
2. fusion `0.50/0.50 − 0.30/0.70`.

The tool independently validates all three formal conditions and fails closed
unless they are complete variant B at exactly those weights. It requires
dataset, scope/order, models, graph profile, answer protocol, immutable query
artifact, and every retrieval parameter except the two fusion weights to be
identical. Each comparison preserves all 1,986 paired QA rows and runs 10,000
paired-QA plus 10,000 whole-conversation cluster bootstrap resamples with seed
`20260727`.

Holm step-down correction is applied across the two hypotheses separately
within each outcome metric and estimator. The estimators are robustness
estimators of the same hypotheses, not four extra hypotheses. The tool uses
immutable official serialized per-row F1 and evidence-recall contributions
and does not recalculate official metrics.

Focused analysis tests pass 19/19 and the full experiment suite passes 79/79.
All 16 frozen evaluator hashes pass. The tool does not touch
`code/locomo_eval/`, graph files, embedding indexes, extraction caches, query
artifacts, or formal result directories.

Publication gate: `tooling_locked`, `paper_ready=false`. Commit and push this
lock before generating the fusion-family report.
