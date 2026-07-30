# v29 — immutable query embedding artifact and cache-integrity gate

Decision date: 2026-07-28 Asia/Shanghai.
Base commit: `0f2a22b72e185e1711527c79004dd21b407e25cb`.
Base tree: `93a469b994641c3433ed510df7569c5e0fbf3e1e`.

This source-only recovery milestone implements the repair required by the v28
A/B_embed dense-control failure. No model API was called and no metric was
generated. The exact source is recoverable from the commit containing this
snapshot; the file hashes are recorded in `result.json`.

## Implemented repair

`TextEmbeddingCache` no longer lets independently loaded stale instances
rewrite the same complete NPZ:

- one in-process lock is resolved per cache path;
- writes also take an OS file lock;
- only pending additions are merged into a freshly reloaded disk image;
- an existing key with a different vector raises instead of being overwritten;
- vectors, dimensions, duplicate keys, and finite values are validated;
- output is written to a same-directory temporary file and atomically replaced.

Malformed or unsupported artifacts fail explicitly. The implementation does
not silently skip an old cache schema.

`QueryEmbeddingArtifact` is a physically separate, immutable retrieval-time
artifact. It binds:

- full dataset SHA-256;
- embedding model and role;
- normalization version;
- ordered sample id, QA index, and full question SHA-256 for every row;
- unique question digests, vector matrix, dimension, and file SHA-256.

`prepare_query_embeddings.py` builds the artifact only at an absent output
path. Formal graph runs now require `--query-artifact`, validate exact all-10
coverage before creating the condition output, share one read-only artifact
across all recalls, and fail on a miss without making a live embedding call.
The same run also shares one writable context cache and one question-Entity
cache/extractor instead of creating ten stale instances.

Every new graph-method `run_config.json` fingerprints the query artifact
identity. `query_cache_usage.json` records QA count, required/looked-up
vectors, hits, misses, and live requests. The external validator requires the
artifact hash and exact ordered coverage, zero misses, zero live requests, and
enough hits for every semantic-retrieval QA. `significance_report.py
dense-control` additionally requires A and B_embed to have the same query
artifact SHA-256 before comparing all ordered context ids.

## Planned commands after this source commit

The old corrupted whole-file text cache will be deleted explicitly before
building from absent paths. The new query artifact command is:

```text
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/prepare_query_embeddings.py --data-file data/locomo10.json --embedding-model text-embedding-3-small --role context --output outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --report outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1_report.json
```

Every corrected formal command must add:

```text
--query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz
```

## Tests and compliance

- Full experiment suite: 68 passed, 0 failed.
- Frozen vendor manifest: 16/16 passed.
- Python syntax compilation: passed.
- `git diff --check`: passed.
- `code/locomo_eval/`: unchanged.
- Mandatory graph constraint: unchanged and pass. The new artifact contains
  only retrieval-time QA question vectors and is never a graph-construction
  input.
- Prompt budget: unchanged; no prompt was added.
- Oversized, ineffective, or harmful prompt components: none.
- External model calls: zero.

The tests cover interleaved stale cache writes, conflicting-vector rejection,
atomic artifact round trips, exact dataset/model/role identity, strict
query-cache misses, prevention of live query embedding calls, validator
identity/runtime rejection, and the A/B_embed same-artifact gate.

Publication gate: `continue_tooling_only`, `paper_ready=false`. The source
repair is ready to commit and push. It does not restore experiment validity by
itself. Next, delete the exact corrupt cache, build and validate the new
artifact, then rerun corrected A/B_embed and A/B.
