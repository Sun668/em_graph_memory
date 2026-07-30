# v66 — valid fusion-family Holm significance

Decision date: 2026-07-29 Asia/Shanghai. Repaired locked tooling commit:
`2908616`.

The valid report is
`outputs/locomo_analysis/fusion_family_2908616_seed20260727.json`, SHA-256
`ce003823092844d077206b80cb2cdd816108805b7d0916a9bb20d2fb3f1bdd3c`.
An independent second execution is byte-identical. The report fingerprint is
`04df5e0d79f5f495b99f2ed6abbd6e2fc7ae736d57e6726c617e704a798b6fcb`.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/fusion_family_report.py \
  --primary-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 \
  --fusion-e10-s90-dir outputs/locomo_formal/formal_all10_M5_B_e10_s90_top25_7fd96e6_qfrozen_run01 \
  --fusion-e50-s50-dir outputs/locomo_formal/formal_all10_M5_B_e50_s50_top25_0eb464c_qfrozen_run01 \
  --resamples 10000 --seed 20260727 \
  --output outputs/locomo_analysis/fusion_family_2908616_seed20260727.json
```

## Conditions and exact behavior

| Dimension / parameter | Primary B | Fusion 0.10/0.90 | Fusion 0.50/0.50 | Expected impact |
|---|---|---|---|---|
| Dataset / order | LoCoMo-10 SHA `047d8e…d74`; 10 conversations; 1,986 QA; 446 Category 5 | Exact same | Exact same | No sampling or denominator effect |
| Graph construction | Conversation-only complete B; captions, time annotations, speakers; QA/judge fields excluded | Exact same 10 graph paths, hashes, and identities | Exact same | No extraction or graph confound |
| Graph schema | 5,882 Memories, 12,808 Entities, 36,227 Entity–Memory edges, 11,744 directed chronology edges | Exact same | Exact same | No node/edge effect |
| Memory indexes | Exact ten `text-embedding-3-small` index paths/hashes | Exact same | Exact same | No Memory-vector effect |
| Query vectors | SHA `bef99a…6f9f`; L2 float32; 1,536 dimensions; 1,986 ordered QA | Exact same | Exact same | No query-vector effect |
| Retrieval | complete B, top-k 25, Entity/Semantic `0.30/0.70`, sequence scale `0.5` | Only weights change to `0.10/0.90` | Only weights change to `0.50/0.50` | Isolates fusion sensitivity |
| Other retrieval settings | threshold `0.5`, top 20/key, who dampening `0.25`, degree discount on, dense fill, signed cosine | Exact same | Exact same | No other retrieval confound |
| Reader | `gpt-3.5-turbo`; system role; temperature 0; 32 tokens; batch 1 | Exact same | Exact same | No intended generation-protocol effect |
| Metrics | Frozen official F1 and `recall_acc`; local Categories 1–4 diagnostics | Exact same | Exact same | No metric-definition effect |

The repaired report explicitly binds the complete `cache_identity`, including
all graph/index identities and the query artifact. It independently validates
all three formal conditions before loading immutable official per-row values.
It does not recalculate metrics.

## Metrics and inference

| Condition | Official F1 | Official `recall_acc` | Local Cat. 1–4 F1 | Local Cat. 1–4 recall |
|---|---:|---:|---:|---:|
| Primary `0.30/0.70` | 42.5680% | 84.4842% | 51.9740% | 85.0232% |
| `0.10/0.90` | 42.2040% | 82.1780% | 51.5696% | 83.9647% |
| `0.50/0.50` | 42.2440% | 84.3280% | 52.1406% | 83.9126% |

For `0.10/0.90 − primary`, overall F1 is `-0.3640` points. Its Holm-adjusted
p-values are `0.9591` paired and `0.6911` cluster; neither rejects. Recall is
`-2.3062` points with paired CI `[-3.1598, -1.4790]` and cluster CI
`[-3.1310, -1.4518]`. Both Holm-adjusted p-values are `0.0004`.

For `0.50/0.50 − primary`, overall F1 is `-0.3240` points with adjusted
p=`0.9591` paired and `0.6911` cluster. Recall is `-0.1562` points with
adjusted p=`0.7017` paired and `0.8233` cluster. No interval excludes zero and
no adjusted test rejects.

The family contains exactly the two preregistered new contrasts. Holm is
applied separately within F1/recall and paired-QA/conversation-cluster
estimators. The estimators are robustness views of the same hypotheses.

## Extraction, recall, Reader, and judge audit

All three conditions reuse the same conversation-built Entity–Memory graph.
Entity extraction uses the bounded `gpt-3.5-turbo` prompt over one normalized
conversation Memory at a time; normalized/deduplicated Entities link to
Memories, deterministic speaker Entities are included, and Memories have
chronology links. Construction excludes questions, answers, evidence,
categories, judge outputs, predictions, and question-driven ledgers.

The full question supplies the immutable dense query vector and cached
question Entities. Retrieval gates through graph Entities, fuses Entity and
signed-cosine scores, applies degree discount, expands chronological neighbors
at scale `0.5`, and dense-fills exactly 25 unique Memory ids. Only the two
fusion weights differ.

The frozen Reader consumes recalled graph Memories through `QARecall`.
Official F1 and evidence `recall_acc` are aggregated by the frozen evaluator.
No judge was used; Categories 1–4 values are local diagnostics.

## Reproducibility and publication decision

The valid report has 10 cache records and the explicit query artifact SHA
`bef99a…6f9f`; all three source formal validations pass. Reproduction is
byte-identical. The repaired tooling passed 20/20 focused and 80/80 full
tests; all 16 evaluator hashes pass. No external request occurred during
family inference. No cache or formal result was deleted, overwritten, or
rebuilt; graphs remain `70`, Memory indexes `30`.

Maximum supported claim: reducing Entity weight to `0.10` significantly
reduces evidence recall relative to primary `0.30`, while neither new fusion
point produces a supported overall F1 change and `0.50/0.50` has no supported
overall recall change. This shows sensitivity to strong semantic weighting;
it does not prove `0.30/0.70` is globally optimal.

Publication gate remains `continue`, `paper_ready=false`: proceed to the
preregistered sequence-scale family, then O2, costs, and final claim audit.
