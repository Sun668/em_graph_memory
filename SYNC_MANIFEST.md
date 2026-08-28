# Synchronization manifest

## Snapshot scope

This repository is the publication-and-reproduction snapshot for the
Entity--Memory graph retrieval paper.

Included:

- The active three-package implementation under code/common, code/em_graph,
  and code/locomo_eval.
- The fixed LoCoMo-10 input under data/locomo10.json.
- The authoritative formal experiment bundle under
  experiments/exp_2026_07_27_locomo_stack_refactor.
- Formal results, reports, and audit artifacts under outputs/.
- The latest v108 paper PDF under paper/.

The legacy top-level em_graph package and the historical
exp_2026_07_26_locomo_official_compare experiment are excluded because they
are not used by the current paper.

## Intentionally excluded

- LaTeX source and arXiv packaging files; the uploadable PDF is retained in
  paper/.
- API keys, credentials, environments, downloaded model weights, and local
  configuration.
