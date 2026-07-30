# v32 — strict formal retrieval no longer seeds a context cache

Decision date: 2026-07-28 Asia/Shanghai.
Base commit: `e28a843af968bd15478d73b603a249d29ce6a361`.

Strict artifact-backed formal runs now call `_load_recall` with
`use_text_cache=False`. Existing hash-bound Memory indexes are loaded directly,
the immutable query artifact supplies every query vector, and no Memory vector
is reverse-seeded into a mutable cross-conversation text cache.

This removes the unnecessary operation that stopped v31 without changing any
Memory index, retrieval score, graph, prompt, evaluator, or metric. A regression
test proves a valid loaded index can run with no context cache or seeding.

Source SHA-256:

- `run.py`: `6624d995c71da86a150efbd833c27e7993c8cdc01e66de27995b296e6d7d68d7`
- `formal_graph.py`: `20eabf21fe2a595de3875290bb22d8c27bfcbd733abf7ec6dec3de90726a10af`
- `test_refactor.py`: `0b8a251d9833384e6c4757c5e0ba3c8361970864d3fd39b644ddf5635e72e41a`

Full suite: 69/69 passed. Frozen evaluator unchanged; no model call or metric
was generated. Mandatory graph constraint and prompt budgets are unchanged.

Publication gate: `continue_tooling_only`, `paper_ready=false`. Next: delete
only the partially reseeded context cache and repeat the all-10 retrieval-only
A/B_embed exact gate.
