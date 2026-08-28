# Publication evidence ledger

This ledger is journal-neutral. Every numerical statement below points to a
frozen machine-readable artifact. Ledger IDs use the E prefix and are
independent of the canonical claim IDs in .paper/claims.yml.

| ID | Claim | Evidence | Allowed certainty | Status / required wording |
|---|---|---|---|---|
| E1 | Complete B improves official evidence recall over matched A at top-k 25 by 4.7374 points. | `snapshots/v40_corrected_primary_ab_significance/result.json`, `overall.recall_at_25` | Statistical within the evaluated ten-conversation set | Supported under paired-QA and conversation-cluster bootstrap. |
| E2 | Complete B improves overall final-answer F1 over A. | Same file, `overall.f1` | Descriptive only | Unsupported statistically. Write that F1 differs by +0.4998 points and both intervals include zero, or omit the difference. |
| E3 | The recall advantage holds at top-k 5, 10, 25, and 50. | `v55`, `v57`, `v40`, and `v60` snapshot results | Robust over the tested cutoff range | Supported. Do not extend beyond 5–50. |
| E4 | A and B_embed provide an exact dense-retrieval control. | `snapshots/v36_corrected_b_embed_all10_dense_control/result.json` | Direct protocol fact | Supported: zero ordered-context mismatches across 1,986 QA rows and identical `recall_acc`. |
| E5 | Sequence expansion contributes to recall inside complete B. | `snapshots/v46_component_family_significance/result.json`; component-family report | Mechanistic under the declared ablation | Supported after Holm for recall, not F1. |
| E6 | Entity-score fusion contributes to recall. | Same component-family evidence | Mechanistic under the declared ablation | Supported after Holm for recall, not F1. |
| E7 | The semantic channel contributes to both recall and F1 relative to Entity-only retrieval. | Same component-family evidence, `semantic_signal` | Mechanistic under the declared ablation | Supported after Holm for both metrics. |
| E8 | Deterministic speaker links contribute to recall within B. | `snapshots/v53_b_no_speaker_all10/result.json` | Mechanistic under the speaker ablation | Supported for recall (+1.4822 points), not F1. |
| E9 | Time annotations improve overall B retrieval. | `snapshots/v52_input_family_significance/result.json` | None beyond descriptive | Not supported after Holm. Do not claim an effect. |
| E10 | The B-over-A recall advantage persists under raw-text input. | Same input-family evidence | Statistical input sensitivity | Supported after Holm; F1 is not supported. |
| E11 | Primary 0.30/0.70 fusion is insensitive to the tested weights. | `snapshots/v66_fusion_family_significance/result.json` | Mixed | `0.50/0.50` is not distinguishable, but `0.10/0.90` lowers recall. Do not call the whole range insensitive. |
| E12 | Sequence scale is insensitive from 0.25 to 1.0. | `snapshots/v70_sequence_family_significance/result.json` | Sensitivity robustness | Supported as “no family-corrected difference established,” not equivalence. |
| E13 | Local DRAGON reproduces the official reference. | `snapshots/v75_o2_local_dragon_all10/result.json` plus failed O1 evidence | None | Rejected. Label local diagnostic only. |
| E14 | The system is state of the art on LoCoMo. | No valid controlled official-reference evidence | None | Rejected. |
| E15 | Complete primary-B cold/warm construction and retrieval usage is measured. | `snapshots/v97_v93_complete_cold_warm_cost/result.json`; `outputs/locomo_cost/primary_b_v93_report.json` | Direct measured system evidence | Supported for requests, tokens, latency, and storage. Per-question token values are deterministic aggregates. The dollar conversion is illustrative only because prices were accessed after the run. |
| E16 | The result generalizes to other datasets or populations. | One LoCoMo dataset only | None | Gap. Requires external datasets. |
| E17 | The requested GPT-3.5/DeepSeek by TES/Doubao configured-pipeline matrix establishes exact model/deployment equivalence. | `paper/robustness_audit.json`, `valid_four_cell_matrix` | None | Rejected. No corrected F1 or requested-extraction recall difference is detected, but failure to reject is not equivalence and actual deployment revisions are incompletely observed. |
| E18 | Across the paper-eligible four-cell configured-pipeline matrix, F1 and evidence recall support limited empirical robustness across the tested requested extractors; embedding robustness is outcome-specific because F1 supports empirical robustness under the declared rule while evidence recall remains sensitive to the frozen embedding artifacts. | `paper/robustness_audit.json`, `valid_four_cell_matrix.holm` | Statistical within the tested requested two-extractor/two-embedding matrix | Supported with the stated factor, outcome, artifact, and family boundaries. This is not formal equivalence and must not be generalized to arbitrary or fully identified provider deployments. |
| E19 | Doubao frozen embedding artifacts lower `recall_acc@25` relative to TES frozen artifacts by 2.0227 points under DeepSeek extraction and 2.2864 points under GPT-3.5 extraction. | `paper/robustness_audit.json`, `valid_four_cell_matrix.holm.embedding_recall` | Statistical within the valid matrix | Both cluster-bootstrap contrasts remain supported after two-test Holm correction. Their intervals contain values on both sides of the preregistered −3-point materiality boundary, so neither strict equivalence nor material robustness failure is established. |
| E20 | Across the four paper-eligible configurations, Single-hop has the highest B answer-F1 range; Temporal and Adversarial B recall is numerically above the non-protocol Dialog@25 anchor; Open-domain has the lowest B answer-F1 range among Categories 1–4; Adversarial has the lowest raw B answer-F1 range under the separate Category-5 branch. | `paper/robustness_audit.json`, `category_ranges_percent` and `external_positioning`; LoCoMo Tables 2–3; LightGMEM Table 2 | Descriptive external positioning only | Supported as a descriptive profile, not as a protocol-matched ranking or category-level SOTA claim. |
| E21 | The sequence-gating sign reversal is compatible with the metric definitions. | `paper/robustness_audit.json`, case `sequence_metric_sign_reversal`; primary prediction artifacts | Illustrative mechanism case | Supported as an example: evidence recall rises 0→1 while the correct concise answer receives lower token F1 than an incorrect verbose answer. Do not treat one row as causal proof. |
| E22 | GPT-5 mini completes a valid third-extractor robustness comparison. | `paper/robustness_audit.json`, `excluded_gpt5_mini_cells` | None | Rejected pending rerun. Frozen extraction budget is 2,500 but runtime used 4,000; 12 calls exceeded 2,500. Keep both cells diagnostic only. |
| E23 | The system is state of the art within any LoCoMo category. | External rows in `paper/robustness_audit.json` | None | Rejected. Readers, embeddings, endpoints, category scope, and/or metrics differ. |

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
| 309.48× | cold-to-warm mean retrieval speedup | v97 |
| 5,873 / 591 / 1,974 | cold conversation-Entity / Memory-embedding / question-Entity requests | v97 |
| 0 | new warm requests across those three cache-sensitive stages | v97 |
| 7,903,980 / 546,178 | cold input / output tokens including the attached answer trace | deterministic sum of v97 stage values |
| 8,450,158 / 4,254.9 | cold total tokens / amortized tokens per QA | deterministic sum and division by 1,986 from v97 |
| 1,389.9 | answer-stage total tokens per QA | `(2,744,099 + 16,269) / 1,986` from v97 |
| $4.67 / $0.00235 | illustrative total / per-QA API cost at prices accessed 1 August 2026 | v97 usage × OpenAI public GPT-3.5 Turbo and text-embedding-3-small list prices; not a frozen metric |
| 42.1087%–42.8158% | Overall F1 range across the four valid model cells | `paper/robustness_audit.json`, `valid_four_cell_matrix.overall_ranges` |
| −2.0227 / −2.2864 points | DB−TES `recall_acc@25` under DeepSeek / GPT-3.5 extraction | Same file, `holm.embedding_recall` |
| 12 / 3,014 | GPT-5 mini calls above the frozen 2,500-token limit / maximum observed output tokens | Same file, `excluded_gpt5_mini_cells.runtime_evidence` |
| 37.56–39.95 / 40.24–43.14 / 17.26–18.60 / 63.80–64.13 / 8.30–11.21 | Valid-cell F1 ranges for Multi-hop / Temporal / Open-domain / Single-hop / Adversarial | Same file, `category_ranges_percent` |
| 61.50–67.28 / 89.17–90.24 / 48.36–56.36 / 91.14–92.69 / 80.16–82.62 | Corresponding valid-cell `recall_acc@25` ranges | Same file, `category_ranges_percent` |

## Terminology

- `recall_acc` means the official evidence-recall calculation.
- “Categories 1–4 subset F1” is a repository-defined local summary, not an
  official LoCoMo metric.
- “Final-answer F1” refers to the frozen evaluator’s per-QA F1 aggregation.
- “Robust” must name the tested axis and outcome. Cutoff robustness covers
  the B-over-A recall advantage from top-k 5–50. Extraction-model robustness
  covers F1 and evidence recall for the requested GPT-3.5 and DeepSeek v4
  Flash configurations only. Embedding robustness is outcome-specific: F1 is
  empirically robust under the declared rule, while evidence recall differs.
  None of these claims means strict equivalence, arbitrary-model invariance,
  fully identified deployment robustness, or cross-dataset generalization.
