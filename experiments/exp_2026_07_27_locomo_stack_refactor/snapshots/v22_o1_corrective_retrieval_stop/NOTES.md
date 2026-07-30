# v22 — corrective O1 retrieval terminal stop

Source commit: `d57027539aaf700ab650978100c19aaaa07195df`.
Source tree: `5a7495baeeae01c4719f7cd96efcf802ae1a3cc6`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
Pinned LoCoMo upstream commit:
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

This snapshot records the predeclared O1 terminal gate. The dependency-matched
retrieval result still misses the official Recall@25 tolerance, so no Reader,
M1, significance, ablation, robustness, O2, or cost experiment was launched.

Bulky generated artifacts remain under:

- `outputs/runtime_envs/o1_official_py3918_b10b2d4/`;
- `outputs/locomo_formal_cache/official_dragon_all10_d570275/`.

No formal result directory was created.

## Exact environment and commands

Runtime:

- Python 3.9.18;
- macOS 15.5 arm64, CPU;
- PyTorch 2.0.1, no CUDA build;
- Transformers 4.35.0;
- tokenizers 0.14.1;
- NumPy 1.26.0;
- NLTK 3.8.1, regex 2022.10.31, tqdm 4.64.1;
- OpenAI client 2.45.0 for the repository compatibility wrapper, unused in
  this retrieval-only result.

```bash
uv venv --python 3.9.18 \
  outputs/runtime_envs/o1_official_py3918_b10b2d4

uv pip install \
  --python outputs/runtime_envs/o1_official_py3918_b10b2d4/bin/python \
  -r experiments/exp_2026_07_27_locomo_stack_refactor/requirements_o1_official.txt

PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache \
HF_HUB_DISABLE_TELEMETRY=1 \
outputs/runtime_envs/o1_official_py3918_b10b2d4/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/official_dragon.py \
  build-cache \
  --cache-dir \
  outputs/locomo_formal_cache/official_dragon_all10_d570275 \
  --local-files-only

PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache \
HF_HUB_DISABLE_TELEMETRY=1 \
outputs/runtime_envs/o1_official_py3918_b10b2d4/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/official_dragon.py \
  retrieval-check \
  --cache-dir \
  outputs/locomo_formal_cache/official_dragon_all10_d570275 \
  --top-k 25 \
  --report \
  outputs/locomo_formal_cache/official_dragon_all10_d570275/retrieval_check_k25.json
```

The worktree was clean at cache construction. Both generated targets were
absent before the run. No old cache was loaded, migrated, resumed, or
overwritten.

## Retrieval protocol

All 10 LoCoMo conversations and 1986 QA questions were used. Dialog embedding
text was exactly `speaker said, "raw text"` plus ` and shared blip_caption`
when present. Date/time was excluded from embeddings. The raw question was the
query.

Query/tokenizer model:
`facebook/dragon-plus-query-encoder`, revision
`2d3808c087119b953f8494b7638c216c71712cee`.
Context model: `facebook/dragon-plus-context-encoder`, revision
`68074e7406bb0061b0d049b58592acafae00e9d4`.

The implementation used batch size 24, `last_hidden_state[:, 0, :]`, no L2
normalization, raw dot product, and descending NumPy `argsort`. The retrieval
check passed all 1986 rows with exactly 25 unique valid context ids.

Recall was aggregated from the official serialized per-QA contribution:
non-empty evidence used the per-row recall rounded to three decimals;
empty evidence contributed zero; all 1986 QA rows remained in the denominator.

## Result and fixed gate

| Metric | Official Table 3 | Corrective O1 | Difference | Tolerance | Gate |
|---|---:|---:|---:|---:|---|
| Recall@25 | 76.7 | 78.113293 | +1.413293 | ±1.0 | fail |

Category recall percentages were:

- Category 1 Multi Hop: `66.019504`;
- Category 2 Temporal: `84.683801`;
- Category 3 Open Domain: `54.498958`;
- Category 4 Single Hop: `86.979905`;
- Category 5 Adversarial: `69.394619`.

Compared with the v19 cache, all 1986 top-25 sets were exactly equal. Nine
rows changed only the ordering inside the same set. Therefore dependency
alignment does not alter Recall@25. Reader generation cannot alter evidence
recall and was not run.

The sole remaining runtime difference is CPU versus the upstream PyTorch
2.0.1 CUDA 11.7 build. CUDA 11.7 is unavailable on this macOS arm64 host.
Because the dependency-matched corrective result still misses tolerance and
the remaining device mismatch cannot be resolved locally, publication-plan
stop condition 2 is active.

## Artifact identity

- cache manifest SHA-256:
  `f3e843b4c8d55b9bfb62c0a4a20fca74095e66dd810f69fee816ddb2b322d202`;
- retrieval check SHA-256:
  `4a2c4e33b192e3fda6bf04c4e1abd8bd8461f8c6d776936b1ab5bf69ab3a95c2`;
- `official_dragon.py` SHA-256:
  `710e036d008af7c77f9e866c12ea4156df2daabecb169479260e575f511335b5`;
- `requirements_o1_official.txt` SHA-256:
  `cd442a00cde5d5e6add1542278a69639a58409eb8e2a3875bfb31f77b3df9cf0`.

Individual cache hashes are recorded in `result.json` and the generated
manifest.

## Compliance and publication decision

O1 is a flat Dialog reference baseline and intentionally fails the mandatory
graph constraint; it cannot count as an EM-Graph result. Graph construction
was not performed. No QA answer, evidence, category, judge output, previous
prediction, or question-driven ledger was used to construct an index. The QA
question was used only as the retrieval query. No prompt scaffold or external
model call was used.

The frozen evaluator remains unchanged and all 16 vendor hashes still pass.
Publication gate: `stop`. `o1_accepted=false`, `paper_ready=false`, and all
later publication experiments are blocked under the current plan.
