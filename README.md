# em_graph_memory

Entity--Memory graph retrieval experiments for long-term conversational
memory on LoCoMo.

This repository contains the complete publication experiment package synced
from `graph_memory` commit `314c95a` on 2026-07-30. The current authoritative
experiment is:

[`experiments/exp_2026_07_27_locomo_stack_refactor/`](experiments/exp_2026_07_27_locomo_stack_refactor/)

The earlier
[`exp_2026_07_26_locomo_official_compare`](experiments/exp_2026_07_26_locomo_official_compare/)
bundle is retained as historical diagnostic evidence; its headline numbers
must not replace the corrected publication results.

## Current result

The matched comparison uses all 10 LoCoMo conversations and 1,986 QA rows.
At top-k 25:

| Condition | Overall F1 | Official `recall_acc` |
|---|---:|---:|
| A: dense Memory retrieval | 42.0681 | 79.7468 |
| B: Entity--Memory graph retrieval | 42.5680 | 84.4842 |

The supported headline is a `+4.7374`-point evidence-recall improvement.
Paired-question and conversation-cluster bootstrap intervals are above zero.
The `+0.4998` overall F1 difference is not statistically supported, so this
repository does not claim a final-answer improvement, cross-dataset
generalization, official DRAGON reproduction, or state-of-the-art status.

See:

- [`paper/results_tables.md`](paper/results_tables.md)
- [`paper/evidence_ledger.md`](paper/evidence_ledger.md)
- [`experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v98_post_cost_publication_audit/`](experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v98_post_cost_publication_audit/)

## Paper

- [Final verified PDF](paper/entity_memory_graph_retrieval_arxiv.pdf)
- [LaTeX source](paper/arxiv/main.tex)
- [Bibliography](paper/arxiv/references.bib)
- [Literature verification](paper/literature_verification.md)
- [Full manuscript draft](paper/ARXIV_DRAFT.md)

The PDF is an eight-page arXiv-style technical manuscript. Its 20
bibliography entries are all cited and were checked against primary paper
pages or official proceedings records. Author and affiliation fields remain
anonymous placeholders.

## Repository layout

```text
code/
  common/                 # model/API clients
  em_graph/               # active graph build, cache, and retrieval package
  locomo_eval/            # frozen LoCoMo evaluator and vendored source
data/locomo10.json        # fixed 10-conversation dataset
experiments/
  exp_2026_07_27_locomo_stack_refactor/
    snapshots/            # v01-v101 immutable progress/result snapshots
    paper/                # evidence ledger, tables, manuscript, LaTeX
outputs/
  locomo_formal/          # 24 isolated formal condition outputs
  locomo_analysis/        # bootstrap and family-analysis reports
  locomo_cost/            # validated v93 checkpoint/events/report
  em_graph/query_embeddings/
                           # frozen formal query-vector artifacts
  paper/                  # final PDF and preview
paper/                    # convenient copy of final manuscript artifacts
SYNC_MANIFEST.md          # copied scope, provenance, and exclusions
```

## Reproducibility boundary

Graph construction uses conversation data only: session anchors, dialog IDs,
speakers, dialog text, timestamps, and captions. It excludes QA answers,
evidence annotations, category labels, judge outputs, and previous
predictions. Answer recall uses the conversation-built graph.

Every formal condition has its own output directory with a resolved
`run_config.json`, predictions, statistics, audit, validation, progress,
query-usage, and warm-cost event record. The complete execution commands,
parameters, cache identities, source snapshots, significance procedures, cost
measurements, and claim gates are documented in the current experiment
README and snapshots.

Large graph-construction and Memory-index caches are intentionally omitted
from this Git snapshot because they are reproducible and total hundreds of
megabytes. Frozen query-vector artifacts, formal predictions, metrics,
validation records, analysis reports, and the final cost report are included.

## Verification

From the repository root:

```bash
python -m unittest discover \
  -s experiments/exp_2026_07_27_locomo_stack_refactor \
  -p 'test_*.py'

cd paper/arxiv
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The immutable evaluator rules and exact formal commands are documented in
[`experiments/exp_2026_07_27_locomo_stack_refactor/README.md`](experiments/exp_2026_07_27_locomo_stack_refactor/README.md).
