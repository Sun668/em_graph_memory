# Synchronization manifest

## Provenance

- Source repository: `Sun668/graph_memory`
- Source baseline: graph_memory publication branch commit 29220439180615e61e0269b515b10d23dcdec73d
- Publication snapshot: v1.0.8
- Synchronization date: 2026-08-28
- Destination repository: `Sun668/em_graph_memory`
- Dataset: `data/locomo10.json`
- Dataset SHA-256:
  `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`

## Included

1. The active three-package implementation:
   - `code/common/`
   - `code/em_graph/`
   - `code/locomo_eval/`, including the frozen vendor manifest and source.
2. The complete tracked experiment bundle:
   - `experiments/exp_2026_07_27_locomo_stack_refactor/`
   - all scripts, tests, plans, conclusions, paper materials, and v01-v102
     immutable snapshots.
3. Formal and analytical evidence:
   - all 24 condition directories under `outputs/locomo_formal/`;
   - all reports under `outputs/locomo_analysis/`;
   - `primary_b_v93_checkpoint.json`;
   - `primary_b_v93_events.json`;
   - `primary_b_v93_report.json`.
4. Formal query-vector inputs:
   - `locomo10_047d8e25_text-embedding-3-small_v1.npz` and its report;
   - `locomo10_047d8e25_dragon_raw_v2.npz` and its report.
5. Publication artifacts:
   - manuscript, evidence ledger, results tables, literature audit;
   - LaTeX and BibTeX sources;
   - final eight-page PDF and rendered preview;
   - identified author metadata for `Shumao Sun`.
6. Project-state copies of the source `PLAN.md` and `TODO.md`.

## Intentionally excluded

- API keys, `env.sh`, `env_gpt.sh`, credentials, and local configuration.
- Python environments, compiled bytecode, TeX intermediates, editor files,
  and operating-system metadata.
- Rebuildable graph-extraction, entity, question-entity, text-embedding, and
  Memory-index caches under the source `outputs/em_graph/`.
- The 55 MB v93 cold/warm graph-and-index cache tree. Its immutable tree
  manifest, measurements, event stream, report, and validation evidence remain
  preserved in the experiment snapshots and included v93 JSON files.
- The diagnostic DRAGON model runtime environment and other downloaded model
  weights.

These exclusions do not remove the ordered query-vector artifacts, formal
predictions, per-condition configurations, statistics, audits, validations,
bootstrap reports, measured provider-usage events, or paper evidence required
to inspect the published claims.
