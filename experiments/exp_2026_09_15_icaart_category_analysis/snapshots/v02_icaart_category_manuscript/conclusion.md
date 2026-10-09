# Conclusion: descriptive category outcomes

## Settings and provenance

All 1,986 QA from ten LoCoMo conversations, Categories 1--5, original paired order; primary A/B top25. Dataset SHA, prediction/stat SHA, source commits, pairing checks and cases are in `result.json`; full exact original commands, effective settings, environment-facing values and cache identities are frozen in v01 run configs. Offline command is in README. Requested extraction/answer model GPT-3.5-turbo; embedding text-embedding-3-small. B weights .3/.7, sequence .5, threshold .5, top20/key, who-only .25, degree discount on; A dense0/1. Reader system role, temp0, max32, batch1. No new randomness or API calls. Original deployments unknown; Category5 ordering unseeded. Existing primary bootstrap uses seed20260727 and 10,000 QA/cluster resamples; new counts have no inferential test.

## Extraction, construction and recall

Conversation-only normalized dialog Memories include speaker, session anchors and BLIP captions. B uses extract-v4 LLM Entities, normalized/deduplicated plus speaker Entities, linked to Memories; NEXT/PREV edges encode chronology. QA/gold/evidence/category/judge/prediction/ledger inputs are excluded from construction. A uses graph Memory embeddings; B Entity seeds and neighbor expansion gate signed-cosine fusion, followed by dense fill to25. Shared frozen Memory indexes/query vectors and context-to-reader interface remain unchanged; neither side supplies test annotations at runtime. Full source/stage comparison is in `protocol.md` and original v34/v37 NOTES.

## Outcomes

| Type | QA | F1 delta (pp) | Recall delta (pp) | F1 up/down/tie | Recall up/down/tie | Recall up, F1 not up |
|---|---:|---:|---:|---|---|---:|
| Multi-hop | 282 | +1.7674 | +1.9333 | 61/53/168 | 33/21/228 | 17 |
| Temporal | 321 | -0.4399 | -0.0520 | 47/56/218 | 8/7/306 | 7 |
| Open-domain | 96 | -0.9302 | +6.9094 | 7/13/76 | 12/1/83 | 11 |
| Single-hop | 841 | +0.9807 | +2.6358 | 136/125/580 | 33/10/798 | 16 |
| Adversarial | 446 | -0.2242 | +13.4529 | 16/17/413 | 68/4/374 | 66 |

Positive F1 means are confined to multi-hop and single-hop; temporal declines slightly in both outcomes. Open-domain and adversarial recall gains frequently do not coincide with answer-score gains. Tied recall is not tied context. Cases document incomplete multi-hop support despite perfect stored F1, temporal date/wording errors, missing rationale, successful fact recovery, and premise/person mismatch. These selected examples cannot estimate error-class prevalence or attribute changes to components. New results are descriptive only; original category means and v40 overall significance decisions are unchanged.

## Judge, metric and compliance boundaries

No LLM-as-Judge was used; no judge-quality target or promotion is applicable. Existing frozen per-row F1 and official evidence recall are read, not recomputed; Category5 is a binary branch despite the F1 field. Direction counts are not correctness counts. Four empty-evidence rows use the frozen aggregate zero contribution. Input hashes/pairing/category-mean checks and two fresh validators pass. Original prompt-budget check records Entity scaffold 2,410 characters below5,000; this analysis adds no runtime prompt and removes/enables no component. Conversation-only graph and graph-retrieval audits pass. Outputs are isolated under the dedicated offline output directory; no formal output or cache is changed. Source/results/settings/validator reports were frozen in v01 before manuscript edits. API calls and new answer-generation cost: zero.

## Next action

Use the paired category table and five calibrated paragraphs in the ICAART manuscript; have authors review interpretation. Further causal claims require separate controlled, compliant experiments as outlined in `next_steps.md`.
