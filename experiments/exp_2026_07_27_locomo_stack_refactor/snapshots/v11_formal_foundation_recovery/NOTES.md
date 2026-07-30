# v11 — formal experiment foundation recovery

## Purpose

This is the required recovery point immediately before adding formal-result
validators, DRAGON orchestration, significance analysis, or cost reporting.
It records the fully committed foundation so later implementation can be
recovered without copying mutable generated outputs.

## Exact source

- Repository commit:
  `cad7bca7103c1ea9189e94725c8798a47711b35c`
- Git tree:
  `2cc898579921ce51b87a675e5f1d66f38604e1c0`
- Worktree before snapshot creation: clean.
- The complete exact source is the committed tree above; this snapshot adds no
  patch to that base.
- Dataset: `data/locomo10.json`
- Dataset SHA-256:
  `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`
- Pinned upstream LoCoMo commit:
  `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`

Important source hashes:

| File | SHA-256 |
|---|---|
| `AGENTS.md` | `09ef926812301c5f8e3445d97dd5ee269187d827f7dd3c594a72b1493c339ad3` |
| `README.md` | `36f8123e95eb9b28d93ca8c2c0450b4f7f90bda79c54fb5c2e0a4dc80226b9dd` |
| `code/locomo_eval/evaluator.py` | `de118f6ab0880abc2a3380d632ed9be2035cd883a749ed7286b28ccab1919202` |
| `code/locomo_eval/recall.py` | `0cb8605bf847d4ff2ceb511827461be0fc0a9757b5c99a47966801f891c94207` |
| `code/em_graph/recall/retrieval.py` | `ca19ff96c27461e92293946d0e8818a2385dcf912d867dbf71b6cad47e6794ff` |
| `code/em_graph/recall/service.py` | `0b908beb3be6b01f95a2eed03a12508066a6abe5db2264410369f73ee0e57513` |
| experiment `run.py` | `1c39988766360b2542f57d0d70a4e7209c30316c08abc8676024416eabae443f` |
| experiment `test_refactor.py` | `6fc9ab389f3dd1c4d0378bc8b7fcd3ef769e8fd7254e133dbd03815743c0e778` |
| `PUBLICATION_PLAN.md` | `26778ffcaf527aa2be4ef819d05790dd4ac394ee35a86edf81b6e104011e2106` |
| `next_steps.md` | `2ba7655bf2a46e952389b8fca5ca4bcd6ee2b303af6bd780e92085f3e833ef68` |

## Compliance audit

- `code/locomo_eval/` had no uncommitted difference.
- All 16 entries in `code/locomo_eval/vendor/MANIFEST.sha256` passed.
- No source, prompt, answer-generation behavior, metric, rounding, or
  aggregation under the frozen evaluator was changed.
- No metric-bearing run was performed in this step.
- Mandatory graph constraint: not applicable to this source-only recovery
  snapshot; no graph was built and no result is promoted.
- Prompt budget: the current Entity extraction scaffold is 2410 characters,
  below the 5000-character limit. No prompt was added in this step.
- Formal output isolation: not applicable; this step created no output
  condition and resumed no prediction.
- API/model calls and cost: none.

## Result status

This is a reproducibility/process milestone, not a metric result. It does not
change any accuracy claim and does not count toward the graph target. The next
allowed change is the external formal-result validator described in
`PUBLICATION_PLAN.md`.
