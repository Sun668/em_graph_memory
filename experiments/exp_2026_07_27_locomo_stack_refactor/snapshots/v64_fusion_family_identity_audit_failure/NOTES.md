# v64 — fusion-family identity-audit failure

Decision date: 2026-07-29 Asia/Shanghai. Locked tooling commit:
`4c5c12a`.

The first family report attempt ran locally without external API requests:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/fusion_family_report.py \
  --primary-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 \
  --fusion-e10-s90-dir outputs/locomo_formal/formal_all10_M5_B_e10_s90_top25_7fd96e6_qfrozen_run01 \
  --fusion-e50-s50-dir outputs/locomo_formal/formal_all10_M5_B_e50_s50_top25_0eb464c_qfrozen_run01 \
  --resamples 10000 --seed 20260727 \
  --output outputs/locomo_analysis/fusion_family_4c5c12a_seed20260727.json
```

The report SHA-256 is
`78d98cf1b14a406b8c69b4ae2e6b0b4b5c3daef7c6d69da390146acfa52a63ca`.
It is diagnostic only and must not be promoted.

## Failure

The report's `scientific_identity_except_fusion_weights` serialized
`query_embedding_artifact` as `null`. The tooling read a nonexistent
top-level `run_config["query_embedding_artifact"]` field. The actual validated
identity is under
`run_config["cache_identity"]["query_embedding_artifact"]`.

All three underlying formal conditions remain independently valid and bind
the same query artifact SHA
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.
The defect is confined to the new family tool's explicit non-weight identity
gate. It does not modify, invalidate, or require rerunning any graph, index,
query vector, retrieval context, answer, or official metric.

## Decision

Status: `failed_identity_audit`, `paper_eligible=false`. Preserve the report
as diagnostic evidence. Before recomputing family conclusions, bind the full
`cache_identity` object (including graph/index records and query artifact),
add a regression test that rejects a query-artifact mismatch, rerun all tests,
and create a new source lock.

No cache or old result was deleted, overwritten, or rebuilt. Graphs remain
`70`; Memory indexes remain `30`.
