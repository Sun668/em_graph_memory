# v73 — O2 raw query build API-key preflight failure

Date: 2026-07-29 Asia/Shanghai. Source commit:
`b1fda5e`.

The first raw DRAGON query-artifact build attempt failed before model loading,
vector generation, or artifact/report creation. `prepare_query_embeddings.py`
unconditionally called `set_api_key_from_env()`, although `dragon` is a fully
local pinned dual encoder. With no `OPENAI_API_KEY` exported in this shell, the
unrelated API guard raised:

```text
RuntimeError: OPENAI_API_KEY is not set.
```

Exact attempted command:

```text
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
outputs/o2_dragon_runtime/bin/python \
experiments/exp_2026_07_27_locomo_stack_refactor/prepare_query_embeddings.py \
--data-file data/locomo10.json \
--embedding-model dragon \
--role query \
--normalization none_float32_v1 \
--output outputs/em_graph/query_embeddings/locomo10_047d8e25_dragon_raw_v2.npz \
--report outputs/em_graph/query_embeddings/locomo10_047d8e25_dragon_raw_v2_report.json
```

Both target paths remain absent. Graphs remain 70, Memory indexes remain 30,
no O2 formal directory exists, and no old cache/result was deleted,
overwritten, or rebuilt. No metric or provider/model request occurred.

The minimal repair is to require the API key only for non-local embedding
models. Add regression coverage proving DRAGON skips the API guard while
remote embedding models still call it. Do not change vector, retrieval,
artifact identity, or frozen-evaluator behavior.

Publication gate: `repair_query_builder_preflight`; `paper_ready=false`.

