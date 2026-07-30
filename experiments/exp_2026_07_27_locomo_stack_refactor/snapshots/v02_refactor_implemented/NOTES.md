# v02_refactor_implemented

## Status

- Source-only refactor; no external model calls and no new QA metric.
- Mandatory graph constraint: pass.
- Prompt budget: pass; entity extraction scaffold is below 5000 characters.
- Counts as a reproducible implementation checkpoint, not a metric result.

## Source

`source/` contains the exact completed `common`, `em_graph`, `locomo_eval`,
runner, tests, and experiment documentation. The vendored LoCoMo tree is pinned
to upstream commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

## Validation

```bash
.venv/bin/python -m unittest \
  experiments.exp_2026_07_27_locomo_stack_refactor.test_refactor -v

.venv/bin/python -m unittest discover \
  -s experiments/exp_2026_07_26_locomo_official_compare \
  -p 'test_*.py' -v
```

The first suite covers official source hashes, the injected recall boundary,
official generation arguments, all five QA scoring categories, signed
similarity, context formatting, cache identity, shared LLM role forwarding,
and package dependency boundaries. The second covers real-datetime Memory
ordering and evidence-preserving normalization.

## Graph/no-test audit

- Graph inputs: session timestamps, dialog ids, speakers, dialog text, and
  `blip_caption`.
- Excluded: QA questions/answers/evidence/categories, judge outputs, prior
  predictions, and question-driven ledgers.
- QA questions are used only after graph construction for graph recall.
- Answer context is produced only from retrieved Memory nodes.
