# Completed T v03 treatment — independent formal validation

Run: `pt_all10_T_v03`; source commit `d2e678cc27329c79cf254ece953035a28167a760`.
Exact secret-free launch command: `../pt_all10_T_v03/command.txt`.
Frozen parameter SHA-256: `b761fe5899959d07e70c6f2bfd106f920f27779929ed21daddbed70f0620c528`.
The approved `/Users/sun/Documents/git/graph_memory/env_gpt.sh` supplied
API settings, with no secrets stored here.

Scope: `data/locomo10.json`, all 10 conversations and 1,986 QA in dataset
order, all categories; no sample/category filter. The 1,540 Category 1–4
rows have a repository-defined subset F1 of
`0.538285714`. This is a single
condition and is not yet the audited paired difference. Official category
sums/counts and recall means are copied in `stats.json`. The frozen
upstream LoCoMo evaluator at vendored commit
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376` performed its established
category-specific F1/recall scoring, with unseeded Category 5 option order.
No local judge was used. Independent `validate_formal_result.py` returned
`pass`, 10 conversations, 1,986 QA, 446 Category 5 rows.

Graph/extraction: reused the validated B Entity–Memory bipartite graphs,
with conversation dialog Memory nodes, extracted Entity nodes/links,
session/dialog NEXT/PREV sequence edges and Memory indexes. Inputs were
dialog text, speaker, conversation timestamp and official `blip_caption`;
`gpt-3.5-turbo` Entity extraction was cached. Caption/time/speaker graph
profile was enabled. QA questions, gold answers, evidence annotations,
category labels, judge outputs, previous predictions and question-driven
ledger fields were excluded from graph construction. No new extraction,
normalization, deduplication or indexing was performed in this condition.
Graph/index identities for all conversations are in `run_config.json`.

Retrieval: each question used cached Entity keys and the read-only
`text-embedding-3-small` ordered query-vector artifact. The same B graph
recall scored Memories with Entity weight 0.30, signed semantic weight
0.70, relative Entity threshold 0.5, Entity top20 per key, Who-only
dampening 0.25, degree discount enabled and sequence secondary scale 0.5.
Top25 was ordered by relevance. Treatment mode `point_time_first` changed
only the Reader-facing first Memory text for supported `when`/`how long`
relative point-time questions; `last week`/`last weekend` remained
verbatim. It did not alter graph construction, retrieved nodes/edges or
question-vector formation. Query cache: 1997
hits, zero misses and zero live query embedding calls.

Answer: the same official `gpt-3.5-turbo` full prompt as a `system`
message, temperature 0, batch size 1 and max 32 completion tokens. No
extra model call or reranker was added by the treatment. The non-data
Entity scaffold was 2,410 characters versus the 5,000 limit; no
oversized or failed component was active. Usage: 2744442
answer-input tokens, 16250
answer-output tokens and 2383.1
answer seconds, below the frozen 3.5 million/50,000/14,400 ceilings.
The dedicated output directory was absent at start, used for this
condition only, and never resumed.

The exact output is `outputs/locomo_formal/pt_all10_T_v03/`; bulky
`predictions.json` remains there with SHA-256
`e70fb80641adb7d0ccab4d75a758ef74120456a6ccc9ca4ba44e1994fce3832e`. Compact result, config, validation,
usage and source are copied here, with hashes in `result.json`.
This is a valid formal graph condition; the treatment effect awaits
strict paired audit against the B output.
