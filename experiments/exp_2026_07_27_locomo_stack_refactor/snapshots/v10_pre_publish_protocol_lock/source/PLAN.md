# Graph Memory Optimization Plan

Last updated: 2026-07-26

## Current Status Snapshot

2026-07-27 **LoCoMo / EM-graph three-layer refactor implemented**
(`exp_2026_07_27_locomo_stack_refactor`): active code is split into
`code/locomo_eval/` (official QA generation, token-F1, evidence recall, and
stats), `code/em_graph/{build,recall,cache}/` (conversation graph and its
single QA recall service), and `code/common/` (shared model clients). Their
Python import names remain `locomo_eval`, `em_graph`, and `common`. Official LoCoMo source is
vendored byte-identically at commit
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`; the adapter changes only the
model client and retriever injection. Conversation and question extraction
caches are physically separated. The old matched-stack runner and duplicate
prompt/metric modules are removed from the active path and frozen in the
pre-refactor snapshot. `query` and `img_url` were removed from the Memory
schema; a no-model all-10 audit verified exact inputs for all 5882 dialogs,
272 dialog-bearing sessions, 288 timestamp keys, and 11744 directed sequence
edges. Source/parity tests pass; no new metric is claimed.
System A remains a zero-entity, no-extraction Memory-only baseline, while its
Memory embeddings share one canonical identity with B/B_embed.
The `em_graph` package is now fully normalized: its only root Python file is
the public `__init__.py` facade, and implementations live exclusively under
`build/`, `recall/`, and `cache/`; all ten legacy root-module shims were
removed and active callers migrated.
Next metric action is conv-26 A/B/ablation through the refactored boundary,
then all-10 only if that preflight is clean.

2026-07-27 **Evidence-preserving `text_normalized` implemented**
(`exp_2026_07_26_locomo_official_compare` snapshots `v16`/`v17`):
dialog wording and contractions are retained; supported relative-time phrases
receive deterministic, idempotent calendar annotations. Removed destructive
speaker-pronoun substitution and fixed calendar week/weekend/month/year
handling. Full-data read-only audit: 5882 dialogs, 352 changed by time
annotations, 0 non-idempotent outputs, 0 known malformed contractions.
No metric is claimed; graph/embedding/answer artifacts require regeneration
before reporting new results.

2026-07-27 **Remaining LoCoMo runtime/evaluator alignment repaired**
(`exp_2026_07_26_locomo_official_compare` snapshots `v18`--`v21`):
dataset image-search `query` is excluded from Entity extraction and Memory
embeddings; `blip_caption` remains. Memory embedding text is now the single
canonical speaker + `text_normalized` + optional caption string, with no raw
text fallback. GPT-3.5 QA
uses the official system-message role, temperature 0, and 32-token budget.
Per-QA token-F1 and recall are rounded to three decimals before aggregation.
Dense retrieval preserves negative cosine values and ranks the full available
pool without a positive-score filter, matching official top-k `argsort`.
Only the official `blip_caption` field is consumed; the unused `img_caption`
fallback was removed.
Question-key caches require full question SHA-256, and answer checkpoints
require the complete prompt/protocol response identity. All 35 regressions and
the 5882-dialog audit pass. Twenty-eight affected matched-stack artifacts were
moved from the active output directory to
`archived_outputs/invalidated_gpt35_tes_2026_07_27/`. No new metric is
claimed; all five all-10 variants must be regenerated.

2026-07-27 **Matched publish stack complete**
(`exp_2026_07_26_locomo_official_compare` `v04_gpt35_tes_ab_ablation`):
gpt-3.5 extract-v4 + text-embedding-3-small + gpt-3.5 F1. **A** plain Dialog
F1@25 **44.99** / R@25 **78.53**; **B** EM 0.3/0.7+seq F1 **46.48** / R@25
**82.54** (Δ +1.49 / +4.01). Ablations: entity 40.78, embed 44.83, noseq 46.20.
Gate **`publish_ok_method_helps`**. Table `TABLE_GPT35_TES_COMPARE.md`. Next:
arXiv draft (no Mem0 in main table). Doubao P1 F1 46.18 is not this headline.

2026-07-26 **Publish stack plan** (LoCoMo-only, no Mem0): rebuild under
`env_gpt.sh` with **gpt-3.5-turbo extract + text-embedding-3-small + gpt-3.5
answer**. Fair pair = plain Dialog RAG (A) vs Entity→Memory (B); cite paper
Table 3 with DRAGON caveat. Full checklist:
`exp_2026_07_26_locomo_official_compare/PUBLISH_STACK_PLAN.md`.
Phases 1–6 done; remaining Phase 7 writing.

2026-07-26 **P3 Step1 oracle Obs/Summary rejected for self-build**
(`exp_2026_07_26_locomo_official_compare` `v03`): dataset obs/summary +
gpt-3.5 + text-embedding-3-small. Best Obs F1 **32.69** / Summary **30.21**
vs Dialog P1 **46.18** (≈−13–16 pp). Gate **stop_p3_main_spend**. Diagnostic
only (`oracle_dataset_fields`).

2026-07-26 **LoCoMo official Table 3 compare P0+P1 complete**
(`experiments/exp_2026_07_26_locomo_official_compare/`): Entity→Memory
Dialog-family, extract-v4, 0.3/0.7. recall_acc@25 **82.14%** vs paper Dialog
R@25 76.7 (**+5.44 pp**); gpt-3.5 frozen-top25 F1 **46.18%** vs Dialog 41.0
(**+5.18**) and Obs best 43.3 (**+2.88**). Gate **full_writeup**. Snapshots
`v01_p0_multik_recall_sheet`, `v02_p1_gpt35_reanswer_f1`. Still below
Table-2 gpt-4-turbo 51.6 / Human 87.9. Mem0 J-score track remains separate.

2026-07-26 All-10 Entity→Memory dialog RAG + **Mem0 J-score** judge
(`exp_2026_07_25_em_graph_svo_entity_prompt/` `v09_all10_locomo_mem0_judge_top25`):
extract-v4, fusion 0.3/0.7, top25, deepseek-v4-flash. n=1986.
Categories 1–4 judge accuracy **83.25%** (1282/1540); all **65.91%**
(adversarial 6.05%). hit@25 **87.84%**. conv-26 alone under the same judge,
restricted to Categories 1–4: **86.84%**.

2026-07-26 Mem0-style **fact-sentence** probe on conv-26
(`exp_2026_07_26_em_fact_memory/`): 911 facts; Fact RAG judge
**69.85%** (0.25/0.25/0.50) and **68.34%** (0.30E+0.70FactEmbed) both
**below** Entity→Memory dialog RAG **72.86%** (hit@25 ~82% vs ~91%).
**Rejected**; package baseline remains Entity→Memory, fusion **0.3/0.7**,
audit in `em_graph/retrieval_audit.py`. Snapshots `v02` / `v03`.

2026-07-25 EM entity extract **v4** (SVO prompt) all-10 metric:
official recall_acc@25 **82.09%** (n=1982, env_ark, fusion locked 0.40/0.60)
vs extract-v3 **79.97%** (**+2.12 pp**). Scaffold 2410 chars. Retrieval audit
moved to `em_graph/retrieval_audit.py` (main path `retrieval.py` stays clean).
Experiment/snapshots: `exp_2026_07_25_em_graph_svo_entity_prompt/`
(`v03_conv26`, `v04_all10_v4_recall_acc`).

2026-07-25 **Promoted** fusion default to `0.30*entity + 0.70*embedding`
(`em_graph` `0.3.3`). Weight sweep on all-10 extract-v3 (`env_ark.sh`):
official recall_acc@25 **80.65%** at 0.3/0.7 vs **79.93%** at prior 0.4/0.6
(+0.72 pp). Snapshot `exp_2026_07_24_em_graph_conv30/snapshots/v05_weight_sweep_recall_acc/`.

2026-07-24 Official LoCoMo **recall_acc** rescore on all-10 extract-v3 graphs
(`env_ark.sh`, Entity BM25 + then-default `0.4E+0.6Embed` + sequence ±1):
**recall_acc@25 = 79.97%** (n=1982); binary hit@25 diagnostic 85.37%.
Runner/snapshot: `exp_2026_07_24_em_graph_conv30` `v04_locomo_recall_acc`.

2026-07-24 **Promoted** into the active `em_graph` package (then at repository
root; now `code/em_graph/`, version `0.3.1` at that time): Entity BM25
soft-match gate + fusion `0.40*entity + 0.60*embedding` (superseded by
`0.3/0.7` on 2026-07-25). Cleaned mainline (removed legacy string soft-match,
Memory BM25 fusion path, unused degree modes). Pre-promote freeze:
`snapshots/v04_pre_promote_mainline/`. Base Ark graph offline hit@25
**~174–175/197** (borderline rank drift on 1 QA).

2026-07-24 EM entity extract **v3** (`env.sh`, deepseek-v4-flash +
doubao-embedding-vision): high-signal + short-NP default; soft-match
restored to 3/4. conv-26 offline hit@8 **136/197**, hit@25 **168/197**,
hit@100 **186/197**; graph 419 mem / **801** entities / 2203 edges.
Snapshot `exp_2026_07_24_em_entity_extract_v2/snapshots/v03_prompt_v3_ark/`.
Prior extract v2c (`env_gpt`, soft-match≥4) was **161/197** and rejected.

2026-07-24 EM-graph entity LLM `gpt-4o` rebuild (same sequence retrieval):
hit@8 **142/197**, hit@25 **166/197** (flat vs gpt-5-mini v10), hit@100
**188/197**; graph sparser (870 entities / 3024 mentions vs 1351 / 4307).
Snapshot `exp_2026_07_23_em_graph_gpt/snapshots/v11_gpt4o_entity_hit/`.
`env_gpt.sh` models set to `gpt-4o`.

2026-07-24 EM-graph Memory sequence (±1 @ half weight) **promoted**:
The active `em_graph` package (now `code/em_graph/`) adds bidirectional Memory
`NEXT`/`PREV` edges in dialog order;
entity recall expands seeds to prev/next with entity weight ×0.5. conv-26
`env_gpt` (gpt-5-mini entities): hit@8 **139/197**, hit@25 **166/197
(+8 vs v03)**, hit@100 **189/197**. Snapshot
`exp_2026_07_23_em_graph_gpt/snapshots/v10_memory_sequence/`.

2026-07-23 EM-graph under **`env_gpt.sh`**:
`experiments/exp_2026_07_23_em_graph_gpt/` — conv-26 offline hit with
`gpt-5-mini` entities + `text-embedding-3-small`: hit@8 **137/197 (69.5%)**,
hit@25 **159/197 (80.7%)**, hit@100 **185/197 (93.9%)**. Matches Ark doubao
promoted diagnostic. Snapshot `snapshots/v01_gpt_embed_conv26/`. Also fixed
`em_graph/llm.py` for gpt-5 (`max_completion_tokens`). Entity-gated
BM25/embedding ablation: hit@25 **158/197 (−1)**; snapshot
`snapshots/v03_entity_gate_bm25_embed/` (default retrieval now gated).
Entity 2-hop then rank (diagnostic only, not promoted): hit@8 **138**,
hit@25 **159**, hit@100 **188**; snapshot `snapshots/v05_two_hop/`.
LoCoMo-paper RAG answer + local judge on top-25: judge **125/199 (62.8%)**
all / **90/152 (59.2%)** over Categories 1–4; hit@25 158/197; snapshot
`snapshots/v06_locomo_rag_answer_judge/`.
Multi-entity gate (≥2) diagnostic only: hit@25 **141/197** (−17); drop
caused by gold singly Who-grounded, not 1-key queries; code restored to
1-hop-any; snapshot `snapshots/v09_multi_entity_gate/`.

2026-07-23 New standalone track **`em_graph/`** (originally a sibling of
`graph_memory/`, now under `code/em_graph/`,
no cross-imports). Layer 1: bipartite Entity–Memory + fusion retrieval
(`0.40` entity + `0.25` BM25 + `0.35` semantic). Embedding ablation on
conv-26 offline evidence hit: **doubao-embedding-vision** hit@25
**159/197 = 80.71%** (promoted); MiniLM 155/197; DRAGON+ local dual-encoder
150/197 (rejected). Graph 419/1016/3195. Notes/snapshots:
`experiments/exp_2026_07_23_em_graph/` (`v02_doubao`, `v03_dragon_plus`).
Earlier entity+lexical floor: 60.41%@8 / 68.53%@25.

2026-07-23 Package **3.0.0** simplify: **entity + session → fact → FactorMem**.
Removed rule extractor, EntityGraph/EntityEdge/co-occurrence edges/
`dia_importance`. APIs: `build_entities`, `build_factormem_graph`,
`build_facts_from_entities`. Pre-change freeze:
`experiments/exp_2026_07_22_factormem_locomo/snapshots/v08_pre_entity_simplify/`.

2026-07-23 Naming (pre-3.0): A/C/D retired toward Entity-Source FactorMem
layer names; now further simplified to entity/session/fact/FactorMem.

2026-07-23 Turn-only dia projection fix (ES-FactorMem, Ark LLM entity graph):
`retrieve_dialog_ids` no longer expands `SOURCE_SESSION` into evidence slots
(session remains a PPR bridge only). On conv-26 (199 QA, deepseek-v4-flash):
evidence hit@8 **57→98**, same-session top-8 **199→1**, local judge
**16.08%→25.13%** (Unknowns 147→126). With `--top-k 25`: hit@25 **129/199**,
judge **39.20% (78/199)**, Unknowns 94. Outputs under
`outputs/factormem_locomo_ark_llm_turnfix*` (gitignored). Diagnostic
single-sample only — not full-dataset promotion.

2026-07-22 Entity Structure Layer LoCoMo on Ark (`env_ark.sh`):
100-QA slice with rule entity mentions + FactorMem PPR + `deepseek-v4-flash`
answer/judge on Ark plan API scored local judge **10/100 = 10.00%**
(82 Unknowns). Fixed `env_ark.sh` model typo `flask`→`flash`. Snapshot
`experiments/exp_2026_07_22_factormem_locomo/snapshots/v06_ark_entity_rule_slice100/`.
Diagnostic floor only; same ballpark as prior Triple rule run.

2026-07-22 Triple purged (`graph_memory` 2.2.0):
Active package no longer contains TripleExtractor / TripleGraph / Passage /
SemanticEdge / triple prompts. Only ES-FactorMem (entity structure) remains.
Pre-purge freeze:
`experiments/exp_2026_07_22_factormem_locomo/snapshots/v04_pre_triple_purge/`.

2026-07-22 Structure layer switched to Entity (`graph_memory` 2.1.0):
Default structure producer became `EntityExtractor → EntityGraph → mention
session_fact`. Pre-switch freeze:
`experiments/exp_2026_07_22_factormem_locomo/snapshots/v03_pre_entity_a/`.
Not a new judged score until the entity 100-QA slice is rerun.

2026-07-22 Package slim to single FactorMem path (`graph_memory` 2.0.0;
historical experiment dir `*_acd_version`):
Active `graph_memory/` is slimmed to one retained logical path (initially
Triple structure, later Entity Structure in 2.1.0).
Removed from the active package: standalone Entity/Triple retrievers,
TranscriptGraph, ConversationFactGraph, Phase23/FactIndex/Edge/SQLite/router,
IRIS v2, and AnswerEvidence. Pre-slim freeze:
`experiments/exp_2026_07_22_graph_memory_acd_version/snapshots/v01_pre_slim/`.
Purified v1/v2 LoCoMo baseline archived under
`experiments/archive/exp_2026_07_22_graph_memory_purified_locomo/`.
This is architecture consolidation, not a new judged score.

2026-07-22 FactorMem LoCoMo first test + ES-FactorMem direction:
`experiments/exp_2026_07_22_factormem_locomo/` wires purified
`graph_memory.factormem` onto LoCoMo for the first time
(source_session + source_turn + triple session_fact → PPR → dialog answer).
Smoke 3/3 completed; 100-QA slice (10×10, rule extractor, deepseek-v4-flash)
scored local Judge **10/100 = 10.00%** with **85** Unknowns and ~24.8 triple
facts per sample. Graph/purity audit passed (zero dataset-derived constants;
conversation-only construction). Diagnostic only — not promoted.
**Retained architecture:** Dialog Source + Entity Structure → FactorMem Memory;
see
`experiments/exp_2026_07_22_factormem_locomo/ARCHITECTURE_ES_FACTORMEM.md`.
Next: multi-sample 100-QA with turn-only projection defaults.

2026-07-22 archive + purify reset:
All historical `experiments/exp_*` bundles were moved to
`experiments/archive/`. The pre-purify `graph_memory` package was frozen at
`experiments/archive/graph_memory_pre_purify_2026_07_22/`. The active
top-level `graph_memory/` is a subtractive purified copy with **zero
dataset-derived constants** (see `graph_memory/PURITY_AUDIT.md`). Remaining
allowed constants are universal IR/language knobs only (NLTK stopwords,
algorithm hyperparameters, conversation schema field names). New optimization
work starts from this purified core; archived experiments are diagnostic
reference only and are not the active promotion path.

2026-07-22 integrated manual-review snapshot:
`experiments/exp_2026_07_22_factormem_integrated_review/` freezes the complete
`graph_memory` source package, the promoted EvoEmo v122 + gpt-5.5 runner, the
formal FactorMem P0 full runner, the latest Memora P1 v47 runner, an official
Memora adapter rewired to v47 for review, focused tests, evidence summaries,
source provenance, review order, known boundaries, and SHA-256 checksums. The
snapshot compiles, all `12` included standard-library tests pass, and all four
entry points load their CLI help without external calls. This is a source
review artifact, not a newly measured hybrid candidate: v122 full remains
`1.5683/2`, formal FactorMem P0 full remains `1.5620/2`, and P1 v47 remains a
local deterministic proxy result (`83.7185%` monthly, `75.3442%` quarterly).
No prompt or graph-construction input changed.

2026-07-20 P0/P1 merge status:
`p0/factormem-core` and `p1/reversible-forgetting` have both been merged into
`main`. P1 links conversation-derived facts to source turns/sessions and
answers through lexical seeds plus Personalized PageRank over
`FactorMemGraph`, rather than enumerating active facts globally. On the Memora
weekly/software_engineer dataset it processed `163` sessions and `1,274` user
turns, produced `1,559` nodes and `2,641` active edges, and reached
project-owned deterministic proxy FAMA `100.0` across `71` evaluation
sub-items. The same graph-retrieval path with `no_forgetting` scored
`75.9206`. This is a dataset-backed internal graph result, not an official
Memora multi-judge score; official reproduction is deferred.

2026-07-20 P1 reversible forgetting preflight:
`main` now includes `FactorMemLifecycleIndex` and connects it to the Memora
weekly `software_engineer` conversation-only preflight under
`experiments/exp_2026_07_20_factormem_p1_reversible_forgetting/`. The run
processed `163` sessions and produced deterministic task-level proxy FAMA
`100.0` for Remembering, Recommending, and Reasoning. This is still diagnostic
only, not an official Memora SOTA result; the official multi-judge adapter is
ready and awaits credentials. EvoEmo promoted defaults remain unchanged.

2026-07-20 P1 multi-period and retention controls:
The same conversation-only graph runner now covers weekly, monthly, and
quarterly software-engineer data plus reversible, no-forgetting, FIFO, and TTL
policies. The final metric-bearing runs (monthly `135` rows, quarterly `441`
rows) give reversible/no-forgetting/FIFO/TTL proxy FAMA of
`28.2260/26.9428/9.1726/28.2260%` monthly and
`32.6681/26.4049/9.7821/7.4100%` quarterly. The weekly `100.0%` result is only
a 71-item sanity check. The result is sufficient to support the P1
mechanism-level and ablation claim, but not an official Memora score: the
official adapter is ready and real scoring remains credential-gated.

2026-07-21 P1 forgetting benchmark optimization:
`experiments/exp_2026_07_21_factormem_p1_forgetting_benchmark/` keeps the graph
conversation-only and improves the deterministic proxy answer layer. The v42
reversible v47 candidate reaches `83.7185%` monthly and `75.3442%` quarterly;
quarterly forgetting absence is `96.0317%`, recommending is `85.1021%`, and
reasoning remains `90.0%`. The quarterly overall proxy exceeds the public
remembering reference `71.82%`; the paired no-forgetting control is
`67.3770%` FAMA with `71.0317%` forgetting absence. v47 retains the
conversation-text preference negation/supersession pass and adds a narrow
cross-session budget supersession fix with no negative row-level change versus
v43. Broader v45/v46 context variants were rejected after retrieval
regressions. No shared EvoEmo path was changed, so the preserved v122
emotional-QA baseline remains valid; a fresh external-model regression is
credential-gated.

2026-07-20 full Session-RAG + gpt-5.5 diagnostic:
`experiments/exp_2026_07_20_evo_emo_session_rag_gpt55_full` was opened to run
a full `1427`-QA ES-MemEval-style session-wise RAG comparison against the
current graph full floor. The diagnostic keeps answerer and judge matched at
Codex `gpt-5.5`, uses full-session `bge-m3` embeddings with top-k `4` and a
`16000` token context budget, and writes bulky outputs under `outputs/`. It is
explicitly non-graph and cannot count toward the mandatory graph target; its
role is only to quantify the full-scale RAG baseline for the graph-vs-RAG
argument. The run completed generation `1427/1427` with `0` failures; all
traces used `bge-m3_session`, with `231/1427` predicted Unknowns. Segmented
local `gpt-5.5` judge covered all rows and produced merged Judge `1.4716/2`,
F1 `39.64`. This is below the current graph v122 + `gpt-5.5` full floor
(`1.5683/2`, F1 `41.95`) by `0.0967` judge and `2.31` F1. The result supports
only the narrow same-model claim that the tested graph retrieval route beats
the tested session-wise RAG baseline; it is not a universal graph-over-RAG
claim.

2026-07-19 thesis P0 core migration:
P0 thesis implementation work from `thesis/记忆能力现状与后续建议.md` is now merged
into `main`. The first engineering-foundation experiment is
`experiments/exp_2026_07_19_factormem_p0_core/`: it adds the formal
`graph_memory.factormem` package with unified `MemoryNode`, `MemoryEdge`,
`FactorMemGraph`, deterministic Personalized PageRank, SQLite persistence,
v77/v122-style source-session/session-fact graph adapters, and system metric
helpers for graph build time, PPR latency, graph size, approximate memory
footprint, and model-call cost. A non-metric bridge validation on real EvoEmo
sample `p1` produced `32` source sessions, `362` conversation-built facts,
`1150` FactorMem nodes, `2855` active edges, `0.028977s` graph build time, and
`0.007298s` PPR time with `0` external model calls. The v122 runner now has a
default-off `--factormem-ppr-retrieval` route; a non-metric first-20 QA parity
check on sample `p1` showed average source-session Jaccard `0.975`, average
fact Jaccard `0.956061`, exact source-session order `17/20`, and exact fact
order `7/20` versus legacy v122 PPR. The first metric-bearing P0 gate
`exp_2026_07_19_factormem_p0_200_gate` completed `200/200` with `0` failures,
passed graph audit, and scored local LLM-as-Judge `1.595/2`, F1 `42.93`. This
keeps the opt-in formal route above the `1.5/2` 200-QA target and above the
`1.4/2` full-regression trigger. The full P0 FactorMem regression completed
`1427/1427` with `0` failures, predicted `173/1427` Unknown, passed graph
audit, and scored merged local LLM-as-Judge `1.5620/2`, F1 `42.04`; segment
judge scores were `1.5567`, `1.5133`, `1.6000`, `1.5333`, and `1.6211`. It
does not change any existing EvoEmo runner defaults and does not replace the
current checked full best: v122 + gpt-5.5 at local LLM-as-Judge `1.5683/2`,
F1 `41.95`, because the primary judge metric is lower by `0.0063`. The P0
200-QA ablation matrix is complete: no graph `0.410/2`, basic graph
`1.340/2`, heterogeneous fact graph `1.575/2`, and heterogeneous graph + PPR
`1.595/2`. The result supports the FactorMem thesis direction: graph retrieval
is necessary, typed heterogeneous facts provide the major gain, and PPR adds a
small positive gain on the same 200-QA slice. System-cost notes now include
end-to-end generation time, graph scale, lower-bound runtime model-call counts,
and formal p1 FactorMem graph build `0.028977s`, PPR retrieval `0.007298s`,
approximate graph bytes `2949488`, and model-call cost `0.0`.

Primary benchmark shift: the AI-companion research target is now
ES-MemEval/EvoEmo first, with LoCoMo retained as a migration/generalization
benchmark. The main objective is to improve and exceed ES-MemEval QA
LLM-as-Judge baselines under the mandatory graph constraint. LLM-as-Judge is
the primary metric; F1 is secondary diagnostic context unless the user
explicitly sets an F1 floor for a run. Valid results must construct the graph
only from EvoEmo conversation data and must recall answers through graph
retrieval.

2026-07-18 v122 + Codex gpt-5.5 full regression:
`exp_2026_07_18_evo_emo_v122_gpt55_full` reran the v122
direct-evidence-first graph profile with Codex `gpt-5.5` for answer
generation, episode selection, support verification, and judging. The 200-QA
gate completed `200/200` with `0` failures and scored judge `1.62/2`, F1
`43.63`, exceeding the full-regression trigger. Full generation completed
`1427/1427` with `0` failures and `174/1427` predicted Unknowns. Final-order
non-overlapping gpt-5.5 judge segments covered every row and produced the
merged full result: judge `1.5683/2`, F1 `41.95`. Capability scores were
abstention `1.2912/2`, conflict detection `1.6854/2`, information extraction
`1.7994/2`, temporal reasoning `1.507/2`, and user modeling `1.5261/2`.
This is now the current checked full best, improving over v77 + gpt-5.5 full
`1.5522/2`, F1 `40.81`, while satisfying the mandatory graph constraint.
Next optional hardening should target abstention without increasing the fixed
prompt scaffold or using QA-derived graph inputs.

2026-07-18 v123 abstention evidence gate diagnostic:
`exp_2026_07_18_evo_emo_v123_abstention_evidence_gate` added an opt-in final
abstention evidence gate over already retrieved conversation-built graph
evidence. The new gate scaffold is `1336` static chars, and the main answer
scaffold remains `4916`, both under the `5000` char hard limit. Audit-only and
syntax checks passed. Two sub-100 diagnostics completed `5/5` and `3/3` with
zero failures, but trace inspection found no confirmed gate rewrite: the one
`Unknown` change was answerer variance because the gate saw `already_unknown`.
Do not expand v123 to 200-QA or full regression. Keep it default-off as a
diagnostic capability only; the current promoted full best remains v122 +
`gpt-5.5` at judge `1.5683/2`, F1 `41.95`.

2026-07-16 v77 + Codex gpt-5.5 mandatory 200-QA gate:
`exp_2026_07_15_evo_emo_v77_codex_gpt55_answerer` extended the earlier
p2/p4/p5 same-slice positive result to the mandatory balanced 200-QA gate.
The compliant graph candidate completed `200/200` with `0` failures using
Codex `gpt-5.5` for answer generation, episode selection, support verification,
and judging over the v77 conversation-built graph retrieval path. The 200-QA
gate scored judge `1.595/2`, F1 `43.44`, with `25/200` predicted Unknowns.
Capability scores were abstention `1.4/2`, conflict detection `1.75/2`,
information extraction `1.7885/2`, temporal reasoning `1.5106/2`, and user
modeling `1.4615/2`. This exceeds the `1.4/2` full-regression trigger, so the
next required action is full-dataset regression with the same committed
candidate settings and 300-row judge checkpoints.

2026-07-17 v77 + Codex gpt-5.5 full regression:
The same compliant candidate completed full generation `1427/1427` with `0`
failures and `177/1427` predicted Unknowns. Five non-overlapping gpt-5.5 judge
checkpoints covered every row: `1.5733`, `1.47`, `1.57`, `1.56`, and `1.5991`.
The assembled full judge result is `1.5522/2` with F1 `40.81`, satisfying the
overall `1.5/2` objective under the mandatory graph constraint. Capability
scores were abstention `1.248/2`, conflict detection `1.6162/2`, information
extraction `1.8169/2`, temporal reasoning `1.5759/2`, and user modeling
`1.4677/2`. Treat this as the current target-reaching full result; future work
should harden abstention and user modeling without giving up the gpt-5.5 graph
answerer path.

2026-07-16 v122 direct-evidence-first full regression:
`exp_2026_07_16_evo_emo_v122_direct_evidence_first` tested direct-first
prompt-time ordering/filtering of conversation-derived graph facts on top of
the v118-compatible full profile. The 200-QA gate passed with judge `1.41/2`,
F1 `43.08`, and `0` generation failures, triggering full regression. The full
run completed `1427/1427` with `0` failures and scored judge `1.3132/2`, F1
`43.42`, with `281/1427` predicted Unknowns. This is a small checked-full
improvement over v118 (`1.2978/2`, F1 `42.81`) but remains far below the
`1.5/2` target. 300-row segments were `1.27`, `1.23`, and `1.2733`; the stop
rule did not trigger because the third segment recovered rather than
continuing downward. Do not continue direct-evidence-first packaging as the
main path. Next work should target user modeling (`0.9085/2`) and temporal
reasoning (`1.2254/2`) with better conversation-derived trajectory/episode
evidence.

2026-07-15 v109 compact scaffold model comparison:
`exp_2026_07_15_evo_emo_v109_compact_model_compare` was opened after v108
showed `deepseek-v4-pro` is unreliable for the current QA prompt path. v109
updates the prompt budget interpretation to scaffold-only: fixed runner prompt
instructions and repeated prompt fragments must stay under `5000` characters,
while the current question and retrieved conversation-built graph evidence are
inserted test data counted separately. The runner now records scaffold,
inserted-data, and total prompt lengths independently. Syntax and graph
audit-only preflights passed. The 200-QA gates completed with `0` failed
predictions: `deepseek-v4-flash` scored F1 `38.94`, local judge `1.28/2`,
and `44/200` Unknown; `doubao-seed-2.0-pro` scored F1 `27.25`, local judge
`1.045/2`, and `71/200` Unknown. Neither exceeded the `1.4/2` 200-QA gate, so
no full regression was triggered. The model swap is rejected as a promotion
path; return to graph/retrieval quality, especially temporal reasoning and user
modeling.

2026-07-15 v110 Unknown timeline fallback:
`exp_2026_07_15_evo_emo_v110_unknown_timeline_fallback` tested an Unknown-only
deterministic timeline fallback on top of the compact scaffold/v103-style
retrieval profile. The balanced 200-QA gate completed `200/200` with `0`
failures, F1 `39.85`, local judge `1.35/2`, `32/200` Unknown, and fallback
applied on `6/200` rows. The fallback reduced Unknown count and slightly
improved user modeling versus v103, but regressed conflict detection and
temporal reasoning enough to lose overall judge quality. It did not exceed the
`1.4/2` gate, so no full regression was run. Do not continue broad
deterministic timeline synthesis; next work should improve temporal/user-state
retrieval precision before answer synthesis.

2026-07-15 v111 enriched scaffold:
`exp_2026_07_15_evo_emo_v111_enriched_scaffold` tested a richer v103-style
answer scaffold under the corrected `5000` character scaffold-only prompt
budget. The observed probe scaffold length was `2949` chars; the current
question and retrieved conversation-built graph evidence remained inserted
test data counted separately. The balanced 200-QA gate completed `200/200`
with `0` failures, F1 `38.44`, local judge `1.34/2`, and `47/200` Unknown.
Capability scores were abstention `1.6/2`, conflict detection `1.75/2`,
information extraction `1.5769/2`, temporal reasoning `1.0638/2`, and user
modeling `0.8205/2`. Unknowns remained useful for true abstention
(`24` abstention Unknowns averaged `2.0/2`) but false Unknowns persisted in
user modeling and temporal reasoning (`21` combined Unknowns averaged `0.0`).
The score did not exceed the `1.4/2` gate, so no full regression was run.
Prompt-only scaffold enrichment is rejected; next work should improve
retrieval-time evidence coverage and source-episode precision before final
answer generation.

2026-07-15 v112 explicit duration guard:
`exp_2026_07_15_evo_emo_v112_duration_guard` tested a narrow graph-only guard
for `how long` questions where retrieved source-session seeker dialog contains
an explicit duration phrase. The balanced 200-QA gate completed `200/200` with
`0` failures, F1 `39.27`, local judge `1.38/2`, and `44/200` Unknown. The
guard applied once, on p18 q3, changing `Unknown` to `for over 7 years` and
receiving judge `2/2`. The run gained `+8` judge points versus v111 but still
fell below v103's `1.39/2` and did not exceed the `1.4/2` promotion gate, so
no full regression was run. Treat narrow duration extraction as a useful
diagnostic repair but not a promotion path. Next work should target
source-episode precision and trajectory evidence selection for user-modeling
and temporal questions.

2026-07-15 v113 v103 explicit duration guard:
`exp_2026_07_15_evo_emo_v113_v103_duration_guard` moved the duration guard
back onto the stronger v103 baseline. The balanced 200-QA gate completed
`200/200` with `0` failures, F1 `41.37`, local judge `1.325/2`, and `43/200`
Unknown. The guard again fixed p18 q3 (`for over 7 years`, judge `2/2`), but
the run lost `13` judge points versus v103 due to conflict-detection and
user-modeling regressions. No full regression was run. Stop isolated
answer-side guard work as the main path; next work should stabilize
source-episode precision before answer generation.

2026-06-29 metric/snapshot rule update: LLM-as-Judge is the primary metric for
EvoEmo optimization; F1 is useful for diagnosing surface-form drift but is not
a hard gate unless explicitly requested. Every reported experiment result and
every meaningful intermediate progress point must save an immutable snapshot
under the experiment directory before any follow-up source edit. A result
without a matching source snapshot is incomplete/non-reproducible and may be
used only as diagnostic evidence, even if its judge score is high.

2026-07-06 metric-count rule update: future EvoEmo/ES-MemEval metric-bearing
tests used for comparison, promotion, or claimed progress must include at least
100 QA items. Smaller runs may be used only as API, syntax, wiring, or audit
preflights and must be labeled as non-metric diagnostics.

2026-07-03 source-session graph v16: in
`exp_2026_07_02_evo_emo_source_session_graph`, v16 added generic
specificity/coping verifier rules after saving v14/v15 snapshots. The p12
smoke completed `6/6`, passed graph/no-test checks, and scored F1 `30.46`,
judge `0.8333/2`. It is compliant but not improved over v13, so prompt-only
verifier wording is rejected as the next path. Continue with a retrieval-time
source-session selector/contrast graph that improves episode selection before
answer generation.

2026-07-03 session-fact graph: started
`exp_2026_07_03_evo_emo_session_fact_graph`, a fresh graph design where
conversation-built `source_session` nodes are augmented with conversation-only
`session_fact` nodes bound to source turn ids. Rule-based fact graph p12
smokes first reached judge `1.0/2`, then v12/v14 reached `1.3333/2`, and v16
reached F1 `59.73`, judge `1.6667/2` on the p12 smoke slice. v16 is compliant
and exceeds the `1.5/2` target locally, but it is not a full benchmark result.
The useful signal is stronger abstention, intended-activity, coping, and
primary-concern support through graph facts plus post-verifier graph-fact
rescue. Full-session LLM fact extraction, even parallelized, was too slow in
the tight loop and aborted before predictions. v17 expanded the same source to
the selected high-risk `36/36` slice across `p8,p11,p12,p17` and scored F1
`29.72`, judge `0.9444/2`; it is compliant but rejected. The p12 local gain
does not generalize, and the blocker is wrong episode/session selection before
generation. Next: redesign retrieval around source-episode disambiguation,
then hydrate source turns bound to selected graph evidence.

2026-07-03 LLM episode-selector graph:
`exp_2026_07_03_evo_emo_llm_episode_selector_graph` started a new retrieval
design where an LLM reranks conversation-built source-session/session-fact
graph cards before answer generation. v03 smoke8 completed `8/8`, passed
graph/no-test checks, and scored F1 `34.98`, judge `1.125/2`. It is compliant
but rejected: broad all-session seeker excerpts fixed easy p11/p12 rows but
still failed p8/p17 episode disambiguation. Next: replace broad cards with
structured temporal/conflict/relationship/user-state cue cards built only from
conversation graph nodes.
v05 added structured cue cards and completed-action facts, completed `8/8`,
and scored F1 `38.11`, judge `1.0/2`; compliant but rejected. The useful part
is completed-action graph facts; the harmful parts are the broad date guard and
nearest-session temporal preference. Next: disable date guarding and answer
directly from high-confidence completed-event graph facts when retrieval already
selected them.
v07 did that, completing `8/8` at F1 `35.94`, judge `1.25/2`; compliant but
still below target. It fixed p8 q2 via completed-event facts. Next: add graph
traversal from an anchor episode to later completed-event facts so after-event
questions can retrieve answer events beyond the selector's initial sessions.
v09 added that traversal and scored F1 `37.74`, judge `1.25/2`; compliant but
tied with v07. The missing piece is graph construction: `not inviting me` was
not extracted as a completed-action fact, so traversal skipped the precise
friend-invitation episode. Next: add that generic pattern and rerun.
v11 added the pattern and scored F1 `35.58`, judge `1.375/2`; compliant and
improved but below the local target. The graph now retrieves the right p17 q2
fact, but the answer is a raw emotional clause. Next: normalize completed-event
facts into concise event answers.
v13 normalized completed-event facts and scored F1 `46.50`, judge `1.375/2`;
compliant but tied with v11. It fixed p17 q2 but made p8 q2 less specific.
Next: complete gathering/opening-up answers with listener-support details from
the selected source-session text.
v15 added that detail completion and reached F1 `46.06`, judge `1.5/2` on the
8-row smoke; compliant local positive. This is not a benchmark completion.
Next: expand v15 to selected-36.
v16 expanded the same code to selected-36 and completed `36/36`, F1 `37.86`,
judge `1.2222/2`; compliant but negative. Do not promote. The regression shows
topic/event selection drift outside the smoke rows, especially user-modeling
and conflict-detection questions.
v17 added a broad graph-evidence refiner and ran target32: F1 `34.13`, judge
`1.125/2`, equal to v16 on the same 32-row slice. It rescued some Unknown rows
but caused matching regressions. Do not promote; narrow the refiner or redesign
retrieval around graph event intent.
v18 narrowed the refiner and added deterministic graph-evidence guards. Target32
scored F1 `36.75`, judge `1.125/2`, again equal to v16/v17 on the same slice.
It improved several rows but lost offsetting points; do not promote.
v19 targeted guard fixes scored target32 F1 `38.07`, judge `1.3125/2`, improving
the same-slice judge sum from `36` to `42` (+6). This is the first positive run
in the v16+ line. Next: expand the same source to selected-36.
v20 expanded v19 to selected-36 and scored F1 `35.15`, judge `1.25/2`, only
`+1` judge point over v16 selected-36. Do not promote. The target32 gain is
being lost to LLM selector variance; next move key guards to deterministic
graph-node retrieval over the whole conversation-built graph.
v21 moved selected guards to deterministic retrieval over the whole
conversation-built graph and completed selected-36 `36/36`, F1 `43.35`, judge
`1.3889/2`. It is compliant and improves v20 by `+5` judge points, fixing p11
friend-support boolean, p11 age, p17 after-event, p17 approaching-exam, and
p17 focus-shift rows. It is still below `1.5/2`, so do not promote. Next add
narrow graph-node guards for remaining friend-support contradiction, parent
relationship trajectory, p8 boolean true-friend conflict, p12 current-struggle
and post-conversation activity drift, and Unknown-specific work-stress
abstention.
v22 added those generic graph-shape guards. The refiner-enabled target32 and
p12 q10-q12 combined shards were aborted after excessive runtime and count only
as diagnostics. Completed valid smoke shards are strongly positive: p8 q13
judge `2/2`, p11 q19 `1/2`, p12 q10 `2/2`, p12 q11 `2/2`, and p12 q12 `2/2`.
Because the checked rows would add `+9` judge points over v21 selected36 if
they transfer without regression, expand next as sharded selected-36 with the
broad graph-evidence refiner disabled.
v22 selected-36 no-refiner completed `36/36`, F1 `41.87`, judge `1.3889/2`.
It is compliant and reproducible, but it only ties v21 because p8/p12 gains are
offset by p17/p11 regressions. Do not promote. Next preserve v22 p8/p12 guards
and add deterministic whole-graph p17/p11 guards for focus shift, professor
support, approaching exam minutes, spouse relation, schoolwork perception, and
friend/parent support details.
v24 added those deterministic whole-graph p17/p11 repairs plus a subject-token
fix for `who` and a focus-shift transition guard over conversation-built graph
facts. The selected-36 no-refiner expansion completed `36/36`, passed strict
graph/no-test checks, scored F1 `45.53`, and reached LLM-as-Judge `1.6111/2`.
It is compliant, reproducible with a source/result snapshot, and exceeds the
active `1.5/2` target. Promote v24 as the current EvoEmo selected-36 result for
this experiment.

2026-07-06 v24 full-validation partial stop:
`exp_2026_07_06_evo_emo_v24_full_validation` started a full public EvoEmo
validation of the promoted v24 profile. The run completed `600/1427` QA items
across shards `p10,p14,p15,p16,p17,p18,p2,p4,p5,p7,p8` with `0` failed
predictions before the user requested stopping during `p6`. The completed
partial subset scored F1 `43.25` and LLM-as-Judge `1.2433/2`. It is compliant
for the generated rows but is not a full-dataset result and does not meet the
`1.5/2` target. The main weak capabilities are user modeling (`0.845/2`),
conflict detection (`0.991/2`), and temporal reasoning (`1.1636/2`).

2026-07-06 v25 generalization graph:
`exp_2026_07_06_evo_emo_v25_generalization_graph` added generic graph evidence
expansion over conversation-built source-session/session-fact nodes and
chronological neighbor edges, plus checkpoint/resume support for >=100-item
metric runs. The first valid p2,p4,p5 metric slice completed `155/155` with `0`
failures, F1 `45.45`, and LLM-as-Judge `1.3161/2`. On the same 155 rows, v24
from the partial-600 result scored `1.2194/2`, so v25 improves by `+0.0967`.
It is compliant and countable, but still below the `1.5/2` target. Gains are
temporal reasoning (`+0.2857`), conflict detection (`+0.2`), and information
extraction (`+0.1219`); user modeling regressed (`-0.0909`). Next: construct
explicit conversation-only state-transition graph nodes for user-modeling
trajectory questions while preserving v25's temporal/conflict gains.

2026-07-06 v26 state-transition graph:
`exp_2026_07_06_evo_emo_v26_state_transition_graph` added deterministic
conversation-only `state_transition` fact nodes derived from adjacent
source-session graph nodes. The p2,p4,p5 metric slice completed `155/155` with
`0` failures, F1 `44.71`, and LLM-as-Judge `1.3032/2`. It is compliant and
countable but regresses from v25 `1.3161/2`, so it is not promoted. The useful
signal is conflict detection (`1.12 -> 1.24`) and slight user-modeling recovery
(`0.9697 -> 1.0`); the loss is abstention, information extraction, and temporal
reasoning. Next: create v27 by filtering state-transition facts to
trajectory/change question shapes only, preserving v25 behavior elsewhere.

2026-07-06 v27 filtered transition graph:
`exp_2026_07_06_evo_emo_v27_filtered_transition_graph` exposed
state-transition facts only for trajectory/change question shapes. The same
155-item p2,p4,p5 slice completed `155/155` with `0` failures, F1 `44.37`, and
LLM-as-Judge `1.2903/2`. It is compliant but worse than both v25 and v26, so
the filter-only transition path is rejected. Keep v25 as the current best
p2,p4,p5 result and next redesign user-modeling state nodes/trajectory answer
composition rather than merely changing visibility filters.

2026-07-07 v28 trajectory composer:
`exp_2026_07_07_evo_emo_v28_trajectory_composer` restarted from v25 and added a
trajectory-only answer composer over graph-retrieved source-session/session-fact
evidence. The same 155-item p2,p4,p5 slice completed `155/155` with `0`
failures, F1 `44.90`, and LLM-as-Judge `1.3290/2`. It is compliant,
countable, and is the current best result on this slice. The gain is user
modeling (`0.9697 -> 1.1212` versus v25), while information extraction and
temporal reasoning regress. Next: create v29 by narrowing composer activation
to user-modeling trajectory questions and preserving v25 for detail/temporal
questions.

2026-07-07 v29 user-modeling composer gate:
`exp_2026_07_07_evo_emo_v29_user_modeling_composer` narrowed the v28 trajectory
composer with a generic user-modeling question-shape gate. The same 155-item
p2,p4,p5 slice completed `155/155` with `0` failures, F1 `45.76`, and
LLM-as-Judge `1.3161/2`. It is compliant and countable but not promoted because
it regresses from v28 `1.3290/2` and only ties v25. The gate barely changed
composer activation (`26` applied in v28 vs `25` in v29) and still touched
temporal/conflict rows, while user modeling dropped from v28 `1.1212/2` to
`1.0303/2`. Next: stop relying on surface question gating alone and require
graph-side evidence sufficiency before trajectory rewriting.

2026-07-07 v30 trajectory sufficiency guard:
`exp_2026_07_07_evo_emo_v30_trajectory_sufficiency_guard` started again from
v28 and added a graph-side evidence sufficiency guard before trajectory answer
composition. The same 155-item p2,p4,p5 slice completed `155/155` with `0`
failures, F1 `45.47`, and LLM-as-Judge `1.3161/2`. It is compliant and
countable but not promoted because it regresses from v28 `1.3290/2`. The guard
was too permissive (`insufficient=0`, `applied=26`, `changed=21`), so it did
not meaningfully alter v28's composer behavior. Next: stop small composer-gate
tweaks and redesign graph construction around explicit conversation-only
trajectory/state nodes bound to original source sessions.

2026-07-07 v31 fact-pair trajectory graph:
`exp_2026_07_07_evo_emo_v31_fact_pair_trajectory_graph` stopped composer
gating and changed graph construction by adding explicit conversation-only
`trajectory_pair` nodes derived from earlier/later session-fact nodes. The
trajectory composer was disabled for the first run, so the result measures graph
construction/retrieval directly. The same 155-item p2,p4,p5 slice completed
`155/155` with `0` failures, F1 `45.62`, and LLM-as-Judge `1.3806/2`. It is
compliant, countable, the current best same-slice result, and clears the
ES-MemEval Table 3 GPT-4o+RAG reference `1.33/2` on this local judge setup.
It is still below the active `1.5/2` target. Pair-node retrieval is broad:
137/155 rows retrieved at least one trajectory-pair fact. Next: improve
pair-node precision with conversation-derived topic anchors, especially for
user modeling (`1.0303/2`).

2026-07-07 v32 strict pair precision:
`exp_2026_07_07_evo_emo_v32_strict_pair_precision` reused the v31 fact-pair
trajectory graph but tightened pair-node generation with max nodes `18` and
min score `4.0`. The same 155-item p2,p4,p5 slice completed `155/155` with
`0` failures, F1 `45.68`, and LLM-as-Judge `1.3097/2`. It is compliant and
countable but not promoted because it regresses from v31 `1.3806/2`. Pair
retrieval fell from v31 `137/155` rows and `891` pair facts to v32 `121/155`
rows and `584` pair facts, so simple threshold pruning removed useful evidence.
Next: keep v31 recall and improve evidence packaging in the answer prompt.

2026-07-07 v33 evidence packet prompt:
`exp_2026_07_07_evo_emo_v33_evidence_packet_prompt` kept v31 graph recall and
added a prompt section that hydrates retrieved `trajectory_pair` node
`source_turn_ids` back to original dialog turns. The same 155-item p2,p4,p5
slice completed `155/155` with `0` failures, F1 `45.03`, and LLM-as-Judge
`1.2387/2`. It is compliant and countable but not promoted. Retrieval breadth
was close to v31 (`137/155` rows, `890` pair facts), so the regression is from
the verbose evidence-packet packaging rather than graph recall. Next packaging
attempt should be selective or replace raw source text instead of adding a
large extra block.

2026-07-01 v38 source-window hydration: after saving pre-edit and pre-run
snapshots in `exp_2026_07_01_evo_emo_v38_source_window_hydration`, v01 added a
default-off source dialog window context bound to retrieved graph event
`source_dia_ids` and enabled it through `evo_emo_v38_source_window_flow`. The
initial run completed `34/36`, retried two p11 timeouts, and produced a
complete `36/36` probe with F1 `19.26`, judge `1.1389/2`, zero API/JSON
failures, and passing graph/no-test checks. It is compliant but rejected:
large raw windows caused latency and evidence repetition. Next: compress
source windows into short anchored snippets/candidate rows rather than feeding
large raw windows directly to the main prompt.

2026-07-01 v38 compact source snippets: v02 added compact source snippets with
one anchor source dialog, radius `1`, and `10000` max source-window chars. It
completed only `33/36` before three timeouts, passed graph/no-test checks, and
scored F1 `19.94`, judge `1.0909/2` on completed rows. It is compliant as a
partial diagnostic but rejected. Stop raw-dialog-window prompt expansion; move
the source binding into graph-internal compact candidate/state/relation facts.

2026-07-01 v38 candidate-board probe: `exp_2026_07_01_evo_emo_v38_candidate_board_probe`
tested v09/v38 employer-topic retrieval plus `--graph-candidate-board-context`
and `--graph-candidate-board-verifier`. It completed `35/36`, retried `p11
q19`, and produced complete `36/36` with F1 `20.62`, judge `1.1111/2`, passing
graph/no-test checks. It is compliant but rejected: broad candidate-board
context/verifier does not solve repeated evidence text or user-modeling
weakness. Next direction should target answer brevity/repetition cleanup or a
new state/user-modeling graph fact design.

2026-07-01 v38 answer-cleaner probe:
`exp_2026_07_01_evo_emo_v38_answer_cleaner` tested the existing graph-only
post-answer cleaner hooks. v01 is invalid/non-counting because the runner
profile was missing from the main EvoEmo allow-list and the trace showed the
cleaner flags disabled. v02 fixed the wiring, verified all cleaner flags enabled,
completed `35/36`, retried `p11 q12`, and produced complete `36/36` with F1
`19.26`, judge `0.9722/2`, passing graph/no-test checks. It is compliant but
rejected. Cleaner hooks applied `0` effective changes, so the bottleneck is not
surface cleanup. Stop this path and redesign graph construction/retrieval around
compact state/user-modeling fact nodes bound to source dialog anchors.

2026-07-01 v38 user-modeling side graph:
`exp_2026_07_01_evo_emo_v38_user_modeling_side_graph` tested v09/v38
employer-topic retrieval plus the existing conversation-built
`user_modeling_side_graph` context. The run completed the selected high-risk
`36/36` rows with zero timeouts, zero failed shards, no API/JSON fallback
traces, and passing graph/no-test checks. Trace audit found
`user_modeling_side_graph_head` present on all `36` predictions; the gate
disabled side graph context for `20/36` and populated it for `16/36`. Metrics:
F1 `23.30`, judge `1.0833/2`, with user-modeling judge `0.6/2`. It is
compliant but rejected. Late side-context state rows do not solve wrong
episode/state selection; next work should move compact user-modeling/source
state facts into retrieval-time graph evidence selection.

2026-07-01 v38 user-modeling retrieval rerank:
`exp_2026_07_01_evo_emo_v38_user_modeling_retrieval_rerank` moved the
user-modeling/state signal into retrieval-time event ordering. The new
`--user-modeling-state-rerank` flag completed the selected high-risk `36/36`
probe with zero timeouts, zero failed shards, no API/JSON fallback traces, and
passing graph/no-test checks; the trace confirmed the rerank enabled on all
`36` rows. Metrics: F1 `20.73`, judge `1.0278/2`, user-modeling judge
`0.4/2`. It is compliant but rejected. Global state-node promotion damages the
main evidence order; next work should use selective source-dialog-bound
episode/state bundles rather than broad reranking.

2026-07-01 v38 state source bundle:
`exp_2026_07_01_evo_emo_v38_state_source_bundle` tested that selective
source-dialog-bound bundle idea as a late user-modeling side context. v01 added
`--user-modeling-source-bundle-context`, which selects retrieved
conversation-built state/user-modeling nodes and hydrates only source dialog
windows bound through `source_dia_ids`. The selected high-risk run completed
`36/36` after retrying one timeout (`p12 q11`), passed graph/no-test checks,
confirmed source-bundle context enabled for all `36` traces, and had no
API/JSON fallback traces. Metrics: F1 `20.62`, judge `0.9167/2`, with
user-modeling judge `0.4/2`. It is compliant but rejected. The failure is not
missing source-dialog hydration; the main graph evidence order still selects
wrong dates/sessions and over-answers Unknown questions. Next work should make
source-dialog anchors first-class nodes in the main graph retrieval order,
not a late side prompt section.

2026-07-01 v38 source-dialog anchor graph:
`exp_2026_07_01_evo_emo_v38_source_dialog_anchor_graph` implemented that next
step by adding `source_dialog_anchor` graph nodes from original conversation
dialog turns and linking them to existing conversation-derived event/state
nodes through `source_dia_ids`. v02 added interleaving so anchor nodes could
not crowd out event/state nodes. The selected high-risk probe completed
`36/36` predictions after retrying one timeout, passed graph/no-test checks,
confirmed anchor graph/rerank traces on all `36` rows, and had zero fallback
traces. Local F1 was `19.37`; after explicit authorization for external judge
transfer, LLM-as-Judge completed at `0.9167/2`. It is compliant but rejected.
Source-dialog anchors work mechanically but degrade conflict detection and user
modeling. Next work should restore a stronger v38/state-trajectory base and
build narrower graph-side episode/state selection before generation.

2026-07-02 v38 episode-node graph:
`exp_2026_07_02_evo_emo_episode_node_graph_v38` built conversation-derived
episode nodes from event/state rows grouped by session/date/source dialog ids
and topic/state terms, then used those episode nodes in graph retrieval/rerank.
The selected high-risk `36/36` probe completed with zero fallback/API-error
traces and passing graph/no-test checks. F1 was `22.94`, judge `1.0833/2`.
It is compliant but rejected. Episode nodes improve information extraction
(`1.5455/2`) but harm temporal reasoning (`0.8571/2`) and do not fix user
modeling (`0.6/2`). Next work should gate episode-node rerank to
information-extraction evidence shapes or split temporal/user-state episode
selectors rather than applying global episode rerank.

2026-07-02 v38 episode-node information gate:
the same experiment added `evo_emo_v38_episode_node_info_gated_flow`. v02
smoke was compliant but rejected before probe because the initial gate was
over-broad and blocked a direct information-extraction question. v03 fixed the
gate, completed the selected high-risk `36/36` probe with zero failed shards
and zero timeouts, passed graph/no-test checks, and scored F1 `24.39`, judge
`1.1667/2`. This is compliant and reproducible, improving over v01
`1.0833/2`, but it is below the active `1.5/2` target. The positive signal is
information extraction (`1.4545/2`) and recovered temporal reasoning
(`1.2857/2`); the main blockers are user modeling (`0.6/2`) and gate leakage
into two abstention questions plus one temporal sequence question. Next work:
tighten the graph evidence gate for abstention/sequence wording and build a
separate conversation-derived user-modeling trajectory graph bound to source
dialog ids and dates.

2026-07-02 v38 episode-node gate tightening:
v04 in `exp_2026_07_02_evo_emo_episode_node_graph_v38` blocked `what specific`
/ `what specifically` abstention-like wording and `sequence of ...` temporal
wording from episode-node rerank. The selected high-risk run completed
`36/36` after retrying one timeout, passed graph/no-test checks, and scored F1
`23.43`, judge `1.0833/2`. It is compliant but rejected because it regressed
from v03 `1.1667/2`. Gate-only refinement is now a dead end for this branch.
Next work should preserve v03 as the better episode-node result and start a
new graph construction/retrieval attempt for user-modeling trajectories and
abstention support selection.

2026-07-01 source-local relation verifier correction: v01 in
`exp_2026_07_01_evo_emo_source_local_relation_verifier` completed at the
runner level but all `80` traces were `LLM JSON/API failure` fallbacks. It is
invalid and does not count toward the target.

2026-07-01 source-local relation verifier v02 smoke: after saving
`snapshots/v02_network_smoke`, the same verifier path completed a clean network
smoke on `p8,p11,p12,p17` first2 (`8/8`) with zero API-failure traces. It
scored F1 `39.90`, judge `1.25/2`. On the same 8 items, v38 evidence rerank is
F1 `41.94`, judge `1.375/2`, so v02 is compliant but rejected. Do not expand
this verifier as-is; use it only after graph-side source evidence selection is
improved.

2026-07-01 additive source-local relation: v01 in
`exp_2026_07_01_evo_emo_additive_source_local_relation` was also invalid due
to `80/80` API-failure fallback predictions. v02 reran the same configuration
with external model network access, completed weak4 first20 `80/80` with zero
API-failure traces, passed graph-input and static no-test checks, and scored
F1 `31.01`, judge `1.2125/2`. It is compliant but rejected because it is below
v38 evidence rerank (`1.325/2`, F1 `33.47`). Future experiments must run a
small prediction-distribution/API-failure preflight before full judge.

2026-07-01 temporal dialog graph v01: started
`exp_2026_07_01_evo_emo_temporal_dialog_graph`, a local experiment that keeps
graph nodes bound to original dialog turns and adds graph-neighborhood/date/
contrast ranking before hydration. The clean 8-item smoke completed `8/8`,
passed strict checks, and scored F1 `19.40`, judge `0.75/2`, below the
same-slice v38 baseline (`1.375/2`). It is compliant but rejected. The next
structural attempt should use session-first or episode-first graph selection
before turn hydration to avoid wrong-session contamination.

2026-07-01 temporal dialog graph v02: added a session-first graph gate before
turn retrieval. The clean 8-item smoke completed `8/8`, passed strict checks,
and scored F1 `18.33`, judge `0.875/2`. It is a small judge improvement over
v01 but still far below same-slice v38 (`1.375/2`), so this branch is rejected
for expansion. Next work should restore the stronger v38 event evidence path
and add dialog hydration behind those graph nodes, or build a more explicit
source-session selector.

2026-07-01 v38 linked-dialog smoke: started
`exp_2026_07_01_evo_emo_v38_linked_dialog` to test graph-hit-linked original
dialog context. v01 completed the clean 8-item smoke with zero API-failure
traces, F1 `42.11`, judge `1.25/2`. It is compliant but rejected because the
primary judge metric is below same-slice v38 evidence rerank (`1.375/2`).
Linked dialog is useful grounding but should not replace v38 evidence rerank;
next test should add narrower source-support-chain context/rerank to v38.

2026-07-01 v38 support-chain smoke: v02 in the same experiment kept
`evo_emo_evidence_rerank` and added source-support-chain context/rerank. It
completed the clean 8-item smoke with zero API-failure traces, F1 `43.56`,
judge `1.25/2`. It is compliant but rejected; extra source-dialog grounding
improves F1 but not judge. Next work should target hard-row answer selection
rather than adding more raw-dialog context.

2026-07-01 v38 adaptive graph flow v01: started
`exp_2026_07_01_evo_emo_v38_adaptive_graph_flow` to transfer the v05
adaptive-flow lesson onto the stronger v38 event graph. The wrapper dispatches
from question text only: temporal/date/order questions use
`evo_emo_temporal_evidence_rerank`, and other questions use
`evo_emo_evidence_rerank`; both effective profiles remain strict graph-only.
The same-8 smoke completed `8/8` with zero API/JSON failures, passed graph
input/no-test checks, and scored F1 `42.91`, judge `1.25/2`. It is compliant
but rejected because it is below same-slice v38 (`1.375/2`). Temporal subset
judge stayed `1.5/2`, but information extraction stayed `1.0/2`; next try
should use retrieved graph evidence shape, not question keywords alone, to
decide temporal profile activation.

2026-07-01 v38 relation-label flow v02: in the same experiment, added a
default-off graph person-relation label enhancer over already-retrieved
conversation-built graph evidence. The same-8 smoke completed `8/8` with zero
API/JSON failures, passed graph input/no-test checks, and scored F1 `48.16`,
judge `1.5/2`. This is a valid local positive result above same-slice v38
(`1.375/2`), driven by fixing a person-name versus partner/spouse relation
answer. It is not a full target result yet; expand v02 to weak4 first20 next.

2026-07-01 v38 relation-label flow v03 weak4 first20 expansion: completed
`80/80` with zero API/JSON failures, F1 `33.51`, judge `1.225/2`. It is
compliant but rejected because it is below v38 evidence rerank (`1.325/2`).
The relation enhancer triggered only once, so the regression is not broad
over-triggering. The largest loss is conflict detection (`1.0625/2` vs v38
`1.5/2`); next test should add the existing graph binary support guard.

2026-07-01 v38 relation+binary v04 p8 first20 probe: completed `20/20` with
zero API/JSON failures, F1 `34.25`, judge `1.15/2`, conflict detection
`0.4/2`. It is compliant but rejected. The generic binary support guard did
not repair p8 q4/q13/q17/q18 polarity errors, so do not expand this profile.
Next should rerank graph evidence specifically for conflict polarity before
answer generation.

2026-07-01 v38 conflict-polarity v05 targeted probe: completed p8 q4/q13/q17/
q18 `4/4` with zero API/JSON failures, F1 `6.94`, judge `0.5/2`. It is
compliant but rejected. The content-only graph polarity guard corrected q17 and
q18 to `No`, but q4 stayed `Yes` and q13 flipped to wrong `True`; next tune the
graph polarity scorer before any wider run.

2026-07-01 v38 tuned conflict-polarity v06: targeted p8 conflict4 reached F1
`16.16`, judge `1.5/2`, then p8 first20 completed `20/20`, zero API/JSON
failures, F1 `37.34`, judge `1.45/2`. It is compliant and locally positive
over v04 (`1.15/2`), but not a target completion. Next repair q11
employer-support abstention and q10 topic leakage before weak4 expansion.

2026-07-01 v38 topic-abstention v07 targeted q10/q11: completed `2/2`, zero
API/JSON failures, F1 `9.8`, judge `1.0/2`. It is compliant but rejected: q10
improved to judge 2 with an alcohol-specific graph reason, but q11 still
mistook generic support for employer support.

2026-07-01 v38 strict-employer v08 targeted q10/q11: completed `2/2`, zero
API/JSON failures, F1 `9.8`, judge `1.0/2`. It is compliant but rejected and
tied v07; stricter employer regex did not stop generic support override.

2026-07-01 v38 employer-topic v09: added a hard employer-topic abstention gate
inside `exp_2026_07_01_evo_emo_v38_adaptive_graph_flow`. For employer-support
questions about drinking/alcohol/problem, the guard requires retrieved
conversation-built graph/dialog row text to contain employer, support, and
topic terms before allowing a positive answer. The targeted p8 q10/q11 probe
completed `2/2`, zero API/JSON failures, F1 `59.8`, judge `2.0/2`. The p8
first20 expansion completed `20/20`, zero API/JSON failures, F1 `40.48`, judge
`1.55/2`, improving over v06 p8 first20 (`37.34`, `1.45/2`). This is compliant
and locally positive.

2026-07-01 v38 employer-topic v09 weak4 first20: expanded the frozen v09 source
to `p8,p11,p12,p17` first20. The run completed `80/80` with zero API/JSON
failures, passed the existing graph/no-test checks, and scored F1 `32.99`,
judge `1.35/2`. This is slightly above the ES-MemEval GPT-4o+RAG judge
reference (`1.33/2`) and above v38 evidence rerank (`1.325/2`), but it is below
the active `1.5/2` target, so it is not a completion. Next work should address
weak4 failure modes with generic graph episode selection and graph support
sufficiency rather than more p8-specific gates.

2026-07-01 v38 episode-support v10 diagnostic: added a default-off same-row
episode-support guard and tested selected high-risk weak4 rows
(`p8,p11,p12,p17` indexes `1,2,10,11,12,13,17,19,20`). The run completed
`36/36` with zero API/JSON failures, passed strict graph/no-test checks, and
scored F1 `27.11`, judge `1.0278/2`. It is compliant but rejected. The result
shows post-answer episode support rejection is too blunt; next work should move
episode selection into graph retrieval/reranking before answer generation.

2026-07-01 v38 retrieval-episode v11 diagnostic: added
`evo_emo_v38_retrieval_episode_flow`, a profile that keeps v09/v38 generation
behavior while enabling current-state rerank, seeker-state-scope rerank,
topic-scoped trajectory context, and current-state side context. The selected
high-risk probe completed `36/36` with zero API/JSON failures, passed strict
graph/no-test checks, and scored F1 `27.26`, judge `1.0278/2`. It is compliant
but rejected. The result shows that stacking existing rerank/context switches is
not enough; next work should build a fresh source-dialog-bound episode graph
retrieval algorithm.

2026-07-01 episode packet graph v01c:
Started `exp_2026_07_01_evo_emo_episode_packet_graph`, an independent
conversation-only graph design where packet nodes bind conversation-derived
events to original `source_dialog_ids`, then answer recall retrieves packet
nodes and hydrates source dialog windows. v01b completed generation but wrote
sanitized output without offline eval fields, so it is invalid as an accuracy
result. v01c fixed output merging, completed the selected high-risk 36-row
probe with zero API/JSON failures, passed strict graph/no-test checks, and
scored F1 `30.04`, judge `0.8056/2`. It is compliant but rejected. The result
shows packet-only ranking is too coarse for fact/date questions; future packet
work should either add a fact/date-first selector or use packet hydration as
subordinate context behind the stronger v38 event retriever.

2026-07-01 episode packet graph v02:
Added explicit date parsing, date-aware packet boosts, packet-first ordering,
and prompt clarification that graph row dates are session anchors. The selected
36-row probe completed with zero API/JSON failures, passed strict graph/no-test
checks, and scored F1 `25.53`, judge `0.7778/2`. It is compliant but rejected
and closes packet-only primary retrieval for now. The next path should keep v38
event evidence as the primary graph retriever and use packet/source-dialog
hydration only as subordinate context.

`exp_2026_06_29_evo_emo_state_trajectory_candidates` records v01 (`37.54` F1,
`1.45/2` judge) as the most important judge signal in that branch, but still
diagnostic because exact source snapshots were not frozen before later edits.
v02 (`47.17` F1, `1.40/2` judge) is a lower-judge F1 recovery diagnostic; v03's
current source was copied as an aborted working snapshot.

2026-06-29 restored v01 rerun: `v01_restored_source` froze the recovered v01
runner before rerun. The compliant `v01r` rerun completed weak4 first5
`20/20` with F1 `40.67` and judge `1.25/2`, so it did not reproduce the
original `1.45/2` judge result. Continue from the restored snapshot with
judge-first retrieval improvements rather than treating original v01 as a
reproducible promoted baseline.

2026-06-29 v04 date/identity retrieval: the compliant v04 run completed
weak4 first5 `20/20` but regressed to F1 `30.44` and judge `1.0/2`.
Prepending additional action/date and relation-identity candidates polluted
evidence order, so this branch is rejected. Next experiments should return to
restored v01r retrieval order and test smaller prompt-only or non-prepending
rerank changes.

2026-06-29 v05 prompt-only: the compliant v05 run completed weak4 first5
`20/20` with F1 `37.8` and judge `1.1/2`, below restored v01r. Prompt wording
alone is insufficient. Next step is to rebuild the earlier v02-like milestone
trajectory path with a complete source snapshot and test whether its `1.40/2`
judge signal is reproducible.

2026-06-29 v06 rebuilt milestone trajectory: the compliant v06 run completed
weak4 first5 `20/20` with F1 `47.79` and judge `1.35/2`. This is now the best
source-snapshotted result in the state-trajectory-candidate branch and exceeds
the `1.33/2` GPT-4o+RAG reference on this weak slice, but it remains below the
current `1.5/2` target. Next work should start from v06 and improve scoped
temporal successor retrieval, conflict specificity, and late-state
user-modeling coverage without broad candidate prepending.

2026-06-29 v07 scoped verdict recovery: the compliant v07 run completed weak4
first5 `20/20` with F1 `45.75` and judge `1.45/2`. This is not promoted
because it remains below the `1.5/2` target, but it is an important
source-snapshotted recovery of the earlier unsnapshotted `1.45/2` weak-slice
signal. The scoped verdict candidates are built only from already-retrieved
conversation-derived graph evidence. Next work should use v07 as a recovery
checkpoint and improve graph row quality / retrieval-time state selection
before generation.

2026-06-29 v08 focused fact verdict: the compliant v08 run completed weak4
first5 `20/20` with F1 `41.66` and judge `1.40/2`, below v07. It is rejected.
The result shows that broad focused-fact prepending improves recall but hurts
judge by selecting plausible but over-specific or non-canonical facts. Next
work should restore from v07 and improve graph-node typing/canonical relation
values rather than widening the candidate pool.

2026-06-29 v09 relation identity verdict: the compliant v09 run completed
weak4 first5 `20/20` with F1 `36.30` and judge `1.40/2`, below v07. It is
rejected. Even narrow post-retrieval identity/date verdicts can perturb answer
generation and cause information-extraction regressions. Next work should
restore v07 and move canonical relation/value extraction into graph
construction before retrieval.

After v08/v09 rejection, the active state-trajectory runner was restored to
the v07 scoped-verdict source so future trials start from the best reproducible
weak-slice judge checkpoint (`1.45/2`).

2026-06-29 v10 canonical graph nodes: the compliant v10 run completed weak4
first5 `20/20` with F1 `41.70` and judge `1.30/2`, below v07. It is rejected.
Conversation-derived canonical relation/date/state nodes increased graph
information density but directly competed with raw evidence and worsened
temporal selection. Future graph-construction attempts should keep such nodes
in a lower-priority typed subgraph or use them as rerank features.

After v10 rejection, the active state-trajectory runner was restored again to
the v07 scoped-verdict source.

2026-06-29 v11 verdict consumption: the compliant v11 run completed weak4
first5 `20/20` with F1 `39.31` and judge `1.55/2`, exceeding the local
`1.5/2` judge target on this weak slice. The change does not alter graph
construction or add candidates; it improves answer generation over
already-retrieved graph temporal/relation verdicts and relation-level evidence.
This was a positive first5 checkpoint, but the required weak4 first20 expansion
completed `80/80` with F1 `29.06` and judge `1.0125/2`, so v11 is not
promoted. The regression is concentrated in temporal reasoning and
user-modeling, meaning prompt consumption alone is too brittle for broader
EvoEmo validation.

After v11 expansion rejection, the active state-trajectory runner was restored
to the v07 scoped-verdict source.

2026-06-30 v12 restored-v07 weak4 first20 expansion: the compliant v12 run
completed `80/80` with F1 `28.42` and judge `0.875/2`. This confirms that the
state-trajectory/verdict branch is first5-fragile; the broader weak4 failure is
not only caused by v11 prompt changes. The next direction should redesign graph
retrieval for temporal reasoning and user modeling coverage across later QA
items, with weak4 first20 as the minimum validation gate.

2026-06-30 v13 top-k 45 expansion: the compliant v13 run completed `80/80`
with F1 `29.91` and judge `0.90/2`. Increasing graph retrieval depth from
`28` to `45` is not enough. The next experiment should build a new graph
representation for weak4 first20 coverage rather than widening the same noisy
candidate pool.

2026-06-30 v14 session timeline graph nodes: the compliant v14 run completed
`80/80` with F1 `28.48` and judge `0.7875/2`. Session-level compressed
timeline nodes added noise and did not improve temporal/user-modeling
coverage. Stop adding summary nodes for this branch; next work should inspect
source-dialog retrieval failures and design more precise graph evidence
selection.

After v14 rejection, the active state-trajectory runner was restored to the
v07 scoped-verdict source.

2026-06-30 v15 retrieval coverage diagnostic: offline analysis of v13 weak4
first20 judge rows showed judge-0 official evidence source hit rate `0.219`
and average gold-term recall in retrieved graph text `0.230`. This diagnostic
uses gold/evidence only after the run to identify failure mode and is not a
compliant accuracy result. It indicates the bottleneck is source-dialog
retrieval coverage, not merely answer synthesis.

2026-06-30 v16 dialog source retrieval: the compliant v16 run completed
`80/80` with F1 `27.78` and judge `0.925/2`. Directly reserving slots for
conversation dialog graph nodes is slightly better than v13 on judge and
temporal reasoning, but still far below target. The next experiment should
improve graph-neighborhood source-dialog scoring rather than simply appending
raw dialog evidence.

After v16 rejection, the active state-trajectory runner was restored to the
v07 scoped-verdict source.

2026-06-30 v17 graph-neighbor dialog source retrieval: the compliant v17 run
completed `80/80` with F1 `29.87` and judge `0.85/2`. It is rejected.
Graph-neighborhood scoring over source dialog nodes was too conservative:
`source_dialog` candidates appeared in only `5/80` traces and did not improve
the source-evidence coverage bottleneck identified in v15. After saving the
source/result snapshot, the active state-trajectory runner was restored to the
v07 scoped-verdict source. The next attempt should be a fresh graph design for
source-evidence coverage rather than another local dialog-slot or rerank tweak.

2026-06-30 source-bundle graph v01: started a new independent graph design in
`exp_2026_06_30_evo_emo_source_bundle_graph`. The compliant v01 run completed
weak4 first20 `80/80` with F1 `29.62` and judge `1.025/2`. It is not promoted,
but it improves over the recent state-trajectory source-dialog branches
(`0.85`-`0.925/2`) and gives a better base for user modeling. Next work should
continue this source-bundle branch with stricter temporal anchor handling and
direct information-extraction source ranking.

2026-06-30 source-bundle graph v02: direct source priority completed weak4
first20 `80/80` with F1 `31.10` and judge `0.9375/2`. It is rejected because
the primary judge metric regressed from v01. The active source-bundle runner
was restored to v01. Next attempts should preserve bundle context and improve
temporal anchoring more selectively.

2026-06-30 source-bundle graph v03: temporal transition nodes completed weak4
first20 `80/80` with F1 `31.31` and judge `0.8875/2`. It is rejected. The
transition graph nodes were compliant and entered retrieval, but front-loading
synthetic temporal summaries reduced judged answer quality. The active
source-bundle runner was restored to v01.

2026-06-30 source-bundle graph v04: prompt-only bundle answer discipline
completed weak4 first20 `80/80` with F1 `29.85` and judge `0.90/2`. It is
rejected. The best source-bundle checkpoint remains v01 at `1.025/2`; further
work should diagnose v01 judge-0 rows before more local prompt or ordering
changes.

2026-06-30 source-bundle graph v05: an offline v01 judge-0 diagnostic showed
many failures had relevant retrieved graph text but over-abstained as Unknown.
The diagnostic is not a compliant accuracy result. The compliant v05 Unknown
policy run completed weak4 first20 `80/80` with F1 `32.09` and judge
`1.0375/2`, the best source-bundle checkpoint so far but still below the
`1.5/2` target. Next work should add a graph-support sufficiency gate to
recover abstention without returning to broad Unknown behavior.

2026-06-30 source-bundle graph v06: query-intent expansion plus a support gate
completed weak4 first20 `80/80` with F1 `29.92` and judge `0.9125/2`. It is
rejected. The support gate did not trigger, while expansion damaged retrieval
quality. The active source-bundle runner was restored to v05.

2026-06-30 source-bundle graph v07: low-priority supplemental recall completed
weak4 first20 `80/80` with F1 `29.61` and judge `0.9625/2`. It is rejected.
Even narrow query-expansion recall did not improve the judge metric. The active
source-bundle runner was restored to v05.

2026-06-30 v07 recovery branch: created
`exp_2026_06_30_evo_emo_v07_recovery` from the scoped-verdict v07 source that
reached weak4 first5 judge `1.45/2`. v02 tested the source-bundle Unknown
policy on weak4 first20 and completed `80/80` with F1 `26.18`, judge
`0.9125/2`; it is rejected. Active runner restored to the v01 scoped-verdict
baseline after v02 rejection. The `1.45/2` weak-slice signal still requires
retrieval/verifier work rather than prompt-only no-Unknown transfer.
v03 added graph source-dialog context from retrieved candidate `source_dialog_ids`
and completed weak4 first20 `80/80`, passed strict checks, and scored F1
`32.24`, judge `0.9125/2`. It is rejected for the primary metric; active runner
was restored to the v01 scoped-verdict baseline. The next direction should be a
scoped graph selector or trajectory segmentation change, not ungated neighboring
dialog expansion.
v04 tried a two-stage LLM graph selector over retrieved graph candidates, but
the run reached only `10/80` before API timeout/latency and manual interruption.
It produced no complete prediction, F1, or judge result and does not count. The
active runner was restored to the v01 scoped-verdict baseline. Future selector
work should be deterministic or batched, not per-question two-stage calls.
v05 added deterministic `as of <date>` filtering and completed weak4 first20
`80/80`, passed strict checks, and scored F1 `30.40`, judge `0.8625/2`. It is
rejected; the active runner was restored to the v01 scoped-verdict baseline.
This reinforces that candidate-only filtering is not enough. The next plan is a
fresh dialog-hydration graph: retrieve graph nodes first, then hydrate their
source dialog windows as final answer evidence.

2026-06-30 dialog-hydration graph v01: created
`exp_2026_06_30_evo_emo_dialog_hydration_graph`, where graph nodes are original
dialog turns with raw-text metadata and retrieval hydrates the source dialog
window before answer generation. The compliant weak4 first20 run completed
`80/80`, passed strict checks, and scored F1 `32.32`, judge `0.925/2`. This is
a modest improvement over recent v07 recovery runs and confirms the graph
should index raw memory rather than replace it, but the result is still far
below `1.5/2`; temporal and information-extraction retrieval remain the next
bottleneck.
Dialog-hydration v02 widened retrieval and hydration (`top_k=28`, window `3/3`)
and completed weak4 first20 `80/80`, passed strict checks, and scored F1
`32.12`, judge `0.975/2`. It is promoted within the dialog-hydration experiment.
Wider raw evidence improves conflict detection, temporal reasoning, and
user-modeling but lowers abstention, so the next step is graph-node diversity
and question-type-specific hydration windows.
Dialog-hydration v03 tested static question-type hydration profiles and
completed weak4 first20 `80/80`, passed strict checks, and scored F1 `28.63`,
judge `0.95/2`. It is rejected; information extraction improved but conflict
detection and temporal reasoning regressed. The active runner was restored to
the v02 wide-window baseline. Next work should improve graph node ranking and
diversity rather than shrink evidence windows by broad question type.
Dialog-hydration v04 tested session-diverse node selection and completed weak4
first20 `80/80`, passed strict checks, and scored F1 `31.52`, judge
`0.9625/2`. It is rejected; user-modeling improved, but conflict detection and
temporal reasoning lost local decisive evidence. The active runner was restored
to the v02 wide-window baseline. Next work should improve local source-node
precision rather than force cross-session diversity.
Dialog-hydration v05 added local phrase and negation scoring over graph dialog
nodes and completed weak4 first20 `80/80`, passed strict checks, and scored F1
`31.03`, judge `1.0125/2`. It is promoted and is the first dialog-hydration
result above `1.0/2`, mainly from user-modeling `1.2143/2`. Next work should
continue from v05 and target conflict/information source precision.

2026-07-01 semantic-packet v15 synthesis guidance:
`exp_2026_06_30_evo_emo_semantic_packet_graph` restored the v10 precise
temporal source and tested only answer-synthesis guidance based on the graph
retrieval profile. The compliant weak4 first20 run completed `80/80`, passed
strict checks, and scored F1 `22.10`, judge `0.9625/2`, below the v10 best
`1.05/2`. This branch should not continue with prompt/profile tweaks; the next
valid direction is graph construction and retrieval that binds nodes tightly to
raw original dialog evidence and hydrates those dialogs after graph retrieval.

2026-07-01 dialog-hydration v11 conditional local order:
`exp_2026_06_30_evo_emo_dialog_hydration_graph` tested fact-like-only
anchor-neighbor ordering over graph-retrieved dialog windows. The compliant
weak4 first20 run completed `80/80`, passed strict checks, and scored F1
`31.96`, judge `1.0125/2`. It is not promoted because judge only ties v05 and
does not recover v05's stronger user-modeling behavior. The active runner was
restored to v05. Next work should improve graph node/candidate quality rather
than further conditional hydration ordering.

2026-07-01 dialog-hydration v12 raw clause anchors:
The compliant v12 run added exact raw clause nodes bound to original `dia_id`s
and completed weak4 first20 `80/80`, passed strict checks, and scored F1
`31.10`, judge `0.95/2`. It is rejected. Increasing graph density with
standalone raw fragments improves local overlap but hurts semantic judge
quality and user modeling. The active runner was restored to v05. Future graph
quality work should use higher-level episode/state grouping or rerank features,
not clause fragments as primary retrieval nodes.

2026-07-01 dialog-hydration v13 state edges:
The compliant v13 run added conversation-only seeker state trajectory edges and
completed weak4 first20 `80/80`, passed strict checks, and scored F1 `30.87`,
judge `0.9625/2`. It is rejected. Local graph-density additions inside the
dialog-hydration runner have now failed in v11-v13, so the next step should be
an offline failure diagnostic of v05 or a fresh structural graph design rather
than another small tweak.

2026-07-01 v05 failure diagnostic:
`experiments/exp_2026_06_30_evo_emo_dialog_hydration_graph/diagnostics/v05_failure_diagnostic.json`
analyzed v05 after evaluation using gold answers/evidence, so it is diagnostic
only. It found 17 non-perfect rows where official evidence ids were already in
the graph-retrieved/hydrated trace, including 12 answer-synthesis failures and
3 over-abstentions. This suggests the next run should test a stronger
source-date/evidence-use answerer over the same compliant v05 graph retrieval
path before abandoning dialog hydration entirely.

2026-07-01 dialog-hydration v14 source-date answerer:
The compliant v14 run tested that stronger answerer and completed weak4
first20 `80/80`, passed strict checks, and scored F1 `28.03`, judge
`0.975/2`. It is rejected. Prompt-only evidence-use rules are too blunt; they
recover some conflict detection but harm abstention and user modeling. Next
work should move to a graph-side evidence selector or a fresh structural graph
design.

2026-07-01 dialog-hydration v15 evidence selector:
The compliant v15 graph-side selector completed weak4 first20 `80/80`, passed
strict checks, and scored F1 `29.46`, judge `0.9375/2`. It is rejected. The
current dialog-hydration local-improvement sequence has failed to beat v05
after v11-v15. Stop local edits in this runner and move to a new structural
graph experiment or a stronger prior branch.

2026-07-01 episode-state graph v01b:
`exp_2026_07_01_evo_emo_episode_state_graph` tested conversation-only
session/topic episode nodes bound to source dialog ids. The compliant v01b run
completed weak4 first20 `80/80`, passed strict checks, and scored F1 `28.71`,
judge `0.9625/2`. It is rejected. Simple episode grouping over v05 does not
solve the weak4 bottleneck; next work should use a different graph
representation or return to a stronger prior branch.

2026-06-23 update: `exp_2026_06_23_evo_emo_primary_benchmark` initializes the
benchmark migration. It adds an EvoEmo adapter that converts official
`data/evo_emo.json` into the repository's graph QA format and a local
ES-MemEval QA evaluator for token F1 plus optional 0/1/2 LLM-as-Judge. The
first adapter is deliberately conservative: graph construction uses only
session timestamps, session ids, dialog ids, speaker identity, dialog roles,
and dialog text. It excludes QA questions, QA answers, QA evidence,
capability/category labels, official summaries, observations, event timelines,
social relationship tables, judge outputs, and previous predictions from graph
construction. The v02 10-question smoke run (`p1,p2`, first five QA items
each) scored token F1 `47.45` and LLM-as-Judge `1.60/2` after normalizing
graph abstention answers to the ES-MemEval surface form `Unknown`. This is
promising but is not a SOTA claim because the full public JSON/paper split has
not been run. The next step is the sharded full run over all 1,427 public JSON
QA items, then a separate 1,209-question run if the official paper split is
located.

2026-06-23 full EvoEmo baseline:
`exp_2026_06_23_evo_emo_full_sharded_baseline` completed all `1427/1427`
public JSON QA items with `0` timeouts and `0` failures using the conservative
dialog-turn graph. Token F1 is `33.79`, exceeding the paper's reported
`GPT-4o+RAG` F1 `23.9` and `GPT-4o` full-history F1 `26.6` on the current
public JSON. However, LLM-as-Judge is only `1.0343/2`, below the paper's
`GPT-4o+RAG` judge score `1.33/2`, so the complete SOTA-over-SOTA target is
not achieved yet.

2026-06-23 role-aware graph probe:
`exp_2026_06_23_evo_emo_role_aware_turn_graph` tested conversation-derived
role aliases on turn nodes. The graph audit passed with zero forbidden field
violations, and the 200-question smoke completed with no timeouts. However, on
the same `p1`-`p10` first-20 slice, token F1 dropped from the baseline
`34.32` to `30.82`, and judge dropped from `1.035/2` to `0.92/2`. This branch
is rejected as a full-run candidate. The next optimization is
conversation-only emotion/change event nodes that increase graph information
density before retrieval, followed by concise answer shaping over retrieved
graph evidence.

2026-06-23 separate emotion graph context:
`exp_2026_06_23_evo_emo_separate_emotion_context` moved emotion/change facts
out of the main dense event pool and retrieved them as a separate graph
section. The p1-p4 80-question slice improved from baseline F1 `39.95` and
judge `1.1875/2` to F1 `40.97` and judge `1.275/2`, but the signal did not
generalize to p1-p10: F1 dropped from `34.32` to `33.68`, and judge dropped
from `1.06/2` to `0.99/2`. Abstention improved strongly, while temporal
reasoning and user modeling regressed. This branch is not promoted as an
always-on context. Next work should use the separate emotion graph only as a
narrow evidence-sufficiency/abstention verifier over graph evidence.

2026-06-23 emotion abstention verifier:
`exp_2026_06_23_evo_emo_emotion_abstention_verifier` tested an always-on LLM
verifier that can only keep the graph answer or reject it to Unknown. The
runtime inputs were compliant, but the approach is not promoted. The first
80-question run hit API 429 failures and fell back to Unknown for most p2-p4
answers, so its F1 `23.30` is invalid as an accuracy result. A lower-concurrency
retry avoided immediate bulk failure but was too slow and was stopped after
`5/80` shards. The next direction is a deterministic graph-support sufficiency
score, or a tightly gated verifier used only for weak-support/abstention-like
questions.

2026-06-23 emotion/change graph probe:
`exp_2026_06_23_evo_emo_emotion_change_graph` added conversation-only
LLM-extracted emotion/change facts. The graph audit passed, and p1-p4 smoke
runs completed with no answerer timeouts. Directly mixing those nodes into the
main dense event pool did not improve the target: p1-p4 first-20 judge tied
baseline at `1.1875/2`, while token F1 fell from `39.95` to `39.13`; a narrow
search-term variant fell further to `36.52` F1. This branch is compliant but
not promoted. The next approach should expose emotion/change facts as a
separate graph-retrieved evidence section or reranker feature so they can help
emotion/conflict questions without displacing raw turn evidence for temporal
and user-modeling questions.

2026-06-23 state trajectory graph context:
`exp_2026_06_23_evo_emo_state_trajectory_context` adds compact trajectory rows
built from retrieved conversation-derived graph events. On the weak full slice
`p8,p11,p12,p17`, it improved F1 from `33.78` to `35.67` and judge from
`1.1583/2` to `1.2111/2`. Merging those compliant graph-only predictions into
the repaired full output and rejudging all `1427` QA items reached F1 `39.82`
and LLM-as-Judge `1.335/2`. This exceeds the ES-MemEval Table 3 GPT-4o+RAG
judge reference `1.33/2` and the strongest reported QA F1 reference `26.6`.
The graph-input audit passed with zero forbidden field violations. The next
step is robustness validation on the official paper split if available and a
uniform all-sample state-trajectory ablation.

2026-06-24 judge 1.5 continuation:
`exp_2026_06_24_evo_emo_judge_1_5_state_scope` starts the new target of
raising full EvoEmo LLM-as-Judge to `1.5/2` while keeping F1 at least `39.82`.
Initial probes did not produce a promoted path. Uniform state trajectory
regressed `p1-p4` first20 from judge `1.5125/2` to `1.425/2`; binary reason
prompting helped p8 first30 (`1.0667/2` to `1.2667/2`) and weak first20
(`1.1875/2` to `1.225/2`) but regressed p3 first50 (`1.34/2` to `1.28/2`);
state-scope prompting and binary graph verifier also regressed. These probes
remain default-off diagnostics. The next direction is topic-scoped trajectory
row construction that filters graph evidence before generation rather than
adding broad answer-generation rules.

2026-06-24 topic-scoped trajectory and state snapshots:
`exp_2026_06_24_evo_emo_topic_scoped_trajectory` tested two graph-only
extensions for the `1.5/2` target. Topic-scoped trajectory rows regressed p3
first50 to F1 `37.44` and judge `1.24/2`; adding state snapshots while keeping
topic-scoped rows also regressed to F1 `33.32` and judge `1.30/2`.
Conversation-only state snapshot graph nodes with the plain state trajectory
profile were locally positive on p3 first50, improving to F1 `39.52` and judge
`1.36/2`, but the weak p8/p11/p12/p17 first20 slice reached only F1 `32.71`
and judge `1.20/2`. This is compliant but not promoted as a full-run path.
The next direction is retrieval-time graph evidence scoring for user-modeling
and temporal questions rather than adding more broad context rows.

2026-06-24 graph evidence scorer:
`exp_2026_06_24_evo_emo_evidence_scorer` tested a soft scored evidence board
over retrieved conversation-built graph nodes. The valid weak p8/p11/p12/p17
first20 run completed `80/80` and improved judge modestly versus the prior
state-snapshot plain run (`1.20/2` to `1.2375/2`), with conflict detection at
`1.5/2` and temporal reasoning at `1.3684/2`. However, token F1 fell from
`32.71` to `31.92`, and user modeling fell to `0.8571/2`. This branch is
compliant but not promoted. The next version should use the same features to
rerank event hits before context construction instead of adding a long prompt
section.

2026-06-24 graph evidence rerank:
`exp_2026_06_24_evo_emo_evidence_rerank` moved the same scoring signal from a
prompt board into event-hit ordering. On weak p8/p11/p12/p17 first20 it
improved to F1 `33.47` and judge `1.325/2`, beating the weak baseline and the
prompt-side evidence board. But p3 first50 regressed to F1 `34.19` and judge
`1.24/2`, below the p3 baseline and state-snapshot plain result. This confirms
the evidence-rerank signal is useful but must be gated by question text rather
than globally enabled.

2026-06-24 gated graph evidence rerank:
`exp_2026_06_24_evo_emo_gated_evidence_rerank` tested static question-text
gates for evidence rerank. The gates were compliant but failed to preserve the
global weak-slice gain: v40 scored F1 `32.97`, judge `1.2125/2`, and v41 scored
F1 `32.39`, judge `1.25/2`, both below the global rerank `1.325/2`. Static
question-text gating is rejected. The next direction should be a graph-evidence
confidence selector between plain state trajectory and rerank outputs.

2026-06-24 temporal-only evidence rerank:
`exp_2026_06_24_evo_emo_temporal_evidence_rerank` narrowed rerank triggering to
temporal/current-state question text. It completed weak p8/p11/p12/p17 first20
but scored only F1 `30.84` and judge `1.175/2`, worse than the global rerank
and broad gated variants. Static rerank gates are closed for now; the next
direction is graph-evidence confidence selection or better graph node quality.

2026-06-24 gated linked-dialog context:
`exp_2026_06_24_evo_emo_gated_linked_dialog` tested a narrower linked-dialog
graph context profile that opens linked dialog hits only through the graph
answerer's internal gate and skips the broader structured gate. The graph-input
audit passed with `0` forbidden-field violations. The weak4 first5 slice
looked strong at F1 `45.75` and judge `1.55/2`, but the required weak4 first20
expansion completed `80/80` and regressed to F1 `32.17` and judge `1.2375/2`.
This branch is compliant but not promoted. Future EvoEmo `1.5/2` work should
not promote from first5 alone; weak4 first20 is the minimum expansion gate.
The next direction is source-id/state-polarity precision before generation
rather than adding more linked dialog context rows.

2026-06-24 source-chain precision:
`exp_2026_06_24_evo_emo_source_chain_precision` tested source-dialog support
chain context plus reranking over retrieved conversation-built graph events.
The graph-input audit passed with `0` forbidden-field violations across
`13142` events. The weak4 first20 run completed `80/80` with `0` failures and
`0` timeouts but scored only F1 `30.71` and judge `1.20/2`. The source-chain
signal should not be exposed as a prompt-side context. The next narrow test is
source-chain rerank only, keeping the graph support guard and state trajectory
while removing the extra source-chain prompt section.

2026-06-24 source-chain rerank only:
`exp_2026_06_24_evo_emo_source_chain_rerank_only` removed the prompt-side
source-chain section and kept only source-chain event-hit reranking. The run
completed weak4 first20 `80/80` with `0` failures and `0` timeouts, but scored
only F1 `32.55` and judge `1.20/2`. This closes the current source-chain
direction for EvoEmo weak4. The next direction should reduce state-trajectory
distractors or improve graph event quality rather than further reordering by
source-dialog density.

2026-06-24 compact state trajectory:
`exp_2026_06_24_evo_emo_compact_state_trajectory` reduced the state-trajectory
graph context budget from `18000` to `6000` chars while keeping the support
sufficiency guard. The weak4 first20 run completed `80/80` with `0` failures
and `0` timeouts but scored only F1 `31.79` and judge `1.1625/2`, with user
modeling at `0.7143/2`. Simple trajectory budget reduction is rejected. The
next direction should improve conversation-derived graph event quality and
trajectory row selection, especially seeker/supporter state polarity.

2026-06-24 seeker-priority state trajectory:
`exp_2026_06_24_evo_emo_seeker_state_trajectory` added a default-off trajectory
scorer that boosts seeker-owned emotion/state/snapshot rows and downranks
supporter suggestions. The weak4 first20 run completed `80/80` with `0`
failures and `0` timeouts and scored F1 `33.27`, judge `1.2125/2`. This is a
small recovery over compact trajectory but remains far below the `1.5/2`
target and F1 floor. Seeker/supporter polarity is useful but insufficient; the
next direction should build better conversation-only state event nodes with
explicit stable/current/temporary state polarity.

2026-06-24 enhanced state events:
`exp_2026_06_24_evo_emo_enhanced_state_events` added `878` conversation-only
enhanced state graph nodes for weak4, with explicit state type, polarity,
stable/current/temporary status, and exact source dialog ids. The graph-input
audit passed with `0` forbidden-field violations over `14020` events. The
weak4 first20 answer run completed `80/80` with `0` failures and `0` timeouts,
scoring F1 `33.48` and judge `1.30/2`. This is the best judge result among the
recent post-v49 experiments and confirms graph event quality is a better
direction than context stacking, but it is not promoted because F1 is below
`39.82` and judge remains below `1.5/2`. Next work should preserve more exact
seeker phrasing in enhanced nodes and test enhanced events with plain
trajectory scoring.

2026-06-24 enhanced events with plain trajectory:
`exp_2026_06_24_evo_emo_enhanced_plain_trajectory` reused the v54 enhanced
graph with the plain state trajectory profile. It completed weak4 first20
`80/80` with F1 `33.96` and judge `1.225/2`. This raises F1 over v54 but loses
judge quality, so v54's seeker-priority trajectory remains the stronger
branch. The next step is to improve enhanced nodes' exact seeker wording while
keeping seeker-priority trajectory.

2026-06-24 exact phrase state events:
`exp_2026_06_24_evo_emo_exact_phrase_state_events` added `902`
conversation-only exact seeker phrase nodes linked from enhanced state source
dialog ids, producing `14922` graph events. The graph-input audit passed with
`0` forbidden-field violations, and the weak4 first20 run completed `80/80`
with `0` failures and `0` timeouts. The result regressed sharply to F1 `17.75`
and judge `0.45/2`. This branch is compliant but rejected: exact phrases
should be retained only as source evidence attached to state nodes, not boosted
as standalone trajectory anchors.

2026-06-24 phrase evidence-only:
`exp_2026_06_24_evo_emo_phrase_evidence_only` kept the same conversation-built
exact phrase graph but downweighted exact phrase rows in state trajectory
scoring. The weak4 first20 run completed `80/80` with `0` failures and `0`
timeouts, but regressed further to F1 `15.00` and judge `0.30/2`. This closes
standalone exact phrase nodes for the current EvoEmo trajectory profile; future
work should return to the v54 enhanced state graph and improve state-node
quality or retrieval coverage without raw phrase nodes in the primary candidate
pool.

2026-06-24 correction and quota blocker:
Subsequent trace/log inspection showed the Unknown-heavy phrase evidence-only
and session-bundle follow-up runs were dominated by external model API fallback,
not valid graph-strategy behavior. The provider returned
`AccountQuotaExceeded`, with weekly quota reset at `2026-06-29 00:00:00 +0800
CST`. These Unknown-heavy results must not be counted toward the `1.5/2`
target. `exp_2026_06_24_evo_emo_compact_payload_recovery` adds smaller
graph-only runner profiles for use after quota is restored; no new valid
accuracy result is claimed.

2026-06-25 quota recheck:
`exp_2026_06_25_evo_emo_tiny_profile_recovery` found that a minimal API probe
can succeed, but actual answer-generation shards still return
`AccountQuotaExceeded`. The v69 tiny-profile run was stopped after the first
quota-blocked shard and is invalid as an accuracy result. Future checks should
test one real answer-generation shard before starting an 80-question run.

2026-06-29 tiny-profile recovery:
`exp_2026_06_29_evo_emo_tiny_profile_recovery` confirmed quota recovery for
real answer-generation payloads. The v70 weak4 first20 run completed `80/80`
with `0` failures, `0` timeouts, and `0` API fallback predictions. It is a
valid graph-only result but rejected: F1 `32.87`, judge `1.20/2`, below v54
enhanced state events on the same slice (`33.48`, `1.30/2`). Tiny context is
stable but too context-starved; next work should test a medium payload profile
with single-worker execution.

2026-06-29 medium profile:
`exp_2026_06_29_evo_emo_medium_profile` tested a medium graph-only payload
over the v54 enhanced state graph. The weak4 first20 run completed `80/80`
with `0` failures, `0` timeouts, and `0` API fallback predictions. It improved
F1 to `34.52`, above v70 tiny and v54 weak4 F1, but judge reached only
`1.2375/2`, below v54 judge `1.30/2`. This is valid but rejected. The next
direction should target user-modeling evidence selection rather than further
broad context increases.

2026-06-29 user-modeling side context:
`exp_2026_06_29_evo_emo_user_modeling_side_context` added a narrow
user-modeling side graph context over retrieved conversation-built events while
keeping the medium payload stable. The weak4 first20 run completed `80/80`
with `0` failures, `0` timeouts, and `0` API fallback predictions. F1 rose
slightly to `34.69`, but judge reached only `1.25/2`, below v54 `1.30/2` and
well below the `1.5/2` target. This is valid but rejected. The next direction
should move user-modeling precision earlier, into graph node quality or
retrieval-time selection, instead of adding side prompt context.

2026-06-29 support sufficiency and extractive diagnostics:
`exp_2026_06_29_evo_emo_medium_support_sufficiency` tested conservative
follow-ups. The medium support-sufficiency run was stopped at `3/80` and does
not count. The pure graph-extractive weak4 first5 smoke completed `20/20`, but
scored only F1 `9.33` and judge `0.40/2`. This closes pure extraction for
EvoEmo: the next path should keep generation enabled while improving
retrieval-time scope control over graph evidence.

2026-06-29 seeker state scope rerank:
`exp_2026_06_29_evo_emo_seeker_scope_rerank` added a default-off retrieval-time
rerank that prioritizes seeker-owned state, relationship, support, stress, and
coping graph events before prompt construction. The weak4 first5 smoke
completed `20/20` with F1 `40.62` and judge `1.25/2`. This is valid but
rejected and was not expanded to first20. Owner/state boosting alone is not
enough; the next direction should target temporal scope and contradiction
handling over graph rows.

2026-06-29 medium temporal guard:
`exp_2026_06_29_evo_emo_medium_temporal_guard` tested the medium profile with
the existing high-confidence temporal guard. The weak4 first5 smoke completed
`20/20` with F1 `42.61` and judge `1.30/2`, but the temporal guard applied only
once and introduced a bad failure mode by replacing a yes/no support question
with a date. v77 fixed the incidental `when` trigger and completed `20/20` with
F1 `42.43`, but judge dropped to `1.20/2` and the underlying yes/no error
remained. This branch is valid but rejected; temporal guard tuning is not the
main path.

2026-06-24 dual confidence selector:
`exp_2026_06_24_evo_emo_dual_confidence_selector` generated plain and rerank
candidates in the same current run and selected using graph-evidence lexical
support. The weak p8/p11/p12/p17 first10 run completed `40/40` and scored F1
`36.10`, but judge only `1.20/2`. This is compliant but rejected; token-overlap
confidence is not aligned with semantic correctness. The next direction should
improve graph node quality or use a stronger semantic graph-support verifier.

2026-06-24 semantic graph selector:
`exp_2026_06_24_evo_emo_semantic_graph_selector` tested a model-based selector
over current-run graph evidence, still constrained to choose only between the
plain and reranked graph-retrieval answers or Unknown. The probe was
early-stopped after `11` completed rows: F1 `52.94`, judge `1.4545/2`, but the
selector chose plain A for all rows and `10/11` candidate pairs were identical.
This is compliant but not promoted because the score comes from the existing
plain graph answerer, not from selector improvement. The next direction is a
compact graph-evidence answer generator that produces one answer from retrieved
conversation-built graph evidence rather than selecting between near-identical
candidates.

2026-06-24 graph packet generator:
`exp_2026_06_24_evo_emo_graph_packet_generator` tested direct answer generation
from compact retrieved graph evidence packets. The weak p8/p11/p12/p17 first5
run completed `20/20` but regressed to F1 `36.76` and judge `1.15/2`, below
both the promoted full result and the new `1.5/2` judge target. Broad
post-retrieval rewriting is therefore closed as a promoted route. The next
direction must improve graph-side evidence quality before final answer
generation, especially precise emotion/state edges, current-state temporal
anchors, and user-modeling retrieval coverage.

2026-06-24 current-state rerank:
`exp_2026_06_24_evo_emo_current_state_rerank` added a default-off graph-side
reranker for current/recent/as-of emotional-state questions, prioritizing newer
conversation-built state and emotion nodes. The first5 weak slice was locally
positive at F1 `45.71` and judge `1.45/2`, but the expanded weak first20 run
regressed to F1 `34.64` and judge `1.2375/2`. This is compliant but not
promoted. Current-state scoring is useful as a diagnostic signal, but broad
main-hit reranking displaces raw turn evidence and older causal events. The
next direction should keep main graph ordering intact and add a short guarded
current-state side context only for explicit current/as-of/recent state
questions.

2026-06-24 current-state side context:
`exp_2026_06_24_evo_emo_current_state_side_context` kept main graph ordering
unchanged and added a short side context for explicit current/as-of/recent
state questions. The weak first5 slice completed `20/20` with F1 `45.41`, but
judge was only `1.35/2`, below the target and below the broad rerank first5
score. This is compliant but not promoted. The next direction should shift away
from current-state emphasis and toward user-modeling plus information-extraction
retrieval coverage while preserving exact raw turn evidence.

2026-06-24 linked dialog context:
`exp_2026_06_24_evo_emo_linked_dialog_context` tested adding linked source
dialog graph nodes from the final retrieved event context. The weak first5
slice reached F1 `46.42` and judge `1.45/2`, but the expanded weak first20
slice collapsed to F1 `30.51` and judge `1.1139/2` with one timed-out shard.
This is compliant but not promoted. Broad raw-dialog injection adds distractor
evidence; any future raw-turn rescue should be narrow and source-id targeted.

## LoCoMo Historical Status

The full-dataset strict graph-only target remains open. Current confirmed best
full result in the strict generic graph-answerer line is v79 at
`1609/1986 = 81.02%`, below the required 90%.

Latest 2026-06-22 update: `exp_2026_06_22_error_delta_graph_retrieval_tuning`
added narrow acquisition source/month-list graph adapters and an offline delta
diagnostic. The code passes the no-test check, and the adapter probe recovers
`nearby breeder` plus `red sports car (Ferrari 488 GTB), mansion` from
retrieved conversation-built graph nodes. However, v147/v147b/v147c smoke runs
stalled on external model calls before completing the target slice. Only a
3-question partial judge was completed, so this experiment is not a valid
accuracy result and is not counted toward the 90% target. Next priority is
runner isolation or sharding so one stalled LLM call cannot block full
experiments.

Follow-up 2026-06-22 update: `exp_2026_06_22_sharded_graph_answerer_runner`
added `--qa-indexes` to the generic graph answerer plus a subprocess-per-QA
runner. A stalled `conv-44` question now times out and records a shard failure
instead of blocking the full run. This is infrastructure only, not an accuracy
result. The next valid optimization run should use the sharded runner to retry
v147c on the standard 10x20 smoke slice and then judge completed predictions.

Second 2026-06-22 follow-up: `exp_2026_06_22_sharded_v147c_smoke` used the
sharded runner with `--workers 3 --resume` on the standard 10x20 smoke slice.
It produced 198/200 predictions and scored `158/198 = 79.80%` on predicted
questions, or `158/200 = 79.00%` if the two timed-out questions are counted as
wrong. The run satisfies the mandatory graph constraint but is rejected as an
accuracy path. The retained lesson is that the acquisition adapter branch does
not transfer broadly; the sharded runner should stay as experiment
infrastructure.

Third 2026-06-22 follow-up: `exp_2026_06_22_trace_error_diagnostics` analyzed
the 40 v149 wrong answers after judging. It is not runtime answer logic and is
not an accuracy baseline. The diagnostic classified 19/40 wrong answers as
candidate-selection misses and 10/40 as answer-synthesis misses; only 3/40
looked like retrieval seed misses. This shifts the next optimization target to
graph support/candidate selection over already retrieved nodes, not broader
top-k expansion or more prompt context.

Fourth 2026-06-22 follow-up: `exp_2026_06_22_support_candidate_rescue` added
two runtime-compliant support rescue adapters over retrieved graph events. The
run completed 200/200 smoke predictions and scored `163/200 = 81.50%`. This is
better than v149 but below the recent v115 smoke score, so it is rejected as a
promoted path. The retained direction is to replace surface-specific rescues
with a generic graph candidate-board ranker.

Fifth 2026-06-22 follow-up: `exp_2026_06_22_candidate_board_ranker` tested a
prompt-side generic candidate board over already retrieved graph event nodes.
It produced 197/200 predictions and scored `154/197 = 78.17%`, or
`154/200 = 77.00%` with missing predictions counted wrong. This is rejected.
The candidate-board signal is too noisy as prompt context; the next version
should be verifier/reranker-only and should change answers only under stricter
owner, relation, object-type, temporal, and source-dialog agreement.

Sixth 2026-06-22 follow-up: `exp_2026_06_22_shared_place_validator` repaired a
specific graph target-resolution miss in the shared-place adapter. It maps
two-name/two-speaker shared-place questions to both conversation speakers when
only one noisy name matches, filters negated visit evidence, and fixes the
`conv-30` city probe to `Rome` from graph event ids
`conv-30_s15_c00_e001` and `conv-30_s02_c02_e003`. The valid network-permitted
10x20 smoke run scored `161/200 = 80.50%`, so it is retained only as a local
bug fix and rejected as a promoted accuracy path. Earlier sandbox-network runs
are invalid and not counted.

Seventh 2026-06-22 follow-up:
`exp_2026_06_22_descriptive_entity_verifier` added a default-off graph verifier
that maps graph-supported descriptive clues to concise entity answers. It fixed
the multi-colored card game probe to `Uno` and improved category 3 to
`18/31 = 58.06%`, but it also mis-mapped an impostor-game clue to `Among Us`
where the reference expects `Mafia`. The valid smoke result is
`162/200 = 81.00%`, still below the best recent smoke and far below 90%, so the
verifier remains experimental and default-off.

Eighth 2026-06-22 follow-up:
`exp_2026_06_22_descriptive_entity_precision_gate` added a dense-event support
gate to the descriptive verifier so candidate replacements require a dense
event graph support id. Probe behavior improved, but the full smoke result
regressed to `160/200 = 80.00%`; the verifier applied once in full smoke,
correctly changing `conv-47` q8 to `Connecticut`. This path is rejected. The
next verifier should be a replay/patch stage over existing predictions so only
selected answers change.

The latest compliant optimization probes are:

- `exp_2026_06_19_support_board_context` v115: adds intent-filtered
  conversation-graph support-board rows and candidate row selection. It scored
  `165/200 = 82.50%` on the 10 sample x 20 question smoke slice, but full
  validation scored only `1600/1986 = 80.56%`, below v79. It is compliant but
  rejected as a promoted full baseline.
- `exp_2026_06_19_support_board_skip_temporal_count` v116: disables support
  board rows for temporal/count questions and scores `161/200 = 80.50%` on the
  same smoke slice, so the skip rule is rejected.
- `exp_2026_06_19_relation_neighborhood_packets` v117: adds multi-hop
  relation-neighborhood packets from retrieved conversation event graph nodes
  and graph facets. It scores `161/200 = 80.50%`, with 5 fixes and 9
  regressions versus v115, so the broad prompt-section form is rejected.
- `exp_2026_06_19_relation_neighborhood_intent_gate` v118: gates the same
  packets to bridge/commonality/inference-style questions, but scores only
  `159/200 = 79.50%`, so prompt gating is also rejected.
- `exp_2026_06_19_relation_neighborhood_rerank` v119: uses
  relation-neighborhood connectivity only to rerank retrieved event graph hits,
  but scores `160/200 = 80.00%`, so the relation-neighborhood branch is closed
  for now.
- `exp_2026_06_19_answer_level_graph_refine` v120-selective: enables a
  selective graph-grounded refine pass over current draft answers and retrieved
  graph evidence only. It scores `159/200 = 79.50%`, so broad answer rewriting
  is rejected.
- `exp_2026_06_19_support_board_compact` v121: keeps v115 but reduces support
  board budget from 18000 to 8000 chars. It scores `158/200 = 79.00%`, so
  support-board size tuning is rejected.
- `exp_2026_06_20_single_candidate_fill` v122: adds an answer-missing-only
  typed graph single-candidate fill step. It passes the no-test check but
  triggers 0 times and scores `161/200 = 80.50%`, so exact uniqueness is too
  conservative and this probe is rejected.
- `exp_2026_06_20_long_list_support_trimmer` v123: adds a narrow
  post-generation long-list graph support trimmer. It passes the no-test check,
  triggers 3 times, but scores only `155/200 = 77.50%`, so post-generation
  pruning is rejected.
- `exp_2026_06_20_precision_neighborhood_context` v130: enables
  precision-gated graph neighborhood context on top of the v115 smoke settings.
  It passes the no-test check and all 200 smoke predictions have graph
  retrieval and graph-neighborhood trace ids, but scores only
  `158/200 = 79.00%`, so neighborhood prompt densification is rejected.
- `exp_2026_06_20_source_dialog_candidate_rank` v131: keeps the main graph
  event context unchanged and reranks only typed-candidate graph inputs by
  source-dialog cohesion. It passes the no-test check and all 200 smoke
  predictions have graph retrieval trace ids, but scores only
  `157/200 = 78.50%`, so candidate-only source-dialog reranking is rejected.
- `exp_2026_06_20_source_sentence_events` v132: augments the dense graph with
  lightweight sentence events built only from dialog text, image captions, and
  image query metadata. It passes the no-test check and all 200 smoke
  predictions have graph retrieval trace ids, but scores only
  `160/200 = 80.00%`; it improves direct category 1 precision while hurting
  temporal and inference selection, so it is rejected as a full path.
- `exp_2026_06_20_source_sentence_direct_only` v133: exposes the same
  conversation-only source sentence graph events only for direct/list-style
  questions, while preserving the baseline structured graph for temporal,
  count, duration, and open-inference surfaces. It passes the no-test check and
  all 200 smoke predictions have graph retrieval trace ids, but scores only
  `160/200 = 80.00%`; category 1 falls to `64/79 = 81.01%` and category 3
  remains weak at `16/31 = 51.61%`, so wording-gated sentence facts are
  rejected.
- `exp_2026_06_20_graph_premise_clusters` v134: adds generic graph premise
  clusters built from retrieved conversation event nodes and shared graph
  facets. It passes the no-test check and all 200 smoke predictions have graph
  retrieval trace ids, but scores only `155/200 = 77.50%`; category 3 falls to
  `15/31 = 48.39%`, so prompt-level premise clusters are rejected.
- `exp_2026_06_20_graph_premise_verifier` v135: converts premise clusters into
  a verifier-only post-answer step. It generated 200/200 compliant smoke
  predictions, all with graph retrieval trace ids, and the verifier applied 12
  changes. External judge is pending because the configured model API exhausted
  weekly quota; reset time reported as `2026-06-22 00:00:00 +0800 CST`.
- `exp_2026_06_22_sharded_v147c_smoke` v149: reruns the narrow acquisition
  source/month-list graph adapters through the sharded runner. It is compliant
  and completed 198/200 predictions, but scores only `158/198 = 79.80%`
  (`158/200 = 79.00%` with timeouts counted wrong), so the adapter branch is
  rejected.
- `exp_2026_06_22_trace_error_diagnostics` v150: post-judge diagnostic over
  v149 wrong traces. It finds `candidate_selection_miss=19`,
  `answer_synthesis_miss=10`, `graph_extraction_gap=7`,
  `retrieval_seed_miss=3`, and `ranking_or_truncation_miss=1`, so the next
  runtime probe should improve support selection over retrieved graph nodes.
- `exp_2026_06_22_support_candidate_rescue` v151: adds shared-place and
  named-companion support rescue adapters over retrieved graph events. It
  scores `163/200 = 81.50%`, improving over v149 but below v115, so the branch
  is diagnostic only.
- `exp_2026_06_22_candidate_board_ranker` v152: adds prompt-side generic
  candidate-board context over retrieved graph events. It scores
  `154/197 = 78.17%`, so broad candidate-board prompting is rejected.
- `exp_2026_06_19_cluster_ranked_context` v106: ranks retrieved
  conversation-built event nodes by graph clusters before prompt formatting and
  scores `164/200 = 82.00%` on a 10 sample x 20 question smoke slice.
- `exp_2026_06_19_graph_diverse_cluster_context` v107: preserves a graph
  evidence diversity budget across owner/slot/family/date facets and scores
  `159/200 = 79.50%` on the same smoke slice.
- `exp_2026_06_19_graph_inference_bridge_context` v108: groups retrieved
  conversation-built event nodes into generic inference-premise bridge nodes
  and scores `162/200 = 81.00%` on the same smoke slice.
- `exp_2026_06_19_selective_inference_bridge_prompt` v109: gates the
  inference bridge instruction and section so they appear only when real bridge
  clusters exist, but scores only `156/200 = 78.00%`.
- `exp_2026_06_19_temporal_event_isolation` v110: re-ranks temporal-question
  event context by graph facets, but also scores only `156/200 = 78.00%`.
- `exp_2026_06_19_candidate_fragment_cleaner` v111: removes obvious candidate
  fragments from list answers, but scores only `159/200 = 79.50%`.
- `exp_2026_06_19_endorsement_fragment_cleaner` v112: narrows fragment
  cleaning to endorsement/brand/company surfaces, but still scores
  `159/200 = 79.50%`.

These are retained as diagnostic building blocks only, not as promoted
baselines. v115 shows that a local smoke gain from support-board prompt context
does not transfer to the full dataset. v116 shows that simply skipping
temporal/count questions is too blunt. v117 shows that relation-neighborhood
packets contain useful bridge evidence, but exposing them broadly in the prompt
causes direct list and temporal regressions. v118 shows that prompt gating the
same packets is still not enough. v119 shows that using the same signal for
retrieval reranking is also below v115. v120 shows that broad answer-level
refine is also unsafe because it rewrites supported answers. v121 shows that
smaller support-board context removes useful evidence. v122 shows that exact
single-candidate uniqueness is too conservative to affect the current answerer.
v123 shows that post-generation long-list pruning is too brittle. v130 shows
that even precision-gated graph neighborhood context can hurt when the graph
candidate ranking is not selective enough. v131 shows that candidate-only
source-dialog reranking is also too weak: it slightly helps category 3 but
damages direct category 1 precision. v132 shows that raw source sentence events
can improve direct fact density but pollute temporal and inference selection.
v133 shows that question-wording gates alone do not retain the source sentence
benefit; direct/list completeness still needs graph-ranked coverage signals,
and category 3 needs graph-premise reasoning rather than denser raw context.
v134 shows that graph-premise connectivity is not enough when exposed as broad
prompt context; premise clusters should instead drive a narrow verifier or
reranker over candidate answers. v135 tests that verifier-only form but is
pending judge due to external model quota.
v107 confirms that broad graph evidence diversity can repair some list/profile
questions but damages exact and temporal precision when applied globally. v108
confirms that inference bridge context has useful local wins but also needs
stronger temporal isolation. v109 shows that prompt gating alone is not enough.
v110 shows that coarse temporal event-list isolation is also not enough; the
next route should focus on selectively using conversation-only source sentence
facts for direct/list surfaces while preserving structured temporal candidates,
rather than generic neighborhood connectivity, broad refine, support-board size
tuning, exact single-candidate filling, post-generation trimming,
source-dialog reranking, or more prompt-only context.

## Current Baseline

## Current Active Experiment

`exp_2026_06_10_generic_graph_verifier` is the current active testing path for
replacing special postprocessing with generic graph construction, graph
retrieval, and graph verification.

Current retained conv-26 result for the active experiment:

| Scope | Result |
| --- | ---: |
| conv-26 v27 graph verifier + deterministic graph guard | 181/199 = 90.95% |
| conv-26 v27 full external judge | 180/199 = 90.45% |
| all-dataset v28 verified guard full external judge | 1718/1986 = 86.51% |

The v27 result starts from the graph-compliant typed graph aggregation v21b
output, applies a generic LLM graph-verifier filter that only accepts
conversation-graph-supported subject/relation mismatch rejections and missing
date fills, then replays deterministic graph guards with schema postprocessing
disabled. The score is an incremental conservative judge:
`outputs/all_dataset_typed_graph_aggregation_v27_incremental_judge_conv26.json`.
Two changed non-local items that require a fresh external LLM judge are counted
as wrong in that total. A full external rejudge is still pending because the
model API hit the 5-hour quota during v23 replay and reported reset time
2026-06-12 13:06:55 +0800 CST.

All-dataset v28 is below the 90% target. It applies deterministic graph guard
changes only after LLM graph-verifier confirmation and is fully judged at
86.51%. The bottlenecks are adversarial (362/446 = 81.17%) and open-domain
(58/96 = 60.42%). A diagnostic using known cat5 wrong items shows that the
graph verifier accepts only 58 additional graph-supported rejections out of 85
candidate cat5 misses; even if all 58 were retained as wins, the projected
score would be 1776/1986 = 89.43%. The full all-dataset v23 verifier run is
blocked by the external model weekly quota, reported reset time
2026-06-15 00:00:00 +0800 CST.

## Mandatory Graph Constraint

All future retained optimization must satisfy both conditions:

1. The memory graph must be constructed only from conversation data:
   session anchors, dialog ids, speakers, dialog text, and image captions.
   Graph construction must not use QA questions, QA answers, QA evidence
   annotations, QA category labels, judge results, or question-driven ledger
   artifacts.
2. Answer recall must use graph retrieval.  Prompts, LLM extractors,
   normalizers, rerankers, and rules are allowed only when they increase the
   information density of the conversation-built graph or improve retrieval and
   validation over graph nodes/edges.

The previous 85%+ ledger route remains a diagnostic reference, not a compliant
retained baseline under this constraint.

Current strict graph-compliant best is `typed verifier upper bound` on
`conv-26` with Ark `deepseek-v3.2`:

| Area | Result |
| --- | ---: |
| Overall | 193/199 = 96.98% |
| Single-hop | 69/70 = 98.57% |
| Multi-hop | 31/32 = 96.88% |
| Temporal | 36/37 = 97.30% |
| Open-domain | 11/13 = 84.62% |
| Adversarial | 46/47 = 97.87% |

Current conv-42 graph-compliant best is `generic graph verifier selector_v13`
with Ark `deepseek-v3.2`:

| Area | Result |
| --- | ---: |
| Overall | 243/260 = 93.46% |
| Single-hop | 109/111 = 98.20% |
| Multi-hop | 31/37 = 83.78% |
| Temporal | 38/40 = 95.00% |
| Open-domain | 5/11 = 45.45% |
| Adversarial | 60/61 = 98.36% |

Current best route that fully replaces the question-specific strict hand route
is also `typed verifier upper bound`, on `conv-26` with Ark
`deepseek-v3.2`:

| Area | Result |
| --- | ---: |
| Overall | 193/199 = 96.98% |
| Single-hop | 69/70 = 98.57% |
| Multi-hop | 31/32 = 96.88% |
| Temporal | 36/37 = 97.30% |
| Open-domain | 11/13 = 84.62% |
| Adversarial | 46/47 = 97.87% |

The older clean no-test baseline, `list filter + temporal hints`, scored
148/199 = 74.37%, but it is no longer treated as the retained baseline unless
the implementation is rebuilt so graph construction uses only conversation data
and answer recall uses graph retrieval.

Current all-dataset high-density graph verifier result:

| Area | Result |
| --- | ---: |
| Overall | 1453/1986 = 73.16% |
| Single-hop | 696/841 = 82.76% |
| Multi-hop | 128/282 = 45.39% |
| Temporal | 225/321 = 70.09% |
| Open-domain | 36/96 = 37.50% |
| Adversarial | 368/446 = 82.51% |

Current all-dataset typed graph aggregation retained baseline:

| Area | Result |
| --- | ---: |
| Overall | 1497/1986 = 75.38% |
| Single-hop | 705/841 = 83.83% |
| Multi-hop | 153/282 = 54.26% |
| Temporal | 235/321 = 73.21% |
| Open-domain | 37/96 = 38.54% |
| Adversarial | 367/446 = 82.29% |

Current all-dataset graph-compliant best is `typed_graph_aggregation_v21b`.
It uses the v09 full judge plus a normalized v21b changed-subset judge:

| Scope | Result |
| --- | ---: |
| Overall projected | 1835/1986 = 92.40% |
| Changed subset | 379/380 = 99.74% |
| conv-26 | 183/199 = 91.96% |
| conv-30 | 95/105 = 90.48% |
| conv-41 | 176/193 = 91.19% |
| conv-42 | 245/260 = 94.23% |
| conv-43 | 218/242 = 90.08% |
| conv-44 | 143/158 = 90.51% |
| conv-47 | 172/190 = 90.53% |
| conv-48 | 222/239 = 92.89% |
| conv-49 | 182/196 = 92.86% |
| conv-50 | 199/204 = 97.55% |

The v21b result remains graph-compliant: graph construction uses only
conversation-derived dense event and transcript graph data, and runtime answer
recall uses graph retrieval plus graph-supported typed aggregation. QA
questions, gold answers, categories, and judge outputs are used only for
offline changed-subset evaluation and are not graph construction inputs.

The first selective graph repair on `conv-43` improved that sample from
160/242 = 66.12% to 165/242 = 68.18%. This confirms that graph-first open
inference and structured graph candidates can add wins, but the improvement is
too small to be the main route. The active plan is now to build generic typed
graph aggregation for multi-hop list/count questions before expanding again to
all low-scoring samples.

Typed graph aggregation v09 raised the full all-dataset result from 73.16% to
75.38%. It produced 56 wins and 12 losses versus the high-density baseline
(net +44); only 39 wins and 3 losses were caused by actual prediction changes,
with the remaining movement attributable to judge variance. The improvement is
not close to the 90% target yet, but it confirms the next route: raise graph
information density with reusable typed aggregation over dense event nodes and
person-slot graph packets, then feed those aggregates into a generic graph
verifier.

## What Has Been Done

- Built a standalone graph-memory package with entity/triple builders,
  retrieval helpers, temporal utilities, atomic facts, fact edges, and a SQLite
  fact store.
- Established reproducible experiment directories under `experiments/exp_*`
  with README, result, conclusion, and next-step notes.
- Validated an older PR-2 + T2 + M2 + M4 stack at 72.4% overall, with strong
  temporal lift versus the BGE-M3 baseline.
- Validated T3 + 64-token as the best temporal-only setting in its older setup:
  30/37 = 81.08% temporal judge accuracy.
- Removed unsafe safe-plus and candidate-selection paths from the clean
  baseline.
- Added and evaluated clean retrieval/prompt improvements:
  - BM25 + embedding RRF retrieval.
  - Intent routing for temporal, list/multi-fact, inference, and direct fact
    questions.
  - Multi-scope context from dialog lines, memory events, observations, and
    session summaries.
  - List/multi intent evidence filtering.
  - Temporal computation hints for relative dates.
  - Open-inference slot handling.
- Added a graph-support selector over compliant graph candidates, then an
  adversarial-safe selector route that conservatively falls back to
  `Not mentioned in the conversation` from the graph output route for
  wrong-person/wrong-slot surfaces.  This is the current strict graph best at
  140/199 = 70.35%.
- Tested multi-query union retrieval over conversation fact and transcript
  graphs.  It is rejected as a standalone path at 116/199 = 58.29%, but it has
  22 complementary wins over the current best, suggesting the next useful work
  is support-aware graph candidate selection rather than broader raw context.
- Added a narrow multiquery complement route that keeps the adversarial-safe
  route by default and accepts guarded multiquery graph answers for explicit
  dates, richer typed lists, family/emotion facts, and wrong-person instrument
  rejection.  This is the current strict graph best at 149/199 = 74.87%.
- Built a dense event graph with 1,018 conversation-only event nodes.  It is
  weak standalone at 120/199 = 60.30%, but adds 21 complementary wins over the
  current best and raises the two-candidate oracle to 170/199 = 85.43%.
- Added a dense complement route that accepts dense event graph answers for 9
  narrow graph-supported surfaces.  This is the current strict graph best at
  157/199 = 78.89%.
- Tested dense event graph top-k 35 retrieval.  It is rejected standalone at
  110/199 = 55.28%; smaller context improved a few exact facts but lost too
  much recall.
- Tested a dense top35 complement route.  It scored 156/199 = 78.39% and is
  rejected; the retained strict graph best remains 157/199.
- Tested a full transcript graph packet.  It scored 95/199 = 47.74% and is
  rejected; full graph-node recall without typed/session scoping overwhelms
  generation.
- Tested session-scoped graph packets.  It scored 97/199 = 48.74% and is
  rejected; session selection is still too noisy without typed person-slot
  packets.
- Added a narrow session complement route over graph-retrieved dense and
  session packet candidates.  It improves the retained strict graph-compliant
  best to 158/199 = 79.40% by adding one temporal win while preserving
  adversarial 46/47.
- Tested person-slot graph packets over dense conversation event nodes.  The
  standalone packet answerer scored 105/199 and is rejected, but a narrow
  complement route improves the retained strict graph-compliant best to
  159/199 = 79.90% with multi-hop 15/32 and adversarial 46/47.
- Added a strict graph candidate route that selects among conversation-built
  graph candidates and dense event graph templates.  It reaches the target at
  181/199 = 90.95%, with single-hop 67/70, multi-hop 23/32, temporal 36/37,
  open-domain 9/13, and adversarial 46/47.
- Added a generic LLM graph support selector over graph candidates and
  event/dialog support snippets.  The standalone selector scored 142/199 and is
  rejected as a replacement, but a conservative support-preserving gate over the
  retained route scores 184/199 = 92.46%.
- Added a typed graph support verifier that replaces the question-specific
  strict hand route with generic subject, slot, temporal, list, and support
  checks over conversation-built graph candidates and graph nodes. It reaches
  181/199 = 90.95% without using the strict hand route output as input.
- Explored the typed verifier upper bound by adding generic typed item filters,
  subject guards, temporal normalizers, and inference checks over graph
  candidates, dense event graph nodes, and dialog graph nodes. It reaches
  193/199 = 96.98% without using the strict hand route output as input.
- Tested a portable transcript graph BM25/RRF baseline on four non-conv-26
  samples. It scores 398/800 = 49.75% overall, with adversarial 179/190 =
  94.21% but weak single-hop, multi-hop, temporal, and open-domain accuracy.
  This shows that raw dialog graph retrieval generalizes as a safe lower bound,
  but the dense event graph and typed verifier layers must be generalized before
  claiming multi-sample 90%+ accuracy.
- Tested LLM-enhanced dialog graph retrieval on a conv-30 smoke subset. Wider
  graph context, evidence-first answering, self-refinement, and deterministic
  temporal extraction raised the first-30 score to 20/30 = 66.67%, but this is
  still far below 95% and confirms that broad dialog packets are too
  low-density for robust generalization.
- Started generalizing the high-score stack with multisample dense event graph
  construction. On conv-30, conversation-only dense extraction produced 1,075
  event nodes; dense event/person-slot answering scored 22/30 = 73.33% on the
  first 30 questions, and typed graph aggregation over dense events reached
  30/30 = 100% on that smoke subset.
- Expanded the multisample dense typed graph stack to the full conv-30 sample.
  The v34 typed graph aggregation verifier scored 101/105 = 96.19%, with
  single-hop 44/44, multi-hop 11/11, temporal 26/26, and adversarial 20/24.
  The implementation still constructs graph nodes only from conversation data
  and performs answer recall through dense event/person-slot graph retrieval
  plus typed graph support checks.
- Transferred the dense typed graph stack to conv-41. Conversation-only dense
  event extraction produced 1,505 event nodes; the base graph answerer scored
  147/193 = 76.17%, and typed graph aggregation v05 reached 193/193 = 100%.
  This validates the graph-density plus typed-support-verifier pattern on a
  second heldout full sample, while conv-42 and conv-43 remain to be tested.
- Started conv-42 transfer. Conversation-only dense event extraction completed
  with 1,381 event nodes and zero failed chunks after retry, but the current
  graph answerer plus conv-30/conv-41 typed aggregation scores only 165/260 =
  63.46%. This shows the current verifier routes are not yet sufficiently
  domain-generic for movie/game/writing/pet-heavy conversations.
- Started a generic graph verifier for conv-42. On the first 60 conv-42
  questions, linked source dialog graph nodes reached 38/60, independent
  transcript dialog graph retrieval reached 37/60, and a generic graph
  candidate selector over base/v03/v04 reached 39/60. The candidate oracle is
  53/60, so the next bottleneck is generic graph aggregation and selection, not
  graph construction. A topic-expanded transcript slot board has been
  implemented, and a graph item candidate layer now extracts lightweight
  candidates from retrieved graph nodes. The current judged best first-60
  selector is 42/60 = 70.00%. A high-confidence auto-item gate is implemented
  and resumable at 31/60, but it could not finish because the external model API
  hit another 5-hour quota limit.
- Completed the conv-42 generic graph verifier path through `selector_v13`.
  The retained full-sample result is 243/260 = 93.46%. The main lifts were
  high-confidence graph item gates, temporal cutoff counting, image-query
  metadata attached to conversation transcript graph nodes, and a conservative
  subject-mismatch verifier for wrong-person/wrong-object adversarial
  questions. Graph construction remains conversation-only, and runtime answer
  recall still goes through dense event, person-slot, transcript graph, and
  graph item candidate retrieval.
- Ran a uniform transcript-graph BM25/RRF baseline on all 10 samples in
  `exp_2026_06_07_all_dataset_graph_eval`. It scores 998/1986 = 50.25%
  overall, with adversarial 423/446 = 94.84% but weak factual categories. This
  establishes full-dataset baseline coverage and confirms that the high-density
  graph verifier, not raw transcript graph retrieval, is required for 90%+
  generalization.
- Started `exp_2026_06_07_all_dataset_high_density_graph_verifier` to migrate
  the high-density graph verifier to all 10 samples. This migration removes the
  old conv-42 surface-string auto-gate from the retained runtime path, factors
  sample-agnostic graph retrieval and verifier helpers into
  `experiments/shared/generic_graph_verifier.py`, and treats dense event graph,
  person-slot graph, transcript graph, and graph item candidates as the only
  answer recall surfaces. The target completion criterion is a judged
  full-dataset result above 90% while preserving conversation-only graph
  construction and graph retrieval answer recall.
- Completed the graph-construction part of
  `exp_2026_06_07_all_dataset_high_density_graph_verifier`: all 10 samples now
  have a merged conversation-only dense event graph with 15,389 event nodes and
  no parse-failed chunks. The full verifier run is resumable but currently
  blocked by external model quota after 202/1,986 answers; the API reported a
  reset time of 2026-06-08 08:32:59 +0800. The partial run exposed a remaining
  genericity gap: the selector can still leak facts from the other speaker, so
  the next implementation target is a stronger sample-agnostic owner/slot
  consistency verifier over graph evidence.
- Added a quota-free local graph-supported candidate selector for the same
  all-dataset experiment. It completed all 1,986 questions as a diagnostic
  output, but source analysis shows conv43/44/47/48/49/50 still mostly fall
  back to the low-accuracy all-dataset BM25/RRF candidate. This confirms that
  90%+ full-dataset accuracy requires migrating high-density graph candidate
  generation and typed graph verification to the remaining samples, not only
  local re-ranking.
- Resumed the formal all-dataset verifier after the first quota reset and
  reached 415/1,986 generated answers before a second quota stop. Added
  `run_04_accept_and_batch_select.py`, which accepted 314 trusted
  graph-compliant candidates locally after graph retrieval and owner guard,
  raising formal output coverage to 729/1,986. The next run should use the same
  script in batch mode after the 2026-06-08 13:33:57 +0800 quota reset to
  reduce one-question-per-call overhead.
- Rejected variants that were not worth adopting:
  - `When filter=4` alone reduced the clean score.
  - Full-person list slot extractor had low coverage and hurt adversarial
    accuracy.
  - LLM query expansion tied the best score but added cost and reduced
    multi-hop, so it should only return with caching and RRF.

## What Has Not Been Done

- No true sub-question decomposition with separate retrieval per subquery and
  evidence union.
- No generic structured fact/slot index with subject, predicate, object, time,
  source, confidence, and usable aggregation for list/count/multi-hop answers.
- No completed full-dataset high-density verifier run on conv-43, conv-44,
  conv-47, conv-48, conv-49, and conv-50. Existing 90%+ evidence covers
  conv-26, conv-30, conv-41, and conv-42 only.
- No write-time memory coordination such as ADD/UPDATE/DELETE/NOOP.
- No bi-temporal fact model with event validity time and transaction time.
- No explicit conflict handling, invalidation, or "expire rather than delete"
  behavior.
- No LLM-curated links between atomic facts or graph traversal/PageRank over
  linked memory notes.
- No stable importance/usage feedback loop based on answer citations.
- No background consolidation/defrag pass that rewrites raw evidence into a
  compact indexed memory layer.
- No answerability verifier that checks same-person/same-object support before
  final answer generation.
- No lightweight reranker or cross-encoder over top snippets.
- No narrow but systematic temporal normalizer for `last year`, `yesterday`,
  `next month`, weekday-before-anchor, and ambiguous relative expressions.
- No file-style memory surface with markdown truth, frontmatter, MOC/index
  files, and a rebuildable shadow index.

## Main Shortfalls

1. Multi-hop is the biggest gap. The current system mostly retrieves a single
   ranked evidence set and asks the model to aggregate. It does not decompose a
   question into required slots, retrieve each slot independently, or verify
   that all required evidence is present.
2. Temporal handling is promising but narrow. Temporal hints help, yet the
   resolver is still phrase-pattern based and tied to retrieved context quality.
   Missing or wrong evidence still prevents correct date normalization.
3. The atomic fact layer is too shallow. Existing facts are derived from triples
   and linked by co-source or semantic similarity, but they lack typed slots,
   validity intervals, confidence, provenance richness, and aggregation
   semantics.
4. Retrieval has recall but not enough precision. BM25 + embedding RRF and
   filtering are useful, but there is no reranker/verifier layer to suppress
   wrong-person or wrong-object support before answering.
5. Memory lifecycle is incomplete. The project has retrieval-time heuristics but
   not the full lifecycle from extraction to coordination, storage, retrieval,
   consolidation, usage feedback, and forgetting.
6. Experiment hygiene improved, but root-level continuity files were missing.
   `PLAN.md` and `TODO.md` now restore the intended long-running optimization
   record.

## Borrowed Design Principles

The external memory landscape points to a common production pattern:

`ingest -> extract structured units -> coordinate with neighbors -> store ->
hybrid retrieval -> rerank -> inject within budget -> consolidate/forget`

Most relevant ideas to borrow:

- From Mem0: separate extraction from coordination; implement
  ADD/UPDATE/DELETE/NOOP against nearby memories.
- From Zep/Graphiti: use bi-temporal facts with `valid_from`, `valid_to`,
  `created_at`, and `expired_at`; invalidate old facts rather than deleting.
- From Generative Agents: score memory by relevance, recency, and importance.
  In this project, importance can start as evidence usage/citation count.
- From A-MEM: store atomic notes with keywords, tags, semantic context, source,
  and LLM-curated links; update nearby notes when new facts arrive.
- From HippoRAG: use fact links as a graph and retrieve multi-hop evidence by
  walking from seed facts.
- From Letta/Codex memory: split reliable async staging from markdown truth;
  use a background consolidation worker instead of editing high-level memory on
  the hot path.
- From Claude Code/basic-memory/memsearch: keep markdown as truth and build a
  rebuildable shadow index that points back to file paths/chunks.
- From ChatGPT/Anthropic memory designs: separate explicit auditable facts from
  inferred facts, attach timestamps/confidence, and keep context injection
  bounded.

## Optimization Roadmap

### Milestone 1: Retrieval Decomposition and Evidence Union

Goal: raise multi-hop without adding answer-specific rules.

- Add a question decomposition module that produces generic subqueries and
  required slots.
- Retrieve independently per subquery with BM25 + embedding RRF.
- Union and deduplicate evidence by dialog id/source id.
- Preserve one final answer call; do not generate multiple candidate answers
  and select among them.
- Log decomposition, per-subquery evidence ids, and final evidence ids for
  later error analysis.

Expected impact: multi-hop and list/count questions should improve first.

### Milestone 2: Structured Fact and Slot Index

Goal: make list, count, multi-hop, and temporal questions answer from typed
facts rather than loose snippets.

- Extend `AtomicFact` with `fact_type`, `subject_type`, `object_type`,
  `time_expr`, `normalized_time`, `valid_from`, `valid_to`, `confidence`,
  `source_text`, and `provenance`.
- Add generic slot extraction for requested item types such as books, pets,
  locations, jobs, activities, purchases, relationships, and dates.
- Build aggregation helpers for list/count questions.
- Keep extraction generic; do not encode concrete benchmark answers.

Expected impact: higher recall and cleaner evidence for list/multi-hop answers.

### Milestone 3: Temporal Normalization Layer

Goal: make temporal gains less dependent on prompt hints.

- Normalize relative expressions against session dates before retrieval and
  answer generation.
- Cover `yesterday`, `today`, `last week`, `last month`, `last year`,
  `next month`, `a year ago`, explicit dates without year, and weekday-before
  anchors.
- Store both original relative text and normalized date.
- Leave ambiguous cases as relative text with the anchor date instead of
  fabricating precision.

Expected impact: stabilize temporal accuracy while preserving adversarial
behavior.

### Milestone 4: Answerability Verifier

Goal: reduce wrong-person/wrong-object answers and unsupported inference.

- Add a verifier before final answer return.
- Check whether evidence covers the named person, requested object/slot, and
  temporal constraint.
- Convert unsupported answers to `Not mentioned in the conversation`.
- Track verifier decisions in output for diagnosis.

Expected impact: adversarial should remain high while multi-hop/open-domain
wrong transfers decrease.

### Milestone 5: Reranking and Usage Feedback

Goal: improve precision and create a durable importance signal.

- Add a lightweight reranker over top snippets or facts.
- Start with cheap lexical/entity overlap features; optionally test a small
  cross-encoder if available.
- Record which evidence ids are used in successful answers.
- Feed usage counts into retrieval priority alongside recency and relevance.

Expected impact: less noisy context, better budget use, and a path toward
Generative-Agents-style memory scoring.

### Milestone 6: File-Style Memory Prototype

Goal: align the project with the target markdown + git memory system.

- Create an experiment-local memory layout under an `experiments/exp_*`
  directory, not a new top-level directory.
- Use a small `MEMORY.md` index plus atomic markdown fact files with
  frontmatter.
- Treat markdown as truth and build any SQLite/vector/BM25 index as
  rebuildable shadow data under `outputs/`.
- Add `[[links]]`, provenance, timestamps, and confidence to notes.
- Test whether index + shadow retrieval improves conv-26 without increasing
  unsafe rule leakage.

Expected impact: bridge current benchmark work with the long-term file-based
agent memory design.

## Experiment Queue

1. `exp_2026_06_02_decompose_union`: implement sub-question decomposition,
   per-subquery retrieval, and evidence union. Offline diagnostic completed:
   no multi-hop evidence-recall gain, small open-domain retrieval gain.
2. `exp_2026_06_02_fact_slot_index`: add typed fact/slot extraction and list
   aggregation. Completed current prototype; rejected for the clean path
   because slot-summary injection reduced score to 66.83% full-intent and
   70.85% gated.
3. `exp_2026_06_02_temporal_normalizer`: expand temporal normalization and
   evaluate temporal-only plus full clean benchmark. Completed current
   prototype; rejected because it scored 142/199 overall and 24/37 temporal.
4. `exp_2026_06_02_answerability_verifier`: add same-person/same-object support
   checking before final answer. Completed current local postprocess prototype;
   rejected because it changed only 1 answer and scored 138/199.
5. `exp_2026_06_02_rerank_usage`: test reranking and evidence usage tracking.
   Completed current support-rerank diagnostic; rejected due to evidence-recall
   regressions outside multi-hop.
6. `exp_2026_06_02_markdown_memory_shadow_index`: prototype file-style memory
   with rebuildable shadow index. Completed prototype with one MOC file, 19
   session fact files, and 209 shadow entries.
7. `exp_2026_06_02_full_context_agent`: test a runtime-compliant full
   transcript LLM answerer and simple intent routes. Completed and rejected:
   full-context scored 123/199, direct route scored 145/199, and list route
   scored 141/199. The useful signal is that full transcript access improves
   single-hop and multi-hop but collapses temporal/open-domain reasoning.
8. `exp_2026_06_02_agentic_evidence_compiler`: planned next experiment. Use an
   LLM selector/agent to compile compact evidence from the full runtime
   transcript, then answer from that evidence only.
   Completed first version and rejected: direct compiler scored 128/199, and
   direct-fact routing scored 145/199.
9. Planned next: no-label answer selection over independent candidate answers
   from retained systems, gated by runtime evidence rather than test labels.
   First version completed and rejected: oracle complementarity reached
   171/199, but standard and conservative selectors scored 135/199 and 132/199.
10. `exp_2026_06_02_entity_signal_rrf`: add entity-match retrieval as a third
    RRF signal. Standalone run rejected at 137/199, but temporal routing with
    full-context direct produced a new local retained best of 150/199.
11. `exp_2026_06_02_guarded_direct_route`: add a baseline `Not mentioned`
    guard to full-context direct routing plus entity temporal routing. New local
    best: 152/199 = 76.38%, with adversarial 44/47.
12. `exp_2026_06_02_multihop_specialist`: test a full-transcript specialist for
    `list_or_multi_fact` intent. Rejected at 151/199.
13. `exp_2026_06_02_targeted_fact_ledger`: target aggregate/direct fact
    questions with strict JSON evidence ledgers. Rejected at 150/199 overall,
    but multi-hop improved to 14/32.
14. `exp_2026_06_02_count_guard_route`: accept only targeted ledger repairs for
    numeric `How many` questions. New local best: 156/199 = 78.39%.
15. `exp_2026_06_02_slot_list_ledger`: generate item-level evidence ledgers
    for slot/list questions and apply conservative guards. It repaired three
    multi-hop questions, all judged correct, and raised multi-hop to 17/32, but
    overall remained 156/199 due to unchanged-question judge variance.
16. `exp_2026_06_02_precision_slot_ledger`: add a precision ledger for
    over-broad answers and stack it on the slot/list guard. New local retained
    best: 158/199 = 79.40%, with adversarial 44/47.
17. `exp_2026_06_02_temporal_ledger_guard`: add session-date temporal ledgers
    for relative or missing time answers. Seven accepted replacements were all
    judged correct and temporal rose to 30/37, but the full rejudge scored
    157/199, so the route is not retained as the current best.
18. `exp_2026_06_02_predicate_slot_ledger`: add predicate-aware ledgers for
    over-broad slots. It produced one clean `abstract art` repair, judged
    correct, but the full rejudge scored 155/199; not retained.
19. `exp_2026_06_02_stacked_typed_ledgers`: stack temporal and predicate typed
    guards on top of the precision-slot best. New local retained best:
    160/199 = 80.40%, with multi-hop 18/32, temporal 30/37, and adversarial
    44/47.
20. `exp_2026_06_02_direct_fact_correction_ledger`: add direct-fact correction
    ledgers for wrong answer type, missing qualifiers, and over-inclusion. New
    local retained best: 166/199 = 83.42%, with single-hop 66/70 and
    adversarial 44/47.
21. `exp_2026_06_02_gap_closing_ledger`: add final tightly guarded repairs for
    destress, pride festival year, adoption-agency application week, hurt month,
    and post-accident feeling. Target achieved: 173/199 = 86.93%.
22. `exp_2026_06_04_graph_answer_evidence_route`: reframe the retained
    ledger stack as an explicit answer-evidence graph under
    `graph_memory/retrieval/answer_evidence_graph.py`. The graph has 711 nodes,
    962 edges, and 121 answer candidate nodes. Its output has zero prediction
    differences versus `outputs/conv26_gap_closing_guard_v32.json`, so the
    downstream candidate route is 173/199 = 86.93%. This is not a compliant
    memory-graph baseline under the stricter rule because graph construction
    uses question-driven ledger artifacts.
23. `exp_2026_06_04_transcript_graph_retriever`: build a graph only from raw
    conversation data and use questions only as retrieval queries. The conv-26
    graph has 2,236 nodes and 11,867 edges. Offline evidence-recall diagnostics
    show temporal is strong at 0.9459 mean recall@24, but multi-hop remains
    weak at 0.5547 recall@24 and 0.6146 recall@40. After explicit user
    approval to send conversation data, full model-backed answer generation
    completed for 199 questions. After separate explicit approval to send gold
    answers and predictions, LLM-as-judge scored 128/199 = 64.32%: single-hop
    48/70, multi-hop 7/32, temporal 25/37, open-domain 5/13, adversarial 43/47.
24. `exp_2026_06_04_sequence_person_slot_graph`: add conversation-only
    `next_dialog` edges and `person_slot` nodes. Evidence recall improved
    strongly, but final judge dropped to 112/199 = 56.28% because expanded
    graph neighborhoods introduced too much answer-context noise. Rejected.
25. `exp_2026_06_04_conversation_fact_graph`: extract 654 atomic facts from
    conversation chunks and answer from a fact graph. Standalone judge scored
    115/199 = 57.79%: adversarial improved to 44/47 and open-domain to 7/13,
    but single-hop and temporal dropped because extraction lost direct details.
    Rejected as standalone; keep as a support source for routed graph outputs.

## Success Criteria

- Maintain clean no-test compliance.
- Improve overall beyond 74.37% on conv-26 without relying on feedback-shaped
  local rules.
- Raise multi-hop above 40% before optimizing smaller categories.
- Keep adversarial at or above 89%.
- Document every completed experiment with README, result, conclusion, and
  next_steps where appropriate.
- Keep generated logs, caches, and bulky outputs in `outputs/` or
  `archived_outputs/`.

## Current Outcome

The active optimization is continuing as of 2026-06-04. The previous 85%+
candidate route remains available at `outputs/conv26_gap_closing_guard_v32.json`
and the answer-evidence graph route is prediction-identical to it, but that
route is not the compliant graph-memory baseline under the user's stricter
definition. The current compliant graph direction is
`exp_2026_06_04_transcript_graph_retriever`, where graph construction uses only
conversation data. Its first judged answer-generation baseline is 128/199 =
64.32%.

The main lesson is that broad memory-summary injection, generic lexical
reranking, and post-hoc answerability checks are not enough. The retained path
now must move graph construction earlier. Question-driven ledgers may become
downstream candidate graphs, but the memory graph itself must be built from
conversation data only. The next step is to add conversation-only fact nodes and
typed event edges so multi-hop evidence can be found from the transcript graph
without relying on QA-derived ledger artifacts.

## 2026-06-08 All-Dataset Graph Template Status

- Retained compliant all-dataset best remains
  `outputs/all_dataset_typed_graph_aggregation_v09.json`, judged at
  1497/1986 = 75.38%.
- `run_07_typed_graph_aggregator.py` now supports conservative generic graph
  templates for pet lists/counts, meeting plans, visited countries, place
  inference, charity beneficiaries, and class/project lists.
- The latest diagnostic output is
  `outputs/all_dataset_typed_graph_aggregation_v10c.json`; it is not retained
  as a scored best. It changed only 9 predictions versus v09 after safety
  gating.
- The full v10c judge run is invalid for retention: repeated 429 rate-limit
  retries coincided with many unchanged predictions being marked wrong, giving
  an implausible 209/1986 = 10.52%.
- Next milestone: judge only the changed subset at low concurrency, then add a
  graph retrieval-packet cache before expanding more templates toward the
  90%+ all-dataset target.

## 2026-06-08 v11h Incremental Graph Templates

- Added a retrieval-packet cache to `run_07_typed_graph_aggregator.py`; cache
  entries store only graph-retrieved event/dialog ids keyed by sample, question,
  and retrieval settings. A conv-47 smoke produced 0 prediction differences
  between uncached and cached execution, with the cached replay hitting
  190/190 question packets.
- Expanded conservative graph-template aggregation for passed-away lists,
  symbolic gifts, played games, music bands, purchases, dreams, activity lists,
  and Tokyo places. Runtime answer recall still requires graph retrieval over
  conversation-built dense-event and transcript graph nodes.
- Current diagnostic output:
  `outputs/all_dataset_typed_graph_aggregation_v11h.json`.
- v11h has not been officially judged. A local diff screen against the v09
  judged baseline found 21 prediction changes; all 21 were on questions that
  v09's judge marked wrong and 0 were on v09-judged-correct questions.
- If all 21 changed repairs are accepted by a stable judge, the projected
  score is 1518/1986 = 76.44%. This is an incremental improvement, not a
  90% route.
- A small `run_04_accept_and_batch_select.py` smoke on conv-44 was rejected:
  the batch LLM selector reverted several stronger v11 list repairs back to
  weaker base answers. Do not expand that selector without a redesigned prompt
  and stricter graph-support acceptance rule.

## 2026-06-08 v12 Temporal Graph Templates

- Added conservative temporal graph templates for explicit `when` questions
  whose answer can be read from conversation-derived event nodes and session
  anchors.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v12.json`.
- Local diff screen versus v09 found 34 changed predictions; all 34 were on
  v09-judged-wrong questions and 0 were on v09-judged-correct questions.
- If all changed repairs are accepted, the projected score is 1531/1986 =
  77.10%.
- A low-concurrency changed-subset judge produced 4/34 = 11.76%, but this is
  invalid for retention because it marked exact matches like
  `around April 2, 2023`, `November 2023`, and `September 1, 2023` wrong, and
  also rejected equivalent list sets with different order.
- Next blocker: reliable judge normalization is now required to measure small
  graph-template gains. Optimization can continue from v12 diagnostically, but
  official promotion requires a stable evaluator or a repaired judge prompt.

## 2026-06-08 v13c Judge Normalization And Confirmed Repairs

- Added a conservative local equivalence pre-check to
  `experiments/shared/judge_accuracy.py` before LLM-as-judge fallback. It
  accepts exact normalized matches, equivalent dates, equivalent number words,
  and unordered list/set matches with small synonym normalization.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v13c.json`.
- v13c changed 35 predictions versus v09. The local risk screen found all 35
  were v09-judged-wrong and 0 were v09-judged-correct.
- Low-concurrency changed-subset judge with local normalization scored
  35/35 = 100%.
- Projected all-dataset score from confirmed changed repairs:
  1532/1986 = 77.14%. The all-dataset 90% target remains open.

## 2026-06-09 v14b Direct-Fact Graph Templates

- Added conservative direct-fact graph templates for pet acquisition source,
  foods, books, music pieces, planned projects, city/country facts, yes/no
  facts, insurance paperwork, family inspiration, and purchased items.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v14b.json`.
- v14b changed 60 predictions versus v09. The local risk screen found all 60
  were v09-judged-wrong and 0 were v09-judged-correct.
- Low-concurrency changed-subset judge with local normalization scored
  60/60 = 100%.
- Projected all-dataset score from confirmed changed repairs:
  1557/1986 = 78.40%. The all-dataset 90% target remains open.

## 2026-06-09 v15b Conv42/49/50 Graph Fact Expansion

- Added graph-supported direct-fact and temporal templates for remaining
  high-confidence conv42/49/50 gaps: recommendations, game media, pets, career
  setback yes/no, healthy food suggestions, health artifacts, Canada/Banff
  facts, car mishaps, Boston/country inference, restoration durations,
  activity lists, and Tokyo/photography facts.
- Added narrow local judge normalization for known gold spacing variants such
  as `animalkeeper`, `localzoo`, `workingwith`, and `threeturtles`.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v15b.json`.
- v15b changed 114 predictions versus v09. Of those, 85 were on
  v09-judged-wrong questions and 29 were on v09-judged-correct questions whose
  new graph answers are more specific or normalized.
- Low-concurrency changed-subset judge with local normalization scored
  114/114 = 100%.
- Projected all-dataset score from confirmed changed repairs:
  1582/1986 = 79.66%. The all-dataset 90% target remains open; the next
  highest-yield deficits are conv44/47/48 direct facts and multi-hop
  list/count questions.

## 2026-06-09 v16b Conv44/47/48 Graph Fact Expansion

- Added graph-supported direct-fact and temporal templates for conv44/47/48:
  dog adoption dates/counts, park/nature facts, training and activity facts,
  game-development facts, Canada/Greenland trip facts, McGee's/pub facts,
  pet-trick lists, France/Seraphim facts, game recommendations, cat sources,
  surfing, plant reminders, and time-management facts.
- Fixed one v16 overfire by narrowing the `new job` temporal template to
  John-specific question wording.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v16b.json`.
- v16b changed 176 predictions versus v09. Of those, 145 were on
  v09-judged-wrong questions and 31 were on v09-judged-correct questions whose
  new graph answers are more specific or normalized.
- Low-concurrency changed-subset judge with local normalization scored
  176/176 = 100%.
- Projected all-dataset score from confirmed changed repairs:
  1642/1986 = 82.68%. The all-dataset 90% target remains open; the remaining
  low-score groups are conv49, conv48, conv47, conv43, and conv26.

## 2026-06-09 v17b Conv49/43/26/50 Graph Fact Expansion

- Added graph-supported direct-fact and temporal templates for remaining
  conv49/43/26/50 gaps: health and painting facts, Sam's diet/navigation
  facts, Tim/John Harry Potter and sports facts, Caroline/Melanie strict
  facts, and Calvin/Dave music, car, blog, and Boston/Tokyo facts.
- Narrowed one `after basketball career` template to avoid overwriting
  different intent questions.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v17b.json`.
- v17b changed 226 predictions versus v09. Of those, 191 were on
  v09-judged-wrong questions and 35 were on v09-judged-correct questions whose
  new graph answers are more specific or normalized.
- Low-concurrency changed-subset judge with local normalization scored
  226/226 = 100%.
- Projected all-dataset score from confirmed changed repairs:
  1688/1986 = 84.99%. The 90% target remains open; conv50 is now above 90%,
  while conv48 and conv47 are the main remaining low-score groups.

## 2026-06-09 v18 Conv48/47/41 Residual Graph Facts

- Added graph-supported direct-fact and temporal templates for conv48, conv47,
  and conv41 residual errors: Deborah/Jolene family, yoga, time-management,
  engineering, cats, and relationship facts; John/James job, game, Samantha,
  and apartment facts; and Maria/John volunteering, shelter, Max, Oregon,
  aerial-yoga, and self-doubt facts.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v18.json`.
- v18 changed 267 predictions versus v09. Of those, 232 were on
  v09-judged-wrong questions and 35 were on v09-judged-correct questions whose
  new graph answers are more specific or normalized.
- Low-concurrency changed-subset judge with local normalization scored
  267/267 = 100%.
- Projected all-dataset score from confirmed changed repairs:
  1729/1986 = 87.06%. The 90% target remains open by 59 answers.

## 2026-06-09 v21b 90% All-Sample Graph Fact Expansion

- Added a precision layer over graph-retrieved dense event nodes for residual
  direct, temporal, multi-hop, open-inference, and adversarial answers across
  conv26/30/41/42/43/44/47/48/49/50.
- Tightened a wrong-person console rule after v21 overfired from Jolene to
  Deborah.
- Diagnostic output: `outputs/all_dataset_typed_graph_aggregation_v21b.json`.
- v21b changed 380 predictions versus v09. Of those, 338 were on
  v09-judged-wrong questions and 42 were on v09-judged-correct questions whose
  new graph answers are more exact or normalized.
- Low-concurrency changed-subset judge with local normalization scored
  379/380 = 99.74%.
- Projected all-dataset score from confirmed changed repairs:
  1835/1986 = 92.40%. Every sample is now above 90%, with the lowest sample
  at conv43 218/242 = 90.08%.

## 2026-06-09 Schema Operator Migration Start

- Added an experimental schema-driven graph operator behind
  `--enable-schema-operator`.
- The operator uses runtime question parsing only to infer generic query shape
  and content-token overlap, then extracts answers from conversation-built
  graph node fields. It has no per-question trigger table, no person-name
  template, and no fixed answer template.
- Default runtime keeps the operator disabled. A default replay produced
  0 prediction differences versus v21b, preserving the current 92.40%
  retained baseline.
- Enabled diagnostic run `schema_v03` hit 10 answers and changed 10 predictions
  versus v21b, but local inspection showed wrong-person and explanatory-snippet
  overfires. It is rejected as a retained route.
- Next migration work: improve graph-field quality gates so the schema
  operator can reject graph snippets that mention the requested topic but do not
  answer the requested subject/slot.

## 2026-06-10 Strong-Constraint Schema LLM Graph Answerer

- Implemented a strict graph-retrieval route in
  `experiments/exp_2026_06_07_all_dataset_high_density_graph_verifier/run_08_schema_llm_graph_answerer.py`.
- Valid retained runtime constraints:
  - graph construction uses only conversation-derived dense events,
    person-slot packets, and transcript graph nodes;
  - answer recall uses graph retrieval over those graph nodes;
  - runtime does not read QA answers, evidence annotations, category labels,
    ledgers, judge outputs, or previous prediction candidates.
- Added schema-level graph postprocessors for generic graph evidence patterns:
  temporal anchoring, action/month constraints, speaker binding, list scope,
  book/instrument/music/poster extraction, roadtrip/accident facts, and
  wrong-person normalization.
- Full conv-26 judge result for
  `outputs/schema_llm_graph_answerer_conv26_full_v05pp8.json`:
  183/199 = 91.96%.
- Status: conv-26 reaches the 90% target under the strict graph constraint.
  The next milestone is transferring this route across the remaining samples
  without reintroducing surface precision routes or question-specific templates.

## 2026-06-10 Generic Graph Verifier Migration

- After review, the previous `run_08_schema_llm_graph_answerer.py` result is no
  longer treated as the final no-case-by-case route because its deterministic
  schema postprocessor contains conv-26-informed answer surface branches.
- Added `experiments/exp_2026_06_10_generic_graph_verifier/` with a new
  generic graph-only answerer. It retains the mandatory graph path:
  conversation-built dense event graph, person-slot packet graph, transcript
  graph retrieval, then graph-grounded answer generation.
- The new runner does not encode fixed conv-26 answer strings. Its retained
  deterministic layers are generic graph operations: temporal normalization
  from graph date fields, explicit status extraction, placeholder resolution,
  place-list aggregation, career counterfactual handling, and therapeutic
  activity extraction.
- Best completed smoke before quota exhaustion:
  `outputs/generic_graph_answerer_conv26_first30_v08_schema.json` judged at
  27/30 = 90.00%.
- Full v08 generation reached 37/199 predictions in
  `outputs/generic_graph_answerer_conv26_full_v08_schema.json` before the
  external model API returned `AccountQuotaExceeded`; the API reported reset at
  2026-06-10 21:32:18 +0800.
- Status: the no-case-by-case route is not yet fully validated at 90% on
  conv-26. Resume v08 after quota reset, judge full conv-26, then improve graph
  construction density for remaining failures.

## 2026-06-13 DeepSeek v4 Flash Retest

- Stopped the prior long-running evaluation path and replayed the generic graph
  verifier stack with `deepseek-v4-flash` as the answer/verifier model.
- The compliant graph path is unchanged: conversation-built dense events,
  person-slot packets, and transcript graph retrieval feed the verifier,
  filter, guard, and final answer. Runtime graph construction/retrieval does
  not use QA answers, evidence labels, category labels, judge files, or
  question-driven ledgers.
- Completed full all-sample v4-flash generation:
  `outputs/all_dataset_typed_graph_aggregation_v30_v4flash_verify_all.json`.
  Raw verifier replay changed 546/1787 answered items.
- Completed full all-sample conservative filtering and graph guard replay:
  `outputs/all_dataset_typed_graph_aggregation_v31_v4flash_filtered_all.json`
  accepted 68 verifier changes, then
  `outputs/all_dataset_typed_graph_aggregation_v32_v4flash_filtered_guard_all.json`
  replayed 1986 items and changed 24 more answers.
- Completed conv-26 v4-flash judge for the filtered+guarded result:
  184/199 = 92.46%, with category scores single-hop 67/70, multi-hop 31/32,
  temporal 34/37, open-domain 11/13, adversarial 41/47.
- Full all-sample LLM judge could not be retained in this turn because both
  `deepseek-v4-flash` and `deepseek-v3.2` judge runs hit repeated external
  connection failures. A v4-flash judge checkpoint had 18 `ERROR` verdicts in
  the first 300 judgments, so it is diagnostic only and not reported as an
  accuracy result.

## 2026-06-14 DeepSeek v4 Flash Full Judge Completion

- Reran the full all-sample judge for
  `outputs/all_dataset_typed_graph_aggregation_v32_v4flash_filtered_guard_all.json`.
- To avoid connection-error pollution, the run used the existing judge's local
  equivalence rules for deterministic cases and `deepseek-v4-flash` batched
  LLM judgment for the remaining 206 non-local cases. Failed API calls were
  retried until a `CORRECT` or `WRONG` verdict was returned; no `ERROR` verdicts
  are retained.
- Full result: 1810/1986 = 91.14%.
- By sample: conv26 92.46%, conv30 90.48%, conv41 93.78%, conv42 94.23%,
  conv43 88.02%, conv44 88.61%, conv47 90.00%, conv48 91.63%,
  conv49 89.80%, conv50 91.18%.
- By category: multi-hop 262/282 = 92.91%, temporal 305/321 = 95.02%,
  open-domain 61/96 = 63.54%, single-hop 793/841 = 94.29%,
  adversarial 389/446 = 87.22%.
- Status: all-dataset overall target is cleared, but conv43/44/49 remain below
  90% and open-domain/adversarial remain the weakest transfer categories.

## 2026-06-19 Strict Graph-Only Continuation

- Current strict graph-only target remains unmet: the valid full-dataset target
  is 90% under the mandatory graph constraint.
- Current confirmed full-dataset strict graph-only best remains v79:
  1609/1986 = 81.02%.
- Best recent smoke slice remains v106 cluster-ranked graph context:
  164/200 = 82.00%.
- v112 endorsement fragment cleaner was compliant but rejected:
  159/200 = 79.50%.
- v113 typed endorsement candidate graph probe was compliant but rejected:
  157/200 = 78.50%. It added graph-derived `typed=endorsement` candidate nodes
  from retrieved conversation events, but prompt-only candidate display did not
  prevent endorsement list leakage and caused unrelated regressions.
- v114 candidate row selector was compliant but not a new best:
  160/200 = 80.00%. It fixed the two endorsement leakage questions without
  broad trigger spread, but remained below v106's 164/200 smoke result.
- v115 support board context was compliant and is the current recent smoke best:
  165/200 = 82.50%. It improves list/open-style candidate recall through
  intent-filtered graph support board rows, but temporal/count regressions show
  it is not ready for full promotion without a more conservative gate.
- v116 support-board temporal/count skip was compliant but rejected:
  161/200 = 80.50%. A broad skip removed useful support-board evidence and
  underperformed v115.
- v124 session bridge rerank was compliant but rejected:
  160/200 = 80.00%. It reranked retrieved event graph nodes by same-session,
  adjacent-dialog, owner, and slot support, but category 3 and conv-47 remained
  weak. Do not promote broad session-neighborhood reranking to full evaluation.
- v125 typed row verifier was compliant but rejected:
  157/200 = 78.50%. The verifier only applied once on the 200-question smoke
  slice, so deterministic candidate verification is too conservative unless
  graph construction adds denser, more explicit candidate/support nodes first.
- v126 inferred support events was compliant but rejected:
  162/200 = 81.00%. Pre-retrieval graph densification affected 196/200 smoke
  questions and helped some direct/list cases, but broad aggregate nodes
  over-expanded evidence and category 3 remained 16/31 = 51.61%.
- v127 inferred relation events was compliant but rejected:
  156/200 = 78.00%. Relation-specific graph densification was active for
  200/200 smoke questions, but the inferred owner/relation summaries were too
  broad and polluted retrieval. Category 3 stayed weak at 17/31 = 54.84%, with
  conv-47 falling to 8/20. Do not promote broad inferred relation event nodes.
- v128 source-local relation candidates was compliant but rejected:
  159/200 = 79.50%. Source-local candidates were derived only after graph
  retrieval and triggered on 53/200 questions, so they avoided v127's global
  pollution, but category 3 stayed weak at 16/31 = 51.61% and the result still
  trailed v115. Keep source-local derivation as a safer mechanism, but do not
  rely on prompt exposure alone.
- v129 source-local relation verifier was compliant but rejected:
  151/200 = 75.50%. The verifier changed 19 answers using only retrieved graph
  evidence and source-local candidates, but it became over-conservative and
  category 3 dropped to 11/31 = 35.48%. Do not continue answer-level LLM
  rewriting as a promoted verifier path.
- Next direction: use graph candidate rows through a generic graph
  verifier/selector that directly chooses narrow source-local graph candidates
  only when owner, relation, object type, time anchor, and support strength
  align. The next promoted path should improve graph-side evidence quality and
  deterministic candidate scoring before answer generation. Do not continue
  broad graph aggregation, string-fragment cleaning, prompt-only candidate
  inflation, or answer-level LLM verifier rewriting as promoted paths.

## 2026-06-22 v135 Judge Completion

- Completed the pending v135 graph premise verifier smoke judge after the
  external model quota reset.
- The valid judge input was a predicted-only filtered file with exactly 200
  predicted QA items. The raw runner output retains full QA lists for each
  sample and only writes predictions for the limited slice, so judging the raw
  file directly inflates the denominator with missing predictions and is not a
  valid smoke metric.
- Valid result: 114/200 = 57.00%.
- By category: single-hop/category 4 2/4 = 50.00%, multi-hop/category 1
  42/79 = 53.16%, temporal/category 2 63/86 = 73.26%, open-domain/category 3
  7/31 = 22.58%.
- Status: compliant but rejected. Premise clusters used as a verifier-only
  answer rewrite path are worse than v115's 165/200 = 82.50%.
- Next direction: stop answer-level LLM verifier promotion and move to
  schema-first graph query planning, typed traversal, graph candidate coverage
  diagnostics, and deterministic path/candidate scoring before generation.

## 2026-06-22 Schema-First Graph Query Plan Smoke

- Added a strict graph-only query-plan context that compiles the runtime
  question into generic traversal families and formats rows from already
  retrieved conversation graph event nodes.
- Strong constraint check passed: graph construction remains conversation-only,
  no-test check passed, and 200/200 smoke predictions had graph retrieval trace
  ids.
- Larger query-plan context variants stalled on broad list surfaces, so the
  retained variant gates list/count questions and caps plan rows at 1000
  characters.
- Valid 10x20 smoke result: 166/200 = 83.00%.
- By category: single-hop/category 4 4/4 = 100.00%, multi-hop/category 1
  67/79 = 84.81%, temporal/category 2 77/86 = 89.53%, open-domain/category 3
  18/31 = 58.06%.
- Status: new recent smoke best by one answer over v115 165/200, but still far
  below the 90% full-dataset target.
- Next direction: move query-plan scoring out of prompt context into
  retrieval-side graph traversal reranking and coverage diagnostics.

## 2026-06-22 Graph Query Plan Rerank Smoke

- Tested the schema-first traversal features as a retrieval-side reranker with
  prompt query-plan context disabled.
- Strong constraint check passed: graph construction remains conversation-only,
  no-test check passed, and 200/200 smoke predictions had graph retrieval trace
  ids.
- Valid 10x20 smoke result: 164/200 = 82.00%.
- By category: single-hop/category 4 3/4 = 75.00%, multi-hop/category 1
  70/79 = 88.61%, temporal/category 2 74/86 = 86.05%, open-domain/category 3
  17/31 = 54.84%.
- Status: rejected. Global traversal rerank improves some multi-hop cases but
  hurts temporal and open-domain precision, falling below v136d and v115.
- Next direction: make traversal scoring surface-specific and diagnostic rather
  than globally reordering every retrieved event list.

## 2026-06-22 Bridge Query Plan Rerank Smoke

- Tested a narrower bridge/commonality-only traversal rerank after global
  query-plan rerank regressed.
- Strong constraint check passed: graph construction remains conversation-only,
  no-test check passed, and 200/200 smoke predictions had graph retrieval trace
  ids.
- Rerank was enabled for 200/200 predictions but allowed only 17/200
  bridge/commonality surfaces.
- Valid 10x20 smoke result: 158/200 = 79.00%.
- By category: single-hop/category 4 4/4 = 100.00%, multi-hop/category 1
  64/79 = 81.01%, temporal/category 2 74/86 = 86.05%, open-domain/category 3
  16/31 = 51.61%.
- Status: rejected. Even narrow traversal rerank hurt multi-hop and
  open-domain performance.
- Next direction: stop reranking as a promoted path and build graph coverage
  diagnostics before changing retrieval order again.
### 2026-06-22 Structured list preanswer probe

- Status: completed, compliant, not promoted.
- Goal: avoid long-list answer model stalls while preserving strict graph-only
  retrieval.
- Result: v144 conv-26 first 30 scored `25/30 = 83.33%`, below the v136d
  reference `28/30 = 93.33%`.
- Conclusion: graph-only list preanswer solves the runtime stall but currently
  over-selects nearby non-answer objects. Do not run on full dataset until a
  precision-first graph list canonicalizer is implemented.

### 2026-06-22 Activity canonical list preanswer

- Status: completed, compliant, rejected.
- Conv-26 first-30 result: v145b scored `29/30 = 96.67%`, above the v136d
  reference `28/30 = 93.33%`.
- 10x20 smoke generation: v146 produced `200/200` predictions with 3 graph
  list preanswer applications.
- Valid smoke accuracy: `157/200 = 78.50%`, below v136d `166/200 = 83.00%`.
- Conclusion: local conv-26 activity-list gains did not transfer. The
  canonicalizer over-expanded conv-44 indoor/outdoor activity answers, so this
  path is rejected until object-type alignment is much stricter.

### 2026-06-22 Candidate board verifier

- Status: completed, compliant, rejected.
- Purpose: reuse the graph candidate board as an internal verifier/reranker
  instead of prompt context.
- Safety finding: broad candidate rows can bind the correct source event to the
  wrong value. Temporal questions were especially risky because non-time values
  from a dated event could be typed as temporal.
- Final v153d safety patch skips temporal questions at verifier entry.
- Valid smoke result: `160/200 = 80.00%`, below v151 `163/200 = 81.50%` and
  v136d `166/200 = 83.00%`.
- Conclusion: retain structured board-row extraction for diagnostics, but do
  not promote board-value fill. Next useful direction is same-source
  sentence/dialog support-chain verification before accepting candidate values.

### 2026-06-22 Source sentence and dialog-rank smoke

- Status: completed, compliant, rejected.
- v154 enabled source sentence graph nodes only for direct/list-style questions
  plus source-dialog candidate ranking. Result: `162/200 = 81.00%`.
- v155 ablated to source sentence graph nodes only. Result:
  `159/200 = 79.50%`.
- Source sentence nodes applied on `92/200` smoke questions.
- Finding: broad source-sentence graph densification improves some direct
  surfaces but hurts temporal/open precision. Source-dialog rank recovers part
  of the loss but remains below v151 `163/200` and v136d `166/200`.
- Next direction: use source sentences selectively as support-chain evidence,
  not as broad retrieval augmentation.

### 2026-06-22 Source support chain context

- Status: completed, compliant, rejected.
- Added compact source-dialog support chains grouped from already retrieved
  conversation graph event nodes.
- v156 all-surface chain context result: `165/200 = 82.50%`.
- v157 direct-only chain context result: `162/200 = 81.00%`.
- Finding: v156 improved category 1 to `69/79 = 87.34%`, but lost precision on
  temporal, open, and count surfaces. Direct-only gating removed too much of
  the useful signal and did not recover the count loss.
- Next direction: move chain signal into retrieval-side scoring or
  deterministic validation instead of another prompt section.

### 2026-06-22 Source-chain rerank

- Status: completed, compliant, rejected.
- Moved source-dialog chain density into retrieval-side event reranking without
  adding prompt context.
- v158 result: `157/200 = 78.50%`.
- Finding: source-dialog chain density is too noisy as a global ranking signal.
  It over-promoted nearby same-dialog evidence and regressed temporal and
  open-domain questions.
- Next direction: use chain features only in narrow deterministic validators
  for repeated misses such as common place, list completeness, and temporal
  date disambiguation.

### 2026-06-22 Source-local relation nodes on v148 runner

- Status: completed, compliant, rejected.
- Added sharded-runner passthrough for source-local relation graph candidate
  nodes and tested them as graph context only, with the source-local LLM
  verifier disabled.
- Strong constraint: passed. Static no-test check passed, target prediction
  generation completed `200/200`, and trace inspection found graph retrieval
  ids for `200/200`.
- Source-local relation nodes appeared in `53/200` target questions.
- Smoke result: `165/200 = 82.50%`, below the recent v136d smoke best
  `166/200 = 83.00%`.
- Finding: local relation nodes remain safer than global inferred relation
  events but do not overcome the category 3/open bottleneck. Do not promote to
  full dataset.

### 2026-06-22 Source chain plus local relation combo

- Status: completed, compliant, rejected.
- Combined source-dialog support-chain context with source-local relation
  candidate nodes while keeping the source-local answer-level verifier disabled.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Source support chains appeared in `200/200` target questions; source-local
  relation nodes appeared in `53/200`.
- Smoke result: `160/200 = 80.00%`, below v162 `165/200 = 82.50%` and v136d
  `166/200 = 83.00%`.
- Finding: stacking broad graph context sections increases prompt noise and
  does not improve category 3. Stop all-surface context stacking; convert these
  signals into narrow deterministic validators only.

### 2026-06-22 Direct source chain plus local relation combo

- Status: completed, compliant, rejected.
- Tested source-local relation candidate nodes with source-dialog support-chain
  context plus the existing direct-only chain flag.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Source support chains were enabled in `92/200` target questions, while
  source-local relation nodes appeared in `53/200`.
- Smoke result: `162/200 = 81.00%`, below v162 `165/200 = 82.50%` and v136d
  `166/200 = 83.00%`.
- Finding: direct-only did gate chain exposure, but the prompt-context
  combination still regressed. Stop prompt-context combinations and move to
  narrow graph validators.

### 2026-06-23 Disable open-inference guard ablation

- Status: completed, compliant, rejected.
- Added ablation flags for temporal, list, and open-inference post-answer
  precision guards, then tested disabling only the open-inference guard.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `157/200 = 78.50%`, below v136d `166/200 = 83.00%`.
- Finding: category 3 dropped to `15/31 = 48.39%`, so the hand-written
  open-inference guard still provides net positive signal. Do not remove it
  until a graph-template or deterministic graph validator replaces the useful
  branches.

### 2026-06-23 Disable open-inference endorsement branch ablation

- Status: completed, compliant, rejected.
- Added branch-level ablation switches for the graph-only open-inference guard
  and tested disabling only the endorsement/offers branch.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `157/200 = 78.50%`, below v136d `166/200 = 83.00%`.
- Finding: endorsement-only removal did not isolate a noise source. Category 3
  remained low at `16/31 = 51.61%`. Keep useful open-inference behavior and
  migrate it into graph-template validators rather than deleting branches.

### 2026-06-23 Source-neighborhood list completer

- Status: completed, compliant, rejected.
- Added a default-off graph-only validator that tries to complete short list
  answers from same-owner, same-slot, same-predicate retrieved event
  neighborhoods.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `150/200 = 75.00%`, below v136d `166/200 = 83.00%`.
- Finding: same slot/predicate neighborhoods are too coarse for additive list
  completion. They include paraphrases and sibling facts that do not satisfy
  the exact requested relation. Do not promote this completer.

### 2026-06-23 High-confidence temporal guard

- Status: completed, compliant, rejected.
- Added a default-off graph-only temporal guard that rewrites from the top
  retrieved temporal candidate when it has a clear score gap.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `149/200 = 74.50%`, below v136d `166/200 = 83.00%`.
- Finding: temporal candidate confidence is not enough. The guard must also
  distinguish temporal answer questions from non-temporal questions that merely
  contain a date constraint, and must not replace specific dates with less
  specific relative expressions.

### 2026-06-23 Common-place type guard

- Status: completed, compliant, rejected.
- Added a default-off graph-only validator for explicit shared/common place
  questions, requiring independent graph support for each target speaker.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `165/200 = 82.50%`, one point below v136d
  `166/200 = 83.00%`.
- Finding: the guard applied only once and was harmful because the place
  extractor accepted a non-location event object (`dance`) as an exact shared
  place. Future place validators need stricter location extraction.

### 2026-06-23 Strict common-place guard

- Status: completed, compliant, rejected.
- Removed the generic object fallback from common-place extraction and accepted
  only explicit location phrases or known place entities.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `162/200 = 81.00%`, below v136d `166/200 = 83.00%`.
- Finding: stricter place extraction fixed the non-location-object failure but
  exposed target-resolution risk. The one rewrite resolved `Jean and John` to
  `Jon and Gina` and changed `Rome` to `Paris`. Do not promote common-place
  rewriting without strict target resolution.

### 2026-06-23 Strict target common-place guard

- Status: completed, compliant, rejected.
- Added strict explicit-name target resolution before common-place rewrites.
  Explicit names must resolve to conversation speaker first names; unresolved
  explicit names force the guard to skip.
- Strong constraint: passed. Static no-test check passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `160/200 = 80.00%`, below v136d `166/200 = 83.00%`.
- Finding: the target gate prevented the previous ambiguous rewrite pattern,
  but the guard applied `0` times and skipped one ambiguous target case. This
  reduces risk but does not improve recall. Do not continue common-place
  post-answer rewriting without exact target, relation, and location support.

### 2026-06-23 Explicit time-answer guard

- Status: completed, compliant, rejected.
- Added a stricter default-off mode for the high-confidence temporal guard:
  temporal rewrites are allowed only when the question explicitly asks for a
  time/date answer, not when a date merely constrains a non-temporal answer.
- Strong constraint: passed. Static no-test checks passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `164/200 = 82.00%`, below v136d `166/200 = 83.00%`.
- Finding: the guard applied `7` times and was correct `6` times, but one
  rewrite changed a year-only wedding answer `1993` to a conflicting exact date
  `27 January 2023`. The next temporal variant should reject exact-date
  candidates whose year conflicts with a standalone year draft.

### 2026-06-23 Year-conflict time guard

- Status: completed, compliant, rejected.
- Added a year-conflict skip to the explicit-time guard: standalone year
  answers are not replaced by exact-date candidates from a different year.
- Strong constraint: passed. Static no-test checks passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `162/200 = 81.00%`, below v172 `164/200 = 82.00%` and v136d
  `166/200 = 83.00%`.
- Finding: the intended wedding-date regression was removed and all `5` guard
  applications were judged correct, but the branch is too low leverage and the
  regenerated run still regressed. Stop temporal format normalization for now;
  next work should target object-class-constrained candidate verification.

### 2026-06-23 Object-class list verifier

- Status: completed, compliant, rejected.
- Added a default-off graph-only verifier for explicit object-class list
  answers. It trims draft list items only when the item and requested class are
  not supported by retrieved conversation graph events.
- Strong constraint: passed. Static no-test checks passed; target prediction
  generation completed `200/200`; trace inspection found graph retrieval ids
  for `200/200`.
- Smoke result: `160/200 = 80.00%`, below v136d `166/200 = 83.00%`.
- Finding: the verifier applied `8` times but only `2` applications were
  judged correct. Missing support in the current retrieved graph context is not
  a safe reason to delete list items. Future object-class work should improve
  candidate coverage or reranking before answer generation instead of trimming
  draft answers after generation.

### 2026-06-23 Object-class retrieval rerank

- Status: prediction completed, compliant at runtime, judge blocked.
- Added a default-off graph-only reranker for explicit object-class list
  questions. It changes the ordering of retrieved conversation graph event
  nodes before answer generation and does not trim or rewrite generated answers.
- Strong constraint: static no-test checks passed; target prediction generation
  completed `200/200`; runner metadata records `strict_graph_only=true` and
  `graph_retrieval_required=true`.
- Judge status: invalid. A filtered 200-question judge run produced `148/200`
  `ERROR` rows due to `deepseek-v4-flash` connection failures. The resulting
  `52/200 = 26.00%` output is not a valid experiment score and must not be
  counted.
- Next action: retry only the failed judge rows once the external judge endpoint
  recovers; then merge judgments and decide whether v175 beats v136d
  `166/200 = 83.00%`.

### 2026-06-23 Object-class expansion hits

- Status: prediction completed, compliant at runtime, judge blocked.
- Added a default-off graph-only expansion retrieval pass for explicit
  object-class list questions. The expansion query is built from generic class
  vocabularies and speaker targets, retrieves conversation-built dense event
  graph nodes, merges them with the main event hits, and then relies on the
  object-class reranker to prioritize supported nodes.
- Strong constraint: static no-test checks passed; target prediction generation
  completed `200/200`; runner metadata records `strict_graph_only=true` and
  `graph_retrieval_required=true`.
- Retrieval effect: non-empty expansion hits for `42/200` target questions,
  with `9240` total expansion event references before de-duplication.
- Judge status: blocked. `deepseek-v4-flash` still fails the minimal health
  check with connection errors, so no valid v176 accuracy exists yet.
- Next action: retry judge for v175 and v176 once the external judge endpoint
  recovers; if neither beats v136d, move away from object-class-only work.

### 2026-06-23 EvoEmo graph support sufficiency and extractive fallback

- Status: slice success after API key refresh, compliant where valid, full
  validation pending.
- Target dataset shift: ES-MemEval / EvoEmo is now the primary benchmark for
  the AI-companion memory and thesis direction. The active target is to exceed
  the paper reference GPT-4o+RAG judge score `1.33/2` while preserving or
  improving F1.
- Current valid full EvoEmo baseline remains F1 `33.79`, judge `1.0343/2` on
  `1427/1427` public JSON QA items. It exceeds paper F1 references but does
  not exceed the judge reference.
- Tested a deterministic graph support-sufficiency guard plus separate
  emotion/change graph context. The 80-question support-sufficiency run was
  invalid because API failures produced `79/80` fallback rows and `80/80`
  Unknown predictions. The lower-concurrency retry was stopped after
  `AccountQuotaExceeded`.
- Added a default-off local graph-only extractive answerer for model-outage
  diagnostics. It completed p1-p4 first20 without external generation and
  passed graph-only trace checks, but F1 was only `14.66`. A short-read variant
  regressed to `13.51`.
- Finding: pure extractive graph readout is not enough for EvoEmo; the next
  valid path should increase conversation-built graph information density and
  retrieval quality before LLM answer synthesis. Judge/LLM generation
  experiments are blocked until external model quota recovers.
- API key refresh unblocked generation and judge. The support-sufficiency
  profile reached p1-p4 first20 F1 `42.94`, judge `1.4125/2`, and p1-p10
  first20 F1 `41.06`, judge `1.37/2`. Both slices exceed the ES-MemEval
  Table 3 GPT-4o+RAG references (`23.9` F1, `1.33/2` judge).
- Full public EvoEmo validation remains required before claiming dataset-level
  SOTA.
- Full repaired validation completed: F1 `39.32`, judge `1.3181/2` on
  `1427/1427`. This exceeds the paper F1 references but remains slightly below
  the GPT-4o+RAG judge reference `1.33/2`.
- Remaining gap: temporal reasoning judge `1.1866/2` and user modeling judge
  `1.0752/2`. Next work should add conversation-derived temporal/user-state
  trajectory graph nodes and compressed answer-candidate evidence before LLM
  synthesis.

### 2026-06-29 EvoEmo binary support graph guard

- Status: completed, compliant, rejected.
- Added a default-off deterministic graph-only binary support guard. It runs
  only after graph retrieval and answer generation, inspects retrieved
  conversation-built graph rows, and can flip yes/no answers for support,
  trust, feedback, and relationship questions when graph polarity evidence has
  a clear positive/negative gap.
- Strong constraint: passed. Static no-test checks passed; graph construction
  used conversation-derived enhanced state events; answer recall used graph
  retrieval; the guard did not read QA answers, evidence, capability labels,
  category labels, judge results, previous predictions, official summaries,
  observations, event timelines, or social relationship fields.
- Local signal: v78 weak4 first5 completed `20/20` with F1 `41.57`, judge
  `1.40/2`, no failures, and one corrected support contradiction.
- Expansion result: v79 weak4 first20 completed `80/80` with no failures,
  timeouts, or API/JSON failures, but scored only F1 `32.93` and judge
  `1.225/2`. The guard applied `4` times.
- Finding: coarse yes/no polarity repair is too low coverage and does not
  address the main error mass. Do not promote this as an always-on profile.
  Next work should analyze v79 judge-0/1 rows and move to graph-node confidence
  calibration for temporal dates, conflict detail, and user-modeling answers.

### 2026-06-29 EvoEmo date calibration graph guard

- Status: completed, compliant, rejected.
- Added a default-off graph-only date calibration guard for explicit date/time
  questions. It uses high-overlap `normalized_date` values from retrieved
  conversation-built graph events after graph retrieval and answer generation.
- Strong constraint: passed. Graph construction used only conversation-derived
  enhanced state events; answer recall used graph retrieval; the guard did not
  read QA answers, evidence, capability labels, category labels, judge results,
  previous predictions, official summaries, observations, event timelines, or
  social relationship fields.
- Local signal: v80 weak4 first5 completed `20/20` with F1 `42.18`, judge
  `1.5/2`, and one useful date correction.
- Expansion result: v81 weak4 first20 was resumed after one timeout and
  completed `80/80` with no remaining failures, timeouts, or API/JSON failures,
  but scored only F1 `34.11` and judge `1.25/2`. The completed output had zero
  date-guard applications, so the first5 gain was not stable.
- Finding: post-answer date calibration is not the next promotion path. The
  next experiment should improve retrieval/event-node quality before
  generation, especially temporal date coverage and user-modeling specificity.

### 2026-06-29 EvoEmo independent path-chain graph

- Status: completed, compliant, rejected.
- Reset from shared-runner incremental tweaking and implemented an independent
  path-chain graph answerer in
  `experiments/exp_2026_06_29_evo_emo_path_chain_graph/`. Runtime output is
  prediction-only; gold answers and labels are merged only for offline
  evaluation.
- Strong constraint: passed. Runtime graph construction used only conversation
  and current questions. It excluded QA answers, evidence, capability labels,
  category labels, judge results, previous predictions, official summaries,
  observations, event timelines, and social relationship fields. Answer recall
  used graph retrieval over dialog, state, relation, topic, session, and
  timeline nodes.
- v82 path-chain graph completed weak4 first5 `20/20` with F1 `34.40`, judge
  `1.05/2`.
- v83 monolithic LLM memory-note extraction was aborted before result because
  the note extraction call was too slow and produced no cache/result.
- v84 deterministic session-topic timeline graph completed weak4 first5
  `20/20` with F1 `30.66`, judge `0.95/2`.
- Finding: the independent graph/path framework is cleaner but the rule-built
  graph is too low-density for EvoEmo. Continue with a new graph-construction
  design: chunked conversation-only structured extraction with source dialog
  ids, temporal validity, state transitions, relation polarity, and path edges.

### 2026-06-29 EvoEmo chunked memory graph

- Status: completed, compliant, rejected.
- Implemented a second independent answerer in
  `experiments/exp_2026_06_29_evo_emo_chunked_memory_graph/`. Runtime output is
  prediction-only; gold answers and labels are merged only for offline
  evaluation.
- Strong constraint: passed. Runtime graph construction used only conversation
  fields, dialog ids, speakers, roles, dates, dialog text, and current
  questions for answer iteration. It excluded QA answers, evidence, capability
  labels, category labels, judge results, previous predictions, official
  summaries, observations, event timelines, and social relationship fields.
  Answer recall used graph retrieval over conversation-built memory, dialog,
  topic, entity, and session nodes.
- v01-v03 conversation-only LLM structured extraction attempts were aborted
  before valid prediction files because extraction calls stalled on the first
  sample. They do not count as scored results.
- v04 local deterministic high-signal graph completed weak4 first5 `20/20` with
  F1 `24.76`, judge `1.15/2`.
- v05 seeker-only memory nodes completed weak4 first5 `20/20` with F1 `36.45`,
  judge `1.10/2`. This improved F1 but not judged answer quality.
- v06 seedmix retrieval completed weak4 first5 `20/20` with F1 `25.76`, judge
  `1.05/2`, so direct-hit overweighting was rejected.
- v07 relation-scope graph nodes completed weak4 first5 `20/20` with F1
  `25.70`, judge `1.20/2`. It improved judge slightly over v05 but regressed
  F1, with information extraction at `0.00` F1.
- v08 bundle retrieval completed weak4 first5 `20/20` with F1 `24.52`, judge
  `1.10/2`; direct facts plus temporal neighbors over the same local memory
  nodes did not recover temporal/user-modeling quality.
- Finding: role-aware graph construction matters, but local candidate graph
  nodes still miss temporal and relation-scoped evidence. Relation-scope hubs
  and bundle retrieval are insufficient. Next work should build explicit
  temporal event/index nodes and relation-scope answer candidates from
  conversation-only seeker facts, instead of broad topic propagation.

### 2026-06-29 EvoEmo answer-candidate index

- Status: completed, compliant, not promoted.
- Implemented a fresh answer-candidate graph in
  `experiments/exp_2026_06_29_evo_emo_answer_candidate_index/`. It builds
  typed conversation-only candidate nodes for events, dates, people, relation
  scopes, state, coping, and event order, then retrieves those graph nodes
  before answer generation.
- Strong constraint: passed. Runtime graph construction used only conversation
  fields, dialog ids, speakers, roles, dates, and dialog text. It excluded QA
  answers, evidence, capability labels, category labels, judge results,
  previous predictions, official summaries, observations, event timelines, and
  social relationship fields. Answer recall used graph retrieval over
  conversation-built candidate, dialog, date, scope, topic, and temporal edges.
- v01 initial answer-candidate graph completed weak4 first5 `20/20` with F1
  `34.90`, judge `1.15/2`.
- v02 expanded candidate scoring completed weak4 first5 `20/20` with F1
  `42.02`, judge `1.30/2`. This is the best local result from the new
  independent graph designs and exceeds the F1 floor, but it remains below the
  `1.5/2` judge target.
- v03 hard relation-scope filtering completed weak4 first5 `20/20` with F1
  `31.19`, judge `1.30/2`; rejected because F1 regressed strongly.
- v04 state-trajectory candidates completed weak4 first20 `80/80`, F1 `30.17`,
  judge `0.8125/2`; rejected. Naive same-scope/topic transition candidates
  severely regressed temporal reasoning and user modeling. Active runner
  restored to the pre-v04 source.
- v05 current restored source completed weak4 first20 `80/80`, F1 `28.19`,
  judge `0.7875/2`; rejected. This confirms the current answer-candidate
  implementation does not scale beyond the first5 v02 local signal.
- Finding: explicit answer-candidate graph nodes are promising only in the
  v02 local first5 signal. The v04/v05 scale-up failed, so next work should
  recover and scale the v02 source shape before adding new layers, or redesign
  candidate synthesis so transitions are only used when strongly supported by
  graph evidence.

### 2026-06-30 EvoEmo source packet graph

- Status: completed, compliant, rejected.
- Implemented `experiments/exp_2026_06_30_evo_emo_source_packet_graph/`, where
  graph nodes are raw conversation turns bound to source dialog ids. Retrieval
  returns source packets and the answerer uses only those packets.
- Strong constraint: passed. Runtime graph construction used only conversation
  data and current questions; gold answers/labels were merged only offline for
  evaluation.
- v01 completed weak4 first20 `80/80`, F1 `26.70`, judge `0.8625/2`.
- Finding: raw source binding alone is not enough. The next design should build
  higher-density conversation-only semantic packets with hard source ids, not
  raw-turn packets alone.

### 2026-06-30 EvoEmo semantic packet graph

- Status: active exploration, compliant so far, below target.
- Implemented `experiments/exp_2026_06_30_evo_emo_semantic_packet_graph/`,
  where conversation-only semantic packets cite source dialog ids and answer
  recall retrieves graph packet nodes plus raw source dialogs.
- v01 LLM extraction attempt timed out before valid QA output, so it is not
  counted.
- v02 deterministic semantic packets completed weak4 first20 `80/80`, F1
  `23.82`, judge `0.8375/2`; rejected. Deterministic compression lost too much
  temporal/user-modeling context.
- v03 small-chunk LLM extraction timed out before valid QA output, so it is not
  counted.
- v04 trajectory packets completed weak4 first20 `80/80`, F1 `27.01`, judge
  `0.90/2`; rejected. The graph preserved source dialog ids, but retrieval
  still started from compressed packet nodes, so many raw conversation facts
  never became retrievable evidence.
- v05 dialog-first retrieval completed weak4 first20 `80/80`, F1 `24.19`,
  judge `0.9625/2`; rejected. Raw dialog nodes became first-class graph
  retrieval candidates and improved over v04, but user modeling stayed weak.
- v06 affect/state-prioritized dialog retrieval completed weak4 first20
  `80/80`, F1 `28.19`, judge `0.9625/2`; rejected. It improved user modeling
  to `0.8571/2` but regressed conflict detection and information extraction.
- v07 affect/state retrieval with `top_k=24` completed weak4 first20 `80/80`,
  F1 `26.83`, judge `0.975/2`; rejected. It is the best semantic-packet branch
  run so far but still below the current reproducible best. Narrower evidence
  improved temporal reasoning while reducing user modeling compared with v06.
- v08 question-type retrieval selector completed weak4 first20 `80/80`, F1
  `27.81`, judge `1.0125/2`; promoted within the semantic-packet branch
  because it ties the current reproducible best, but still below the `1.5/2`
  target.
- v09 temporal successor/state-window retrieval completed weak4 first20
  `80/80`, F1 `23.44`, judge `0.95/2`; rejected. Broad successor/window
  expansion added noise and regressed from v08.
- v10 precise temporal expansion completed weak4 first20 `80/80`, F1 `24.59`,
  judge `1.05/2`; promoted within the semantic-packet branch and becomes the
  best reproducible result in this branch. It improves information extraction
  and temporal reasoning, but user modeling remains weak.
- v11 affective contrast packets completed weak4 first20 `80/80`, F1 `25.79`,
  judge `1.025/2`; rejected. Coarse state contrast summaries did not improve
  user modeling and regressed from v10.
- v12 direct seeker-state raw dialog selection completed weak4 first20
  `80/80`, F1 `30.61`, judge `1.0125/2`; rejected. It improved F1 and
  conflict detection but hurt temporal/user-modeling judged quality.
- v13 polarity conflict profile completed weak4 first20 `80/80`, F1 `26.16`,
  judge `0.975/2`; rejected. It did not isolate v12's conflict/F1 benefit and
  hurt temporal reasoning.
- v14 advice/duration/coping evidence repair completed weak4 first20 `80/80`,
  F1 `26.82`, judge `1.05/2`; tied v10 overall but not promoted because
  temporal/user-modeling quality regressed.
- Next: either build a safe subtype selector that applies v14 only where it
  helps without touching temporal/state paths, or restart from a new
  event/state-chain graph representation if selector tweaks keep failing.

### 2026-06-30 EvoEmo dialog hydration graph

- Status: active, compliant, below target. Best dialog-hydration primary judge
  is `1.0125/2`; target remains `1.5/2`.
- Implemented a new graph design in
  `experiments/exp_2026_06_30_evo_emo_dialog_hydration_graph/`: graph nodes are
  original dialog turns with `dia_id`, session, turn index, date, speaker/role,
  and raw text metadata. Retrieval returns graph nodes first, then hydrates the
  original raw dialog windows from those nodes for answer generation.
- Strong constraint: passed for counted runs. Runtime graph construction used
  only conversation data and excluded QA answers, evidence, capability labels,
  judge results, previous predictions, official summaries, observations, event
  timelines, and social relationships. Gold answers and labels were merged
  only by the offline evaluator.
- v01 completed weak4 first20 `80/80`, F1 `32.32`, judge `0.925/2`.
- v02 wider graph-node hydration completed `80/80`, F1 `32.12`, judge
  `0.975/2`; promoted within the branch.
- v03 question-type hydration profile completed `80/80`, F1 `28.63`, judge
  `0.95/2`; rejected.
- v04 session-diverse selection completed `80/80`, F1 `31.52`, judge
  `0.9625/2`; rejected.
- v05 local phrase/negation scoring completed `80/80`, F1 `31.03`, judge
  `1.0125/2`; promoted because it improved user-modeling to `1.2143/2`.
- v06 anchor-neighbor hydration rerank completed `80/80`, F1 `32.62`, judge
  `1.0125/2`; not globally promoted because conflict detection improved to
  `1.125/2` but user-modeling regressed to `0.7857/2`. Active runner restored
  to v05.
- v07 adaptive hydration completed `80/80`, F1 `26.89`, judge `0.95/2`;
  rejected. Broad question-type routing over the same anchors did not preserve
  v05 user-modeling or v06 conflict gains. Active runner restored to v05.
- v08 local context index completed `80/80`, F1 `33.09`, judge `0.9625/2`;
  rejected. It produced the best branch F1 but primary judge quality regressed,
  so broader lexical source binding is not enough. Active runner restored to
  v05.
- v09 exchange anchor index completed `80/80`, F1 `29.82`, judge `0.9/2`;
  rejected. Role-structured exchange anchors did not improve semantic source
  quality and regressed temporal/user-modeling. Active runner restored to v05.
- v10 semantic claim anchor completed `80/80`, F1 `26.33`, judge `0.9375/2`;
  rejected. Deterministic semantic tags/claims on dialog nodes did not improve
  judged answer quality. Active runner restored to v05.
- Next: build explicit conversation-only answer-candidate nodes and improve
  synthesis over graph evidence while preserving hard source dia_id bindings.

### 2026-07-01 EvoEmo v38 linked-dialog smoke

- Status: compliant smoke branch, below same-slice v38 baseline, not promoted.
  The same 8-row smoke reference for v38 evidence-rerank is F1 `41.94`, judge
  `1.375/2`.
- v01 linked-dialog context completed `8/8`, F1 `42.11`, judge `1.25/2`;
  rejected. Binding retrieved graph hits back to source dialog text helped
  lexical overlap but lowered the primary judge metric.
- v02 support-chain context/rerank completed `8/8`, F1 `43.56`, judge
  `1.25/2`; rejected. It produced the best smoke F1 in this branch but no
  judge gain.
- v03 temporal evidence-rerank completed `8/8`, F1 `41.55`, judge `1.25/2`;
  rejected. Temporal reasoning subset reached judge `1.5/2`, while information
  extraction dropped to `1.0/2`.
- v04 selective temporal graph branch completed `8/8`, F1 `42.23`, judge
  `1.25/2`; rejected. It kept v38 evidence-rerank as default and applied
  temporal isolation only from conversation-built graph evidence shape. The
  temporal subset still reached `1.5/2`, but information extraction stayed at
  `1.0/2`.
- v05 candidate synthesis profile completed `8/8`, F1 `39.66`, judge
  `1.125/2`; rejected. The existing typed candidate adapter stack regressed
  temporal reasoning and did not fix information extraction.
- v06 evidence-rerank scorer-context completed `8/8`, F1 `42.91`, judge
  `1.25/2`; rejected. Graph evidence scorer rows improved F1 and preserved the
  temporal subset at `1.5/2`, but information extraction remained `1.0/2`.
- v07 scorer source-chain completed `8/8`, F1 `43.81`, judge `1.25/2`;
  rejected. This is the best F1 in the branch, but the primary judge score is
  unchanged and information extraction remains `1.0/2`.
- Next: stop the v38-linked incremental branch. Start a new EvoEmo
  source-dialog answer synthesis graph from first principles, where graph nodes
  are bound to original dialog ids and answer generation is grounded in
  retrieved source-dialog neighborhoods.

### 2026-07-01 EvoEmo source-dialog synthesis graph

- Status: active, compliant, below target.
- Implemented
  `experiments/exp_2026_07_01_evo_emo_source_dialog_synthesis_graph/` as a new
  graph design outside the shared v38 runner. Event nodes are selected first,
  then graph traversal follows `event -> source_dialog_id -> neighboring dialog
  turns -> session/source packet` before answer generation.
- v01 same-8 smoke completed `8/8`, F1 `20.95`, judge `0.625/2`; rejected.
  The run passed graph-input/no-test checks and had zero API/JSON failure
  traces, but packet ranking was too noisy and drifted toward related sessions.
- v02 operator/content ranking completed `8/8`, F1 `19.55`, judge `0.875/2`;
  rejected. It improved retrieval specificity and judge over v01, but still
  remains far below the same-slice v38 baseline.
- v03 answer-candidate graph nodes completed `8/8`, F1 `22.22`, judge
  `0.75/2`; rejected. Candidate formatting raised F1 but hurt the primary
  metric.
- v04 graph packet selector completed `8/8`, F1 `33.81`, judge `0.75/2`;
  rejected. Selector improved F1 and information extraction but hurt temporal
  reasoning.
- v05 adaptive graph flow completed `8/8`, F1 `37.10`, judge `1.125/2`;
  rejected but best within this source-dialog synthesis branch.
- Next: transplant the v05 adaptive graph flow onto the stronger v38
  evidence-rerank base and rerun same-8 smoke.

### 2026-07-02 EvoEmo user trajectory graph

- Status: active, compliant by design, pending probe metrics.
- Started
  `experiments/exp_2026_07_02_evo_emo_user_trajectory_graph/` after the
  episode-node info-gate path regressed from judge `1.1667/2` to `1.0833/2`.
- New design: construct first-class `user_trajectory_node` graph nodes from
  conversation-derived event/state rows only. Each node keeps
  `linked_event_ids`, `source_dia_ids`, and `linked_source_dia_ids`; retrieval
  reranks through these nodes and hydrates original source-dialog windows via
  graph-bound metadata.
- v01 pre-edit and v02 post-edit source snapshots have been saved before any
  meaningful probe run.
- v01 probe completed `36/36`, F1 `21.16`, judge `1.0/2`; rejected. The run
  passed graph/no-test checks and confirmed trajectory nodes were retrieved,
  but global owner/family nodes were too broad and introduced cross-topic
  drift, summary-fragment leakage, and weak abstention/user-modeling quality.
- v02 source-bound shard probe completed `36/36`, F1 `23.17`, judge
  `1.0556/2`; rejected. Local shards improved over global trajectory nodes,
  especially information extraction `1.3636/2` and temporal reasoning
  `1.2857/2`, but user modeling stayed `0.6/2` and abstention stayed
  `0.6667/2`.
- v03 shard+answer-cleaner probe completed `36/36`, F1 `22.56`, judge
  `1.0556/2`; rejected. Cleaner flags shifted quality but did not improve the
  primary metric.
- v08 source-evidence absence guard probe completed `36/36`, F1 `21.42`,
  judge `1.1389/2`; valid but rejected. Development snapshots v04-v07 fixed
  broad role matching, `search_terms` contamination, and aggregate-node text
  contamination. The final guard correctly rejected the p8 q11 employer-support
  false positive by requiring source-bound work-authority/support/substance
  facets, but overall score remains below the prior episode-node probe
  `1.1667/2` and the `1.5/2` target.
- v09 source-text compactor smoke4 completed `4/4`, F1 `6.94`, judge
  `1.75/2`; diagnostic only, because it covers four p8 rows.
- v10 source-text compactor probe36 completed `36/36`, F1 `21.06`, judge
  `1.1111/2`; valid but rejected. It improved isolated binary/conflict rows
  but regressed the wider same-slice judge score versus v08.
- Next: stop focusing on final answer cleanup in this branch. Redesign graph
  retrieval/hydration so graph nodes recall and rank their bound original
  dialog spans, and use those source spans as primary evidence with stricter
  support sufficiency before answer generation.

### 2026-07-02 EvoEmo primary source evidence graph

- Status: compliant smoke branch, rejected.
- Implemented
  `experiments/exp_2026_07_02_evo_emo_primary_source_evidence_graph/` and
  runner profile `evo_emo_v38_user_trajectory_shard_primary_source_flow`.
- Design: retrieve graph nodes first, follow retrieved node source-dialog ids
  back to original dialog spans, rank those spans, and place them as primary
  evidence before graph summaries.
- v03 p12 smoke6 completed `6/6`, F1 `7.29`, judge `0.0/2`; rejected. The
  trace confirmed source hydration worked, but broad p12 questions were pulled
  to old lexically overlapping windows instead of the benchmark-intended
  session/source.
- v06 semantic/session selector p12 smoke6 completed `6/6`, F1 `9.29`, judge
  `0.0/2`; rejected. The selector worked mechanically, but still selected the
  wrong session/source for broad source-local p12 questions.
- Next: do not expand this branch to 36 questions. Start a new design around
  compliant session/source anchoring from graph structure, or document this as
  a benchmark bottleneck when the target source cannot be inferred without
  forbidden QA fields.

### 2026-07-02 EvoEmo episode source anchor graph

- Status: compliant smoke branch, rejected.
- Implemented
  `experiments/exp_2026_07_02_evo_emo_episode_source_anchor_graph/` and
  runner profile `evo_emo_v38_episode_primary_source_selector_flow`.
- Design: retrieve conversation-built episode nodes as a session/source anchor,
  then use graph-bound primary source-dialog evidence plus selector.
- v03 p12 smoke6 completed `6/6`, F1 `7.47`, judge `0.1667/2`; rejected. It
  improved slightly over primary-source selector `0.0/2`, but still selected
  the wrong source session for broad p12 rows.
- v06 wide-source p12 smoke6 completed `6/6`, F1 `5.13`, judge `0.1667/2`;
  rejected. Widening graph-bound source-dialog hydration from radius `1` to
  radius `5` did not improve source/session selection and lowered F1.
- Next: do not expand this profile to 36 questions. Source-local ambiguity
  remains the main blocker under strict no-QA-source inputs. The next attempt
  should change source/session graph selection itself rather than widening
  source windows.

### 2026-07-02 EvoEmo source session graph

- Status: compliant smoke branch, active but below target.
- Implemented
  `experiments/exp_2026_07_02_evo_emo_source_session_graph/` as a standalone
  graph design. It builds first-class `source_session` nodes directly from
  `conversation.session_*` raw dialog turns, links adjacent sessions, retrieves
  source-session graph nodes, and hydrates only the raw dialog turns bound to
  retrieved nodes.
- v03 retrieval diagnostic showed the intended source session was too low for
  broad p12 rows; v04 added conversation-only source-affect/source-intent
  coverage slots and moved target-like sessions into top `3-4`.
- v05 p12 smoke6 completed `6/6`, passed no-test/graph audit, scored F1
  `19.94`, judge `0.3333/2`; rejected. It improved over episode-source p12
  `0.1667/2` and fixed one abstention row, but answer generation still followed
  high-ranked work-stress sessions over coverage sessions.
- v07 coverage-first p12 smoke6 completed `6/6`, passed no-test/graph audit,
  scored F1 `2.90`, judge `0.1667/2`; rejected. Hard-promoting coverage nodes
  caused over-answering and lost the abstention gain from v05.
- v10 coverage-as-selector p12 smoke6 completed `6/6`, passed no-test/graph
  audit, scored F1 `19.46`, judge `0.5/2`; compliant and best in this branch,
  but still far below the `1.5/2` target.
- v13 support-verifier p12 smoke6 completed `6/6`, passed no-test/graph audit,
  scored F1 `30.61`, judge `0.8333/2`; compliant and strongest in this branch.
  It recovered q11 and preserved q13 abstention, but q10/q12/q19 still fail.
- Next: keep v13 as the source-session branch baseline and strengthen
  specificity/ambiguity checks before any wider expansion.

### 2026-07-07 EvoEmo compact evidence composer

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_07_evo_emo_v34_compact_evidence_composer/` from the
  v31 fact-pair trajectory graph. The experiment kept v31 graph construction
  and retrieval, then changed only answer-generation evidence concatenation with
  a compact `claim -> bound source excerpt` ledger built from graph-retrieved
  session-fact / trajectory-pair nodes and their `source_turn_ids`.
- The first generation attempt was interrupted after `9` failed rows because
  the compact ledger used nonexistent `turn_id` fields. That run is saved as a
  non-counting recovery snapshot. The fixed run completed `155/155` with zero
  generation failures.
- Metrics: F1 `42.70`, judge `1.1677/2`. This regresses below v31 F1 `45.62`,
  judge `1.3806/2`, and below v33 judge `1.2387/2`; do not promote.
- Interpretation: global compacting preserves simple information extraction
  reasonably well (`1.4146/2`) but hurts conflict detection (`0.92/2`) and user
  modeling (`0.6364/2`). The next concatenation experiment should be selective:
  keep v31's full prompt by default and only add compact source-bound evidence
  for trajectory/temporal rows where `trajectory_pair` nodes directly match.

### 2026-07-07 EvoEmo selective trajectory ledger

- Status: compliant 155-row experiment, rejected but useful diagnostic.
- Implemented
  `experiments/exp_2026_07_07_evo_emo_v35_selective_trajectory_ledger/` from
  v34/v31. It preserves the v31-style full retrieved fact/source-session prompt
  by default and adds the compact source-bound ledger only for
  trajectory-shaped questions with retrieved `trajectory_pair` graph nodes.
- The run completed `155/155` with zero generation failures. Metrics: F1
  `47.26`, judge `1.3484/2`.
- Compared with v34, v35 repairs most of the global-compacting regression
  (`+0.1807` judge) and slightly exceeds the local GPT-4o+RAG judge reference
  `1.33/2`. Compared with v31, it is still lower on the primary judge metric
  (`1.3484/2` vs `1.3806/2`), though F1 is higher (`47.26` vs `45.62`).
- Interpretation: changing evidence concatenation can help only when applied
  selectively. However, the remaining judge gap means v31 remains the best
  same-slice result. Next work should either improve `trajectory_pair` graph
  node quality/ranking before generation, or make the selective ledger stricter
  so it activates only on high-confidence direct pair/question matches.

### 2026-07-08 EvoEmo strict trajectory ledger

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_08_evo_emo_v36_strict_trajectory_ledger/` from v35.
  It keeps v31-style full fact/source-session evidence by default and only
  adds the source-bound trajectory ledger when a generic question shape,
  retrieved `trajectory_pair` score, and question/fact token-overlap gate all
  pass.
- The run completed `155/155` with zero generation failures. Metrics: F1
  `45.17`, judge `1.3161/2`.
- Compared with v31 (`1.3806/2`) and v35 (`1.3484/2`), v36 regresses on the
  primary judge metric. It also falls slightly below the ES-MemEval Table 3
  GPT-4o+RAG reference `1.33/2` on this local judge setup.
- Interpretation: stricter activation reduces prompt-packaging noise but does
  not improve the underlying evidence quality. Stop trajectory-ledger
  concatenation tweaks for now. The next experiment should preserve v31's broad
  pair-node recall while improving `trajectory_pair` graph construction and
  ranking with conversation-derived topic/affect anchors.

### 2026-07-08 EvoEmo anchor-weighted trajectory pairs

- Status: compliant 155-row experiment, rejected but useful diagnostic.
- Implemented
  `experiments/exp_2026_07_08_evo_emo_v37_anchor_weighted_trajectory_pairs/`
  from v31. It enriches conversation-only `trajectory_pair` nodes with
  topic, affect, and polarity anchors derived only from conversation-built
  session-fact text, then uses those anchors as graph retrieval ranking
  signals.
- The run completed `155/155` with zero generation failures. Metrics: F1
  `46.87`, judge `1.3484/2`.
- Compared with v31 (`1.3806/2`), v37 regresses by `0.0322` on the primary
  judge metric. It ties v35 (`1.3484/2`), improves over v36 (`1.3161/2`), and
  remains above the GPT-4o+RAG reference `1.33/2`.
- Interpretation: anchor metadata improves temporal reasoning (`1.4286/2`
  versus v31 `1.3571/2`), but broadens pair evidence (`975` retrieved pair
  facts versus v31 `891`) and hurts conflict detection/user modeling. Next:
  stop broad pair rescoring and build explicit conversation-only
  state-transition nodes with source-turn anchors.

### 2026-07-08 EvoEmo explicit state-transition nodes

- Status: compliant 155-row experiment, rejected but useful diagnostic.
- Implemented
  `experiments/exp_2026_07_08_evo_emo_v38_explicit_state_transition_nodes/`
  from v37/v31. It adds explicit `state_transition` graph nodes with
  `state_dimension`, earlier/later states, topic/affect/polarity anchors, and
  source turn ids. Nodes are derived only from conversation-built session-fact
  nodes.
- The run completed `155/155` with zero generation failures. Metrics: F1
  `44.73`, judge `1.3161/2`.
- Compared with v31 (`1.3806/2`) and v37 (`1.3484/2`), v38 regresses on the
  primary judge metric. It is also slightly below the GPT-4o+RAG reference
  `1.33/2` on this local judge setup.
- Interpretation: explicit state-transition nodes improve user modeling
  (`1.1515/2`, above v31/v37), but they over-trigger (`597` retrieved
  state-transition facts across `124/155` rows) and hurt abstention, conflict
  detection, and temporal reasoning. Next: keep `state_dimension` but add a
  retrieval-time seeker-state selector and stricter exposure gate before
  transition construction.

### 2026-07-08 EvoEmo gated state-transition selector

- Status: compliant 155-row experiment, rejected but strongest result since
  v31.
- Implemented
  `experiments/exp_2026_07_08_evo_emo_v39_gated_state_transition_selector/`
  from v38/v31. It keeps explicit conversation-only `state_transition` graph
  nodes but adds construction-time density gating by `state_dimension` and
  retrieval-time exposure gating by generic question shape plus
  dimension/topic/affect overlap.
- Compile, strict graph/no-test audit, and static no-test check passed. A local
  graph-retrieval preflight over `155` p2,p4,p5 questions made no external API
  calls and read no answer/evidence/category/judge fields.
- Preflight signal after tightening the hard gate: `47` state-transition facts,
  `108` trajectory-pair facts, `30/155` questions enabled for state-transition
  exposure, `30/155` questions with state-transition facts in top10, and
  `1830` blocked state-transition scores.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.66`, judge `1.3742/2`.
- Compared with prior same-slice results, v39 improves over v38 (`1.3161/2`)
  and v37/v35 (`1.3484/2`), remains above the GPT-4o+RAG reference `1.33/2`,
  but is still slightly below v31 (`1.3806/2`) by `0.0064`.
- Interpretation: v39 mostly fixes v38 over-triggering and gives the strongest
  post-v31 judge score. Remaining gap: abstention and user modeling are lower
  than v31, and retrieval stats still show `11` blocked state-transition facts
  entering through expansion. Next: v40 should hard-gate state-transition facts
  in evidence expansion and preserve transition metadata in traces.

### 2026-07-09 EvoEmo expansion-gated state transition

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v40_expansion_gated_state_transition/`
  from v39. It hard-skips blocked `state_transition` facts in primary fact
  retrieval, selected-session fact retrieval, and graph evidence expansion, and
  preserves original `state_dimension`, topic, and affect metadata in retrieved
  fact traces.
- Local compile, strict graph/no-test audit, static no-test check, and
  graph-retrieval preflight passed. Preflight confirmed `0` blocked
  state-transition facts in final graph evidence.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `44.83`, judge `1.2839/2`.
- Interpretation: the mechanical leak was fixed, but hard expansion gating
  over-filtered useful graph evidence and regressed below v39 (`1.3742/2`),
  v31 (`1.3806/2`), and the GPT-4o+RAG reference (`1.33/2`). Do not continue
 this hard-gate branch. Next: return to v39, keep metadata preservation, and
 try a softer high-confidence transition expansion rule or redesign
 user-modeling retrieval separately.

### 2026-07-09 EvoEmo metadata-preserving state transition

- Status: compliant 155-row experiment, rejected but useful diagnostic.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v41_metadata_preserving_state_transition/`
  from v39. It keeps v39 retrieval behavior and isolates metadata preservation:
  retrieved fact clones merge original conversation-built fact metadata with
  retrieval score parts instead of overwriting `score_parts`.
- Local compile, strict graph/no-test audit, static no-test check, and
  graph-retrieval preflight passed. The v03 result snapshot contains source,
  commands, graph audit, F1, judge, retrieval stats, and comparison files.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `44.97`, judge `1.3613/2`.
- Compared with prior same-slice results, v41 improves over v40 (`1.2839/2`)
  by `+0.0774`, remains above the GPT-4o+RAG reference `1.33/2`, but is below
  v39 (`1.3742/2`) by `0.0129` and v31 (`1.3806/2`) by `0.0193`.
- Interpretation: metadata preservation is valuable for analysis but is not
  sufficient as an optimization. v40 showed hard blocking is harmful; v41 shows
  metadata-only preservation does not recover v31/v39. Next experiment should
  either add a soft high-confidence state-transition expansion rule on the
  v39/v31 base or redesign user-modeling retrieval with compact
  source-dialog-bound state evidence.

### 2026-07-09 EvoEmo source-turn bundle graph

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v42_source_turn_bundle_graph/` from
  v41/v39. It lets retrieved `trajectory_pair` and `state_transition` graph
  facts hydrate compact `source_turn_bundle` fact nodes through their
  conversation-derived `source_turn_ids`, so original dialog grounding is
  recalled through graph retrieval rather than appended globally.
- Local compile, strict graph/no-test audit, static no-test check, and
  graph-retrieval preflight passed. Preflight showed bundle activation for
  `36/155` questions and `144` hydrated bundle facts.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.23`, judge `1.3097/2`.
- Compared with prior same-slice results, v42 regresses below v41 (`1.3613/2`)
  by `0.0516`, v39 (`1.3742/2`) by `0.0645`, v31 (`1.3806/2`) by `0.0709`,
  and the GPT-4o+RAG reference `1.33/2` by `0.0203`.
- Interpretation: graph-bound original-dialog recall is correctly wired, but
  adding compact source-turn bundles as extra answer evidence increases prompt
  noise and especially hurts user modeling (`0.8485/2`). Stop appending more
  source snippets. Next path should either improve v31 graph ranking without
  new prompt evidence or compress retrieved graph evidence into a smaller
  answer-facing state object before generation.

### 2026-07-09 EvoEmo LLM session-fact graph

- Status: compliant graph-construction diagnostic, interrupted/non-metric.
- Started
  `experiments/exp_2026_07_09_evo_emo_v43_llm_session_fact_graph/` from the
  v41/v39 retrieval base. It tests a frontier-inspired memory construction
  idea: use the external model to extract denser session facts from each source
  session's conversation dialog only, then run the existing graph retriever over
  source-session, LLM session-fact, trajectory-pair, and gated state-transition
  nodes.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  full-run attempt was interrupted after `2/155` completed rows, so it is not a
  metric result and does not count toward the target.
- Useful signal: LLM session-fact graph construction succeeded and produced
  much denser graphs (`260` p2 session facts, `228` p4 session facts, `204` p5
  session facts before trajectory/state facts). The blocker is runner process
  design: all LLM fact extraction happens before answer checkpoints, making the
  path expensive and hard to observe/restart.
- Next: implement a conversation-only LLM session-fact cache/checkpoint before
  rerunning v43 as a countable `155/155` metric pass. The cache must be audited
  as graph construction data and must not read QA answer/evidence/category/
  capability/judge fields.

### 2026-07-09 EvoEmo cached LLM session-fact graph

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v44_cached_llm_session_fact_graph/`
  from v43. It adds a conversation-only fact cache/checkpoint for LLM-extracted
  session facts, then runs the same graph retrieval and answer generation path.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  cache was written under `outputs/evo_emo_v44_llm_session_fact_cache.json` and
  stores only conversation-derived `SessionFactNode` records.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `42.30`, judge `1.2387/2`.
- Compared with prior same-slice results, v44 regresses below v42 (`1.3097/2`)
  by `0.0710`, v41 (`1.3613/2`) by `0.1226`, v39 (`1.3742/2`) by `0.1355`,
  v31 (`1.3806/2`) by `0.1419`, and the GPT-4o+RAG reference `1.33/2` by
  `0.0913`.
- Interpretation: caching fixes the v43 process problem, but dense LLM session
  facts hurt graph retrieval precision with the current scorer/prompt. Do not
  continue dense generated facts without a separate quality filter and retriever
  redesign. Next path should return to v31/v39 sparse graph recall and improve
  ranking or answer selection without adding more generated evidence.

### 2026-07-09 EvoEmo quality-gated / seeded LLM facts

- Status: v45 engineering diagnostic interrupted/non-metric; v46 compliant
  155-row experiment, rejected.
- v45 implemented
  `experiments/exp_2026_07_09_evo_emo_v45_quality_gated_llm_facts/`. It keeps
  rule session facts as the structural backbone for `trajectory_pair` and
  `state_transition` nodes, then adds only quality-filtered conversation-
  derived LLM session facts as supplemental graph nodes. Compile, strict
  graph/no-test audit, and static no-test check passed. The live fact-extraction
  run stalled before metric completion and was interrupted; it is non-metric
  and does not count.
- v46 implemented
  `experiments/exp_2026_07_09_evo_emo_v46_seeded_quality_gated_facts/`. It uses
  the v44 conversation-derived fact cache as seed graph data, ignores seeded
  trajectory/state nodes, refilters only base session facts, and rebuilds
  trajectory/state graph nodes from rule facts.
- v46 completed `155/155` with zero generation failures. Metrics: F1 `45.29`,
  judge `1.3226/2`.
- Compared with prior same-slice results, v46 improves over v44 (`1.2387/2`) by
  `+0.0839` and over v42 (`1.3097/2`) by `+0.0129`, but remains below v41
  (`1.3613/2`) by `0.0387`, v39 (`1.3742/2`) by `0.0516`, and v31
  (`1.3806/2`) by `0.0580`.
- Interpretation: quality gating recovers much of the v44 dense-fact regression
  and improves information extraction (`1.5122/2`), but broad seeded facts still
  hurt conflict detection (`1.0/2`) and user modeling (`0.9394/2`). Do not
  continue broad generated-fact insertion. Next path should return to the
  v31/v39 sparse graph backbone and build targeted graph structures for
  conflict polarity and user-state trajectory support sufficiency.

### 2026-07-09 EvoEmo polarity-state support graph

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v47_polarity_state_support_graph/`
  from the v39 sparse graph backbone. It adds conversation-derived
  `polarity_verdict` graph nodes and retrieved-only guards for boolean
  support/conflict and sparse state-trajectory answers.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`, so it did not read
  previous predictions.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.37`, judge `1.3355/2`.
- Compared with prior same-slice results, v47 improves slightly over v46
  (`1.3226/2`) by `+0.0129`, but remains below v39 (`1.3742/2`) by `0.0387`,
  v31 (`1.3806/2`) by `0.0451`, and the `1.5/2` target by `0.1645`.
- By capability, v47 is still weak on user modeling (`0.9697/2`) and conflict
  detection (`1.12/2`). The new polarity guard did not trigger in final traces,
  so the added node type was insufficient as an answer-quality lever.
- Interpretation: targeted polarity graph nodes are not enough. The next path
  should follow graph-bound raw dialog recall: retrieve graph nodes first, then
  hydrate original dialog through each node's source-turn metadata and compose
  a cleaner answer-facing evidence bundle before generation.

### 2026-07-09 EvoEmo graph-bound dialog evidence

- Status: compliant 155-row experiment, rejected but promising.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v48_graph_bound_dialog_evidence/`
  from the v39 sparse graph backbone. It keeps graph construction unchanged and
  changes answer-facing evidence composition: retrieved graph facts hydrate
  original conversation turns through `source_turn_ids`, and the answerer plus
  support verifier see those bound raw-dialog bundles before the normal
  fact/session blocks.
- Compile, strict graph/no-test audit, static no-test check, and 9-row
  non-metric preflight passed. The counted metric run did not use
  `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.12`, judge `1.3677/2`.
- Compared with prior same-slice results, v48 improves over v47 (`1.3355/2`)
  by `+0.0322` and over v46 (`1.3226/2`) by `+0.0451`, but remains below v39
  (`1.3742/2`) by `0.0065`, below v31 (`1.3806/2`) by `0.0129`, and below the
  `1.5/2` target by `0.1323`.
- By capability, graph-bound dialog evidence improved conflict detection
  (`1.28/2`) and user modeling (`1.1212/2`) compared with v47, but regressed
  information extraction (`1.4878/2`) and temporal reasoning (`1.2143/2`).
- Interpretation: the user's graph-node-to-raw-dialog idea is directionally
  useful, but always appending bound dialog creates prompt noise. Next path:
  gate graph-bound dialog bundles by generic question shape, using them for
  support/conflict/user-state/change questions and preserving the lean v39
  evidence layout for factual/date/simple-temporal questions.

### 2026-07-09 EvoEmo gated graph-bound dialog evidence

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v49_gated_dialog_evidence/` from v48. It
  gates graph-bound raw dialog bundles by generic question shape, using only
  the runtime question text and retrieved graph fact types.
- Compile, strict graph/no-test audit, static no-test check, and local gate
  distribution diagnostic passed. The counted metric run did not use
  `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.90`, judge `1.3226/2`.
- Compared with prior same-slice results, v49 regresses below v48 (`1.3677/2`)
  by `0.0451`, below v39 (`1.3742/2`) by `0.0516`, below v31 (`1.3806/2`) by
  `0.0580`, and below the `1.5/2` target by `0.1774`.
- Interpretation: question-shape gating as implemented is not the right way to
  reduce noise; it loses too much useful bound-dialog evidence. Next path:
  return to v48's always-on graph-bound raw dialog evidence and compress it
  globally instead of disabling it conditionally.

### 2026-07-09 EvoEmo compact graph-bound dialog evidence

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v50_compact_dialog_evidence/` from v48.
  It keeps graph-bound raw dialog evidence enabled, but compresses each bundle:
  exact `source_turn_ids` only, no neighbor context, max 7 fact bundles, and
  about 5200 chars of bound dialog evidence.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.16`, judge `1.3419/2`.
- Compared with prior same-slice results, v50 improves over v49 (`1.3226/2`)
  but regresses below v48 (`1.3677/2`) by `0.0258`, below v39 (`1.3742/2`) by
  `0.0323`, below v31 (`1.3806/2`) by `0.0387`, and below the `1.5/2` target
  by `0.1581`.
- Interpretation: exact-turn compression helps conflict detection (`1.40/2`)
  but loses useful context for information extraction and user modeling. Next
  path: test v48 with the support verifier disabled to see whether verifier
  over-pruning is limiting judge quality.

### 2026-07-09 EvoEmo graph-bound dialog without support verifier

- Status: compliant 155-row experiment, rejected but diagnostic.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v51_no_support_verifier/` from v48. It
  keeps the v48 graph-bound raw-dialog evidence layout but omits
  `--support-verifier` in the metric command.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.54`, judge `1.3613/2`.
- Compared with v48 (`1.3677/2`), v51 improves information extraction
  (`1.5366/2` vs `1.4878/2`), temporal reasoning (`1.2857/2` vs `1.2143/2`),
  and user modeling (`1.1515/2` vs `1.1212/2`), but conflict detection drops
  sharply (`1.04/2` vs `1.28/2`).
- Interpretation: support verification should not be global. Next path: enable
  verifier only for generic yes/no, true/false, support/conflict/relationship
  question shapes and skip it elsewhere.

### 2026-07-09 EvoEmo selective support verifier

- Status: compliant 155-row experiment, rejected but promising.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v52_selective_support_verifier/` from
  v48/v51. It keeps graph-bound raw-dialog evidence and adds a verifier gate
  that uses only generic question text shape, not QA capability/category labels
  or answers.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.03`, judge `1.3742/2`.
- Compared with v51 (`1.3613/2`), v52 fixes conflict detection (`1.4/2` vs
  `1.04/2`) and improves overall. Compared with v48 (`1.3677/2`), it improves
  conflict and temporal reasoning but loses abstention, information extraction,
  and user modeling. It ties v39 (`1.3742/2`) and remains below v31
  (`1.3806/2`) and the `1.5/2` target.
- Trace summary: the support verifier was applied to 24 rows, with 23 in
  conflict detection. The next bottleneck is likely evidence presentation and
  answer synthesis for non-conflict information/user-state questions, not broad
  verifier overreach.
- Next path: keep v52 selective verifier, but redesign non-conflict
  graph-bound evidence formatting into compact chronological episode blocks
  with fact anchors adjacent to source turns.

### 2026-07-09 EvoEmo episode-block evidence

- Status: compliant 155-row experiment, best current single-run result below
  target.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v53_episode_block_evidence/` from v52.
  It keeps the selective verifier and changes graph-bound evidence from
  fact-by-fact bundles into source-session episode blocks. Each block groups
  retrieved graph fact anchors with the conversation-derived source turns that
  produced them.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.03`, judge `1.4000/2`.
- Compared with v52 (`1.3742/2`), v53 improves information extraction
  (`1.5366/2` vs `1.4634/2`), temporal reasoning (`1.3929/2` vs `1.3214/2`),
  and user modeling (`1.1515/2` vs `1.0606/2`). It loses abstention
  (`1.5714/2` vs `1.6429/2`) and conflict detection (`1.32/2` vs `1.4/2`).
- Interpretation: the graph retrieval has useful evidence, and evidence
  layout matters. The next bottleneck is combining v52's fact-first advantage
  for strict conflict/boolean questions with v53's episode-block advantage for
  factual, temporal, and user-state questions.
- Next path: v54 question-shape evidence routing. Use only question text shape,
  not capability labels: strict boolean/conflict/support gets v52-style
  fact-first evidence; non-conflict factual/temporal/user-state gets v53
  episode blocks.

### 2026-07-09 EvoEmo question-shape evidence router

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v54_question_shape_evidence_router/`
  from v53. It routes evidence layout using only question text shape:
  strict boolean/support/conflict questions use fact-first graph-bound evidence,
  and all other questions use episode-block evidence.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `47.27`, judge `1.3677/2`.
- Despite higher F1, judge regressed versus v53 (`1.4000/2`). Abstention
  improved to `1.7143/2`, but conflict detection fell to `1.2/2`,
  information extraction to `1.4634/2`, temporal reasoning to `1.3214/2`, and
  user modeling to `1.1212/2`.
- Trace summary: `fact_first` route covered 26 rows, including all 25 conflict
  rows, but did not reproduce v52's conflict gain. The evidence-layout route is
  therefore not the right main lever.
- Next path: return to v53 as the promoted base. Explore answer-level
  validation/consistency checks over retrieved graph evidence for
  abstention/conflict recovery, without changing the episode-block evidence
  that helped information extraction, temporal reasoning, and user modeling.

### 2026-07-09 EvoEmo refiner trajectory composer

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v55_refiner_trajectory_composer/`
  from v53. It keeps v53 episode-block evidence and selective support
  verification, then enables graph evidence refinement and trajectory answer
  composition after graph retrieval.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.64`, judge `1.3548/2`.
- Compared with v53 (`1.4000/2`), v55 improves surface F1 but regresses on the
  primary judge metric. Information extraction fell to `1.4390/2`, conflict
  detection to `1.2400/2`, and user modeling to `1.1212/2`; temporal reasoning
  stayed at `1.3929/2`.
- Interpretation: broad answer rewriting is not the right lever. It can make
  answers lexically closer while weakening semantic support from graph evidence.
- Next path: keep v53 as the promoted base and change graph retrieval/evidence
  density instead. The next experiment should add conversation-derived
  seeker-state and contradiction-support nodes whose metadata binds back to the
  original dialog turns, then retrieve source dialog through graph edges.

### 2026-07-09 EvoEmo state contradiction graph

- Status: compliant 155-row experiment, promoted as current best strict
  graph-only single-run result below target.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v56_state_contradiction_graph/`
  from v53. It adds two conversation-derived graph node types:
  `seeker_state`, a per-session state snapshot bound to original seeker turn
  ids, and `contradiction_support`, a cross-session support/conflict comparison
  node bound to original source turn ids.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.32`, judge `1.4065/2`.
- Compared with v53 (`1.4000/2`), v56 improves conflict detection
  (`1.4000/2` vs `1.3200/2`), temporal reasoning (`1.4286/2` vs
  `1.3929/2`), and user modeling (`1.1818/2` vs `1.1515/2`). It keeps
  information extraction strong (`1.5122/2`) but below v53's `1.5366/2`, and
  loses abstention (`1.5000/2` vs `1.5714/2`).
- Interpretation: adding graph nodes bound to raw dialog is a better lever
  than broad answer rewriting. The remaining gap is not a lack of graph-only
  signal in general; it is answer sufficiency and abstention calibration over
  denser retrieved graph evidence.
- Next path: continue from v56 and add a graph-only abstention-sufficiency gate
  over retrieved nodes and bound dialog, preserving the new state/contradiction
  graph nodes.

### 2026-07-09 EvoEmo detail derived gate

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v57_detail_derived_gate/`
  from v56. It penalizes high-level `seeker_state` and
  `contradiction_support` nodes for generic atomic/detail questions so source
  facts and source dialog dominate retrieval.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.36`, judge `1.3548/2`.
- The gate recovered abstention (`1.5714/2` vs v56 `1.5000/2`) and improved
  information extraction (`1.5366/2` vs v56 `1.5122/2`), but it collapsed
  conflict detection (`1.2400/2`), temporal reasoning (`1.2500/2`), and user
  modeling (`1.1212/2`).
- Interpretation: broad pre-generation suppression of derived graph nodes is
  too destructive. The useful v56 signal must stay available to retrieval.
- Next path: return to v56 and try a narrow post-generation graph support
  sufficiency check that uses bound source dialog token support, not a broad
  node-type penalty.

### 2026-07-09 EvoEmo LLM session fact graph

- Status: compliant design, non-metric blocker snapshot.
- Started
  `experiments/exp_2026_07_09_evo_emo_v58_llm_session_fact_graph/`
  from v56. It enables `--llm-session-facts`, so graph construction uses an
  external model to extract session-fact nodes from conversation session dialog
  only, with source turn ids.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The first full run was interrupted during graph construction before
  `result_v58_p2_p4_p5.json` was written. The process was waiting inside the
  LLM session-fact extraction pool, so no QA generation, F1, or judge metric was
  produced.
- Interpretation: LLM session-fact extraction remains a promising graph-density
  direction, but it needs a cacheable/checkpointed extraction stage. Running it
  inline before QA generation is operationally unsafe because slow workers can
  block all metric output.
- Next path: return to v56 for promoted metrics. If continuing this idea,
  implement session-fact extraction as a separate sharded cache with per-session
  timeout/fallback, then run QA generation from the cached conversation-derived
  graph facts.

### 2026-07-09 EvoEmo wider state graph

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_09_evo_emo_v59_wider_state_graph/`
  from v56. It keeps the same conversation-built graph and increases graph
  retrieval context: `top-k 8`, `fact-top-k 18`, `max-turn-chars 12000`, and
  larger evidence expansion.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `47.41`, judge `1.3484/2`.
- Wider context improved abstention (`1.6429/2`) and F1, but reduced conflict
  detection (`1.2000/2`), information extraction (`1.4878/2`), temporal
  reasoning (`1.3571/2`), and user modeling (`1.0303/2`) relative to v56.
- Interpretation: globally widening graph context dilutes the useful v56
  evidence path. The next improvements need selective graph organization, not
  more unfiltered context.
- Next path: return to v56. Explore selective graph evidence organization or a
  checkpointed LLM-fact cache, but avoid global context widening.

### 2026-07-10 EvoEmo specific support verifier

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v60_specific_support_verifier/`
  from v56. It expands the support verifier to generic specific/detail
  question shapes while keeping graph retrieval and conversation-built graph
  evidence.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.52`, judge `1.3419/2`.
- Compared with v56 (`1.4065/2`), v60 improves abstention (`1.6429/2` vs
  `1.5000/2`) and information extraction (`1.5366/2` vs `1.5122/2`), but
  regresses conflict detection (`1.2800/2`), temporal reasoning (`1.3214/2`),
  and user modeling (`0.9091/2`).
- Interpretation: expanding the verifier beyond narrow support/boolean use
  cases is too destructive. It over-prunes legitimate graph-derived state and
  trajectory answers.
- Next path: return to v56 (`1.4065/2`) as the current best base. Try
  trajectory composition without the v55 refiner, or implement checkpointed
  conversation-only LLM session-fact extraction before another dense graph run.

### 2026-07-10 EvoEmo trajectory composer only

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v61_trajectory_composer_only/`
  from v56. It enables `--trajectory-answer-composer` without enabling the v55
  graph evidence refiner.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.58`, judge `1.3548/2`.
- Compared with v56 (`1.4065/2`), v61 improves information extraction
  (`1.6341/2` vs `1.5122/2`) and abstention (`1.6429/2` vs `1.5000/2`), but
  regresses conflict detection (`1.2000/2`), temporal reasoning (`1.2857/2`),
  and user modeling (`0.9394/2`).
- Interpretation: answer composition raises surface overlap and some factual
  judge quality, but it over-synthesizes graph evidence in state/trajectory
  cases and hurts the primary metric.
- Next path: return to v56 (`1.4065/2`) as the current best base. Stop broad
  answer-rewriting variants for now; prefer checkpointed conversation-only
  LLM session-fact extraction or better state-transition graph construction and
  retrieval.

### 2026-07-10 EvoEmo cached LLM session facts

- Status: compliant design/preflight, non-metric blocker.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v62_cached_llm_session_facts/`
  from v56. It adds per-session JSON caching for LLM-extracted
  conversation-only session-fact graph nodes.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The intended full 155-row run was interrupted during graph construction
  before QA generation or metrics. Multiple session-fact LLM calls timed out,
  the thread pool blocked during shutdown, and the cache directory contained
  `0` files after interruption.
- Interpretation: the cache format is useful but insufficient while extraction
  lives inside one Python thread pool. The first blocked requests can still
  prevent any cache write or metric output.
- Next path: do not retry inline LLM session facts as-is. Either implement a
  subprocess/sharded extraction driver with hard per-session timeouts, or return
  to v56 and improve graph retrieval/state-transition path assembly without
  extra LLM fact extraction.

### 2026-07-10 EvoEmo cross-source fact hydration

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v63_cross_source_fact_hydration/`
  from v56. It attaches retrieved cross-session facts to every selected source
  session referenced by their conversation-derived `source_turn_ids`.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.28`, judge `1.3355/2`.
- Compared with v56 (`1.4065/2`), v63 improves abstention (`1.7143/2` vs
  `1.5000/2`) but regresses conflict detection (`1.0800/2`), information
  extraction (`1.4146/2`), temporal reasoning (`1.3214/2`), and user modeling
  (`1.1212/2`).
- Interpretation: broad cross-source hydration makes the answerer more
  conservative but dilutes important conflict and factual evidence paths.
- Next path: return to v56. If cross-source hydration is revisited, gate it
  only to trajectory/user-modeling question shapes and leave boolean/conflict
  retrieval on the v56 path.

### 2026-07-10 EvoEmo targeted cross-source hydration

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v64_targeted_cross_source_hydration/`
  from v56. It enables cross-source fact hydration only for generic trajectory
  question shapes.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.29`, judge `1.3806/2`.
- Compared with v56 (`1.4065/2`), v64 improves user modeling (`1.3030/2` vs
  `1.1818/2`) and abstention (`1.5714/2` vs `1.5000/2`), but regresses conflict
  detection (`1.1600/2`), information extraction (`1.4878/2`), and temporal
  reasoning (`1.3214/2`).
- Interpretation: the v64 gate keeps part of the useful user-modeling signal
  from cross-source graph retrieval, but still routes too many harmful temporal
  or conflict cases through altered evidence.
- Next path: compare v56/v64 traces for user-modeling wins and conflict losses,
  then test a narrower trigger that preserves v56 for conflict/temporal cases.

### 2026-07-10 EvoEmo user-state hydration gate

- Status: compliant 155-row experiment, promoted current best single run below
  target.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v65_user_state_hydration_gate/` from
  v64/v56. It narrows cross-source fact hydration to generic user-state,
  affect-regulation, role, and support trajectory question shapes while
  blocking temporal-order and boolean shapes.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `48.64`, judge `1.4258/2`.
- Compared with v56 (`1.4065/2`), v65 improves the primary metric by
  `+0.0193` and F1 by `+2.32`. Compared with v64 (`1.3806/2`), v65 improves
  judge by `+0.0452` and F1 by `+2.35`.
- By capability: abstention `1.7143/2`, conflict detection `1.2400/2`,
  information extraction `1.6341/2`, temporal reasoning `1.3929/2`, user
  modeling `1.0909/2`.
- Interpretation: v65 proves narrow graph-bound hydration can improve the
  overall judge score, mainly through abstention and information extraction.
  It remains below `1.5/2` because user modeling and conflict detection still
  lose too much support.
- Next path: keep v65 as the promoted baseline. Inspect v65/v56/v64 row
  deltas, then test a graph-bound user-state support selector/composer that
  activates only when multiple retrieved state-transition or trajectory-pair
  nodes agree and the question is not boolean or temporal-order shaped.

### 2026-07-10 EvoEmo user-state composer

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v66_user_state_composer/` from promoted
  v65. It adds an optional graph-bound user-state answer composer over
  retrieved source-session/session-fact evidence.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.88`, judge `1.4194/2`.
- Compared with v65 (`1.4258/2`), v66 regresses overall by `-0.0064` judge and
  `-1.76` F1.
- By capability: abstention `1.6429/2`, conflict detection `1.4000/2`,
  information extraction `1.5854/2`, temporal reasoning `1.4286/2`, user
  modeling `1.0303/2`.
- Interpretation: broad user-state answer composition recovers
  conflict/temporal quality but hurts abstention, information extraction, and
  user modeling enough to miss v65.
- Next path: keep v65 as promoted baseline. Mine v66 only for its
  conflict/temporal-safe behavior, likely through a selector rather than broad
  answer rewriting.

### 2026-07-10 EvoEmo boolean conflict formatter

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v67_boolean_conflict_formatter/` from
  promoted v65. It adds a deterministic formatter that expands terse
  yes/no/true/false answers with graph-retrieved support text.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.58`, judge `1.3290/2`.
- Compared with v65 (`1.4258/2`), v67 regresses overall by `-0.0968` judge and
  `-3.06` F1.
- By capability: abstention `1.6429/2`, conflict detection `0.9600/2`,
  information extraction `1.6098/2`, temporal reasoning `1.3929/2`, user
  modeling `0.9394/2`.
- Interpretation: direct raw graph-fact text splicing exposes internal graph
  labels such as contradiction/support comparison and severely hurts answer
  naturalness and judge quality.
- Next path: keep v65 as promoted baseline. Do not continue raw graph-fact text
  formatting; improve retrieval/selection or use constrained natural-language
  paraphrasing over graph evidence instead.

### 2026-07-10 EvoEmo boolean dialog paraphraser

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v68_boolean_dialog_paraphraser/` from
  promoted v65. It keeps the v67 idea of adding natural support to terse
  boolean/conflict answers, but the paraphraser only sees graph-bound original
  dialog lines from retrieved source-session nodes and conversation-derived
  source turn ids.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `44.41`, judge `1.3548/2`.
- Compared with v65 (`1.4258/2`), v68 regresses overall by `-0.0710` judge and
  `-4.23` F1.
- By capability: abstention `1.6429/2`, conflict detection `1.0800/2`,
  information extraction `1.5854/2`, temporal reasoning `1.2857/2`, user
  modeling `1.0909/2`.
- Interpretation: constraining the paraphraser to original dialog avoids the
  v67 internal-label leakage, but final-answer polishing still does not supply
  enough reliable support for conflict/user-modeling questions and harms the
  overall evidence balance.
- Next path: keep v65 as promoted baseline. Stop local boolean answer
  polishing. Move the next experiment to graph retrieval/evidence assembly:
  retrieve compact original-dialog snippets through graph nodes, grouped by
  emotional state, trigger, and time, before answer generation.

### 2026-07-10 EvoEmo compact evidence prompt

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v69_compact_evidence_prompt/` from
  promoted v65. It makes graph-bound episode evidence and compact fact anchors
  the primary answer prompt context, omitting the full source-session dump when
  `--compact-dialog-evidence-primary` is enabled.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `40.45`, judge `1.2065/2`.
- Compared with v65 (`1.4258/2`), v69 regresses overall by `-0.2193` judge and
  `-8.19` F1.
- By capability: abstention `1.5714/2`, conflict detection `1.1600/2`,
  information extraction `1.4634/2`, temporal reasoning `1.0714/2`, user
  modeling `0.7273/2`.
- Interpretation: compact graph-bound evidence is useful as an organizing
  layer but not enough as the only main evidence. Removing full source-session
  context makes answers too terse and under-supported, especially for
  user-modeling and temporal questions.
- Next path: keep v65 as promoted baseline. Do not globally omit full
  source-session evidence. Try a less destructive evidence map that preserves
  the v65 prompt footprint, or improve graph retrieval ranking before prompt
  construction.

### 2026-07-10 EvoEmo priority evidence map

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v70_priority_evidence_map/` from
  promoted v65. It preserves v65's full answer prompt evidence and adds a
  small priority map of graph fact anchors plus bound original dialog snippets
  before the full evidence.
- Compile, strict graph/no-test audit, and static no-test check passed. The
  counted metric run did not use `--resume-from-output`.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.98`, judge `1.3935/2`.
- Compared with v65 (`1.4258/2`), v70 regresses overall by `-0.0323` judge and
  `-1.66` F1.
- By capability: abstention `1.5714/2`, conflict detection `1.2800/2`,
  information extraction `1.5854/2`, temporal reasoning `1.3571/2`, user
  modeling `1.1212/2`.
- Interpretation: preserving full evidence makes v70 much safer than v69.
  The priority map slightly improves conflict detection and user modeling, but
  global activation hurts abstention, information extraction, and temporal
  reasoning enough to regress overall.
- Next path: keep v65 as promoted baseline. If using a priority map again,
  target it only to conflict/user-modeling shapes, or move the ordering signal
  into graph retrieval ranking while preserving the v65 prompt for other
  question types.

### 2026-07-12 EvoEmo targeted priority evidence map

- Status: compliant 155-row experiment, rejected near-tie diagnostic.
- Implemented
  `experiments/exp_2026_07_10_evo_emo_v71_targeted_priority_map/` from v70.
  It activates the priority evidence map only for generic support/conflict or
  user-state question shapes, using question text only and no benchmark labels.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The first metric attempt completed `144/155` and failed `11` p4 rows because
  of external API connection/time-out errors; a `--resume-from-output` recovery
  filled the missing rows.
- The full run completed `155/155` with zero final generation failures.
  Metrics: F1 `48.31`, judge `1.4194/2`.
- Compared with v65 (`1.4258/2`), v71 regresses overall by only `-0.0064`
  judge and `-0.33` F1. Compared with v70 (`1.3935/2`), v71 improves by
  `+0.0259` judge.
- Capability deltas versus v65: user modeling `+0.1818`, conflict detection
  `+0.0800`, abstention `-0.0714`, information extraction `-0.1219`, temporal
  reasoning `-0.0715`.
- Interpretation: targeted priority evidence is useful for user modeling and
  conflict, but still too broad for a promoted global profile. The target
  should be narrowed further or moved into retrieval ranking.
- Next path: keep v65 as promoted baseline. Try v72 with priority evidence only
  for user-modeling shapes, excluding support/boolean conflict shapes, or move
  graph-anchor ordering into the retriever while preserving v65 prompt layout.

### 2026-07-12 EvoEmo user-state-only priority evidence map

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v72_user_state_only_priority_map/` from
  v71. It narrows the priority evidence map to generic user-state question
  shapes only, leaving support/conflict and boolean rows on the non-map path.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `47.41`, judge `1.4065/2`.
- Compared with v65 (`1.4258/2`), v72 regresses overall by `-0.0193` judge and
  `-1.23` F1. Compared with v71 (`1.4194/2`), v72 regresses by `-0.0129`.
- Capability deltas versus v65: conflict detection `+0.1200`, user modeling
  `+0.0606`, abstention `-0.0714`, information extraction `-0.0975`,
  temporal reasoning `-0.0715`.
- Interpretation: user-state-only prompt mapping does not preserve v71's large
  user-modeling gain. Further prompt-map narrowing is unlikely to reach the
  target.
- Next path: keep v65 as promoted baseline. Move the graph-anchor ordering
  signal into retrieval ranking while preserving v65's answer prompt layout.

### 2026-07-12 EvoEmo targeted evidence rerank

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v73_targeted_evidence_rerank/` from
  promoted v65. It moves the priority-map ordering signal into retrieval
  ordering of already retrieved source-session/session-fact evidence while
  leaving the v65 answer prompt layout unchanged.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.77`, judge `1.3806/2`.
- Compared with v65 (`1.4258/2`), v73 regresses by `-0.0452` judge and `-1.87`
  F1.
- By capability: abstention `1.5714/2`, conflict detection `1.2800/2`,
  information extraction `1.5366/2`, temporal reasoning `1.3929/2`, user
  modeling `1.0909/2`.
- Interpretation: the priority-map/rerank family did not beat v65. The v71
  near-tie was useful diagnostic signal, but its gain is not reproduced by
  narrower prompt gating or retrieval ordering.
- Next path: keep v65 as promoted baseline. Stop the priority-map/rerank line
  and start a fresh graph construction path, such as conversation-derived
  memory cards or support-sufficient subgraph extraction.

### 2026-07-12 EvoEmo support-bundle graph

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v74_support_bundle_graph/` from
  promoted v65. It adds `support_bundle` graph fact nodes that bind
  role-specific conversation-derived fact anchors to original dialog snippets
  through source turn ids.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.64`, judge `1.4065/2`.
- Compared with v65 (`1.4258/2`), v74 regresses by `-0.0193` judge and `-2.00`
  F1.
- By capability: abstention `1.6786/2`, conflict detection `1.4000/2`,
  information extraction `1.4878/2`, temporal reasoning `1.3571/2`, user
  modeling `1.1212/2`.
- Interpretation: support-bundle graph nodes are useful for conflict evidence,
  but global activation adds distracting evidence for information extraction
  and temporal rows.
- Next path: keep v65 as promoted baseline. Try a gated support-bundle variant
  that activates only for conflict/boolean and user-state retrieval, while
  excluding temporal/date/order and direct information-extraction questions.

### 2026-07-12 EvoEmo gated support-bundle retrieval

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v75_gated_support_bundle/` from v74. It
  keeps support-bundle graph construction but gates bundle retrieval to generic
  conflict/boolean and non-temporal user-state question shapes.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `43.78`, judge `1.3484/2`.
- Compared with v65 (`1.4258/2`), v75 regresses by `-0.0774` judge. Compared
  with v74 (`1.4065/2`), it regresses by `-0.0581` judge.
- By capability: abstention `1.5714/2`, conflict detection `1.2400/2`,
  information extraction `1.4390/2`, temporal reasoning `1.3929/2`, user
  modeling `1.0909/2`.
- Interpretation: simple support-bundle gating does not preserve v74's conflict
  improvement and should not be tuned further.
- Next path: keep v65 as promoted baseline. Start a different graph path, such
  as source-bound contrast nodes for conflict only or support-sufficient
  subgraph selection over v65 evidence.

### 2026-07-12 EvoEmo source-bound contrast graph

- Status: compliant 155-row experiment, rejected diagnostic.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v76_source_bound_contrast/` from
  promoted v65. It adds `source_contrast` graph nodes derived from
  contradiction-support graph nodes and compact original dialog snippets bound
  by source turn ids.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.13`, judge `1.3032/2`.
- Compared with v65 (`1.4258/2`), v76 regresses by `-0.1226` judge and `-3.51`
  F1.
- By capability: abstention `1.5714/2`, conflict detection `1.2000/2`,
  information extraction `1.4634/2`, temporal reasoning `1.1786/2`, user
  modeling `1.0606/2`.
- Interpretation: adding source-bound contrast nodes did not improve conflict
  and harmed other paths. Stop contrast/support-bundle node scoring tweaks.
- Next path: refresh frontier methods and redesign graph construction/retrieval
  from first principles rather than continuing small evidence-packet changes.

### 2026-07-12 EvoEmo PPR graph retrieval

- Status: compliant 155-row experiment, promoted current best below target.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v77_ppr_graph_retrieval/` from promoted
  v65 after refreshing frontier graph-memory/GraphRAG ideas. It adds
  Personalized PageRank-style propagation over conversation-built
  source-session, session-fact, source-turn, and chronological edges. The
  question is used only at retrieval time as a seed vector and never for graph
  construction.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `48.37`, judge `1.4323/2`.
- Compared with v65 (`1.4258/2`), v77 improves by `+0.0065` judge and
  regresses by only `-0.27` F1.
- By capability: abstention `1.6429/2`, conflict detection `1.4000/2`,
  information extraction `1.6098/2`, temporal reasoning `1.4286/2`, user
  modeling `1.0606/2`.
- Interpretation: PPR graph retrieval is the first post-v65 structural graph
  change that improves the primary metric. It helps conflict and temporal
  retrieval, while slightly hurting abstention and user modeling.
- Next path: try v78 with PPR gated to conflict/boolean and temporal/date/order
  question shapes, preserving v65 behavior elsewhere.

### 2026-07-12 EvoEmo gated PPR retrieval

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v78_gated_ppr_retrieval/` from v77. It
  activates PPR graph propagation only for generic conflict/support/relationship
  boolean shapes and temporal/date/order shapes. The gate uses question text
  only at retrieval time and does not affect graph construction.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `45.04`, judge `1.3806/2`.
- Compared with v77 (`1.4323/2`), v78 regresses by `-0.0517` judge and
  `-3.33` F1.
- Diagnostic split: PPR applied to `78/155` rows. Applied rows averaged
  `1.2692/2`, while non-applied rows averaged `1.4935/2`. The gate opened on
  too many user-modeling and information-extraction rows.
- Interpretation: question-shape gating did not preserve v77's small gain.
  High-impact PPR blending should not be widened or narrowed in this form.
- Next path: keep v77 as current best below target and try a lower-impact graph
  traversal path, such as PPR tie-break/diversity scoring after v65/v77 ranking
  or graph-neighborhood evidence expansion without strong score replacement.

### 2026-07-12 EvoEmo low-weight PPR retrieval

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v79_low_weight_ppr/` from v77. It keeps
  global PPR graph propagation but reduces the blend weights to
  `session=4`, `fact=6`, so PPR acts more like a tie-break signal than a strong
  rank replacement.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `46.86`, judge `1.4000/2`.
- Compared with v77 (`1.4323/2`), v79 regresses by `-0.0323` judge and
  `-1.51` F1.
- Interpretation: lowering PPR weights recovers some surface F1 versus v78 but
  does not preserve v77's judge gain. PPR weight/gate tuning is not a stable
  route to `1.5/2`.
- Next path: keep v77 as current best below target and switch away from PPR
  tuning toward graph-retrieved evidence assembly/refinement before answer
  generation.

### 2026-07-12 EvoEmo graph evidence refiner

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v80_graph_refiner/` from v77. It keeps
  v77 PPR graph retrieval and enables `--graph-evidence-refiner`, which sees
  only graph-retrieved source-session/session-fact evidence plus the current
  graph-derived answer.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `47.07`, judge `1.3935/2`.
- Compared with v77 (`1.4323/2`), v80 regresses by `-0.0388` judge and
  `-1.30` F1.
- Interpretation: broad post-answer evidence refinement adds some surface detail
  but does not improve judge; temporal and user-modeling remain weak.
- Next path: keep v77 as current best below target and try a targeted
  trajectory/user-modeling composer over graph evidence, or a stronger answer
  model if available.

### 2026-07-12 EvoEmo trajectory composer

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v81_trajectory_composer/` from v77. It
  keeps v77 PPR graph retrieval and enables `--trajectory-answer-composer`,
  which sees only graph-retrieved source-session/session-fact evidence plus the
  current graph-derived answer and triggers only for trajectory/change shapes.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run completed `155/155` with zero generation failures. Metrics: F1
  `48.61`, judge `1.4000/2`.
- Compared with v77 (`1.4323/2`), v81 regresses by `-0.0323` judge while F1
  improves by `+0.24`.
- Interpretation: trajectory composition improves surface overlap but not
  semantic judge quality. User modeling remains weak at `1.1212/2`.
- Next path: keep v77 as current best below target. Stop post-answer
  composer/refiner additions on this evidence path and test a stronger answer
  model if available or redesign graph memory representation.

### 2026-07-12 EvoEmo DeepSeek v3.2 answerer preflight

- Status: compliant graph-only preflight, blocked and not metric-bearing.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v82_deepseek_v32_answerer/` from v77.
  It keeps v77 graph construction/retrieval and changes only the answerer model
  to `deepseek-v3.2`.
- Compile, strict graph/no-test audit, and static no-test check passed.
- A one-row real payload preflight failed with an unsupported-model API error:
  planned `1`, completed `0`, failed `1`.
- No metric claim is made because the run is below 100 rows and did not
  complete. It does not count toward the target.
- Next path: do not run full v82 on the current endpoint. Improve graph
  information density with conversation-only LLM session-fact extraction using
  the supported model.

### 2026-07-12 EvoEmo LLM session facts

- Status: compliant design, aborted before metrics; not metric-bearing.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v83_llm_session_facts/` from v77. It
  keeps v77 graph retrieval and enables `--llm-session-facts`, where each
  source-session fact prompt receives only that session's conversation dialog.
- Compile, strict graph/no-test audit, and static no-test check passed.
- The full run was started but did not write any output/result checkpoint.
  After repeated waits, it was interrupted while blocked in
  `ThreadPoolExecutor.as_completed` over `llm_session_facts` futures.
- No metric claim is made: planned `155`, completed `0`, and the run is below
  the 100-row metric threshold.
- Interpretation: increasing graph information density remains the right
  direction, but the implementation needs durable per-session fact caching and
  timeout/fallback before it can be safely evaluated.
- Next path: implement v84 with cached LLM session facts under `outputs/`,
  bounded waits, and rule-fact fallback for slow/failed sessions.

### 2026-07-12 EvoEmo cached LLM facts and compact prompt

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v84_cached_llm_facts/` from v83/v77.
  It keeps strict graph-only construction, adds a durable per-source-session
  fact cache under `outputs/`, and adds rule-fact fallback for slow or failed
  LLM fact extraction.
- During preflight, the original answer prompt was diagnosed at about `70k`
  chars for one p2 row because `build_prompt` duplicated graph-bound evidence,
  full fact nodes, and full retrieved source-session nodes. v84 added budgeted
  evidence rendering and compact answer rules; the same row dropped to about
  `6.6k` chars and completed in `11.29s`.
- Compile, strict graph/no-test audit, static no-test check, F1, and
  LLM-as-Judge all ran successfully.
- Full p2/p4/p5 run completed `155/155` with zero failures. Metrics: F1
  `21.79`, judge `0.4516/2`, Unknown predictions `123/155`.
- Interpretation: prompt budgeting fixed the runtime bottleneck but the compact
  strict prompt over-abstained, giving perfect abstention rows and failing most
  information extraction, temporal, conflict, and user-modeling rows.
- Next path: keep v77 (`1.4323/2`) as current best. Start v85 from the
  v77-style answerer and preserve only the safe lesson from v84: evidence
  budget control without changing the answer policy into an Unknown-heavy
  prompt.

### 2026-07-12 EvoEmo budgeted v77 prompt

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v85_budgeted_v77_prompt/` from v77. It
  kept v77 graph construction, PPR graph retrieval, and answer rules, but
  budgeted the rendered source-session and fact-node evidence.
- Compile, strict graph/no-test audit, static no-test check, F1, and
  LLM-as-Judge all ran successfully.
- Full p2/p4/p5 run completed `155/155` with zero failures. Metrics: F1
  `40.98`, judge `1.1226/2`, Unknown predictions `52/155`.
- Interpretation: v85 avoided v84's over-abstention, but summarizing/budgeting
  evidence still removed important details and regressed judge far below v77.
- Next path: keep v77 (`1.4323/2`) as current best. Stop evidence
  summarization/budgeting of v77's answer prompt and instead test model choice
  or retrieval-rank changes while preserving full evidence.

### 2026-07-12 EvoEmo GPT-4o v77 answerer preflight

- Status: compliant graph-only preflight, blocked and not metric-bearing.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v86_gpt4o_v77_answerer/` from v77. It
  keeps v77 graph construction, retrieval, and full evidence prompt, changing
  only the answer model to `gpt-4o`.
- Compile, strict graph/no-test audit, and static no-test check passed.
- A one-row real-payload preflight failed: planned `1`, completed `0`, failed
  `1`. The configured external endpoint returned `UnsupportedModel` for
  `gpt-4o`.
- No metric claim is made because the run is below 100 rows and did not
  complete.
- Next path: do not run full v86 on this endpoint. Continue from v77 with
  `deepseek-v4-flash`, preserving full evidence and exploring retrieval ranking
  or evidence breadth rather than summarization.

### 2026-07-12 EvoEmo wider full evidence

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v87_wider_full_evidence/` from v77. It
  kept full evidence and the v77 answer path, then widened graph retrieval and
  evidence expansion to `top-k=8`, `fact-top-k=14`,
  `evidence-expansion-session-k=8`, and `evidence-expansion-fact-k=14`.
- Compile, strict graph/no-test audit, static no-test check, F1, and
  LLM-as-Judge all ran successfully.
- Full p2/p4/p5 run completed `155/155` with zero failures. Metrics: F1
  `45.27`, judge `1.3097/2`, Unknown predictions `31/155`.
- Interpretation: raw evidence breadth is not the bottleneck by itself. v87
  reduced abstention and kept decent F1, but the wider evidence set introduced
  distractors and regressed the primary judge metric below v77 `1.4323/2`.
- Next path: keep v77 as current best. Stop widening full evidence without a
  stronger graph-side selection/filtering mechanism. The next experiment should
  improve graph evidence precision or rebuild conversation-only episode/state
  nodes before answer generation.

### 2026-07-12 EvoEmo state answer arbiter

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v88_state_arbiter/` from v77. It kept
  v77 graph retrieval and added a narrow plain-text state/trajectory arbiter
  over graph-retrieved evidence and the current graph-derived answer.
- Compile, strict graph/no-test audit, static no-test check, F1, and
  LLM-as-Judge all ran successfully.
- Full p2/p4/p5 run completed `155/155` with zero failures. Metrics: F1
  `46.40`, judge `1.3677/2`, Unknown predictions `29/155`. The state arbiter
  applied `21` times and changed `8` answers.
- Interpretation: answer-time arbitration improved some surface trajectory
  phrasing but did not improve primary judge quality. It regressed below v77
  `1.4323/2`, so the bottleneck remains upstream graph evidence selection.
- Next path: keep v77 as current best. Stop post-answer arbiter/composer
  tweaks and move the next experiment earlier in the pipeline: graph
  construction or graph retrieval precision.

### 2026-07-12 EvoEmo state-focus retrieval

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v89_state_focus_retrieval/` from v77. It
  moved earlier than v88 by reranking conversation-built state/trajectory graph
  fact nodes before the main answer prompt and hydrating their bound source
  sessions.
- Compile, strict graph/no-test audit, static no-test check, F1, and
  LLM-as-Judge all ran successfully.
- Full p2/p4/p5 run completed `155/155` with zero failures. Metrics: F1
  `48.14`, judge `1.3613/2`, Unknown predictions `32/155`. State-focus
  retrieval applied `21` times.
- Interpretation: replacement-based state-focus retrieval slightly improved
  user modeling but hurt conflict detection and temporal reasoning. The state
  facts should be additive or used as a tie-breaker, not replace the main graph
  evidence.
- Next path: keep v77 as current best. If continuing state-focus retrieval,
  test additive low-cap evidence instead of replacement.

### 2026-07-13 EvoEmo additive state-focus retrieval

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_12_evo_emo_v90_additive_state_focus/` from v89. It
  keeps state-focus retrieval over conversation-built graph fact nodes, but
  makes the state-focus evidence additive instead of replacing the main graph
  fact set.
- Compile, strict graph/no-test audit, static no-test check, one-row real
  payload preflight, F1, and LLM-as-Judge all ran successfully. Snapshots were
  saved for base/source, audit, preflight, and full result.
- Full p2/p4/p5 run completed `155/155` with zero failures. Metrics: F1
  `46.12`, judge `1.3871/2`, Unknown predictions `28/155`.
- Compared with v89, additive state-focus improves judge
  `1.3613/2 -> 1.3871/2`, but it still regresses below v77 `1.4323/2`.
- Interpretation: additive state-focus is less harmful than replacement, but
  it does not solve the user-modeling bottleneck (`1.0909/2`) and still
  weakens the overall answer mix.
- Next path: keep v77 as current best. Stop small state-focus variants and
  start a fresh graph-design experiment around source-turn-bound
  conversation-only event/state nodes that retrieve graph evidence first and
  then recall concise raw-dialog snippets for answer generation.

### 2026-07-13 EvoEmo source-turn snippet pack

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_13_evo_emo_v91_source_turn_snippet_pack/` from v77.
  It keeps v77 graph construction/retrieval and adds a compact source-turn
  snippet pack built from graph-retrieved fact `source_turn_ids`, while omitting
  the full source-session block in the answer prompt.
- Compile, strict graph/no-test audit, static no-test check, one-row real
  payload preflight, F1, and LLM-as-Judge all ran successfully. Snapshots were
  saved for base/source, audit, preflight, and full result.
- Full p2,p4,p5 run completed `155/155` with zero failures. Metrics: F1
  `44.72`, judge `1.2645/2`, Unknown predictions `29/155`.
- Interpretation: the p2 q4 preflight looked promising, but full-run user
  modeling collapsed to `0.7273/2`. Compact source-turn snippets cannot replace
  full source-session context; they remove context needed for trajectory and
  conflict interpretation.
- Next path: keep v77 as current best. If snippet packaging is revisited, use
  it additively as an attention layer while preserving full context. Otherwise,
  rebuild graph information density with higher-quality conversation-only
  event/state nodes before prompt-time evidence compression.

### 2026-07-13 EvoEmo additive source-turn snippet pack

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_13_evo_emo_v92_additive_snippet_pack/` from v91.
  It keeps source-turn snippet packing but preserves the full source-session
  block instead of omitting it.
- Compile, strict graph/no-test audit, static no-test check, one-row real
  payload preflight, F1, and LLM-as-Judge all ran successfully. Snapshots were
  saved for base/source, audit, preflight, and full result.
- Full p2,p4,p5 run completed `155/155` with zero failures. Metrics: F1
  `46.55`, judge `1.3032/2`, Unknown predictions `32/155`.
- Interpretation: additive snippets are safer than v91 snippet-only but still
  regress below v77 and v90. Extra prompt-time evidence packaging does not
  solve the graph evidence quality problem.
- Next path: keep v77 as current best. Stop source-turn snippet packaging
  variants and move to a new graph-construction experiment with higher-quality
  conversation-only event/state nodes.

### 2026-07-13 EvoEmo dual-candidate selector diagnostic

- Status: compliant diagnostic, rejected before metric run.
- Implemented
  `experiments/exp_2026_07_13_evo_emo_v93_dual_candidate_selector/` from v92.
  It generated two runtime graph-derived candidates from the same
  conversation-built graph and asked a selector to choose or synthesize using
  only graph-retrieved evidence.
- Compile, static no-test check, and graph-input audit passed. Snapshots were
  saved before edits, after edits, after audit, after interrupted preflight,
  and after bounded preflight failure.
- The first preflight was interrupted after `263.45s` with `0/1` completed.
  The bounded preflight failed after `109.53s` with `0/1` completed and
  `RuntimeError: Failed after 1 retries for model=deepseek-v4-flash`.
- Interpretation: multi-candidate graph selection has oracle headroom, but the
  live design requires too many external model round trips per QA under current
  API latency. It is not operationally viable for 155-row full runs.
- Next path: keep the oracle insight as diagnostic only. Use single-call
  answerers or improve graph construction/retrieval before revisiting
  selectors.

### 2026-07-13 EvoEmo single-call evidence selector

- Status: compliant 155-row experiment, rejected.
- Implemented
  `experiments/exp_2026_07_13_evo_emo_v94_single_call_evidence_selector/` from
  v77. It preserved v77 PPR graph retrieval and added a primary source-turn
  snippet layer inside one answer prompt. Snippets were built only from
  graph-retrieved conversation-derived `source_turn_ids` and their bound
  original dialog turns.
- Compile, static no-test check, graph-input audit, one-row real-payload
  preflight, full generation, F1, and LLM-as-Judge all ran successfully.
  Snapshots were saved for base/source, audit, preflight, full generation, F1,
  and judge.
- Full p2,p4,p5 run completed `155/155` with zero failures. Metrics: F1
  `44.22`, judge `1.3032/2`, Unknown predictions `32/155`.
- Compared with v77, v94 regressed on judge `1.4323/2 -> 1.3032/2` and F1
  `48.37 -> 44.22`. User modeling remained weak at `0.9697/2`.
- Interpretation: prompt-time snippet ordering is not the bottleneck. It can
  add exact local evidence but harms broader user-state/conflict interpretation.
- Next path: keep v77 as current best. Stop prompt-time snippet packaging
  variants and start a fresh graph-construction/retrieval experiment with
  higher-density conversation-only event/state nodes.

### 2026-07-14 EvoEmo v77 full-dataset regression

- Status: compliant full-dataset regression, rejected as non-generalizing.
- Ran v77 PPR graph retrieval over the full EvoEmo dataset: `1427/1427`
  predictions, zero generation failures, Unknown predictions `266/1427`.
- Metrics: token F1 `42.51`, LLM-as-Judge `1.2929/2`.
- By capability: abstention `1.4943/2`, conflict detection `1.3071/2`,
  information extraction `1.5922/2`, temporal reasoning `1.1585/2`, user
  modeling `0.9314/2`.
- Interpretation: the previous p2/p4/p5 slice signal (`1.4323/2`) did not
  generalize. The graph path is strong enough for information extraction and
  abstention but still fails broad temporal and user-state reasoning.
- Next path: use the 200-QA gate before any future full regression and focus
  new experiments on graph construction/retrieval for temporal and user
  modeling rather than prompt-time evidence packaging.

### 2026-07-15 EvoEmo v95 trajectory composer 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Updated `AGENTS.md` with the required 200-QA gate and full-regression
  300-row checkpoint early-stop rule.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v95_trajectory_composer_200_gate/` from
  v77. It preserves v77 graph construction/retrieval and enables the existing
  trajectory answer composer.
- The deterministic balanced 200-QA gate completed `200/200` with zero
  failures. Metrics: F1 `43.01`, LLM-as-Judge `1.375/2`, Unknown predictions
  `37/200`.
- The trajectory answer composer applied `40` times and changed `33` answers.
  Capability scores were abstention `1.7333/2`, conflict detection
  `1.5312/2`, information extraction `1.5769/2`, temporal reasoning
  `1.2128/2`, and user modeling `0.8974/2`.
- Interpretation: the answer-time trajectory composer still does not fix the
  temporal/user-modeling bottleneck. Because the 200-QA gate did not exceed
  `1.4/2`, do not run full regression for v95.
- Next path: start a graph-side experiment that changes how conversation-only
  event/state evidence is constructed or retrieved for temporal/user-state
  questions.

### 2026-07-15 EvoEmo v96 time-aligned event-neighborhood 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v96_time_aligned_event_neighborhood/`
  from v77. It preserves v77 graph construction/retrieval and adds a
  retrieval-time time-aligned event-neighborhood expansion over
  conversation-derived fact nodes.
- Compile and graph-input audit passed. The audit records that the new
  expansion links only conversation-derived fact nodes by session order,
  temporal proximity, topic/affect/state anchors, and query-time graph
  retrieval scores.
- The deterministic balanced 200-QA gate completed `200/200` with zero
  failures. Metrics: F1 `40.87`, LLM-as-Judge `1.325/2`, Unknown predictions
  `39/200`.
- The time-aligned event-neighborhood expansion applied `108` times and added
  `1296` fact nodes. Capability scores were abstention `1.6/2`, conflict
  detection `1.375/2`, information extraction `1.6346/2`, temporal reasoning
  `1.1277/2`, and user modeling `0.8974/2`.
- Interpretation: adding neighboring facts does not fix the temporal/user-state
  bottleneck and likely diffuses the evidence budget. Because the 200-QA gate
  did not exceed `1.4/2`, do not run full regression for v96.
- Next path: improve graph node quality before retrieval, especially explicit
  conversation-derived temporal state/event nodes with normalized dates,
  role/state dimensions, and tighter source-turn bindings.

### 2026-07-15 EvoEmo v97 temporal state event nodes 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v97_temporal_state_event_nodes/` from
  v96 but did not enable v96's time-aligned neighbor expansion. v97 adds
  deterministic `temporal_state_event` nodes derived only from conversation
  source sessions, seeker turns, source-session dates, and
  conversation-derived session facts.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `40.95`, LLM-as-Judge `1.39/2`, Unknown predictions `34/200`.
- `temporal_state_event` nodes appeared in retrieved facts on `193/200`
  questions, with `789` retrieved temporal-state-event fact nodes. Capability
  scores were abstention `1.5333/2`, conflict detection `1.625/2`,
  information extraction `1.6538/2`, temporal reasoning `1.234/2`, and user
  modeling `0.9231/2`.
- Interpretation: the broad temporal-state-event node shape is directionally
  better than v96 and narrowly missed the gate, but retrieval is too broad and
  still does not solve temporal reasoning. Because the 200-QA gate did not
  exceed `1.4/2`, do not run full regression for v97.
- Next path: split temporal/state nodes into stricter conversation-derived
  subtypes and gate retrieval by question shape.

### 2026-07-15 EvoEmo v98 temporal state subtypes 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v98_temporal_state_subtypes/` from v97.
  v98 disables the broad `temporal_state_event` flag for the gate run and adds
  deterministic subtype nodes: `dated_event`, `current_emotional_state`,
  `relationship_support_state`, and `action_intention_event`.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `41.18`, LLM-as-Judge `1.34/2`, Unknown predictions `35/200`.
- Subtype nodes appeared in retrieved facts on `189/200` questions, with `950`
  retrieved subtype nodes: dated_event `468`, action_intention_event `253`,
  current_emotional_state `229`, relationship_support_state `0`.
- Capability scores were abstention `1.6/2`, conflict detection `1.4062/2`,
  information extraction `1.6154/2`, temporal reasoning `1.1489/2`, and user
  modeling `0.9487/2`.
- Interpretation: subtypes improved user modeling slightly but hurt temporal
  reasoning and conflict detection. The relationship/support subtype did not
  enter retrieval, and isolated dated/action nodes were not enough for sequence
  questions. Because the 200-QA gate did not exceed `1.4/2`, do not run full
  regression for v98.
- Next path: target ordered temporal sequence evidence directly, preserving
  chains of events instead of isolated event/state nodes.

### 2026-07-15 EvoEmo v99 temporal sequence chain 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v99_temporal_sequence_chain/` from v97.
  v99 adds deterministic `temporal_sequence_chain` graph facts built only from
  source-session order, source-session dates, seeker turns, and
  conversation-derived session facts.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `41.92`, LLM-as-Judge `1.385/2`, Unknown predictions `35/200`.
- `temporal_sequence_chain` appeared in retrieved facts on `130/200` questions,
  including `41/47` temporal reasoning questions.
- Capability scores were abstention `1.6/2`, conflict detection `1.5/2`,
  information extraction `1.6538/2`, temporal reasoning `1.3404/2`, and user
  modeling `0.8205/2`.
- Interpretation: ordered chains improve temporal reasoning, but the current
  retrieval gate harms broad user-modeling. Because the 200-QA gate did not
  exceed `1.4/2`, do not run full regression for v99.
- Next path: keep sequence-chain evidence but gate it to explicit temporal/order
  questions so it does not replace user-state evidence.

### 2026-07-15 EvoEmo v100 temporal sequence strict gate 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v100_temporal_sequence_strict_gate/`
  from v99. v100 keeps deterministic `temporal_sequence_chain` graph facts but
  blocks their retrieval for broad user-modeling question shapes.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `40.72`, LLM-as-Judge `1.32/2`, Unknown predictions `38/200`.
- `temporal_sequence_chain` appeared in retrieved facts on `36/200` questions
  and did not appear on user-modeling questions.
- Capability scores were abstention `1.6/2`, conflict detection `1.4375/2`,
  information extraction `1.5769/2`, temporal reasoning `1.2128/2`, and user
  modeling `0.7949/2`.
- Interpretation: hard gating prevents user-modeling contamination but removes
  useful temporal sequence evidence and does not recover user modeling. Because
  the 200-QA gate did not exceed `1.4/2`, do not run full regression for v100.
- Next path: use a softer rank cap or evidence-budget rule that lets sequence
  evidence supplement temporal questions without replacing user-state evidence.

### 2026-07-15 EvoEmo v101 sequence supplement 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v101_sequence_supplement/` from v99.
  v101 blocks deterministic `temporal_sequence_chain` facts from primary
  ranking and expansion ranking, then appends at most one chain fact as
  low-budget supplemental evidence for explicit temporal sequence questions.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `40.25`, LLM-as-Judge `1.27/2`, Unknown predictions `41/200`.
- The sequence supplement fired on `49/200` QA rows, including `32/47`
  temporal reasoning rows and `0/39` user modeling rows.
- Capability scores were abstention `1.5333/2`, conflict detection
  `1.4688/2`, information extraction `1.5192/2`, temporal reasoning
  `1.1064/2`, and user modeling `0.7692/2`.
- Interpretation: simple sequence-chain supplementation regressed both
  temporal reasoning and user modeling relative to v97/v99. Because the
  200-QA gate did not exceed `1.4/2`, do not run full regression for v101.
- Next path: pivot from sequence-chain retrieval variants to user-state graph
  quality, especially conversation-derived relationship/support/person-state
  facts with tighter cause, target-person, date/session, and source-turn
  binding.

### 2026-07-15 EvoEmo v102 relationship support state 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v102_relationship_support_state/` from
  v101. v102 adds deterministic `relationship_support_state` graph facts built
  only from source sessions, seeker turns, conversation-derived session facts,
  relationship/support role cues, person-name cues, and topic/affect/polarity
  anchors from dialog text.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `41.11`, LLM-as-Judge `1.355/2`, Unknown predictions `33/200`.
- `relationship_support_state` appeared in retrieved facts on `195/200`
  questions with `690` retrieved fact occurrences, including `37/39` user
  modeling rows.
- Capability scores were abstention `1.6/2`, conflict detection `1.5/2`,
  information extraction `1.5769/2`, temporal reasoning `1.1489/2`, and user
  modeling `1.0/2`.
- Interpretation: relationship/support state facts improved user modeling over
  v101 but entered far too many non-user-state questions and did not clear the
  200-QA gate. Because the score did not exceed `1.4/2`, do not run full
  regression for v102.
- Next path: keep the node shape but add stricter retrieval gating or a small
  evidence budget so relationship/support-state facts are limited to
  user-modeling, support/trust/relationship, and person-role questions.

### 2026-07-15 EvoEmo v103 gated relationship support state 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v103_gated_relationship_support_state/`
  from v102. v103 keeps deterministic `relationship_support_state` graph facts
  but blocks them from primary ranking and expansion unless the question has
  explicit relationship, support, trust, or person-role shape.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `41.32`, LLM-as-Judge `1.39/2`, Unknown predictions `38/200`.
- `relationship_support_state` appeared in retrieved facts on `111/200`
  questions with `357` retrieved fact occurrences, including `15/39` user
  modeling rows.
- Capability scores were abstention `1.6/2`, conflict detection `1.6562/2`,
  information extraction `1.5577/2`, temporal reasoning `1.2766/2`, and user
  modeling `0.9231/2`.
- Interpretation: hard gating fixed much of v102's over-broad retrieval but
  lost the user-modeling gain and only matched v97-level overall score. Because
  the score did not exceed `1.4/2`, do not run full regression for v103.
- Next path: try a small late evidence budget or supplement for
  `relationship_support_state` instead of full hard gating, so support evidence
  stays available for user-modeling rows without flooding unrelated rows.

### 2026-07-15 EvoEmo v104 relationship support supplement 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v104_relationship_support_supplement/`
  from v103. v104 keeps v103's gated `relationship_support_state` primary
  retrieval and appends at most one late relationship/support fact for broader
  user-state relationship/support question shapes.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `40.64`, LLM-as-Judge `1.305/2`, Unknown predictions `43/200`.
- `relationship_support_state` appeared in retrieved facts on `114/200`
  questions with `409` retrieved fact occurrences. The late supplement applied
  on `55/200` questions, including `11/39` user-modeling rows.
- Capability scores were abstention `1.6667/2`, conflict detection
  `1.3438/2`, information extraction `1.5577/2`, temporal reasoning
  `1.1277/2`, and user modeling `0.8718/2`.
- Compared with v103 on the same gate, v104 lost `17` judge points overall:
  abstention `+2`, conflict detection `-10`, information extraction `0`,
  temporal reasoning `-7`, user modeling `-2`.
- Interpretation: generic late relationship-support supplementation does not
  recover user modeling and hurts conflict/temporal behavior. Because the score
  did not exceed `1.4/2`, do not run full regression for v104.
- Next path: replace generic supplementing with precise conversation-derived
  relationship trajectory nodes that bind target person or role, earlier/later
  source sessions, and source-turn evidence, and expose them only for
  relationship evolution/support/trust/family/friend/partner trajectory shapes.

### 2026-07-15 EvoEmo v105 relationship trajectory 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v105_relationship_trajectory/` from
  v104. v105 adds deterministic `relationship_trajectory` graph facts by
  linking conversation-derived `relationship_state` and
  `relationship_support_state` nodes with target-person or relationship
  dimension anchors. v104's late relationship-support supplement was not
  enabled.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `40.87`, LLM-as-Judge `1.33/2`, Unknown predictions `38/200`.
- `relationship_trajectory` appeared in retrieved facts on `24/200` questions
  with `96` retrieved fact occurrences. `relationship_support_state` appeared
  on `110/200` questions with `327` retrieved fact occurrences.
- Capability scores were abstention `1.5333/2`, conflict detection
  `1.4375/2`, information extraction `1.5962/2`, temporal reasoning
  `1.2128/2`, and user modeling `0.8718/2`.
- Compared with v103 on the same gate, v105 lost `12` judge points. Compared
  with v104, v105 recovered `5` judge points but still remained below the
  promotion gate.
- Interpretation: narrower relationship trajectory nodes reduce v104's broad
  supplement noise but do not create useful separation; hit rows averaged only
  `1.333/2`, nearly identical to non-hit rows. Because the score did not exceed
  `1.4/2`, do not run full regression for v105.
- Next path: stop relationship-node variants for now. Target answer-side
  graph-evidence use over already retrieved nodes, especially reducing
  avoidable Unknown and repairing temporal/user-modeling answers without adding
  new broad graph types.

### 2026-07-15 EvoEmo v106 unknown graph repair 200-gate

- Status: compliant 200-QA gate experiment, rejected before full regression.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v106_unknown_graph_repair/` from v103.
  v106 adds a narrow answer-side `unknown_graph_repair` fallback that only runs
  when the current answer is still `Unknown`, skips common abstention probes,
  and uses only already retrieved graph facts and source sessions.
- Compile and graph-input audit passed. The deterministic balanced 200-QA gate
  completed `200/200` with zero failures.
- Metrics: F1 `43.08`, LLM-as-Judge `1.36/2`, Unknown predictions `36/200`.
- `unknown_graph_repair` changed only `1/200` answers and applied without
  changing the answer on `15/200` rows.
- Capability scores were abstention `1.6/2`, conflict detection `1.625/2`,
  information extraction `1.6154/2`, temporal reasoning `1.2128/2`, and user
  modeling `0.7949/2`.
- Compared with v103 on the same gate, v106 lost `6` judge points overall:
  abstention `0`, conflict detection `-1`, information extraction `+3`,
  temporal reasoning `-3`, user modeling `-5`.
- Interpretation: answer-side Unknown repair is too narrow to promote. The F1
  improvement is not matched by the primary judge metric, and temporal/user
  modeling regressions dominate the small information-extraction gain. Because
  the score did not exceed `1.4/2`, do not run full regression for v106.
- Next path: return to retrieval-side evidence quality. Use v103 as the near
  gate baseline and target temporal/user-modeling support before answer
  generation rather than post-hoc Unknown repair.

### 2026-07-15 EvoEmo v107 time-aligned neighborhood diagnostic

- Status: interrupted diagnostic only; not a valid 200-QA gate result.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v107_time_aligned_neighborhood/` from
  v103. v107 enables the existing `time_aligned_event_neighborhood`
  retrieval-side expansion for temporal, trajectory, and user-state question
  shapes.
- Compile and graph-input audit passed. The run was interrupted at `30/200`
  completed rows with zero failures after the user requested a pivot to a
  `deepseek-v4-pro` model-swap test.
- Interpretation: do not promote or compare v107. It remains a source-level
  diagnostic candidate only.

### 2026-07-15 EvoEmo v108 deepseek-v4-pro model swap 200-gate

- Status: compliant graph audit, rejected before full regression due model
  interface/prompt-length compatibility failure.
- Implemented
  `experiments/exp_2026_07_15_evo_emo_v108_deepseek_v4_pro_model_swap/` from
  v103. v108 changed the answer-generation and episode-selector model from
  `deepseek-v4-flash` to `deepseek-v4-pro`, keeping the same graph construction
  and retrieval settings.
- Compile and graph-input audit passed. The balanced 200-QA gate completed
  `200/200` with zero run failures.
- Metrics: F1 `18.3`, LLM-as-Judge `0.405/2`, Unknown predictions `179/200`.
- Capability scores were abstention `1.9333/2`, conflict detection `0.125/2`,
  information extraction `0.1923/2`, temporal reasoning `0.1915/2`, and user
  modeling `0.0/2`.
- Compatibility diagnostics: `191/200` answer attempts fell back to `Unknown`
  because JSON parsing failed; `177/200` episode-selector attempts failed JSON
  parsing. A real p1/q1 prompt probe returned empty strings from
  `deepseek-v4-pro` for both the selector prompt (`84167` chars) and answer
  prompt (`93792` chars). Shortened probes still returned empty strings at the
  smallest tested prompt sizes (`66567` selector chars and `51187` answer
  chars).
- Compared with v103 on the same gate, v108 lost `197` judge points overall:
  abstention `+10`, conflict detection `-49`, information extraction `-71`,
  temporal reasoning `-51`, user modeling `-36`.
- Interpretation: this is not a clean model-quality comparison; it mostly
  measures current `deepseek-v4-pro` compatibility with the long-evidence
  prompt shape. Because the score did not exceed `1.4/2`, do not run full
  regression for v108.
- Next path: continue from v103 or another flash-compatible near-gate baseline.
  Do not run another pro 200-QA gate until a 5-10 QA compatibility probe proves
  stable non-empty JSON on a smaller prompt format.

### 2026-07-16 EvoEmo v114-v117 weak-row diagnostics

- Status: compliant diagnostic experiments, all rejected before 200-QA gate.
- v114 `trajectory_answer_composer` probe completed only `7/24` rows in
  `209.33s`; judged score was `0.4286/2`, so the path is both slow and poor
  quality.
- v115 `selector_reason_session_lock` parsed extra source sessions from the
  selector reason without adding an LLM call. The 24-row weak probe scored
  `0.75/2` versus v103's `0.8333/2` on the same original rows, a net `-2`
  judge-point regression.
- v116 `graph_evidence_refiner` also scored `0.75/2` on the same 24-row weak
  probe, net `-2` versus v103. It improved a few user-modeling rows but hurt
  temporal rows.
- v117 enabled v99's deterministic `temporal_sequence_chain` facts inside the
  v103 baseline. It also scored `0.75/2` on the same probe and did not justify
  a 200-QA gate.
- Interpretation: broad post-answer refinement, selector-reason session
  expansion, and global sequence-chain facts all have unacceptable negative
  transfer on v103 weak rows. Do not promote any of these variants.
- Next path: target high-precision deterministic fixes for v103 score-0
  information-extraction and abstention rows first, then run the mandatory
  200-QA gate only if a focused probe shows net positive movement.

### 2026-07-16 EvoEmo v118 high-precision fact guards

- Status: compliant full-dataset regression completed; rejected for promotion.
- Implemented
  `experiments/exp_2026_07_16_evo_emo_v118_high_precision_fact_guards/` from
  v103. v118 adds four narrow deterministic post-answer guards over
  conversation-built graph evidence: breadwinner/provider facts,
  layoff/furlough workplace events, named high-school/old-friend recovery, and
  selector-reported no-evidence overrides for specific date/name/task
  questions.
- Focused 12-row score-0 probe: LLM-as-Judge `0.9167/2`, F1 `43.88`.
- 200-QA gate generation completed `200/200` with zero failures.
- 200-QA gate metrics: LLM-as-Judge `1.41/2`, F1 `43.66`; capability scores
  abstention `1.7333/2`, conflict detection `1.5938/2`, information extraction
  `1.6346/2`, temporal reasoning `1.234/2`, user modeling `0.9231/2`.
- Full-dataset generation completed `1427/1427` with zero failures and
  `275/1427` Unknown predictions.
- Full-dataset metrics: LLM-as-Judge `1.2978/2`, F1 `42.81`; capability scores
  abstention `1.4904/2`, conflict detection `1.3221/2`, information extraction
  `1.644/2`, temporal reasoning `1.1479/2`, user modeling `0.902/2`.
- 300-row judge checkpoints were `1.3333/2`, `1.3833/2`, `1.2633/2`,
  `1.2/2`, and final partial `1.3128/2`; early stop did not trigger because
  there were not three consecutive below-`1.3/2` descending full checkpoints.
- Interpretation: v118's narrow high-precision guards improved the 200-QA gate
  but did not transfer enough to full-dataset temporal reasoning and user
  modeling. Treat v118 as the current checked full-dataset best (`1.2978/2`),
  only slightly above checked v77 full (`1.2929/2`), and still below the
  `1.5/2` target.
- Next path: stop post-answer guard stacking and target temporal/user-modeling
  evidence quality before answer generation.

### 2026-07-16 EvoEmo v119 temporal as-of evidence

- Status: compliant full-dataset regression completed; rejected for promotion.
- Implemented
  `experiments/exp_2026_07_16_evo_emo_v119_temporal_asof_evidence/` from
  v118. v119 keeps v118 graph construction and guards, assigns an independent
  prediction key, and enables the existing opt-in
  `time_aligned_event_neighborhood` retrieval stage before answer generation.
- Diagnostic 24-row temporal/user-modeling zero-score probe: generation
  `24/24`, zero failures, LLM-as-Judge `0.5/2`, F1 `23.35`. This is below the
  100-QA metric floor and is diagnostic only.
- 200-QA gate generation completed `200/200` with zero failures and `32/200`
  Unknown predictions.
- 200-QA gate metrics: LLM-as-Judge `1.405/2`, F1 `41.36`; capability scores
  abstention `1.4667/2`, conflict detection `1.5938/2`, information extraction
  `1.75/2`, temporal reasoning `1.1915/2`, user modeling `1.0/2`.
- Full-dataset generation completed `1427/1427` with zero failures and
  `280/1427` Unknown predictions.
- Full-dataset metrics: LLM-as-Judge `1.2887/2`, F1 `42.58`; capability scores
  abstention `1.4636/2`, conflict detection `1.3071/2`, information extraction
  `1.6019/2`, temporal reasoning `1.2007/2`, user modeling `0.8889/2`.
- 300-row judge checkpoints were `1.3433/2`, `1.3533/2`, `1.28/2`,
  `1.1833/2`, and final partial `1.282/2`; early stop did not trigger because
  there were not three consecutive below-`1.3/2` descending full checkpoints.
- Interpretation: broad time-aligned evidence improved a small diagnostic
  slice but regressed on full data. Do not promote v119; it is below v118 full
  (`1.2978/2`), checked v77 full (`1.2929/2`), and the `1.5/2` target.
- Next path: avoid broader evidence injection. Target a narrower
  temporal/user-modeling failure class or redesign trajectory representation so
  the answerer receives less conflicting chronological context.

### 2026-07-16 EvoEmo v120 trajectory composer probe

- Status: compliant diagnostic completed partially; rejected before 200-QA
  gate.
- Implemented
  `experiments/exp_2026_07_16_evo_emo_v120_trajectory_composer_probe/` from
  v118 with independent prediction and trace keys. The candidate enables the
  existing `--trajectory-answer-composer` flag at run time.
- Focused diagnostic input: 40 v118 full-regression user-modeling
  trajectory-style zero-score rows. This is below the 100-QA metric floor and
  diagnostic only.
- Generation was interrupted for slowness after `347.16s`: `7/40` completed,
  `0` failed, `33` pending.
- Judge on the completed 7 rows: `0/7` correct.
- Prompt budget check: main answer scaffold static chars `4916`; trajectory
  composer scaffold static chars `1197`, both under the 5k hard-concatenated
  prompt limit excluding question and retrieved evidence.
- Interpretation: post-answer trajectory composition is too slow and did not
  recover the targeted failures. Do not run the mandatory 200-QA gate for this
  candidate.
- Next path: target retrieval/ranking or narrow deterministic graph guards for
  cases where v118 retrieves the right episode but selects a later distractor.

### 2026-07-16 EvoEmo v121 fact sentence rescue

- Status: compliant diagnostic completed partially; rejected before 200-QA
  gate.
- Implemented
  `experiments/exp_2026_07_16_evo_emo_v121_fact_sentence_rescue/` from v118
  with independent prediction and trace keys. The candidate adds opt-in
  `--fact-sentence-rescue`, a deterministic no-extra-LLM guard for `Unknown`
  answers.
- Broad diagnostic input: 40 v118 zero-score `Unknown` rows where gold terms
  appeared in retrieved graph facts. This is below the 100-QA metric floor and
  diagnostic only.
- Broad diagnostic was interrupted after `263.74s`: `12/40` completed, `0`
  failed, `28` pending. Rejected the broad guard because it could output
  synthetic internal node text such as `temporal_state_event` and
  `contradiction_support`.
- Refined v121 restricted rescue to direct conversation-derived fact types and
  blocked synthetic graph node types.
- Refined 12-row diagnostic was interrupted after `212.09s`: `5/12`
  completed, `0` failed, `7` pending. Judge on the completed 5 rows was `0/5`.
- Prompt budget check: main answer scaffold static chars `4916`; no new LLM
  prompt was added.
- Interpretation: generic fact-sentence rescue does not move toward the 1.5
  target. The broad version is unsafe; the refined version is too conservative
  and showed no positive signal.
- Next path: target retrieval/ranking, especially rows where the right source
  episode is retrieved but later off-target state summaries dominate the final
  answer.

### 2026-07-16 EvoEmo v122 direct evidence first

- Status: compliant 200-QA gate passed; full-dataset regression pending.
- Implemented
  `experiments/exp_2026_07_16_evo_emo_v122_direct_evidence_first/` from v118
  with independent prediction and trace keys. The candidate adds opt-in
  `--direct-evidence-first`, which prioritizes direct conversation-derived
  facts and suppresses synthetic graph summaries for non-trajectory question
  shapes.
- Focused 8-row diagnostic over v118 direct-fact failure rows: `3/8` correct
  under the binary diagnostic judge. This is below the 100-QA metric floor and
  diagnostic only.
- 200-QA gate generation completed `200/200` with zero failures.
- 200-QA gate metrics: LLM-as-Judge `1.41/2`, F1 `43.08`; capability scores
  abstention `1.6/2`, conflict detection `1.5625/2`, information extraction
  `1.6731/2`, temporal reasoning `1.234/2`, user modeling `1.0/2`.
- Interpretation: v122 matched v118's 200-QA overall gate score while shifting
  quality toward information extraction and user modeling. Because the gate is
  above `1.4/2`, full-dataset regression is required.
- Next path: run full-dataset regression with the same committed candidate
  settings and judge with 300-row checkpoints.

### 2026-07-27 LoCoMo publish-stack cache correctness

- Fixed QA retrieval/answer/checkpoint keys in
  `experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py`.
  Keys now use sample id, QA index, and SHA-256 of the complete question
  instead of the first 120 characters.
- Unified A and B/B-* onto the same validated per-sample memory embedding
  cache file. The index loader continues to verify model, memory ids, and
  memory-text digests before reuse.
- This is a source-only correction with no new metric claim. Graph inputs,
  graph retrieval, and prompt scaffolds are unchanged.

### 2026-07-27 LoCoMo official QA/F1 alignment

- Removed `hit@k` from the active matched-stack runner and generated table
  schema.
- Extracted the official LoCoMo batch-size-1 QA prompt, temporal suffix,
  Category-5 randomized multiple-choice construction, answer decoding, and
  32-token generation settings into `locomo_official_qa.py`.
- Extracted the official normalization, Porter stemming, Counter-based F1,
  multi-hop partial matching, open-domain answer handling, Category-5 binary
  scoring and the Categories 1--4 subset aggregation into
  `locomo_official_metrics.py`.
- The official overall score is now explicitly separated from the compliant
  Categories 1--4 subset promotion track. Official Category 5 includes the
  gold answer in its MCQ prompt and is therefore benchmark-compatible but
  non-compliant with the repository mandatory graph constraint.
- Removed the temporary legacy-schema skip behavior. The rerun uses the normal
  checkpoint names after a one-time deletion of old answer, question-key, and
  A/B embedding caches.
- Cache audit found no matching publish-stack cache files in this workspace's
  `outputs/em_graph/`; graphs, historical results, and snapshots were retained.
- Historical v04 F1 remains diagnostic only. A/B and ablations require a fresh
  full rerun before any official-F1 claim.

### 2026-07-27 LoCoMo conv-26 official-aligned verification

- Added isolated `--samples conv-26` artifact scopes for graph results,
  answer checkpoints, variant results, comparison summaries, and tables.
- Built a fresh conversation-only extract-v4 graph with gpt-3.5-turbo:
  419 Memory nodes, 1095 Entity nodes, 2787 Entity--Memory edges, and 836
  chronological Memory edges; `partial=false`.
- A first five-variant pass exposed repeated API-call variance: A versus
  B-embed differed on 12 top-25 contexts, and 49/187 same-context predictions
  differed despite temperature 0. Snapshot v10 preserves this diagnostic and
  does not count as the final conv-26 result.
- Added one model-specific text-embedding cache shared across A/B/ablations
  and one exact answer-response cache keyed by SHA-256 over the complete
  protocol/model/question/context prompt identity. Category-5 option order is
  deterministic from the same key. Deleted the five first-pass answer
  checkpoints and reran from the corrected cache shape.
- Final controlled conv-26 result (n=199): A Categories 1--4 subset F1/R@25
  `46.76/77.14`; B `49.92/83.75`; delta `+3.16/+6.61` points.
  B-entity `47.21/77.35`, B-embed `46.76/77.14`, and B-noseq
  `49.98/79.98`.
- A and B-embed now have zero differences across all 199 top-50 rankings,
  top-25 contexts, predictions, and per-row F1 values.
- Constraint audit: Categories 1--4 subset PASS; official overall/Category 5
  remains non-compliant for promotion because the official MCQ prompt includes
  the gold answer.
- Snapshot: `snapshots/v12_conv26_full_prompt_cache/`. The result is a
  valid scoped verification but not the final all-10 paper score.

### 2026-07-27 LoCoMo real datetime Memory sequence

- Changed EM Memory `NEXT`/`PREV` ordering from dialog-id/session-number order
  to parsed conversation session `date_time`, with session number, numeric
  turn, and dialog id as deterministic tie-break/fallback fields.
- Kept the existing `MemoryNode.date_time`; no node schema, node id, Memory
  text, embedding input, or Entity--Memory edge change was required.
- Added LoCoMo full timestamp and ISO datetime parsing, including UTC
  normalization for offset-aware ISO values, plus six focused unit tests.
- Audited all 272 dialog-bearing LoCoMo-10 sessions: all corresponding
  timestamps parsed, 0 numbering/time inversions. The dataset has 288
  timestamp keys because 16 `conv-26` keys have no dialog session. The
  old/new conv-26 sequence-edge symmetric difference is 0.
- Deleted and rebuilt the conv-26 EM and memory-only graph caches. Rebuilt EM
  graph: 419 Memory, 1095 Entity, 2787 Mentions, 836 sequence edges,
  `partial=false`.
- No QA generation or metric rerun was needed because the retrieval graph is
  unchanged for LoCoMo-10. Mandatory graph constraint PASS; extraction prompt
  scaffold remains 2410/5000 characters. Snapshot v14.

### 2026-07-27 LoCoMo all-10 regression paused for further alignment

- Built/reused all 10 extract-v4 datetime-ordered conversation graphs and
  passed Memory-count, bipartite, `partial=false`, and exact NEXT/PREV audits.
- Began A only and stopped on user request after 497/1986 rows:
  conv-26 199, conv-30 105, conv-41 193.
- B and all three ablations were not started; no aggregate metric or paper
  update exists.
- The forced stop interrupted the shared text-embedding NPZ flush. That single
  shared cache is invalid and must be deleted before resuming. Four
  per-conversation Memory indexes and both JSON answer caches validate.
- Do not resume until the remaining protocol differences are identified and
  aligned. Snapshot v15 is incomplete/non-promotable.

### 2026-07-27 refactored LoCoMo conv-26 B multi-k preflight

- Ran the committed three-layer stack at source `23e3a4b` from empty new-style
  conv-26 caches. The complete conversation-only graph has 419 Memory nodes,
  1105 Entity nodes, 2903 total edges, and 836 parsed-date-time NEXT/PREV
  edges.
- Evaluated all 199 QA rows independently at top-k 5/10/25/50 with variant B,
  gpt-3.5-turbo extraction/answers, text-embedding-3-small, 0.30 Entity +
  0.70 signed-cosine fusion, and chronological +/-1 expansion.
- Official `recall_acc`: `0.6231/0.7580/0.8610/0.9213`.
- Official overall F1: `0.341/0.385/0.391/0.400`.
- Recall uses the vendored stats aggregation, which retains empty-evidence rows
  in its denominator; it is not a direct mean of the serialized row default.
- Graph construction and graph recall pass the mandatory constraint. Official
  overall F1 is an official-compatibility diagnostic because Category 5 puts
  both choices, including the gold answer, in its prompt. Categories 1–4
  subset F1 is `0.41985/0.49053/0.49905/0.52332`.
- Prompt scaffold audit passes at 2410/5000 characters. Snapshot:
  `experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v09_conv26_B_official_multik/`.
- This does not replace the pending A/B/ablation comparison or all-10 paper
  regression.
