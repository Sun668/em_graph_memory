# v07_code_directory_layout

Source-layout checkpoint requested by the user.

The three active stack packages were moved under one top-level source root:

```text
code/
  common/
  em_graph/
  locomo_eval/
```

`code/` intentionally has no `__init__.py`; the public import names remain
`common`, `em_graph`, and `locomo_eval`, avoiding a collision with Python's
standard-library `code` module. The legacy `graph_memory/` package and all
historical experiment snapshots remain in place.

Validation:

- 14/14 refactor/parity/cache/resume tests pass.
- 17/17 normalization and real-datetime tests pass.
- 16/16 pinned official LoCoMo vendor hashes pass.
- both the new runner and old compatibility entry point load directly.
- `standalone_graph_memory-0.2.0` wheel builds offline; SHA-256
  `bf8e71386c0af625e2b548e5140511fa9632effc258a303a3eb01256824744d7`.
- the wheel contains all three packages and all 16 pinned vendor files, no
  `__pycache__` or `.pyc`, and passes an import/vendor runtime smoke test.
- `git diff --check` passes.

This is a source-layout change only. Graph inputs, retrieval behavior, prompt
logic, cache identity, and metric definitions did not change. The mandatory
graph constraint therefore remains satisfied, and no new QA metric is claimed.
