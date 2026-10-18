# All-ten paired point-time F1 result

Both formal conditions were independently validated and snapshotted before
this analysis: B `pt_all10_B_v02` at `../v09_b_v02_complete/`; treatment
`pt_all10_T_v03` at `../v12_t_v03_complete/`. Frozen parameter snapshots
and exact secret-free launch commands are under `../pt_all10_B_v02/`
and `../pt_all10_T_v03/`. B source commit was
`f455bbac23d665ec35c9ecc146e5ae25c7a8a9e8`; T source commit was
`d2e678cc27329c79cf254ece953035a28167a760`. Intermediate commits
contain only experiment notes, snapshots and analysis run-ID/provenance
checks; executable runner and treatment transformer hashes match byte for
byte. The final paired comparison command was
`PYTHONDONTWRITEBYTECODE=1 /Users/sun/Documents/git/graph_memory/.venv/bin/python experiments/exp_2026_10_17_point_time_all10/compare.py`.
The exact compare source and result are copied here. It was frozen before
treatment in `../v11_analysis_treatment_v03_id/`.

Dataset: `data/locomo10.json`, SHA-256
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`;
all 10 conversations, all 1,986 QA in original order, no category filter.
Categories 1–4 contain 1,540 QA and form the predeclared primary local
subset metric. Category 5 has 446 QA and is descriptive because the
upstream option order is unseeded. The query artifact SHA-256 was
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`;
both runs used it read-only, 1,997 hits each, zero misses and zero live
query embeddings. No retriever seed was set; exact Top25 identity was
checked for every QA. The comparison bootstrap used 10,000
conversation-cluster draws and seed 20261017.

Graph and extraction: both conditions reused identical conversation-built
Entity–Memory bipartite graph and Memory embedding indexes. Dialog text,
speaker, supported time annotations, session/dialog order and official
`blip_caption` supplied the graph; `gpt-3.5-turbo` Entity extraction
and its normalization/deduplication were completed in those validated
caches before this experiment. No new graph extraction or construction
was performed here. Graph profile had captions, time annotations and
speaker Entity nodes enabled. QA questions, gold answers, evidence
annotations, categories, judge outputs, previous predictions and
question-driven ledgers were excluded from graph construction. Answer
recall used graph nodes/edges. Full cache identities and model fields are
in the copied condition `run_config.json` files.

Retrieval: question Entity keys plus the ordered `text-embedding-3-small`
query vectors feed B graph recall. Entity weight 0.30, signed semantic
weight 0.70, no semantic score normalization, relative Entity threshold
0.5, Entity top20 per key, Who-only dampening 0.25, degree discount on,
sequence expansion on at secondary scale 0.5, no forced full pool, Top25
in relevance order. Treatment is deterministic: on `when`/`how long`
questions, it converts a supported relative point time in only the
first retrieved Memory's Reader text using conversation timestamps;
`last week`/`last weekend` stay verbatim. Other 24 Memories and
inactive contexts were unchanged in the pre-generation audit. It adds
no AI call, embedding or graph modification. Preflight recorded 99
changed contexts, first-Memory-only parity on 1,986 rows. Formal
outputs independently confirm the same ordered Top25 IDs and official
`recall_acc` row for all 1,986 QA.

Answer and scoring: both conditions used the frozen upstream LoCoMo
`gpt-3.5-turbo` answer protocol: full prompt as `system`, temperature
0, batch size 1, maximum 32 completion tokens. The upstream evaluator
at pinned vendor commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`
computed category-specific per-QA F1 and official evidence recall;
the comparison averages its serialized per-row F1 over Categories 1–4.
No local LLM-as-Judge was used. Graph constraint audit passed for both;
Entity scaffold length 2,410 was below the 5,000-character budget.
No oversized or ineffective prompt component was retained.

Main result: B Categories 1–4 subset F1
`0.518458442`; treatment
`0.538285714`; paired delta
`+0.019827273` (about +1.98 percentage points).
The predeclared 95% 10-conversation cluster-bootstrap interval is
`[+0.012374900,+0.027652484]`; its lower bound and the mean are
positive, so the fixed claim gate passes. All 10 conversation deltas
are positive. Of 98 changed-context Categories 1–4 QA, mean delta
is +0.287602041, with 58 wins, 11 losses and 29 ties. The remaining
1,442 Categories 1–4 QA have mean delta +0.001628988; a separate
independent NumPy cluster bootstrap includes zero for that inactive
subset. Category 2 improves from
`0.413754` to
`0.508349` (+0.094595);
other category deltas are in `independent_audit.json`.

Generation variability is material: despite byte-identical inactive
contexts in the preflight, 431 inactive answer strings differed between
fresh temperature-0 API runs, and 138 inactive Categories 1–4 per-row
F1 values differed. Their net F1 effect is small and its bootstrap
interval crosses zero, while the routed-row effect is much larger.
This experiment supports a positive result for this one fresh paired
all-ten execution; repeated independent answer runs would better
quantify API sampling variability. Conv26, Conv30 and Conv49 informed
development/confirmation, so all-ten is an expanded test, not a fully
unseen holdout.

B answer usage: 2,744,098 input/16,243 output tokens; T:
2,744,442 input/16,250 output tokens. The deterministic treatment adds
344 input tokens and no extra model request per question. Both were
below the prespecified 3.5-million/50,000 token and 14,400-second
ceilings, with distinct absent-at-start output directories and no
answer resume. No price is asserted without provider billing data.
Large predictions remain in the two exact output directories with
SHA-256 recorded in `result.json` and `independent_audit.json`.
The official overall/category F1 and `recall_acc` summaries are in
`result.json`; Categories 1–4 subset F1 is explicitly a
repository-defined aggregation, not an official LoCoMo metric.
