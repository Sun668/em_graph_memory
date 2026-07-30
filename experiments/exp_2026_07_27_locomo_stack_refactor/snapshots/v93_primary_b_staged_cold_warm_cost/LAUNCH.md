# v93 exact launch record

## Frozen identities

- Parameter SHA-256:
  `530eefcea86d5374f3898a1bc744186d46a60d959abdd53fa6517c6b914a8581`
- Source commit:
  `ccb9c6ab30c8a6b720d5c7ec1546f8bc25ee870e`
- Source tree:
  `df7d0d259659e0edbc9ee50c10307296704c80e9`
- Detached source worktree:
  `/private/tmp/graph_memory_v93_source_ccb9c6a`
- Runner SHA-256:
  `610d308a6de281f229885d33151fe2f8bf28eb299321ea5085fee9e79df1bd66`

The detached source worktree was created and verified clean before launch.
All generated outputs remain under the main repository's `outputs/` tree.

## Environment and resolved arguments

Run from
`/private/tmp/graph_memory_v93_source_ccb9c6a` with:

```bash
source /Users/sun/Documents/git/graph_memory/env_gpt.sh
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache

V93_PYTHON=/Users/sun/Documents/git/graph_memory/.venv/bin/python
V93_RUNNER=/private/tmp/graph_memory_v93_source_ccb9c6a/experiments/exp_2026_07_27_locomo_stack_refactor/cost_probe_staged.py
V93_ARGS=(
  --checkpoint /Users/sun/Documents/git/graph_memory/outputs/locomo_cost/primary_b_v93_checkpoint.json
  --measurement-id v93_primary_b_staged_cold_warm_cost
  --parameter-snapshot-sha256 530eefcea86d5374f3898a1bc744186d46a60d959abdd53fa6517c6b914a8581
  --data-file /private/tmp/graph_memory_v93_source_ccb9c6a/data/locomo10.json
  --cache-dir /Users/sun/Documents/git/graph_memory/outputs/locomo_cost/primary_b_v93_cache
  --warm-cost-file /Users/sun/Documents/git/graph_memory/outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01/cost_events_warm.json
  --output-events /Users/sun/Documents/git/graph_memory/outputs/locomo_cost/primary_b_v93_events.json
  --output-report /Users/sun/Documents/git/graph_memory/outputs/locomo_cost/primary_b_v93_report.json
  --query-artifact /Users/sun/Documents/git/graph_memory/outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz
  --formal-query-usage /Users/sun/Documents/git/graph_memory/outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01/query_cache_usage.json
  --scope all10
  --variant B
  --top-k 25
  --batch-size 50
  --provider-recovery-attempts 6
  --provider-recovery-wait-seconds 30
  --provider-recovery-max-wait-seconds 120
  --extract-model gpt-3.5-turbo
  --embedding-model text-embedding-3-small
  --answer-model gpt-3.5-turbo
  --entity-weight 0.3
  --semantic-weight 0.7
  --sequence-scale 0.5
  --entity-min-rel-score 0.5
  --entity-top-k-per-key 20
  --who-only-dampen 0.25
)
```

Degree discount remains enabled because `--no-degree-discount` is absent.
The runner resolves and freezes this entire argument vector in the checkpoint.

## Commands

After the unauthenticated connectivity check and both one-call telemetry
preflights pass:

```bash
"$V93_PYTHON" "$V93_RUNNER" init "${V93_ARGS[@]}"
```

Then execute exactly one operation per `step` transaction until all 128 are
complete:

```bash
"$V93_PYTHON" "$V93_RUNNER" step "${V93_ARGS[@]}"
```

Inspect progress without changing state:

```bash
"$V93_PYTHON" "$V93_RUNNER" status "${V93_ARGS[@]}"
```

After 128/128:

```bash
"$V93_PYTHON" "$V93_RUNNER" finalize "${V93_ARGS[@]}"
```

Initialization must not run if any of the four v93 output paths exists. A
persisted `in_progress` value invalidates v93; it must never be cleared or
resumed manually.
