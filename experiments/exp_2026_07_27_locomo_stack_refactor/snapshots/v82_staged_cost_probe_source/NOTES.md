# v82 staged cost-probe source

Status: **validated source-only tooling; no cost result**.

Long single-process measurements could not survive Codex session ownership,
ordinary background processes were reaped, launchd lacked workspace privacy
access, and Terminal Apple Events required an unresolved OS permission. v82
removes that environmental dependency without changing the primary-B
scientific condition.

`cost_probe_staged.py` expresses the same cold/warm measurement as 128 ordered
transactions at batch size 50:

- 10 cold graph operations;
- 10 cold Memory-index operations;
- 44 cold QA-retrieval batches covering all 1,986 rows;
- the same 10 + 10 + 44 operations under warm cache state.

Each command performs exactly the next operation. Before work it atomically
records `in_progress`; after success it atomically appends raw stage events and
marks completion. If a process is interrupted, the next command fails closed
and the run must restart under a new id. It never infers or discards partial
cost. The checkpoint binds every data/model/retrieval/cache/output argument and
the frozen parameter SHA, so later steps cannot drift.

Within each retrieval transaction, one text cache, question extractor, and
question cache are shared. Across transactions, the sequential process reloads
the complete files before adding new keys, eliminating stale whole-file
overwrites. Finalization requires all 128 operations and then delegates the
unchanged event validation/aggregation to `cost_report.py`.

Reported stage wall times remain component-operation times measured inside the
same `CostTelemetry` contexts. Interpreter startup and repeated checkpoint or
Recall-loading overhead are not included; this is explicit and the report is
not an end-to-end shell wall-clock benchmark.

Validation:

- focused staged/current cost tests: 12/12;
- current refactor experiment suite: 95/95;
- historical official-comparison suite: 17/17;
- frozen evaluator hashes: 16/16;
- Python compilation and `git diff --check`: pass.

No API call or generated cost cache was made for v82. It supports no paper
claim. Next: commit/push, freeze v83, run a small wiring diagnostic, then
initialize and execute the all10 staged measurement from absent paths.
