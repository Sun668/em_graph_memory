# v38 — recovery point before relocation validation support

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `de14040fbed5fdfcda104f26ccea937584864d8b`.
Source tree: `0dc94164a39f3d1422f6ff943c5067936af00ace`.

The user stopped a proposed A rerun after confirming that the accepted A result
already exists. The attempted new run did not start, no new condition
directory was created, no formal process remains active, and no duplicate
answer cost was incurred.

## Evidence inspected

The existing corrected A directory contains all eight transferred formal
files and all 1,986 QA rows:

```text
outputs/locomo_formal/formal_all10_M1_A_top25_76fcf5b_qfrozen_run01/
```

Its immutable `run_config.json` records the original output root:

```text
/Users/smsun/Documents/github/graph_memory
```

The current repository root is:

```text
/Users/sun/Documents/git/graph_memory
```

This is the only reason the current default validator rejects the relocated
directory. The run id, condition fingerprint, dataset hash, query artifact,
QA rows, metrics, graph audit, and result content are present.

The current A hashes exactly match the pre-migration v34 snapshot for every
metric-critical or cost artifact recorded there:

- `audit.json`: `7a8b8169…704a9`;
- `cost_events_warm.json`: `bd945ba7…8d40`;
- `predictions.json`: `0c843b7f…79c`;
- `query_cache_usage.json`: `d94d1765…d74`;
- `run_config.json`: `1057173e…43c`;
- `stats.json`: `203f30b1…63c`.

The current `validation.json` differs from the hash recorded in v34 because
the validator was run again after v34 was frozen and before the v36 transfer
archive was created. The current file is byte-identical to the v36 ZIP entry
and still reports the original-location validation pass. It is a derived
report, is not read as an input by the validator or significance analysis, and
will be recomputed on this machine.

The transfer chain is independently recorded by:

- v34 result snapshot SHA-256 `5e114d1e…58a56`;
- v36 result snapshot SHA-256 `a54a0221…caec`;
- v36 exhaustive transfer-path manifest SHA-256 `d7ad4874…5ce4`;
- migration ZIP SHA-256 `8ab9dc38…267f`;
- v37 corrected B result snapshot SHA-256 `da4640b8…4daa`.

## Planned change

The default formal validator will continue to reject any configured/actual
output-directory mismatch. Relocation will be accepted only when the caller
explicitly supplies a relocation manifest that:

1. identifies the unchanged run id, condition fingerprint, original output
   directory, and current condition directory;
2. binds a pre-existing source snapshot by SHA-256;
3. requires byte equality for the run config, predictions, stats, graph audit,
   and query-usage artifacts recorded by that source snapshot;
4. leaves historical formal JSON untouched;
5. still runs the complete current formal validator over all dataset rows,
   contexts, stats, graph/prompt audits, and query-artifact checks;
6. records the relocation-manifest hash in the significance report.

Invalid, missing, or tampered relocation manifests must fail closed. Direct
same-path validation remains unchanged.

No source, evaluator, result, metric, prompt, or cache was changed in this
snapshot. No external model call occurred. Mandatory graph constraint and
prompt budget are not applicable to this source-only recovery point.

Publication gate: `continue_tooling_only`, `paper_ready=false`. Commit and push
this recovery point before editing the validator or significance loader.
