# Conclusion — LoCoMo top-25 retrieval comparison

## Result and scope

The ten-conversation, 1,986-QA adapted retrieval-only comparison is complete.
No new answer generation or judge evaluation was performed. All 5,882 original
dialog turns were indexed; all 1,986 HippoRAG results contain 25 unique
original `dia_id` values. Four QA have empty gold evidence: they contribute
zero but remain in the denominator. The metric is the mean per-QA fraction of
gold evidence IDs in the top-25 list, following the frozen LoCoMo aggregate
policy. Local raw fractions bypass the official three-decimal per-row
serialization; A/B means match frozen official stats within 0.0005. This is
an adapted local retrieval comparison, not an official answer benchmark score.

| Method | Evidence recall at 25 | Difference from dense A |
|---|---:|---:|
| A, dense Memory-node retrieval | 79.7468% | reference |
| EM-Graph B | **84.4841%** | +4.7373 points |
| Adapted HippoRAG 2 | 79.7025% | −0.0443 points |

B minus HippoRAG 2 is **+4.7816 points**; its paired 10-conversation cluster
bootstrap 95% interval is **[+2.8314,+6.8006] points**, seed `20261008`,
10,000 resamples. B is higher in **10/10** conversations. It is higher on
191 individual QA rows, HippoRAG is higher on 65, and they tie on 1,730.
HippoRAG minus A is −0.0443 points, cluster interval
[−1.5643,+1.2997] points: no established improvement over dense A. B minus
A is +4.7373 points, cluster interval [+3.5348,+6.0095] points. The cluster
resample recomputes the QA-weighted mean after sampling whole conversations.

| LoCoMo category | QA | A | B | Adapted HippoRAG 2 |
|---|---:|---:|---:|---:|
| 1 | 282 | 65.16% | **67.09%** | 62.88% |
| 2 | 321 | **89.67%** | 89.62% | 86.68% |
| 3 | 96 | 48.28% | **55.19%** | 47.22% |
| 4 | 841 | 90.05% | **92.69%** | 88.53% |
| 5 | 446 | 69.17% | **82.62%** | 75.67% |

No per-category significance claim is made. Full conversation/category
results and usage are in `result.json`. Conv-26 QA 55 asks what subject
Caroline and Melanie both painted: B finds both gold dialogs at ranks 4 and
17; A and HippoRAG find neither. Conv-26 QA 127 asks what Caroline made for a
local church: HippoRAG ranks the gold dialog first, B misses it, and A finds
it at rank 24. These cases demonstrate both directions without proving why.

## Inputs and effective settings

Dataset `data/locomo10.json` has SHA-256
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
The ten sample IDs in order are conv-26, conv-30, conv-41, conv-42, conv-43,
conv-44, conv-47, conv-48, conv-49, conv-50. No QA/category filter was
applied. The offline bootstrap seed is 20261008. Extraction/fact filtering
used temperature 0; no stochastic generation seed was set.

Baseline owners are `experiments/exp_2026_07_27_locomo_stack_refactor/run.py`,
`code/em_graph/build/builder.py`, and `code/em_graph/recall/retrieval.py`.
The exact corrected historical comparison is frozen in that experiment's
`snapshots/v40_corrected_primary_ab_significance/`. The HippoRAG owner is
official upstream `outputs/hipporag_upstream/src/hipporag/HippoRAG.py` at
commit `d5c8329422e0a0b834a15874545cb6a74b4f9b26` (2.0.0a5). The
adapter is `run_retrieval.py`. Ten complete parameter files, runner source
copies, and exact commands are under `snapshots/locomo_hippo_conv*_all_v01/`.
The exact comparison source, command, and result are frozen in
`snapshots/v01_full10_paired/`.

| Dimension / parameter | Side A: EM-Graph B exact behavior | Side B: adapted HippoRAG 2 exact behavior | Expected impact of the difference |
|---|---|---|---|
| Dataset/evidence | All 10 histories, 1,986 QA; original dialog `dia_id`, top-25 | Same history/question order, ID and top-25 | Aligned evidence unit and denominator |
| Graph input | Session time, speaker, text and official `blip_caption`; deterministic relative-time annotations | Same information fields, formatted per original turn as session time/speaker/raw utterance/caption | Same information scope; text processing can change extraction and embeddings |
| Extraction | `gpt-3.5-turbo` extract-v4 Entity keys from normalized text/caption, plus speaker Entities; normalization/dedup in `code/em_graph/build/` | `gpt-3.5-turbo-0125` online OpenIE NER and RDF triples per turn, upstream normalization | Different extracted content and model version; graph-only effects are not isolated |
| Graph | Bipartite Entity–Memory links plus chronological NEXT/PREV | Passage/entity/fact graph with provenance and synonym links | Different paths for query relevance |
| Embeddings | `text-embedding-3-small` Memory vectors; same immutable L2 A/B query artifact SHA `bef99a…986f9f` | `text-embedding-3-small` passage/entity/fact/query vectors in independent upstream cache | Same named model; vector/protocol bytes are not matched across methods |
| Query | Retrieval-time cached `gpt-3.5-turbo` Entity-key extraction and Entity BM25 | Query/fact embeddings and two-example recognition-memory fact filter | Different query representations and API cost |
| Ranking | Entity gate, signed cosine Memory score fused 0.30/0.70, sequence neighbor scale 0.50; entity threshold 0.50, top 20/key, who dampening 0.25, degree discount; dense fill | Fact retrieval/filtering, dense passage scoring and personalized PageRank; linking top-k 5, damping 0.50, passage-node weight 0.05; dense fallback when no facts | Intended retrieval-algorithm difference |
| Prompt/limits | Frozen extract-v4 and query prompts; B's recorded fixed scaffold 2,410 chars | NER/triple/fact-filter scaffolds 554/1,836/3,808 chars; OpenIE token caps 2,048/4,096, 4 workers, 2 retries | Both meet the 5,000-char cap; two-example Hippo prompt adapts upstream default |
| Answers/judge | Historical A/B answer files exist, but only context IDs are read here | No answer/judge stage | Only retrieval is compared |
| Cache/output | A/B condition-specific validated results; shared query artifact, zero query misses/live requests | Ten absent-at-start independent graph/index/output conditions, pinned input/prompt/upstream hashes | No mixed result directory; caches are not interchangeable |

Dense A uses the same 5,882 Memory nodes and Memory vectors as B, with
entity/semantic weights 0/1, full-pool signed cosine, no sequence expansion,
top-25. Its graph is Memory-only. A/B's historical frozen answer model was
`gpt-3.5-turbo`, system role, temperature 0, 32-token cap; those answers were
not used here. HippoRAG used extraction/fact-filter `gpt-3.5-turbo-0125`,
embedding `text-embedding-3-small`, temperature 0, OpenIE workers 4,
`linking_top_k=5`, `damping=0.5`, `passage_node_weight=0.05`, and two retries.
No answer or judge model was configured. The API endpoint was sourced from
`env_gpt.sh`; no secret is stored in snapshots. Each exact `command.sh` sets
`RESEARCH_RUN_CLASS=diagnostic`, `RESEARCH_PARAMETER_SNAPSHOT`, and
`RESEARCH_CONDITION_DIR`, then invokes the isolated HippoRAG Python runtime.

Exactly aligned: dataset, question order, original evidence ID, top-25 and
offline denominator. Functionally similar: conversation-only graph retrieval.
Different: graph schema, extraction model/prompt, input normalization,
embeddings, query processing and ranking. Image-search `query` and forbidden
fields are absent from both graph inputs, so they have no effect here.
Changing Hippo's prompt, input format, model or upstream source invalidates
its index and retrieval results; changing top-k or ranking invalidates its
retrieval output. Historical A/B artifacts are unchanged. A stricter
method-isolation claim needs matched model snapshots and reruns. Answer
accuracy requires a separate matched answer experiment.

## Graph, prompt, metric, and cost audit

`prepare_data.py` writes graph-only, question-only and offline-gold files.
`run_retrieval.py` indexes only conversation fields, then loads questions.
Gold is read only by `compare_results.py` after all runs complete. QA
questions, answers, evidence, categories, judge data, past predictions and
question-driven artifacts were excluded from graph construction. The
HippoRAG graph uses original dialog passages, OpenIE entities/triples,
passage/fact links and synonym links; answer recall uses upstream graph
retrieval. Prompts only improve graph information density or retrieval. The
mandatory graph constraint passes. OpenIE has records for all 5,882 turns;
93 entity lists were empty, no triple list was empty, and no turn was dropped.

The comparison validates the dataset hash; A/B prediction hashes, query
artifact identity and zero query misses/live requests; Hippo upstream,
parameters, input/prompt hashes; all 1,986 row identities and 25 unique
valid IDs per row; graph/prompt audits; and OpenIE passage coverage. A/B
`validation.json` both pass. The frozen LoCoMo vendor manifest passes and
`code/locomo_eval/` is clean. The Hippo offline metric follows the evidence
recall definition without calling or changing the frozen evaluator. There is
no judge prompt, model, rubric, F1 or answer aggregation in this experiment.

Hippo's ten conditions made **13,738 live chat calls**, 12 cache hits, zero
recorded chat errors, **6,299,539 chat input / 508,596 output tokens**.
There were **1,719 embedding requests / 626,126 embedding input tokens**.
These counts include building and retrieval, exclude earlier A/B costs and
the separate 20-turn pilot, and are not a monetary estimate. The sum of ten
per-condition elapsed times is 8,629 seconds; runs overlapped, so this is
not wall-clock project time. Before every full condition, the NER/triple/
fact-filter fixed scaffolds were checked against 5,000 chars. The ten-example
upstream fact-filter prompt was disabled because it exceeded this budget;
the two fixed upstream examples are retained. No component was removed after
the successful pilot because of an observed negative effect.

## Interpretation and limits

EM-Graph B has a stable LoCoMo top-25 retrieval advantage over **this adapted
HippoRAG 2 configuration**. The conversation-cluster analysis does not show a
reliable HippoRAG–A difference. Both methods uniquely recover some evidence.
The observed gap does not identify which Hippo stage caused lower recall:
OpenIE, fact filtering, PageRank, input formatting and model-version
differences remain entangled. The two-example prompt prevents a claim about
unmodified upstream HippoRAG 2. No answer-quality or cross-dataset
generalization result was produced.
