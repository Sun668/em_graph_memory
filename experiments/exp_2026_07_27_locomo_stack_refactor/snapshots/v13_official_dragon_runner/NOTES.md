# v13 — official Dialog DRAGON runner

## Purpose and exact source

This snapshot records the experiment-local official Dialog DRAGON
implementation and its retrieval-only conv-26 parity check before the next
tooling change.

- Base commit: `1766b28d`
- Runner: `official_dragon.py`
- Runner SHA-256:
  `86ff13a5552a665229f88c354c38a3e559c1d828abe490db5d8b021b99ff7094`
- Tests: `test_official_dragon.py`
- Test SHA-256:
  `5f34b97578fcb86380b42ed73e36a5ffb80472907e349ca8e0fb331789f87ebe`
- Extended validator: `validate_formal_result.py`
- Validator SHA-256:
  `6101a83c0632f46cf5acb4dfd32c33bfbf48abac93b18f342623d5496ef8b5b8`
- Exact sources are committed with this snapshot. Generated cache vectors stay
  under `outputs/` and are identified below by SHA-256.

## Protocol

- Dataset: `data/locomo10.json`,
  SHA-256 `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
- Slice: `conv-26`, 199 QA, retrieval-only diagnostic.
- Upstream: `snap-research/locomo` commit
  `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.
- Query encoder: `facebook/dragon-plus-query-encoder`.
- Context encoder: `facebook/dragon-plus-context-encoder`.
- Tokenizer: query-encoder tokenizer.
- Batch size: 24.
- Dialog text: raw `speaker said, "text"` plus ` and shared blip_caption`
  when present.
- Query: raw QA question.
- Pooling: `last_hidden_state[:, 0, :]`.
- Normalization: none.
- Similarity/ranking: raw dot product and descending NumPy `argsort`.
- Reader evidence: upstream date-time prefix plus raw dialog.
- Top-k: 25.
- Device: CPU; PyTorch 2.13.0; Transformers 5.14.1.
- Answer/extraction/judge models: not used.
- Random seed: not applicable; embedding and retrieval are deterministic.

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache \
  .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/official_dragon.py \
  build-cache --samples conv-26 --local-files-only \
  --cache-dir outputs/locomo_formal_cache/official_dragon_v13_conv26

PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache \
  .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/official_dragon.py \
  retrieval-check --samples conv-26 --top-k 25 \
  --cache-dir outputs/locomo_formal_cache/official_dragon_v13_conv26 \
  --report \
  outputs/locomo_formal_diagnostics/o1_conv26_v13_retrieval_check.json
```

## Result and artifacts

- Context matrix: 419 × 768.
- Query matrix: 199 × 768.
- Exact 25 unique context ids: 199/199 QA rows.
- Retrieval failures: 0.
- Context norm range: 65.1454–66.3124.
- Query norm range: 10.0860–10.8967.
- Unit-normalized context/query vectors: false/false.
- Cache NPZ SHA-256:
  `2fd96d3bd0de445ccfcd4563e8e8ba5585c8bac200897df4c71db9f3eea87b6a`.
- Cache manifest SHA-256:
  `4096671203f424b58b633e79f4cae1caeeae49f9e818ab0bfaddad7fa54bb7c8`.
- Retrieval report SHA-256:
  `a7b0c8dc54dd711ddc726e92548ba260e99eb23b220857661b930a957cd56e3a`.
- Metric-bearing: no.
- Official F1 / `recall_acc`: not generated.

## Tests

Six official-DRAGON tests cover upstream input parity, raw CLS vectors,
raw-dot ranking and reader context parity, pinned model ids/batch size,
formal reference/cache identity, all 16 vendor hashes, and absence of an
`em_graph` import. Combined command:

```bash
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache \
  .venv/bin/python -m unittest \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_official_dragon.py \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_validate_formal_result.py \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_refactor.py
```

Result: 31/31 passed.

## Compliance audit

- Graph construction: none.
- Indexed inputs: conversation session order, dialog id, speaker, raw dialog
  text, optional `blip_caption`; date-time is used in reader formatting.
- Excluded from index construction: QA questions, answers, evidence,
  categories, judge outputs, previous predictions, and question-ledger
  artifacts. Raw questions are used only as retrieval queries.
- Answer recall: flat dense Dialog retrieval, not graph retrieval.
- Mandatory graph constraint: **fail**, intentionally and explicitly. This is
  a non-compliant official reference baseline and cannot count toward the
  graph target.
- Frozen `code/locomo_eval/`: unchanged.
- Vendor manifest: 16/16 passed.
- Prompt budget: added runtime scaffold 0 characters; pass.
- Output isolation: fresh cache directory; no formal answer output created.
- External model/API calls: zero.
- Metric or improvement claim: none.
