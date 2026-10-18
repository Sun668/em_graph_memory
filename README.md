# em_graph_memory

Code and paper repository for Entity--Memory graph retrieval on LoCoMo.

## Contents

- code/: active graph construction, retrieval, cache, and frozen evaluator code.
- data/: dataset required to rerun the formal evaluation.
- experiments/exp_2026_07_27_locomo_stack_refactor/: authoritative runner, settings, evidence definitions, and reproduction notes.
- outputs/: retained formal results, reports, and audit artifacts.
- paper/entity_memory_graph_retrieval_arxiv_en_v108.pdf: latest v108 paper PDF.

The exact paper snapshot is pinned by tag v1.0.8:
https://github.com/Sun668/em_graph_memory/tree/v1.0.8

The Chinese journal manuscript's current B method is available at tag
`v1.0.10`. This release adds the optional first-Memory point-time Reader
context to the frozen LoCoMo formal runner, its no-provider tests, and the
original all-ten paired experiment's source and small result snapshots.
Run the current complete B with `--variant B --top-k 25
--reader-context-mode point_time_first`; the default `raw` mode retains the
earlier graph-retrieval behavior. The original treatment score belongs to
the source commits named in
`experiments/exp_2026_10_17_point_time_all10/`, not to a new model run at
this release commit. Generated answer files, model caches, and API secrets
are not distributed with the tag.

The legacy top-level em_graph package and the historical official-compare
experiment are not used by the paper and have been removed.
