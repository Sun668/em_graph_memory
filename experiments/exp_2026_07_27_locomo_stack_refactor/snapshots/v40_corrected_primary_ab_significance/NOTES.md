# v40 — corrected primary M1-B versus M1-A significance

Decision date: 2026-07-28 Asia/Shanghai.
Analysis source commit:
`01988bef65315f9ac5d583c863d702d5b274f61a`.
Analysis source tree:
`8c41ccb3c22dc358cf009c14d6a49bdd13f0be82`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

This is the predeclared corrected all-10 M1-B versus M1-A comparison after the
immutable query-artifact repair and migration. It uses the existing accepted A
through the committed v39 relocation proof and the new local B from v37. It
does not rerun answers or recalculate official metrics.

## Exact command

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
  .venv/bin/python \
  experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py \
  compare \
  --a-dir \
    outputs/locomo_formal/formal_all10_M1_A_top25_76fcf5b_qfrozen_run01 \
  --a-relocation-manifest \
    experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v39_relocation_validation_gate/a_relocation_manifest.json \
  --b-dir \
    outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 \
  --data-file data/locomo10.json \
  --resamples 10000 \
  --seed 20260727 \
  --output \
    outputs/locomo_analysis/corrected_m1_ab_01988be_seed20260727_10000.json
```

No secret or model API is used. The analysis source SHA-256 is
`98c8b8dbb5d0f05b1061aa3d1eca5a99efdbb3f7f285a7eb2cc06a77755da2fa`.
The generated report SHA-256 is
`00f9c345131032141a18066ea2f756603cdfe1110e0ea6fe158f8cd498aa05ee`;
an independent second run is byte-identical. Report fingerprint:
`f64861bd70a6e6321cf2bcabb9028173f4d70de94ef18b1ade3aff518ed97db4`.

## Exact condition comparison

Both original behavior owners were reinspected. `git diff` is empty between
A source `76fcf5b` and B source `41a7812` for `code/em_graph/`,
`code/locomo_eval/`, `formal_graph.py`, `run.py`,
`significance_report.py`, and `validate_formal_result.py`. The source commits
differ, but the scoped construction, retrieval, formal orchestration,
evaluation, and analysis code is byte-identical. The condition configs and
artifacts provide the intended method difference.

| Dimension / parameter | Side A: exact behavior | Side B: exact behavior | Expected impact of the difference |
|---|---|---|---|
| Dataset / scope | LoCoMo-10 SHA `047d8e…d74`; all 10 conversations; 1,986 QA; 446 Category 5 | Exactly the same dataset, order, scope, and counts | No dataset or denominator effect |
| Source | Commit `76fcf5b`; scoped behavior files byte-identical to B source | Commit `41a7812`; scoped behavior files byte-identical to A source | No implementation drift in the compared path |
| Graph inputs | Conversation date/time, dialog ids, speakers, dialog text, captions; no QA/test annotation | Same allowed conversation fields; no QA/test annotation | No graph-constraint difference |
| Graph structure | Memory-only: 5,882 Memory, 0 Entity, 0 Entity–Memory, 11,744 NEXT/PREV edges | Entity–Memory: 5,882 Memory, 12,808 Entity, 36,227 Entity–Memory, 11,744 NEXT/PREV edges | B can gate/fuse through conversation-derived Entity links |
| Conversation extraction | No Entity extraction | Cached extract-v4 `gpt-3.5-turbo` over normalized conversation text/caption; builder adds speaker Entities; normalized/deduplicated | Construction and cached extraction cost increase; denser graph |
| Memory embedding | `text-embedding-3-small`; canonical speaker + normalized text + caption; same 10 indexes | Exactly the same model, text protocol, ids, digests, and indexes | No Memory-vector confound |
| Query vector | Immutable L2 float32 artifact SHA `bef99a…986f9f`, 1,986 ordered QA, 1,974 unique questions, 1,536 dimensions | Exactly the same immutable artifact and ordered identity | No semantic-query-vector confound |
| Query Entity extraction | None | Retrieval-time `gpt-3.5-turbo`; cache plus 1,671 calls during migrated B run | Enables Entity gating/fusion; increases retrieval-time cost; never changes graph construction |
| Candidate pool | Full-pool signed-cosine dense ranking | Entity-gated pool with exact dense fill | B prioritizes graph-connected Memories while preserving exact top-k |
| Score fusion | Entity `0.0`, semantic `1.0` | Entity `0.30`, semantic `0.70` | Direct intended graph-fusion effect |
| Entity controls | Not applicable in scoring; configured threshold `0.5`, top 20/key, who dampening `0.25`, degree discount have no active Entity channel | Threshold `0.50`, top 20/key, who-only dampening `0.25`, degree discount enabled | Controls B candidate relevance and high-degree Entity bias |
| Sequence expansion | Disabled | Enabled; secondary scale `0.50` | B can add chronological neighbors |
| Top-k | Exactly 25 unique ordered Memory ids | Exactly 25 unique ordered Memory ids | No context-budget difference |
| Answer protocol | Frozen LoCoMo Reader; `gpt-3.5-turbo`; one system message; temperature 0; 32 tokens; batch 1; upstream unseeded Category-5 order | Exactly the same | No intended answer-protocol difference; residual Reader/Category-5 variance remains |
| Metric | Frozen official serialized token-F1 and `recall_acc`; empty-evidence recall contributes zero with all rows retained | Exactly the same | No metric or aggregation difference |
| Formal isolation | New absent directory at original run; no resume/overwrite; v39 relocation manifest binds unchanged bytes to v34 | New absent local directory; no resume/overwrite | Relocation affects provenance only, not metric content |
| Statistical estimator | B-minus-A paired QA and whole-conversation cluster bootstrap; seed `20260727`; 10,000 resamples | Same joint comparison | Quantifies row-level and conversation-level uncertainty |

Exactly aligned: dataset/order, Memory representations and vectors, immutable
query vectors, top-k, answer protocol, official metrics, empty-evidence policy,
and all scoped implementation files. Functionally similar but structurally
different: both recall graph Memory nodes, while B additionally uses Entity
gating/fusion and chronological expansion. Intentionally different:
conversation Entity graph, query Entity extraction, fusion, gate, and sequence
expansion.

The absolute repository root differs only for A's transferred files. v39
proves the run config, predictions, stats, audit, query usage, and query
artifact are unchanged; this has no dataset or metric effect. No cache,
answer, metric, or prior comparison is invalidated by the relocation proof.
The component experiments still required to isolate the intended differences
are B_gate, B_gate_seq, B_entity, and B_noseq.

## Graph extraction and construction logic

A creates one Memory per dialog and chronological NEXT/PREV edges. B uses the
same Memories and edges, then extracts Entity keys from normalized
conversation text plus optional `blip_caption`, adds speaker Entities, and
links mentions as Entity–Memory edges. Extract-v4 normalization and
deduplication are bound by each graph identity.

Construction uses session date/time, dialog id, speaker, normalized dialog
text, and caption only. It excludes QA questions, answers, evidence,
categories, judge outputs, prior predictions, and question-driven ledgers.
The immutable query artifact and question Entity extraction are retrieval-time
inputs only.

## Recall and answer logic

A ranks the full Memory pool by signed cosine. B obtains candidates through
question-Entity matching, applies threshold/top-per-key/who/degree controls,
fuses Entity and signed semantic scores at `0.30/0.70`, expands chronological
neighbors at scale `0.50`, fills from dense ranking when necessary, and emits
exactly 25 unique ordered Memory ids.

Both convert the recalled Memories to the same Dialog evidence format and pass
them through the unchanged `QARecall` interface. The frozen package owns the
Reader prompt, Category 1–5 branches, answer generation, per-row
three-decimal F1/recall serialization, and aggregation.

## Judge and statistical logic

There is no LLM-as-Judge. The analysis consumes immutable official per-row F1
and recall; it does not recalculate either. Four empty-evidence Category-3
rows in each condition contribute zero recall but remain in all denominators.
Computed category recall exactly matches each official `stats.json`.

The primary difference direction is B minus A. The single predeclared primary
comparison has no multiple-comparison adjustment. Category results and the
Categories 1–4 subset are descriptive; any later component-family claims must
use Holm correction.

## Primary results

| Metric | A | B | B − A | Paired-QA 95% CI / p | Conversation-cluster 95% CI / p |
|---|---:|---:|---:|---:|---:|
| Official overall F1 | 42.0681% | 42.5680% | +0.4998 pt | [-0.5745, +1.5514], p=0.3620 | [-0.1773, +1.2711], p=0.1712 |
| Official Recall@25 | 79.7468% | 84.4842% | +4.7374 pt | [+3.6504, +5.8425], p=0.0002 | [+3.5286, +6.0124], p=0.0002 |
| Local Categories 1–4 F1 | 51.2645% | 51.9740% | +0.7095 pt | [-0.4533, +1.8751], p=0.2280 | [-0.1166, +1.5873], p=0.0970 |
| Local Categories 1–4 Recall@25 | 82.8099% | 85.0232% | +2.2133 pt | [+1.2389, +3.1966], p=0.0002 | [+1.3107, +3.0734], p=0.0002 |

Recall improvement is statistically significant under both estimators.
Overall F1 and the local Categories 1–4 F1 diagnostic both cross zero under
both estimators and are not statistically significant.

Category deltas:

| Category | QA | F1 B − A | Recall@25 B − A |
|---|---:|---:|---:|
| 1 | 282 | +1.7674 pt | +1.9333 pt |
| 2 | 321 | -0.4399 pt | -0.0520 pt |
| 3 | 96 | -0.9302 pt | +6.9094 pt |
| 4 | 841 | +0.9807 pt | +2.6358 pt |
| 5 | 446 | -0.2242 pt | +13.4529 pt |

These category deltas are descriptive and uncorrected. Category 2 is the only
recall category with a tiny negative mean.

Recall improves in all 10 conversations. F1 improves in six and decreases in
four; the largest F1 increase is conv-26 (`+2.9312` points), and the largest
decrease is conv-47 (`-1.1695` points). The retrieval gain is therefore not
driven by only one or two conversations.

## Compliance, cost, and decision

Both formal inputs pass full validation. A relocation uses manifest SHA
`9c65b3de…b2672` and v34 result SHA `5e114d1e…58a56`; B is validated directly.
All scoped behavior sources are identical between their run commits.
The post-analysis audit passes all 75 experiment tests, all 16 vendored source
hashes, and confirms that `code/locomo_eval/` has no uncommitted change.

Mandatory graph constraint: **pass**. Both graphs are conversation-built and
answers use graph retrieval. Prompt budget: A `0/5000`, B `2410/5000`, both
pass; the analysis adds no runtime prompt. No oversized, ineffective, or
harmful prompt component is introduced here.

The analysis makes zero external calls and adds negligible local CPU cost.
Formal run cost remains the partial warm telemetry already frozen in v34 and
v37; the dedicated cold/warm cost experiment is still pending.

Supported claim: **M1-B significantly improves Recall@25 over matched M1-A;
there is no statistically significant overall F1 improvement.** This is not a
stop condition. Publication gate: `continue`, `paper_ready=false`.

Next: commit/push v40, then run B_gate, B_gate_seq, B_entity, and B_noseq from
isolated absent directories before input ablations and robustness studies.
