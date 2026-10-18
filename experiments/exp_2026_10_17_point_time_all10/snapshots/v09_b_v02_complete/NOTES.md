# Completed B control — independent formal validation

Run: `pt_all10_B_v02`; source commit `f455bbac23d665ec35c9ecc146e5ae25c7a8a9e8`.
Exact secret-free launch command: `../pt_all10_B_v02/command.txt`.
The frozen parameter snapshot is `../pt_all10_B_v02/parameters.json`; its SHA-256 is
`e1478be87bc2c440d1fd913e7f77af35caeef76772c04d38321ab8a310559927`. Input API settings came from the approved
`/Users/sun/Documents/git/graph_memory/env_gpt.sh`, with no secrets stored here.

Scope: `data/locomo10.json`, all 10 conversations and all 1,986 QA in dataset
order, all categories; no sample or category filter and no retrieval random seed.
The 1,540 Category 1–4 rows have a repository-defined subset F1 of
`0.518458442`. This is a single-condition
control and provides **no paired improvement estimate**. Official category
sums/counts and recall means are copied in `stats.json`. The frozen upstream
evaluator (vendored commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`)
uses its established category-specific F1/recall rules and unseeded Category 5
option order; no local judge was used. Independent `validate_formal_result.py`
returned `pass`, 10 conversations, 1,986 QA, 446 Category 5 rows.

Graph construction and extraction: existing conversation-only B Entity–Memory
graph caches, with dialog Memory nodes and Entity nodes linked by extracted
Entity mentions; session/dialog order and graph NEXT/PREV sequence edges are
unchanged. Dialog text, speaker, supported time annotation and `blip_caption`
are conversation fields. Entity extraction was cached from `gpt-3.5-turbo`;
graph profile enables captions, time annotations and speaker entities. Graph
and Memory index identities are recorded for every conversation in
`run_config.json`. QA questions, answers, evidence annotations, categories,
judge outputs and previous predictions were excluded from graph construction.
No additional extraction, normalization, deduplication or indexing took place
in this condition; the validated caches were reused.

Retrieval: the question feeds the cached question-Entity extraction and a
read-only `text-embedding-3-small` ordered query-vector artifact. Graph
retrieval scores Memory nodes with Entity weight 0.30 and signed semantic
weight 0.70; per-key Entity top 20, relative Entity threshold 0.5, Who-only
dampening 0.25, degree discount enabled, NEXT/PREV secondary scale 0.5,
Top25 in relevance order. Reader context mode is `raw`. The graph Memory
texts are the answer evidence. Query-cache hits: 1997;
misses: 0; live query embeddings: 0. Full query/cache identities are in
`run_config.json`. This run therefore satisfies conversation-only graph
construction and graph recall.

Answer protocol: frozen official GPT-3.5 `system` prompt, batch size 1,
temperature 0, max 32 completion tokens, model `gpt-3.5-turbo`, no reranker
or validator added to the prompt. The non-data Entity prompt scaffold was
2,410 characters, below the 5,000-character limit; no oversized or failed
component was retained. Answer usage: 2744098
input tokens, 16243 output tokens,
2639.9 answer seconds; ceilings
were 3.5 million input, 50,000 output and 14,400 seconds. Output directory
was absent at start and used only by this condition, with no answer resume.

The exact output is `outputs/locomo_formal/pt_all10_B_v02/`; bulky
`predictions.json` remains there with SHA-256
`d12e8c2815512c5ae94e9bb012477a55101f86070e3faabf8208ee5f7ee1d579`. The compact result/config/validation/progress
files and exact execution source are copied here. All copied file SHA-256
values are in `result.json`. B is valid as a formal graph control; F1
improvement is pending a separately validated paired treatment.
