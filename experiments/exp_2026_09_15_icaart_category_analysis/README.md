# ICAART five-category descriptive analysis

Requested 2026-09-15. Baseline manuscript commit: `11a3b96`.
Analyze existing primary A/B scores, without generating answers or modifying any evaluator, graph, cache, or formal condition. This is post-hoc descriptive analysis, not preregistered inference or a new formal run.

## Analysis definition (written before execution)

Pair all 1,986 QA rows across ten conversations by ordered sample id and QA index; require identical question, gold, evidence, and category. Bind prediction/stat hashes to frozen v40. Preserve existing category means; count exact stored-score increases, decreases and ties, plus joint recall/F1 directions. F1 transitions are not correctness counts. Empty-evidence rows contribute zero to recall as in frozen aggregation. Do not run new significance tests. Select cases explicitly as illustrative, including a favorable multi-hop example and a temporal regression; never infer a component's causal effect from A/B examples.

## Reproduce offline

From the thesis worktree, with raw artifacts at the main checkout:

```sh
python3 experiments/exp_2026_09_15_icaart_category_analysis/analyze_categories.py --artifact-root /Users/sun/Documents/git/graph_memory --output outputs/icaart_category_analysis/primary_ab_v01
```

The output path must be absent. A reproduction must use a new output path. The script uses Python standard library only. No environment credentials, external calls, random seed, or judge are applicable. Analysis source and result are frozen under `snapshots/v01_primary_ab_descriptive/`.

## Formal evidence and protocol

Original runner: `experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py`; full commands, graph/input/cache identities, model configuration, cost and compliance are frozen in v34 (A), v37 (B), v39 (validated A relocation), and v40 (matched A/B comparison). These are read-only inputs, not new conditions. See `protocol.md` in this directory for the end-to-end comparison and validation commands. Original evaluator remains immutable; no source, runtime prompt or metric is changed.

## Public v1.0.9 entry

Portable commands, environment requirements, archive boundaries and migration validation are documented in [the release guide](../exp_2026_10_09_public_reproduction_release/README.md). Historical snapshots retain their original absolute paths; create new snapshots for a new workspace.
