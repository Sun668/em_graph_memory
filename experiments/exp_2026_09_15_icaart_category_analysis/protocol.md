# Protocol and interpretation audit

This is a descriptive analysis of one frozen matched A/B comparison, not an external-paper comparison. Source: A `76fcf5b68998622012371a704c703c3004414224`, B `41a78125d640d5ebb127d1cb817843b4eef35a8b`; v40 records an empty behavioral source diff. Frozen evaluator upstream: `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`. Inspected original scoring symbols: `f1`, `f1_score`, `eval_question_answering` in `code/locomo_eval/vendor/locomo/task_eval/evaluation.py`; no modification or invocation by analysis. Manuscript method sections and v34/v37 NOTES retain the complete extraction/build/recall path. Exact commands and resolved identities are copied into snapshot `a_run_config.json` / `b_run_config.json`.

| Dimension / parameter | Side A: exact behavior | Side B: exact behavior | Expected impact of the difference |
|---|---|---|---|
| Scope | LoCoMo10, 10 conversations, 1,986 QA, all categories, original order | Identical dataset hash and paired rows | Fair paired descriptive scope; no new category tests |
| Extraction | Memory-only conversation graph; no Entity extraction | extract-v4 GPT-3.5 Entity extraction, temperature .3, 2,500-token limit, normalization/dedup/speaker links | Additional Entity indexing and query-extraction cost |
| Graph input | Session anchors, dialog ids, speakers, normalized text, BLIP captions; time annotations enabled | Same inputs and Memory texts; Entity nodes and edges added | QA/gold/evidence/categories/judge/predictions/ledgers excluded from both builds |
| Graph structure | 5,882 Memory nodes; 11,744 sequence edges unused | Same Memories, 12,808 Entities, 36,227 Entity-Memory links, 11,744 sequence edges | B can gate by Entity and expand chronological neighbors |
| Embedding | text-embedding-3-small; matched Memory indexes | Same | Query artifact shared SHA bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f; 1,536-dim L2 float32; zero query misses/live embedding calls |
| Retrieval | Full Memory pool, cosine, Entity/semantic weights 0/1, top-25 | Question Entity matching; Entity/semantic .3/.7; threshold .5; 20 Memories/key; who-only dampening .25; degree discount enabled; sequence scale .5, then gated fusion and dense fill; top-25 | Context composition/order can change; stage causality requires separate ablations |
| Generation | GPT-3.5-turbo requested alias, system message, temperature 0, max32, batch1 | Same requested protocol | Actual deployment revision unknown; answers are independently generated |
| Scoring | Frozen Category1 comma-split sub-answer F1; Categories2--4 token F1; Category3 first gold segment; Category5 binary abstention branch; scores stored at three decimals | Same frozen package and scoring branches | F1-up is not a correctness label, nor proof of complete multi-hop evidence |
| Recall | Official annotated-evidence fraction; empty-evidence rows contribute zero in summary | Same | Tied recall can hide changed evidence ids, order, and distracting context |
| Caches and outputs | Dedicated empty-at-start directory, no resume/overwrite; bound immutable query artifact | Different dedicated empty-at-start directory; same query artifact | Fresh validators pass; prior outputs preserved unchanged |
| Judge / inference | No LLM-as-Judge; existing v40 overall bootstrap seed20260727, 10,000 QA and cluster resamples | Same | New category report adds no significance/causal claim |

The dataset, Memory/query vectors, requested answer settings and evaluator are aligned as documented by v40 and fresh validators. Retrieval is intentionally different. Unknown provider deployments and unseeded Category-5 option order prevent stronger generation-equivalence claims. No cache, answer or metric is invalidated by this read-only analysis; no formal rerun is needed for its descriptive statements. Component attribution, new answer improvements or deterministic Category-5 generation comparisons would require separate valid controlled experiments. No new prompt is introduced; original validated prompt scaffolds remain unchanged. API/model-call cost of this analysis is zero.

## Fresh read-only validation

Run from the main checkout using `.venv/bin/python` and the existing `experiments/exp_2026_07_27_locomo_stack_refactor/validate_formal_result.py`:

```sh
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/validate_formal_result.py --condition-dir outputs/locomo_formal/formal_all10_M1_A_top25_76fcf5b_qfrozen_run01 --relocation-manifest experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v39_relocation_validation_gate/a_relocation_manifest.json --report /tmp/icaart_category_a_validation.json
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/validate_formal_result.py --condition-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 --report /tmp/icaart_category_b_validation.json
```

Both report `pass`, paper eligibility and graph compliance. Reports are frozen in v01; formal condition directories are not changed. Exact resolved parameters, cache identities, and original run commands are in the accompanying run configs. See README for the offline-analysis command and result JSON for all counts/selection rules.
