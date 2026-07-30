# v35 — corrected B_embed Reader connection abort

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `6506fc6`.

The first corrected formal B_embed attempt started from the absent condition:

```text
outputs/locomo_formal/formal_all10_M2_B_embed_top25_6506fc6_qfrozen_run01/
```

It used the same immutable query artifact as corrected M1-A, SHA-256
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`,
and loaded the exact same ten read-only Memory embedding indexes. The general
writable context cache remained absent.

Exact command:

```bash
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_M2_B_embed_top25_6506fc6_qfrozen_run01 \
  --scope all10 --variant B_embed --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model text-embedding-3-small \
  --answer-model gpt-3.5-turbo \
  --query-artifact \
    outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal
```

The retrieval phase completed far enough to enter the frozen Reader loop.
The first answer request never completed. The client reported ten consecutive
`OpenAI API Error: Connection error` failures with bounded backoff and then
raised `RuntimeError: Failed after 10 retries for model=chatgpt`.

Only `run_config.json` and `audit.json` exist. There is no prediction,
progress, stats, validation, query-usage, or cost-event artifact. No successful
answer completion or metric is recorded. Provider billing for failed
connection attempts is not observable locally and is therefore unknown.

The graph audit remained conversation-only and the prompt scaffold remained
within budget. The failure did not alter `code/locomo_eval/`, the query
artifact, graph caches, Memory indexes, or any reported result. This is an
external connectivity abort, not a protocol, graph, metric, or control gate
failure.

Artifact hashes:

- `audit.json`:
  `1646265d6a5f987a22caf17303368c05ec657f8a5cef098c1383333b7d791cbe`;
- `run_config.json`:
  `0ad014d499d873051193092da6119aea372747413431f4135e0a251546a4cce1`.

Publication gate: `continue_after_connectivity_preflight`,
`paper_ready=false`. This directory is immutable and must not be resumed.
After a minimal successful Reader connectivity preflight, retry B_embed from a
new absent `run02` condition directory with unchanged committed settings.
