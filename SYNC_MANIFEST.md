# Synchronization manifest

## Snapshot scope

This repository is the lightweight publication-and-reproduction snapshot for
the Entity--Memory graph retrieval paper.

Included:

- The active three-package implementation under code/common, code/em_graph,
  and code/locomo_eval.
- The fixed LoCoMo-10 input under data/locomo10.json.
- The authoritative formal experiment bundle under
  experiments/exp_2026_07_27_locomo_stack_refactor.
- The latest v108 paper PDF under paper/.

## Intentionally excluded

- Historical pre-refactor experiments.
- Generated outputs, model predictions, reports, caches, and query-vector
  artifacts under outputs/.
- LaTeX source and arXiv packaging files; the uploadable PDF is retained in
  paper/.
- API keys, credentials, environments, downloaded model weights, and local
  configuration.

The formal commands, source snapshots, parameters, and evaluation protocol
needed to regenerate the paper results remain in the authoritative experiment
bundle.
