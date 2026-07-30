# Publication evidence ledger

This ledger is journal-neutral. Every numerical statement below points to a
frozen machine-readable artifact.

| ID | Claim | Evidence | Allowed certainty | Status / required wording |
|---|---|---|---|---|
| C1 | Complete B improves official evidence recall over matched A at top-k 25 by 4.7374 points. | `snapshots/v40_corrected_primary_ab_significance/result.json`, `overall.recall_at_25` | Statistical within the evaluated ten-conversation set | Supported under paired-QA and conversation-cluster bootstrap. |
| C2 | Complete B improves overall final-answer F1 over A. | Same file, `overall.f1` | Descriptive only | Unsupported statistically. Write that F1 differs by +0.4998 points and both intervals include zero, or omit the difference. |
| C3 | The recall advantage holds at top-k 5, 10, 25, and 50. | `v55`, `v57`, `v40`, and `v60` snapshot results | Robust over the tested cutoff range | Supported. Do not extend beyond 5–50. |
| C4 | A and B_embed provide an exact dense-retrieval control. | `snapshots/v36_corrected_b_embed_all10_dense_control/result.json` | Direct protocol fact | Supported: zero ordered-context mismatches across 1,986 QA rows and identical `recall_acc`. |
| C5 | Sequence expansion contributes to recall inside complete B. | `snapshots/v46_component_family_significance/result.json`; component-family report | Mechanistic under the declared ablation | Supported after Holm for recall, not F1. |
| C6 | Entity-score fusion contributes to recall. | Same component-family evidence | Mechanistic under the declared ablation | Supported after Holm for recall, not F1. |
| C7 | The semantic channel contributes to both recall and F1 relative to Entity-only retrieval. | Same component-family evidence, `semantic_signal` | Mechanistic under the declared ablation | Supported after Holm for both metrics. |
| C8 | Deterministic speaker links contribute to recall within B. | `snapshots/v53_b_no_speaker_all10/result.json` | Mechanistic under the speaker ablation | Supported for recall (+1.4822 points), not F1. |
| C9 | Time annotations improve overall B retrieval. | `snapshots/v52_input_family_significance/result.json` | None beyond descriptive | Not supported after Holm. Do not claim an effect. |
| C10 | The B-over-A recall advantage persists under raw-text input. | Same input-family evidence | Statistical input sensitivity | Supported after Holm; F1 is not supported. |
| C11 | Primary 0.30/0.70 fusion is insensitive to the tested weights. | `snapshots/v66_fusion_family_significance/result.json` | Mixed | `0.50/0.50` is not distinguishable, but `0.10/0.90` lowers recall. Do not call the whole range insensitive. |
| C12 | Sequence scale is insensitive from 0.25 to 1.0. | `snapshots/v70_sequence_family_significance/result.json` | Sensitivity robustness | Supported as “no family-corrected difference established,” not equivalence. |
| C13 | Local DRAGON reproduces the official reference. | `snapshots/v75_o2_local_dragon_all10/result.json` plus failed O1 evidence | None | Rejected. Label local diagnostic only. |
| C14 | The system is state of the art on LoCoMo. | No valid controlled official-reference evidence | None | Rejected. |
| C15 | Complete primary-B cold/warm construction and retrieval usage is measured. | `snapshots/v97_v93_complete_cold_warm_cost/result.json`; `outputs/locomo_cost/primary_b_v93_report.json` | Direct measured system evidence | Supported for requests, tokens, latency, and storage. Monetary cost remains unreported because price was not frozen. |
| C16 | The result generalizes to other datasets or populations. | One LoCoMo dataset only | None | Gap. Requires external datasets. |

## Numeric source map

| Displayed number | Meaning | Source |
|---:|---|---|
| 1,986 | QA rows in every promoted all-10 condition | v34/v37 counts; dataset audit |
| 10 | conversation clusters | v40 statistical report |
| 42.0681% / 79.7468% | A@25 overall F1 / `recall_acc` | v34 |
| 42.0677% / 79.7468% | B_embed@25 overall F1 / `recall_acc` | v36 |
| 42.5680% / 84.4842% | B@25 overall F1 / `recall_acc` | v37 |
| +0.4998 points | B−A F1 at top-k 25 | v40 |
| +4.7374 points | B−A `recall_acc` at top-k 25 | v40 |
| +4.8083 / +5.5702 / +3.6159 points | B−A `recall_acc` at top-k 5 / 10 / 50 | v55 / v57 / v60 |
| +1.4822 points | complete B minus no-speaker B `recall_acc` | v53 |
| −2.3062 points | 0.10/0.90 fusion minus primary `recall_acc` | v66 |
| 0.25–1.0 | tested sequence-scale range | v70 |
| 1.5123 / 0.004886 s | cold / warm mean retrieval latency per QA | v97 |
| 5,873 / 591 / 1,974 | cold conversation-Entity / Memory-embedding / question-Entity requests | v97 |
| 0 | new warm requests across those three cache-sensitive stages | v97 |

## Terminology

- `recall_acc` means the official evidence-recall calculation.
- “Categories 1–4 subset F1” is a repository-defined local summary, not an
  official LoCoMo metric.
- “Final-answer F1” refers to the frozen evaluator’s per-QA F1 aggregation.
- “Robust” means stable over the preregistered top-k range in this dataset; it
  does not mean cross-dataset generalization.
