# v51 — raw-text input-family inference tooling lock

Decision date: 2026-07-28 Asia/Shanghai. Base commit:
`ee8255dfffcf537e8272b90603f9403e541d590e`.

This source-only snapshot locks the raw-text family analysis method before
generating its family-wise report. It follows the pairwise analysis frozen in
v50 and does not make a new model, embedding, graph-build, Reader, or judge
request.

Locked sources:

- `input_family_report.py`, SHA-256
  `d714682dc2f56b8c74711b0bb9f91ce6f5a6a8f0bcc60e5be11627d90fe8eef8`;
- unchanged `significance_report.py`, SHA-256
  `98c8b8dbb5d0f05b1061aa3d1eca5a99efdbb3f7f285a7eb2cc06a77755da2fa`;
- `test_analysis_tools.py`, SHA-256
  `c16d1dadb4d852dfe7a75f2cd99e62a1089d9fede8a365cd8e9d4141e12e3812`.

The two predeclared hypotheses are:

1. `B_raw_text − B`, testing deterministic time annotation inside complete B;
2. `B_raw_text − A_raw_text`, testing B over A under matched raw input.

Each comparison loads and independently validates its formal condition, uses
immutable official serialized per-row F1 and evidence-recall contributions,
and preserves all 1,986 paired QA rows. It runs 10,000 paired-QA and 10,000
whole-conversation cluster bootstrap resamples with seed `20260727`. Holm
step-down correction is applied across the two hypotheses separately within
each outcome metric and estimator. The estimators are robustness estimators
of the same hypotheses, not four additional hypotheses.

Focused analysis tests pass 17/17. The tool does not recalculate official
metrics and does not touch `code/locomo_eval/`, graph files, embedding
indexes, extraction caches, query artifacts, or result directories.

Publication gate: `tooling_locked`, `paper_ready=false`. Commit and push this
lock before generating the formal input-family report.
