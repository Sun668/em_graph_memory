# Conclusion

The three-layer source refactor is implemented:

1. `locomo_eval` contains a byte-identical pinned LoCoMo vendor tree and one
   injected QA-recall boundary.
2. `em_graph` contains only build, recall, and cache layers.
3. `common` is the single active model-client implementation.

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

Unit/parity validation passes, but no external model call and no metric-bearing
rerun was performed as part of this source refactor. Historical A/B numbers
must not be relabeled as results from the new stack.
