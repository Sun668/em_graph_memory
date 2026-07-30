# v17 — formal cold/warm cost orchestration

Base commit: `10092efdb315a29489f97d1740f45a39b0ff6043`.
Exact sources are committed with this snapshot.

Key source SHA-256 values:

- `cost_report.py`: `d976804959769084b0c99aeafbb03bf024f4ec4b5b4ea834170702768dd3cb87`
- `cost_telemetry.py`: `bf83321611f71b3e81e5ec4ab79b94640a51671720d3dd9fe0b69a6bf785d9ec`
- `cost_probe.py`: `26b0a7c71c5916e75c00d11eabea7fb37bbbe8c3363297ec7135b4144ae5ebe2`
- `formal_graph.py`: `ebb369ac9801bb6a18f0b680c46a585448d92be312678645e28def0ff2ce0c51`

Formal conditions write a warm telemetry artifact containing provider answer
and query usage plus per-QA retrieval latency. The probe revalidates the
formal condition and exact fingerprint/sample/variant/top-k/model identity,
requires absent outputs and a fresh cold cache, measures cold and warm graph,
entity, embedding, query, and retrieval stages, and reuses the same measured
answer event for both cache states because answer generation is independent
of graph-cache state. This reuse is explicit in the manifest.

Warm cache hits may correctly contain zero requests and tokens. Missing
provider usage fails. Graph construction contains entity API time and
retrieval contains query/embedding time, so stage wall sums are labeled
non-exclusive and must not be interpreted as end-to-end latency.

Verification: 57/57 combined tests pass; frozen evaluator clean; vendor 16/16.
No external call, metric, or measured cost in this source-only step.

Compliance: graph construction remains conversation-only, recall remains over
graph nodes/edges, prompt budget unchanged, outputs identity-bound. Publication
gate is `continue_tooling_only`; `paper_ready=false`.
