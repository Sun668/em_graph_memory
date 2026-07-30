# v45 — component-family inference tooling lock

Decision date: 2026-07-28 Asia/Shanghai. Base commit:
`f92fa51` (`experiment: freeze B no-sequence result`).

This source-only snapshot locks the analysis method before inspecting formal
component p-values. No metric report was generated in this snapshot.

The exact source is committed in the same commit as this note:

- `experiments/exp_2026_07_27_locomo_stack_refactor/component_family_report.py`
  SHA-256 `beaf63821caf693e09f94e35974eff9e229913b0a7d6bbe9ef170ae9d0498a26`;
- existing `significance_report.py` SHA-256
  `98c8b8dbb5d0f05b1061aa3d1eca5a99efdbb3f7f285a7eb2cc06a77755da2fa`;
- `test_analysis_tools.py` SHA-256
  `a819d7ca20d3c8842dea287f78ca01a0808b4f35cbdc977c0540ab103a6baab1`.

The predeclared four hypotheses are:

1. complete B minus B_noseq: sequence inside B;
2. complete B minus B_gate_seq: explicit Entity-score fusion;
3. B_gate_seq minus B_gate: sequence over a gated semantic retriever;
4. complete B minus B_entity: semantic signal.

Each comparison uses immutable official per-row values, seed `20260727`, and
10,000 paired-QA plus 10,000 conversation-cluster bootstrap resamples. Holm
step-down correction is applied across the four component hypotheses
separately within each outcome metric (official overall F1 and Recall@25) and
bootstrap estimator. The two estimators are robustness estimators of the same
hypothesis, not extra hypotheses.

The focused analysis suite passes 16/16. This tooling does not modify or
recalculate official metrics and does not touch `code/locomo_eval/`.
Mandatory graph constraint is not newly exercised because this snapshot makes
no model/retrieval run; all five input conditions must independently pass
formal graph validation when the report is generated.

Publication gate: `tooling_locked`, `paper_ready=false`. Commit/push, then
generate the formal component-family report from the committed source.
