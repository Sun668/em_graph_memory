# v92 — provider-recovery measurement repair

## Purpose

v90 lost an otherwise valid all-10 cold-cost transaction when one question
Entity request exhausted the shared client's ten internal retries. This repair
keeps the strict fail-closed checkpoint rule, but lets the same process retry
that same QA before the staged operation is abandoned.

## Exact behavior

Only a `RuntimeError` matching the shared client's exact exhausted-provider
message is recoverable. The default policy allows six additional attempts with
30-second exponential backoff capped at 120 seconds. The attempt count and wait
parameters are part of the frozen checkpoint identity. A graph-identity error,
cache error, validation failure, or any other runtime exception still fails
immediately.

Each retry remains inside the same QA, process, cache objects, and staged
transaction. No completed operation is resumed from disk. If all additional
attempts fail, the checkpoint remains `in_progress` and the whole run is still
invalid, exactly as before.

## Measurement policy

`latency_seconds` records the successfully completed retrieval attempt. Time
spent in fully exhausted attempts and between-attempt waits is excluded from
the service-latency distribution because it reflects a local connectivity
incident, not normal model or retrieval latency. Both excluded quantities,
the retry count, and individual recovery events are retained in the raw event
manifest and aggregated into the final cost report.

Provider token/request accounting remains response-derived. An exhausted
connection with no provider response contributes no fabricated tokens or
successful request. If a later attempt succeeds, its actual provider usage is
recorded once.

## Validation

- Focused cost/analysis tests: 44/44.
- Full current experiment tests: 108/108.
- Frozen upstream LoCoMo hashes: 16/16.
- `code/locomo_eval/` has no worktree changes.
- Python compilation and `git diff --check`: pass.

Tests cover recovery followed by success, non-provider errors, bounded capped
backoff, single successful latency accounting, report aggregation, and
rejection of malformed recovery evidence.

## Compliance and scope

This repair made no model request and changed no graph input, extraction
prompt, graph schema, retrieval score, rank order, query vector, answer
generation, or evaluation behavior. The mandatory conversation-only graph
constraint remains unchanged. The runtime prompt scaffold remains 2,410
characters, below the 5,000-character limit.

The repair itself has no paper metric. A new source/parameter lock and a fresh
four-path-isolated run are required before any cost value is reportable. v90
and all earlier failed runs remain quarantined and are not reused or deleted.
