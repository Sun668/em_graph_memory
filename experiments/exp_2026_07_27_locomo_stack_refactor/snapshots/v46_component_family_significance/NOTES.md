# v46 — component-family significance with Holm correction

Decision date: 2026-07-28 Asia/Shanghai. Analysis source commit/tree:
`6557f839801301e3ffa6606db85c71e9228a0b57` /
`ccca309422a300335007bbd580c1954b31d4ebd3`.

This report uses the four hypotheses and correction method locked in v45,
before formal p-values were inspected. It reads immutable official per-row
metrics; it does not call a model or recalculate an official metric.

## Exact command

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
.venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/component_family_report.py \
  --b-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 \
  --b-gate-dir outputs/locomo_formal/formal_all10_M2_B_gate_top25_faebb2f_qfrozen_run01 \
  --b-gate-seq-dir outputs/locomo_formal/formal_all10_M2_B_gate_seq_top25_1bb800b_qfrozen_run01 \
  --b-entity-dir outputs/locomo_formal/formal_all10_M2_B_entity_top25_31d8c78_qfrozen_run01 \
  --b-noseq-dir outputs/locomo_formal/formal_all10_M2_B_noseq_top25_cabad81_qfrozen_run01 \
  --data-file data/locomo10.json --resamples 10000 --seed 20260727 \
  --output outputs/locomo_analysis/component_family_6557f83_seed20260727.json
```

Every condition independently passes the formal validator for the same
LoCoMo-10 order, 1,986 QA, 446 Category-5 rows, top-k 25, requested
`gpt-3.5-turbo` answer model, frozen Reader protocol, and official metrics.
The graph conditions share the conversation-only graph profile: captions,
time annotations, and speaker Entities enabled; 5,882 Memory, 12,808 Entity,
36,227 Entity–Memory, and 11,744 stored sequence edges.

| Dimension / parameter | Side A: ablated condition | Side B: added component | Expected impact |
|---|---|---|---|
| Sequence inside B | B_noseq: fusion `0.30/0.70`, sequence off | B: same fusion, sequence scale `0.50` | Direct sequence contribution |
| Entity-score fusion | B_gate_seq: fusion `0.0/1.0`, sequence on | B: fusion `0.30/0.70`, sequence on | Explicit Entity-score contribution |
| Sequence over gate | B_gate: fusion `0.0/1.0`, sequence off | B_gate_seq: same fusion, sequence on | Sequence contribution under semantic-only scoring |
| Semantic signal | B_entity: fusion `1.0/0.0`, sequence on | B: fusion `0.30/0.70`, sequence on | Necessity of semantic relevance |

All graph inputs, gate controls (threshold `0.50`, top 20/key, who dampening
`0.25`, degree discount), exact dense fill, top-k, Reader, and evaluation are
aligned except the component stated in each row. Each condition's full
extraction/construction/recall logic is frozen in snapshots v37 and v41–v44.
Construction excludes QA answers/evidence/categories, judge results, prior
predictions, and question-driven ledgers. Recall uses graph Memories and
Entity/sequence edges. Prompt scaffold is 2,410/5,000 characters.

## Statistical method

Seed is `20260727`. Each comparison uses 10,000 paired-QA bootstrap resamples
and 10,000 whole-conversation cluster bootstrap resamples over 10 clusters.
Differences are Side B minus Side A. Recall contributions use serialized
official per-row recall for non-empty evidence, zero for empty evidence, and
retain all QA rows in the denominator; exact official-stat parity passes.

The family contains four component hypotheses. Holm step-down adjustment is
performed separately within official overall F1/Recall@25 and each robustness
estimator. Alpha is 0.05.

## Results

### Official overall F1

| Component contrast | Difference | Paired 95% CI | Cluster 95% CI | Holm p paired / cluster | Supported by both? |
|---|---:|---:|---:|---:|---|
| B − B_noseq | +0.5137 pt | [-0.3010, +1.3167] | [-0.0884, +1.2243] | 0.4500 / 0.2152 | No |
| B − B_gate_seq | +0.8014 pt | [-0.2741, +1.8756] | [-0.0512, +1.7545] | 0.4260 / 0.1956 | No |
| B_gate_seq − B_gate | -0.0609 pt | [-0.6041, +0.4865] | [-0.7044, +0.6292] | 0.8157 / 0.8369 | No |
| B − B_entity | +5.0780 pt | [+3.6058, +6.5287] | [+3.2245, +7.0697] | 0.000800 / 0.000800 | Yes |

Only the semantic-signal F1 hypothesis remains significant under both
estimators after Holm correction.

### Official Recall@25

| Component contrast | Difference | Paired 95% CI | Cluster 95% CI | Holm p paired / cluster | Supported by both? |
|---|---:|---:|---:|---:|---|
| B − B_noseq | +1.6728 pt | [+0.9881, +2.3736] | [+0.7876, +2.6351] | 0.000800 / 0.000800 | Yes |
| B − B_gate_seq | +4.7626 pt | [+3.6822, +5.8671] | [+3.5789, +6.0225] | 0.000800 / 0.000800 | Yes |
| B_gate_seq − B_gate | +0.4364 pt | [+0.1511, +0.7553] | [+0.1489, +0.7563] | 0.001000 / 0.002600 | Yes |
| B − B_entity | +17.4634 pt | [+15.5825, +19.3991] | [+14.4569, +20.9635] | 0.000800 / 0.000800 | Yes |

All four Recall@25 component hypotheses remain significant under both
estimators after Holm correction.

## Validation, graph audit, and decision

The report has fingerprint
`679ca12fa311e6fc0c1c084bfa0618842c99746f2954113cf5bc2f1010d75223`
and file SHA-256
`2aabbf88b1269b70a43ab8677ed9cb2742f51b674fab9444840be1eaa8085189`.
An independent second invocation is byte-identical. The complete suite passes
76/76; all 16 vendor hashes pass; `code/locomo_eval/` is clean.

There is no LLM-as-Judge and no new runtime cost. The inputs' warm costs and
model calls are reported in their own snapshots. Mandatory graph constraint:
**pass for every input condition**. This analysis is eligible for component
claims but does not change the primary A/B conclusion.

Supported paper claims:

- semantic relevance is necessary for both F1 and retrieval recall;
- sequence expansion and explicit Entity-score fusion improve Recall@25;
- sequence over the gated semantic retriever improves Recall@25;
- F1 improvements for sequence and Entity-score fusion are not statistically
  established.

Publication gate: `continue`, `paper_ready=false`. Next execute the predeclared
input ablations, followed by top-k/fusion sensitivity, cost, and final audit.
