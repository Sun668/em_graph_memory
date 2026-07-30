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
recall caches. Prompt scaffold length remains below the 5000-character limit.

Unit/parity validation passes, but no external model call and no metric-bearing
rerun was performed as part of this source refactor. Historical A/B numbers
must not be relabeled as results from the new stack.
