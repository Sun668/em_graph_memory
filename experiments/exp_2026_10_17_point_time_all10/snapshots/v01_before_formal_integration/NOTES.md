# Formal integration base

Base commit: `39ddcbf5b8ba65e64cb20f252a9647e4152d5baa`.

Before editing the active formal runner, preserve the exact control source at
this commit:

- `experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py`
- `experiments/exp_2026_10_17_point_time_only/run.py`
- `code/em_graph/recall/service.py`
- `code/em_graph/build/replace_pronouns.py`

The first is the formal B runner; the second contains the fixed small-slice
point-time transformation to be copied without logic changes. The last two
are the existing graph-context and deterministic date resolver. No all-ten
answers or metrics exist yet. This snapshot is a base-commit pointer; the
subsequent Git diff against that commit is the source patch for the new
condition. Graph compliance and prompt budget are pre-run requirements, not
yet all-ten results.
