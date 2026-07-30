# Conclusion

The three-layer source refactor is implemented under top-level `code/`:

1. `code/locomo_eval` contains a byte-identical pinned LoCoMo vendor tree and one
   injected QA-recall boundary.
2. `code/em_graph` contains only build, recall, and cache layers.
3. `code/common` is the single active model-client implementation.

Their Python import names remain `locomo_eval`, `em_graph`, and `common`;
`code` is deliberately not a Python package, avoiding a collision with the
standard-library module named `code`.

The ten temporary `em_graph.<legacy_module>` compatibility files have now
been removed. Active callers use `em_graph.build`, `em_graph.recall`, or
`em_graph.cache`; `em_graph.__init__` remains the sole stable convenience
facade. Historical snapshots and self-contained experimental package copies
were not rewritten.

The prior 1044-line matched-stack runner is preserved in
`snapshots/v01_pre_refactor/legacy_matched_stack/`; its active path is now a
small compatibility entry point. The duplicated local LoCoMo prompt and metric
modules were removed from the active experiment.

The strict graph audit passes by construction: graph building consumes
conversation fields only, while QA-derived question entities live in separate
recall caches whose identities include model, extraction protocol, QA index,
and full question SHA-256. `query` and `img_url` were removed from the Memory node schema;
only raw/normalized dialog text and `blip_caption` remain. A no-model all-10
audit verified all 5882 dialogs, 272 dialog-bearing sessions, 288 timestamp
keys, and 11744 directed chronological edges. Prompt scaffold length is 2410,
below the 5000-character limit.

The A baseline retains its original condition: it builds 5882 Memory nodes and
zero Entity nodes, so it incurs no entity-extraction call. B and B_embed use the
complete EM graph. All variants share one canonical per-sample embedding index,
validated by Memory ids and full Memory-text digests.

Unit/parity validation passes. A fresh metric-bearing variant-B preflight was
then run on all 199 `conv-26` QA rows from source commit `23e3a4b`, with no
legacy graph, embedding, question, or answer artifact reused.

Official `recall_acc` at k=5/10/25/50 is
`0.6231/0.7580/0.8610/0.9213`. Official overall F1 at the same cutoffs is
`0.341/0.385/0.391/0.400`. The official stats implementation, rather than a
direct mean of serialized recall fields, is authoritative because it retains
empty-evidence questions in the denominator without accumulating their
row-level default recall.

The graph contains 419 Memory nodes, 1105 Entity nodes, and 2903 total edges,
including 836 chronological Memory edges. Graph construction and recall pass
the mandatory conversation-only graph audit. Official overall F1 remains an
official-compatibility diagnostic because Category 5 exposes both answer
options in its official prompt; the compliant Categories 1–4 subset F1 is
`0.41985/0.49053/0.49905/0.52332`.

This is a single-conversation result. A, B_entity, B_embed, B_noseq, and all-10
regression remain pending; historical A/B numbers must not be relabeled as
results from the new stack.
