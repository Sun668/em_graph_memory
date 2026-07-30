# Next steps

- [x] Vendor pinned official LoCoMo QA evaluation source.
- [x] Create `common` model-client layer.
- [x] Split `em_graph` into build, recall, and cache packages.
- [x] Group `common`, `em_graph`, and `locomo_eval` under top-level `code/`
      without making `code` a Python package.
- [x] Add the single `locomo_eval` QA-recall protocol and EM implementation.
- [x] Migrate matched-stack runner and remove active duplicate evaluators.
- [x] Run dependency, vendor-hash, prompt, metric, cache, and context tests.
- [ ] Run `conv-26` A/B/ablation through the refactored stack.
- [ ] If the preflight is clean, run all-10 A/B/ablation at top-k 25 and the
      official recall runs at top-k 5/10/50.
- [ ] Snapshot every metric-bearing result before any source edit.
