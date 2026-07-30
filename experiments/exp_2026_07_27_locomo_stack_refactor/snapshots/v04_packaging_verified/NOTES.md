# v04_packaging_verified

Final implementation checkpoint after packaging validation.

- Metric-bearing: no.
- Mandatory graph constraint: pass.
- Tests: 11 refactor/parity + 17 normalization/datetime.
- Full construction audit: 10 samples / 5882 dialogs / 272 dialog-bearing
  sessions / 288 timestamp keys / 11744 directed Memory edges.
- Prompt scaffold: 2410/5000 characters.
- Active duplicate LoCoMo metric functions outside vendor: zero.
- Old source-directory entity cache: deleted; generated caches now resolve
  under `outputs/em_graph/`.

Wheel verification:

```bash
.venv/bin/python -m pip wheel . --no-deps --no-build-isolation \
  --wheel-dir /private/tmp/graph_memory_dist
```

The built `standalone_graph_memory-0.2.0` wheel contains `common`,
`em_graph/{build,recall,cache}`, `locomo_eval`, the pinned official vendor
source, and its license.

`source/` contains the package sources and all compatibility files changed by
the refactor. Files copied from separate experiment locations retain their
original basenames; their origins are the paths listed in the parent
experiment README and git diff.
