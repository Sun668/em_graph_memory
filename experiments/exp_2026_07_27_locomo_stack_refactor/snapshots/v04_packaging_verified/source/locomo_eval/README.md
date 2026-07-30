# LoCoMo evaluation

This package vendors the official `snap-research/locomo` QA implementation at
commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

The files under `vendor/locomo/` are byte-identical upstream copies, including
the license. Do not edit them. `vendor_runtime.py` only adapts the old OpenAI
client call to `common.llm` and replaces the upstream dense retriever with one
injected protocol:

```python
recall(sample, qa_index, question, top_k) -> RecalledQAContext
```

All QA prompt text, temporal and Category-5 generation behavior, 32-token
answer budget, temperature 0, category-aware token-F1, evidence recall, per-row
three-decimal rounding, and aggregate statistics execute from the vendored
official modules.

`locomo_eval` does not import `em_graph`; any retriever satisfying `QARecall`
can be injected.
