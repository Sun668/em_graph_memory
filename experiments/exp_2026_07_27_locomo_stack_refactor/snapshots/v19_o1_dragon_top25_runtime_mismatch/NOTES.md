# v19 — O1 DRAGON top-25 runtime-mismatch diagnostic

Source commit: `9511f94f4568e275977d06825008cbf17c3224dc`.
Source tree: `fe5dffb99498bd5df50b76c0ca6e780a290fe57e`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
Pinned LoCoMo upstream commit:
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

This snapshot freezes the first formal all-10 O1-25 result before changing the
official-reference runner or its runtime identity. The result passes formal
output validation but exceeds the predeclared official Recall@25 reproduction
tolerance. It is retained as a diagnostic and is not an accepted reproduced
baseline.

Bulky generated artifacts remain under:

- `outputs/locomo_formal_cache/official_dragon_all10_9511f94/`
- `outputs/locomo_formal/formal_all10_O1_dragon_top25_9511f94_run01/`

## Exact commands and settings

```bash
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/official_dragon.py \
  build-cache \
  --cache-dir outputs/locomo_formal_cache/official_dragon_all10_9511f94 \
  --local-files-only

PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/official_dragon.py \
  retrieval-check \
  --cache-dir outputs/locomo_formal_cache/official_dragon_all10_9511f94 \
  --top-k 25 \
  --report \
  outputs/locomo_formal_cache/official_dragon_all10_9511f94/retrieval_check_k25.json

source env_gpt.sh
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/official_dragon.py \
  evaluate \
  --cache-dir outputs/locomo_formal_cache/official_dragon_all10_9511f94 \
  --output-root outputs/locomo_formal \
  --answer-model gpt-3.5-turbo \
  --run-id formal_all10_O1_dragon_top25_9511f94_run01 \
  --scope all10 --top-k 25
```

The run covered all 10 conversations, 1986 QA rows, and 446 Category-5 rows.
The requested Reader was `gpt-3.5-turbo`, system-role prompt, temperature 0,
maximum 32 output tokens, and batch size 1. The unchanged upstream Category-5
option order used unseeded `random.random()`. The provider's actual resolved
Reader model was not captured by this version of the O1 runner; this is a
reproduction-record gap to fix before another O1 run.

## Retrieval logic

Dialog embedding text was exactly `speaker said, "raw text"` plus
` and shared blip_caption` when the caption key existed. Session `date_time`
was excluded from embeddings and added only to the Reader context wrapper.
The raw QA question was the query.

The context encoder was
`facebook/dragon-plus-context-encoder`; the query encoder and tokenizer were
`facebook/dragon-plus-query-encoder`. Both used
`last_hidden_state[:, 0, :]`, batch size 24, no L2 normalization, raw dot
product, and descending `np.argsort`. The cached Hugging Face refs were:

- query: `2d3808c087119b953f8494b7638c216c71712cee`;
- context: `68074e7406bb0061b0d049b58592acafae00e9d4`.

The all-10 retrieval check passed 1986/1986 rows at exactly 25 unique context
ids. A second direct full-data audit compared the experiment implementation
with the pinned upstream sorting expression and found zero ordered-ranking
mismatches over all 1986 rows. Context vector norms ranged from 65.0435 to
66.3607, confirming no normalization. The minimum score gap between ranks 25
and 26 was `0.0000305`, the 1st percentile was `0.0009018`, and the median was
`0.0426331`; there were no zero or negative gaps.

## Reader and metric logic

The ranked Dialog contexts were passed to the byte-pinned LoCoMo Reader.
Official token-F1, `recall_acc`, per-row rounding, Category-5 conversion, and
stats aggregation were unchanged. No LLM-as-Judge was used. The official
paper PDF at the pinned repository revision was visually inspected; Table 3
does report Dialog top-25 overall F1 `41.0` and Recall@25 `76.7`.

## Formal result

| Metric | Official Table 3 | O1 run | Difference | Tolerance | Gate |
|---|---:|---:|---:|---:|---|
| overall F1 | 41.0 | 42.2 | +1.2 points | 2.0 | pass |
| Recall@25 | 76.7 | 78.11 | +1.41 points | 1.0 | fail by 0.41 |

Category-level comparison:

| Category | Official F1 | O1 F1 | Official R@25 | O1 R@25 |
|---|---:|---:|---:|---:|
| Single Hop (4) | 59.9 | 62.2 | 87.1 | 87.0 |
| Multi Hop (1) | 38.7 | 40.5 | 62.5 | 66.0 |
| Temporal (2) | 37.2 | 41.9 | 83.5 | 84.7 |
| Open Domain (3) | 25.0 | 22.3 | 52.6 | 54.5 |
| Adversarial (5) | 12.8 | 10.1 | 66.3 | 69.4 |

The direction and scale are broadly consistent, but the fixed overall recall
tolerance is still exceeded and cannot be waived post hoc.

The external validator returned `pass`: correct all-10 order and counts,
complete prediction/F1/recall/context fields, exactly 25 unique valid context
ids per QA, official-stats parity, clean committed source, absent output
directory at start, no resume/overwrite, and unchanged prompt budget.

## Runtime mismatch diagnosis

The pinned upstream requirements specify Python 3.9.18, PyTorch 2.0.1 with
CUDA 11.7, Transformers 4.35.0, tokenizers 0.14.1, and NumPy 1.26.0. This run
used Python 3.10.19 on macOS arm64 CPU, PyTorch 2.13.0, Transformers 5.14.1,
tokenizers 0.22.2, and NumPy 2.2.6.

The input text, dataset, model ids, vector normalization, dot product, sorting,
and official evaluation were verified. The remaining concrete reproduction
differences are therefore runtime/library/device identity and the unrecorded
actual Reader deployment. The O1 cache identity recorded library versions but
did not bind Python, NumPy, tokenizers, Hugging Face revision, or device as
validated stable identity fields. These must be added outside
`code/locomo_eval/` before the corrective run.

## Artifact identity

- prediction SHA-256:
  `d5d903b4091ac33da4467b3b7f6152a982caff53004a9dee1a5af51125eb1c46`
- stats SHA-256:
  `393dd5dafb5ace579874ec1c838c12e246e436166a055fc0d61bbf9ddac8456b`
- audit SHA-256:
  `a2997c7b048ea6e90acc62edb94d93c4eea0c33f510ba8fb40b2afd2651c1aaa`
- validation SHA-256:
  `ca1ba0c4d8f0012457f8369a9d5d1ece0713fe3e57458d3fb27afafefb402f84`
- cache manifest SHA-256:
  `f5bf20c78c6e58ee9996b4106724f10bf61ec0a51bed604434dc2fbfb932da0f`
- retrieval-check SHA-256:
  `b56a554958a8d593b34aba64df66503c7c13d683f8db8eddf360cc9a6372c214`
- `official_dragon.py` SHA-256:
  `86ff13a5552a665229f88c354c38a3e559c1d828abe490db5d8b021b99ff7094`
- `validate_formal_result.py` SHA-256:
  `6101a83c0632f46cf5acb4dfd32c33bfbf48abac93b18f342623d5496ef8b5b8`
- pinned official PDF SHA-256:
  `a72c82117d01d8e304a24364a189afb91d25bf5e871b023f1e8172d6bdf64025`

## Compliance and publication decision

O1 is intentionally a non-compliant flat Dialog reference baseline: it builds
no graph and cannot count as an EM-Graph result. It is permitted only for
official calibration. It adds no experiment prompt scaffold and leaves
`code/locomo_eval/` unchanged.

Publication gate: `continue`, but only to the predeclared corrective O1
reproduction. `o1_accepted=false` and `paper_ready=false`; M1 and all later
paper experiments remain blocked. If dependency-matched O1 still exceeds the
recall tolerance and the residual CUDA/device difference cannot be resolved,
the publication experiment track must stop.
