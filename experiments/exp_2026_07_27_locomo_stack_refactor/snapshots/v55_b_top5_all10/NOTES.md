# v55 — formal all-10 B top-k 5 robustness result

Decision date: 2026-07-29 Asia/Shanghai.
Formal source commit: `753113f6aac44158ab7606aa1ec4a1917e11da89`.
Formal source tree: `72acc9bdd0fe7c2d374385e8e23360ce842d1cb7`.
Frozen parameter SHA-256:
`12952b757e29a09923f8ca7532f02c88dd86c4d492d641ee2ce14c2f96c262bb`.
Frozen command SHA-256:
`47fdfcaaa9f587557f157a1dfe4b89c532fc23a8f9162051070c0013aac65ce1`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

## Outcome

The all-10 complete Entity–Memory `B` condition completed at the
preregistered robustness cutoff `top_k=5` from the absent isolated directory:

```text
outputs/locomo_formal/formal_all10_M4_B_top5_dff9df4_qfrozen_run01/
```

Across 10 conversations, 1,986 QA rows, and 446 Category-5 rows:

- official serialized-row mean F1: `39.8264%`;
- official evidence `recall_acc`: `64.1667%`;
- local Categories 1–4 subset F1: `46.4255%`;
- local Categories 1–4 subset recall: `65.2176%`.

Relative to matched A@5, B@5 changes overall F1 by `-0.0790` points and
`recall_acc` by `+4.8083` points. The 10,000-resample, seed-`20260727`
analysis finds no overall F1 difference:

- paired-QA 95% CI `[-1.4187, +1.2368]` points, `p=0.9059`;
- conversation-cluster 95% CI `[-1.2738, +0.9872]` points, `p=0.9277`.

The recall advantage is supported under both estimators:

- paired-QA 95% CI `[+3.3450, +6.2808]` points, `p=0.0002`;
- conversation-cluster 95% CI `[+2.8809, +6.6134]` points, `p=0.0002`.

The local Categories 1–4 recall difference is `+2.0775` points; its paired-QA
interval is positive, but its conversation-cluster interval crosses zero.
Category and local-subset analyses remain exploratory. Top-k 25 remains the
primary comparison; this is one robustness point, not yet a complete
top-k-range claim.

## Exact command

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v55_b_top5_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M4_B_top5_dff9df4_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M4_B_top5_dff9df4_qfrozen_run01 --scope all10 --variant B --top-k 5 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

## Complete A@5 versus B@5 behavior comparison

| Dimension / parameter | Side A: A@5 exact behavior | Side B: B@5 exact behavior | Expected impact of the difference |
|---|---|---|---|
| Dataset / scope | LoCoMo-10 SHA `047d8e…d74`; canonical 10-conversation order; 1,986 QA; 446 Category 5 | Exactly the same bytes, order, rows, and denominators | No sampling or aggregation effect |
| Conversation preprocessing | Date/time anchors, dialog ids, speakers, time-annotated dialog text, and official `blip_caption`; no QA-derived build inputs | Exactly the same Memory preprocessing | No Memory-content difference |
| Extraction | No Entity extraction used by the memory-only profile | Existing conversation-only GPT-3.5 `v4` Entity/SVO/fact extraction with normalization, filtering, merge, and dedup; cached read-only | Adds conversation-derived Entity structure without changing Memory text |
| Graph construction | Memory-only graph over the same 5,882 chronological Memory nodes | Bipartite Entity–Memory graph with `Mentions` links, chronological `NEXT/PREV` Memory edges, and deterministic speaker Entities | Changes candidate gating, Entity scores, and sequence expansion |
| Memory indexes | Ten canonical `text-embedding-3-small` indexes over `{speaker} said, "{normalized text}"` plus caption when present | Exact same ten index paths and SHA-256 values reused read-only | No Memory-vector difference |
| Query vectors | Frozen artifact SHA `bef99a…986f9f`, role `context`, L2 float32, 1,536 dimensions | Exact same artifact; 1,988/1,988 lookups hit, 0 misses, 0 live requests | No query-vector identity difference |
| Query Entities | Not applicable because A forces the full Memory pool | Existing question-Entity cache keyed by sample, QA index, full-question SHA, model, and protocol; zero external requests | Enables Entity gate without new model nondeterminism or cost |
| Candidate pool | Full Memory pool | Entity-related gated candidates plus deterministic dense semantic fill | Can concentrate relevant candidates before top-k truncation |
| Scoring / fusion | Signed cosine only; Entity/semantic weights `0.0/1.0`; degree discount not active | Entity/semantic weights `0.30/0.70`; minimum relation `0.50`; top 20 Memories per Entity key; who-only dampening `0.25`; degree discount enabled | Changes Memory ranking through graph and semantic evidence fusion |
| Sequence | Disabled | Bidirectional chronological expansion enabled at secondary scale `0.50` | Can add adjacent evidence and change ranking |
| Cutoff / formatting | Exactly 5 unique Memory contexts, ordered by A ranking and rendered as dialog evidence | Exactly 5 unique Memory contexts, ordered by B ranking and rendered identically | Shared context budget; content/order can differ |
| Reader | Frozen `gpt-3.5-turbo`; system role; temperature 0; 32 tokens; batch 1; upstream Category-5 option randomness unchanged | Exactly the same | No intended answer-protocol effect; retrieved context is the causal path |
| Metrics | Frozen official category-aware per-row F1 and `recall_acc`, three-decimal serialization and official aggregation | Exactly the same | Differences come from retrieval/context and resulting answers |
| Statistics | 10,000 paired-QA and whole-conversation bootstrap resamples, seed `20260727`, B−A direction | Same paired report contains both sides | Supports measured-population inference; no top-k-family multiplicity claim |
| Output | Existing validated v54 isolated directory | New absent isolated v55 directory; no resume/overwrite | No cross-condition contamination |

Exactly aligned: dataset/order, Memory preprocessing and text, Memory ids and
embedding vectors, question-vector artifact, top-k budget, context formatting,
Reader protocol, official evaluator, serialization, aggregation, and
statistical seed/procedure.

Functionally similar: both recall implementations return unique chronological
Memory evidence through the same `QARecall` boundary, but their candidate and
ranking mechanisms are intentionally different.

Different: B adds the conversation-extracted Entity graph, Entity gate,
`0.30/0.70` fusion, degree-aware scoring, and sequence expansion. These
differences affect candidate order, contexts, answers, metrics, retrieval
latency, and the method claim, but not cache validity.

No present-data no-effect exception is used to dismiss an intended component:
the observed context and recall changes show that the B retrieval path is
active. Provider/backend identity and unseeded Category-5 option ordering
remain common uncontrolled factors.

No prior graph, index, query artifact, answer, metric, or comparison is
invalidated. The minimal remaining reruns for the predeclared cutoff-range
claim are matched A/B at top-k 10 and 50; top-k 25 remains the primary
already-completed pair.

## Graph extraction, construction, recall, and answer logic

Graph construction consumes only session anchors, dialog ids, speakers,
normalized/time-annotated dialog text, and official image captions. The
conversation extractor creates Entity/SVO/fact units with the committed
schema, normalization, filtering, merging, and deduplication logic. Entity
nodes connect to Memory nodes through `Mentions`; Memory nodes connect through
chronological `NEXT/PREV` edges. QA questions, answers, evidence labels,
categories, judge outputs, and previous predictions are excluded from graph
construction.

At retrieval, the complete question supplies the immutable dense query vector
and addresses the separately cached question-Entity keys. B gates candidates
through related graph Entities, combines Entity score `0.30` with signed
semantic similarity `0.70`, applies the declared Entity threshold/top-per-key,
who-only dampening, degree discount, and sequence scale, then fills
deterministically to exactly five unique Memory ids. Retrieved dialog evidence
is passed through the unchanged `QARecall` interface. The frozen Reader uses
only the question and graph-retrieved context to generate the answer.

The judge is not applicable: this LoCoMo condition uses the frozen official
category-aware F1 and `recall_acc` implementation, not the local EvoEmo
LLM-as-Judge.

## Cache, graph, prompt, and cost audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.

- graph files remained exactly `70`;
- Memory embedding indexes remained exactly `30`;
- all ten complete-B graphs and canonical Memory indexes were reused read-only;
- graph construction, Entity extraction, Memory embedding, and query-Entity
  external request counts were all zero;
- immutable query use was 1,988 hits, 0 misses, 0 live embedding requests,
  satisfying the 1,986-row coverage requirement;
- graph construction excluded every QA, answer, evidence, category, judge,
  and prediction field;
- answer recall traversed the conversation-built Entity–Memory graph;
- non-data Entity prompt scaffold was `2,410/5,000` characters; no oversized,
  ineffective, or harmful prompt component was added.

Warm telemetry records 30.3827 seconds retrieval, 1,986 answer requests,
667,165 answer input tokens, 14,210 answer output tokens, and 2,098.4169
seconds answer-generation wall time. Provider-resolved model revision,
hardware identity, and monetary price remain unknown.

## Validation and reproducibility

Both in-run and independent validators pass with
`paper_metric_eligible=true`, `graph_claim_eligible=true`, exact official
aggregation, complete contexts, and expected counts. The directory did not
exist at start; `resume=false`, `overwrite=false`.

Verification:

- prediction SHA:
  `c41d51b9f8f3ab7ab1391fec26a8e35c0b54e71fe03171daa67783cd325103f0`;
- stats SHA:
  `c52d99afc3f68d2dd0b1a3dd842f4ff1fbf99d030654f64a88408983d796cd01`;
- audit SHA:
  `c6ae75a9e58516adad8979db8d6925b172d16907bca7fcf3ea5b5597699980e0`;
- query-usage SHA:
  `71f2c594e37aaf6d42ac47815299022b12505b726963933ca72b6fd86b4a67cd`;
- in-run validation SHA:
  `2f3ea00e82339d6213cd38cbbfe08abf8b129528473facab358123bc7ca2e36f`;
- independent validation SHA:
  `32835a868697b9bcdaa5c151144147cfe25206b5b973e13b78bd9cb84d82de7f`;
- significance report and independent repeat are byte-identical, SHA:
  `22efbbd3ae8d895c5d737c0d05e25e3e66f31ee180fb8cee918367a87aa01440`;
- 77/77 tests pass;
- 16/16 frozen vendor hashes pass;
- `code/locomo_eval/` has no diff.

Source hashes: `formal_graph.py` `20eabf21…a10af`, `run.py`
`6624d995…68d7`, `validate_formal_result.py` `c0cf9c0e…d5ff`,
`code/em_graph/build/builder.py` `a35cd8fa…be80`, and
`code/em_graph/recall/retrieval.py` `ca19ff96…94ff`.

## Publication decision

This result is valid, reproducible, conversation-only, graph-claim eligible,
and counts as B@5 in the paper robustness matrix. At top-k 5, complete B has
a statistically supported `+4.8083`-point overall evidence-recall advantage
over A under both preregistered estimators, while no final-answer F1
difference is supported.

This strengthens the primary top-k-25 retrieval claim at one smaller cutoff,
but does not yet establish robustness across the declared cutoff range.
Publication gate remains `continue`, `paper_ready=false`. Commit and push v55,
then preregister matched A@10 without modifying shared caches.
