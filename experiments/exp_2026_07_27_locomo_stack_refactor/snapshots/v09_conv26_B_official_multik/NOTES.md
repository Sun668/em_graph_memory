# v09 conv-26 B official multi-k

## Result

This is the first metric-bearing run through the refactored three-layer stack.
It evaluates all 199 QA rows in `conv-26` four times, once for each official
dialog-retrieval cutoff.

| top-k | official `recall_acc` | official overall F1 |
|---:|---:|---:|
| 5 | 0.6231155779 | 0.341 |
| 10 | 0.7579547739 | 0.385 |
| 25 | 0.8609748744 | 0.391 |
| 50 | 0.9212763819 | 0.400 |

The unrounded means of the official per-row, three-decimal F1 values are
0.3407889447, 0.3847286432, 0.3912311558, and 0.3997236181.

The official stats implementation is the authority for recall aggregation. It
keeps empty-evidence rows in the total category denominator but does not add
their row-level default recall value. Directly averaging the serialized row
field therefore produces a different and non-official number.

## Exact source and commands

- Repository source commit:
  `23e3a4b941d328d948ffa3981be786c1a60eb315`
- Upstream LoCoMo vendor commit:
  `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`
- Active runner SHA-256:
  `d2ce07e0f251928913c9467bc68058dc8b2a02865132cd451da3858a5fe035cd`
- Official `evaluation.py` SHA-256:
  `8e3be5d57ff2ff9ec5cd05939592f468c5f3f1fd95d13e431932bdf6bf0fd6fd`
- Official `evaluation_stats.py` SHA-256:
  `d36bf596de05ea6f1c355e433167a8cd704bea3a3745277c650ac0c464bba139`
- Official `gpt_utils.py` SHA-256:
  `5fc977375878199735acd28fba5ae6f4d657fa0e000c0d2918a90c07b6035793`

Commands, after `source env_gpt.sh`:

```bash
EM_GRAPH_EXTRACT_WORKERS=6 .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  build-graphs --samples conv-26

.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  evaluate --variant B --top-k 5 --samples conv-26 --overwrite
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  evaluate --variant B --top-k 10 --samples conv-26 --overwrite
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  evaluate --variant B --top-k 25 --samples conv-26 --overwrite
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/run.py \
  evaluate --variant B --top-k 50 --samples conv-26 --overwrite
```

The last three commands ran concurrently only after the first run had fully
populated and flushed the shared question/entity/embedding caches. Each run
wrote a separate output, stats, and graph-audit file under
`outputs/locomo_eval/`.

## Parameters and settings

- Dataset: `data/locomo10.json`; sample `conv-26`; 199 QA rows; no category
  filter.
- Conversation and question entity extractor: `gpt-3.5-turbo`.
- Answer model: `gpt-3.5-turbo`.
- Embedding model: `text-embedding-3-small`.
- Variant B: 0.30 Entity score + 0.70 signed cosine score.
- Entity degree discount: `1/log1p(degree)`.
- Who-only entity matches are multiplied by 0.25.
- Parsed-`date_time` previous/next Memory neighbors are expanded one hop with
  0.5 of the Entity seed score.
- The Entity-derived pool is used when nonempty; otherwise dense retrieval
  falls back to all Memory nodes.
- Cutoffs: 5, 10, 25, 50.
- Official reader: batch size 1, one system message, temperature 0, 32
  completion tokens. No random seed is exposed or set by the official runner.
- `--overwrite` was used for every cutoff; no prior answer output was resumed.

## Graph extraction and construction

- One Memory node is built per dialog.
- Entity extraction sees only `text_normalized` plus optional `blip_caption`.
- The builder adds speaker entities and normalizes/deduplicates extracted
  entity keys under the extract-v4 schema.
- The completed graph contains 419 Memory nodes, 1105 Entity nodes, 2903
  total edges, and 836 directed chronological NEXT/PREV edges.
- Sequence edges use parsed session `date_time`, then session/turn/dialog-id
  tie-breaks.
- Construction inputs are session `date_time`, dialog id, speaker, dialog
  text, and `blip_caption`.
- QA questions, answers, evidence, categories, judge outputs, previous
  predictions, and question-driven ledgers are excluded from graph
  construction.

## Recall and answer generation

- Question entities are extracted into a physically separate QA-only cache.
- Entity BM25 soft matching produces Entity-to-Memory seeds.
- Entity scores are degree-discounted and optionally sequence-expanded.
- Signed cosine is evaluated on the gated Memory pool; an empty gate uses the
  full Memory pool.
- Reader evidence is raw dialog text plus optional `blip_caption`, prefixed by
  its session `date_time`.
- Retrieved dialog ids are supplied to the byte-identical official LoCoMo
  answer generator and evidence-recall evaluator.

## Metric and constraint audit

- Official F1 uses the vendored category-aware logic: Category 1 partial
  multi-answer F1, Categories 2–4 token F1 with the official Category-3 answer
  handling, and Category 5 binary scoring.
- Every per-row F1 and recall value is rounded to three decimals before the
  official aggregation.
- There is no `hit@k` metric.
- Graph construction and answer recall satisfy the conversation-only graph and
  graph-retrieval requirements.
- Official overall F1 includes Category 5. Its official multiple-choice prompt
  includes both answer options, including the gold answer, so the overall score
  is an official-compatibility diagnostic rather than the repository-compliant
  promotion score. The Categories 1–4 subset F1 values are 0.41985, 0.49053,
  0.49905, and 0.52332 at k=5/10/25/50.
- Entity prompt scaffold length is 2410 characters, below the 5000-character
  limit. No oversized or previously rejected prompt component is active.
- This run uses the official LoCoMo QA evaluator, not the repository's local
  EvoEmo LLM-as-Judge.
