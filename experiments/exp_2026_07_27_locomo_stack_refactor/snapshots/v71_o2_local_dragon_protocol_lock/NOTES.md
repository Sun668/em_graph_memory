# v71 — O2 local DRAGON diagnostic protocol lock

Base/source commit before implementation: `6ad8976`.

This source-only snapshot locks the remaining O2-B-25 diagnostic before any
implementation edit, external model call, cache construction, retrieval, or
answer generation. The local O1 reproduction did not pass the preregistered
official tolerance, so O2 is not an official-stack controlled comparison and
must never be described as beating or matching the official LoCoMo table.

## Locked scientific condition

- Dataset: `data/locomo10.json`, SHA-256
  `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`,
  all 10 conversations and all 1,986 QA rows in dataset order.
- Variant: `B`, top-k `25`.
- Graph: the already validated conversation-only entity–Memory graph profile
  with captions, time annotations, and speaker entities.
- Entity extraction/question extraction: `gpt-3.5-turbo`, existing v4
  extractor, unchanged caches and prompts.
- Semantic encoders:
  `facebook/dragon-plus-query-encoder` for questions and
  `facebook/dragon-plus-context-encoder` for Memory search text.
- Vector behavior: raw float32 CLS vectors, no L2 normalization.
- Semantic score: raw query/context dot product, then query-local min–max
  normalization over the active candidate pool. If every score is equal, all
  normalized values are fixed to zero. Dense-fill scores are independently
  min–max normalized over the full Memory pool, while gated rows retain
  priority exactly as in the current top-k fill protocol.
- Fusion: Entity `0.30`, normalized DRAGON semantic `0.70`.
- Sequence expansion: enabled, secondary scale `0.5`.
- Entity threshold `0.5`, entity top-k-per-key `20`, who-only dampening
  `0.25`, degree discount enabled.
- Answer model: requested `gpt-3.5-turbo`; frozen LoCoMo system-role,
  temperature-0, batch-size-1, 32-token Reader.
- Output: one new, absent O2-specific condition directory.
- Query vectors: one new immutable raw-DRAGON query artifact, role `query`,
  complete 1,986-row coverage, loaded read-only with zero misses and zero live
  query-vector requests during the formal run.

## Hypothesis and interpretation

The diagnostic hypothesis is that replacing the primary condition's
OpenAI-compatible cosine semantic signal with a locally executed DRAGON raw
dot-product signal, calibrated by the preregistered query-local min–max rule,
changes retrieval and answer quality under the same conversation-built graph
and frozen Reader.

The result is descriptive and local-stack-only. It is not paired inference
against the official paper table, because O1 remains outside the reproduction
tolerance. No parameter may be tuned after observing O2.

## Cache and output safety lock

At lock time, `outputs/em_graph/` contains 70 graph files and 30 Memory
embedding indexes. No DRAGON file is present there. The implementation must:

1. preserve every existing graph, index, text cache, query artifact, and formal
   result byte-for-byte;
2. reuse matching B graph files read-only;
3. create DRAGON indexes only at new identity-derived paths that bind raw
   normalization and the separate query/context encoder protocol;
4. create the DRAGON query artifact and report only from absent paths;
5. never treat an old normalized DRAGON cache as a raw-dot-product artifact;
6. abort on any path collision or identity mismatch instead of rebuilding or
   overwriting.

## Required implementation and run gates

- Backward-compatible loading of existing L2 query artifacts and v2 Memory
  indexes must be regression-tested.
- Raw-vector query artifacts and raw DRAGON Memory indexes must bind their
  normalization protocol in file identity and validation.
- Retrieval tests must prove exact min–max behavior, equal-score behavior,
  fusion behavior, and default-path non-regression.
- Formal configuration must explicitly label O2 as
  `local_dragon_stack_diagnostic` and `official_comparison_eligible=false`.
- The frozen evaluator must remain clean and all 16 vendor hashes must pass.
- Formal preflight, independent output validation, mandatory graph audit,
  prompt budget, query identity/coverage, cache counts, and snapshot
  verification must pass before this diagnostic can be cited.

Publication gate: `continue_tooling_only`; `paper_ready=false`.

