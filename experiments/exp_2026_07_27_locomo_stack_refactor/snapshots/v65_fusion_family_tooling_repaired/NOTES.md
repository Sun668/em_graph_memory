# v65 — repaired fusion-family inference tooling lock

Decision date: 2026-07-29 Asia/Shanghai. Base commit:
`94445cbf2f5c4ee83986cba69e9364a7ea9a50b1`.

This source-only snapshot replaces v63 after the v64 identity-audit failure.
No formal condition was rerun because all underlying formal artifacts were
already valid and unaffected.

Locked sources:

- `fusion_family_report.py`, SHA-256
  `6f27dcccac1ffbb4c218081cc6938e4a887910f9864c097f0dbd9d11b4285181`;
- unchanged `significance_report.py`, SHA-256
  `98c8b8dbb5d0f05b1061aa3d1eca5a99efdbb3f7f285a7eb2cc06a77755da2fa`;
- `test_analysis_tools.py`, SHA-256
  `9bd0b5a10a5a632bcc3b913265c8ecc503222736e71c635ae354337137515efe`.

The repaired scientific identity includes the complete formal
`cache_identity`: all ten graph paths/hashes/identities, all ten Memory index
paths/hashes/identities, and the immutable query artifact path, SHA, dataset
SHA, role, normalization, coverage, dimension, and ordered-QA digest. The only
fields excluded from cross-condition equality are the two preregistered
fusion weights.

A new regression test changes only the query-artifact SHA and proves that the
family tool fails closed. The original weight-identity and Holm-stratification
tests remain active.

The fixed family remains:

1. fusion `0.10/0.90 − 0.30/0.70`;
2. fusion `0.50/0.50 − 0.30/0.70`;

with 10,000 paired-QA and 10,000 whole-conversation cluster resamples, seed
`20260727`, and Holm correction separately by F1/recall and estimator.

Focused analysis tests pass 20/20; the full suite passes 80/80; all 16 frozen
evaluator hashes pass. No API request occurred and no cache, query artifact,
formal answer, result, or metric was modified.

Publication gate: `tooling_locked`, `paper_ready=false`. Commit and push v65
before regenerating the fusion-family report.
