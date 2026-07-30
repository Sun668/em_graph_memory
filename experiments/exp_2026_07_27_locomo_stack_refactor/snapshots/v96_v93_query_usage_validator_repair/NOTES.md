# v96 — v93 query-usage validator repair

The terminal validator now treats the formal run's 1,997 query-vector reads as
a SHA-bound reference rather than requiring a fresh stochastic question-Entity
extraction to reproduce that incidental count exactly.

The replacement gate is stricter about the matched comparison itself. Cold and
warm must contain the same ordered retrieval-batch signatures, including QA
count, query hits, query misses, and live query-embedding requests. Each state
must cover all 1,986 QA, have at least one immutable query-vector hit per QA,
and have zero misses and zero live query-vector requests. The measured delta
from the formal reference is written into the final manifest.

This repair does not change any measurement operation. The remaining warm
graph, index, and retrieval steps continue under the frozen `ccb9c6a` source
worktree. Commit `f606f21` is used only to validate and report the completed
event stream.

Focused tests passed 19/19 and the experiment suite passed 112/112. All 16
vendored LoCoMo hashes match `MANIFEST.sha256`, and `code/locomo_eval/` has no
worktree changes.

Graph construction remains conversation-only. The validator consumes only
cost telemetry and artifact counters. It does not change prompt scaffolds,
retrieval evidence, answer generation, or metrics. This snapshot authorizes
continuation but is not itself a paper result.
