# Vendored LoCoMo source

- Repository: `https://github.com/snap-research/locomo`
- Commit: `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`
- Vendored scope: complete `task_eval/*.py`, `global_methods.py`,
  `scripts/evaluate_rag_gpts.sh`, `requirements.txt`, `README.MD`, and
  `LICENSE.txt`.
- Modification policy: files under `vendor/locomo/` are byte-identical to the
  pinned upstream files. Project adapters live outside this directory.

The runtime adapter replaces only unavailable optional dependencies and the
model transport. Official prompt construction, Category-5 randomization and
decoding, per-category F1, recall, per-row three-decimal rounding, and official
aggregate reporting execute from the vendored modules.

