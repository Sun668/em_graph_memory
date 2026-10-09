# v01 — full LoCoMo adapted HippoRAG 2 paired retrieval comparison

All ten per-conversation HippoRAG conditions are complete and individually
frozen under sibling `snapshots/locomo_hippo_conv*_all_v01/`. This snapshot
freezes the exact `compare_results.py`, `command.sh`, and compact `result.json`
before follow-up analysis edits. Raw per-QA results and graph/index/cache
artifacts remain under `outputs/locomo_hipporag2/`; the result binds each
run's raw SHA-256. The source branch's pre-run commit is `9e2fa55`.
The frozen comparison source SHA-256 is
`d4497718e6223037602106683c9483751dc7fc1fb71ae8cc83dd6b0a2a2a0db6`;
the result SHA-256 is
`a2fd88b15e9d20e8b4dbd0197faf45a428cbdf0fffb40ede77130f9bc13bed2f`.
A second independent offline comparison reproduced identical bytes. All ten
raw result hashes match their individual committed-size summaries.

The dataset is LoCoMo-10 SHA-256
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`,
ten conversations, 5,882 original turns and 1,986 QA (including four with
empty evidence). A/B are the validated corrected runs
`formal_all10_M1_A_top25_76fcf5b_qfrozen_run01` and
`formal_all10_M1_B_top25_41a7812_qfrozen_run01`, with the identical frozen
query-vector artifact SHA
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.
Both validation files pass; the paired comparison is v40 of the 2026-07-27
LoCoMo stack refactor. The frozen vendored LoCoMo hash manifest passes and
`code/locomo_eval/` has no uncommitted changes.

HippoRAG uses official upstream commit
`d5c8329422e0a0b834a15874545cb6a74b4f9b26` (2.0.0a5), one passage per
original dialog with `dia_id` as source ID. Conversation session time,
speaker, text, and official `blip_caption` are the only graph inputs. QA,
answers, evidence, category labels, summaries, observations, judge outputs
and prior predictions were excluded from graph construction. Questions were
loaded after `index()` and used only for graph retrieval. All 5,882 passages
have OpenIE records; 93 entity lists are empty, no triple list is empty.
Every question has 25 unique original dialog IDs. This passes the mandatory
graph constraint; no answer or judge was run.

The extraction/fact-filter model is `gpt-3.5-turbo-0125`; embedding is
`text-embedding-3-small`; temperature 0, OpenIE workers 4, NER/triple token
caps 2,048/4,096, retries 2, linking top-k 5, PPR damping 0.5, passage-node
weight 0.05, retrieval top-k 25. The upstream fact-filter prompt was adapted
to its first two examples through the documented prompt-file setting because
the ten-example default exceeds this repository's prompt budget. NER/triple/
fact-filter non-data scaffolds are 554/1,836/3,808 characters, below 5,000;
no oversized or measured harmful component remains active. This is an
**adapted local retrieval-only comparison**, not an exact HippoRAG paper
reproduction or an official LoCoMo answer score.

The offline metric is the fraction of each QA's gold evidence IDs in its
top-25 original-dialog list; the four empty-evidence rows contribute zero
and all 1,986 QA remain in the mean, matching the official aggregate policy.
The local script recomputes raw fractions; A/B raw means agree with their
frozen official serialized category statistics within the 0.0005 gate.
Results: A 0.7974683, B 0.8448410, HippoRAG 2 0.7970252. B minus HippoRAG
is +0.0478158; the 10-conversation cluster bootstrap 95% interval is
[+0.0283140,+0.0680061], seed 20261008, 10,000 resamples. B is better in
all ten conversations. HippoRAG minus A is -0.0004431 with cluster interval
[-0.0156434,+0.0129973]; this does not establish a difference. Category and
conversation results are in `result.json`.

The ten HippoRAG conditions used 13,738 live chat calls (12 cache hits),
6,299,539 chat input and 508,596 output tokens; 1,719 embedding requests
used 626,126 input tokens. This excludes the previously completed A/B costs.
No judge model, rubric or F1 applies. The result supports a LoCoMo
retrieval-only advantage for the current EM-Graph B over this adapted
HippoRAG 2 configuration, not an answer-accuracy or cross-dataset claim.
