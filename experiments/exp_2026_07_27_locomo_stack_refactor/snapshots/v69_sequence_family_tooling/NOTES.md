# v69 — sequence-family inference tooling lock

Decision date: 2026-07-29 Asia/Shanghai. Base commit:
`28b32c11337de442d091e891bf381b57c0ef2c69`.

This source-only snapshot freezes family inference before reading adjusted
outcomes. The two hypotheses are:

1. sequence scale `0.25 − 0.50`;
2. sequence scale `1.00 − 0.50`.

Both use 10,000 paired-QA and 10,000 whole-conversation cluster resamples,
seed `20260727`. Holm step-down correction is applied separately within
F1/recall and estimator. The two estimators are robustness estimators, not
additional hypotheses.

The scientific identity comparison removes only
`sequence_secondary_scale`. It requires exact equality of dataset SHA,
scope/order, models, graph profile, answer protocol, every other retrieval
parameter, all ten graph identities and hashes, all ten Memory-index
identities and hashes, and the complete immutable query artifact identity.
The tool also requires complete variant B and exact scales `0.5`, `0.25`,
and `1.0`.

Locked source hashes:

- `sequence_family_report.py`: `92edf325…3d97`;
- `significance_report.py`: `98c8b8db…a2fa`;
- `test_analysis_tools.py`: `b27a9e96…c90f`.

Focused tests pass 23/23, the full suite 83/83, and evaluator hashes 16/16.
A regression test proves query-artifact mismatch fails closed. No metric is
recalculated, no API request occurs, and no cache/formal result is mutated.

Publication gate is `tooling_locked`, `paper_ready=false`. Commit/push v69
before generating the sequence-family report.
