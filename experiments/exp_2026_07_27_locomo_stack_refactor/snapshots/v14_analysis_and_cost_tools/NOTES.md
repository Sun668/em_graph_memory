# v14 — significance, dense-control, and cost tools

## Purpose and exact source

This snapshot records the external analysis tools before formal graph-run
orchestration is changed.

- Base commit: `35fb02a1f8fb655c1d1759af0b9a6d4c88030a91`
- Significance/dense-control: `significance_report.py`
- SHA-256:
  `f69c2c72aea62dc2364aae05ccd8e58a9eded9d823c81c1787e698c988765a24`
- Cost reporter: `cost_report.py`
- SHA-256:
  `ce587096fc78acbcc238ee4db25e5bd9cd2dee51be3508cce8ad69a79765a2ab`
- Focused tests: `test_analysis_tools.py`
- SHA-256:
  `e216433226eeecb9f99e2e8f39b12244931f37dfa7385f72f2e21dd10fd4a6bb`
- Updated publication plan SHA-256:
  `f594ff0ffde4d85d94484155dfe41655999a8fac9c27bb926039b0e0f6cd02da`
- Exact sources are committed with this snapshot. No generated metric or cost
  output is promoted by this source-only milestone.

## Significance protocol

- Inputs: two individually validated formal graph-method conditions.
- Immutable metrics: frozen evaluator's serialized per-QA F1 and recall.
- Difference: B minus A.
- Paired-QA bootstrap: 10,000 resamples.
- Conversation-cluster bootstrap: 10,000 resamples, resampling whole
  conversations and taking the mean over all QA in sampled clusters.
- External-analysis seed: `20260727`.
- Interval: 2.5th/97.5th percentile.
- Reports: overall, Category 1–5, explicitly local/non-official Categories
  1–4, and per-conversation differences.
- Simultaneous component claims: Holm step-down adjustment is available.

Official recall contribution is:

- evidence non-empty: serialized per-QA recall;
- evidence empty: zero, even if serialized recall is 1;
- denominator: every selected QA row.

Raw serialized recall remains in the condition audit. Computed per-category
contribution means must exactly match the official stats block.

## A/B_embed dense-control gate

The `dense-control` command validates both formal conditions, checks their
matched dataset, sample/QA order, top-k, embedding model, answer model, and
answer protocol, then requires every paired QA's ordered context-id list to
be exactly equal.

- Same ordered ids: pass.
- Any changed id: fail.
- Same ids in a different order: fail.
- Aggregate closeness is not accepted.

## Cost protocol

The reporter accepts explicit measured events only. Both `cold` and `warm`
states must contain graph construction, entity extraction, embedding,
query-entity extraction, retrieval, and answer generation. It reports wall
time; request count and provider input/output tokens; embedding request count
and time; mean/p50/p90/p95/p99/max per-QA retrieval latency; and graph,
embedding-index, and cache bytes. Missing data is rejected, not estimated.
Actual measured costs remain pending instrumented formal runs.

## Verification

```bash
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache \
  .venv/bin/python -m unittest \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_analysis_tools.py \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_official_dragon.py \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_validate_formal_result.py \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_refactor.py
```

Result: 43/43 passed (12 analysis/cost, 6 DRAGON, 9 validator, 16 refactor).

Focused coverage includes:

- empty evidence with serialized recall 1 contributes zero to mean,
  bootstrap, category, and per-conversation analysis;
- category aggregation matches official stats while raw recall is auditable;
- two formal conv-26 A/B_embed conditions pass exact ordered equality for all
  199 QA rows;
- changed context id and order-only change both fail;
- fixed-seed bootstrap reproducibility and Holm correction;
- complete cold/warm aggregation and missing-state/token/stage failures.

## Compliance

- `code/locomo_eval/`: unchanged and clean.
- Vendored manifest: 16/16 passed.
- Official metric reimplementation: none.
- Graph construction or answer recall: no run in this source-only stage.
- Mandatory graph constraint: no new result; analyzed inputs must already
  pass the formal graph audit.
- Prompt scaffold added: zero.
- External model/API calls: zero.
- Metric, significance, improvement, or measured-cost claim: none.
