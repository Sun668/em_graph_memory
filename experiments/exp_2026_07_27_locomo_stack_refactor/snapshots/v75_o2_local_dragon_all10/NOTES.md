# v75 O2 local DRAGON all-10 diagnostic

## Status and claim boundary

The preregistered O2 condition completed all 10 conversations and 1,986 QA
rows from an absent condition directory. Both the embedded and independent
formal validators pass. The result is paper-eligible only as a local-stack
diagnostic. It is not eligible as an official-reference comparison because O1
did not meet the fixed official DRAGON Recall@25 reproduction tolerance.

No post-result tuning was performed. Favorable, null, and unfavorable outcomes
were all admissible under the frozen v75 contract.

## Exact execution

Runtime environment:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
PYTHONPATH=code
Python 3.9.6
torch 2.0.1
transformers 4.35.0
tokenizers 0.14.1
numpy 1.26.0
device=cpu
cuda_runtime=none
```

Scientific command recorded by the runner:

```bash
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9 \
  experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py \
  --run-id formal_all10_O2_B_dragon_raw_minmax_top25_v75_qfrozen_run01 \
  --scope all10 \
  --variant B \
  --top-k 25 \
  --extract-model gpt-3.5-turbo \
  --embedding-model dragon \
  --embedding-normalization none_float32_v1 \
  --semantic-score-normalization query_local_minmax_v1 \
  --answer-model gpt-3.5-turbo \
  --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_dragon_raw_v2.npz \
  --cache-dir outputs/em_graph \
  --output-root outputs/locomo_formal \
  --o2-local-dragon-diagnostic
```

The wrapper sourced `env_gpt.sh`, unset proxy variables, selected
`outputs/o2_dragon_runtime/bin/python`, and enabled offline Hugging Face model
loading. Secrets are intentionally excluded.

## Parameters and settings

- Dataset: `data/locomo10.json`, SHA
  `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
- Scope: all 10 conversations, 1,986 QA rows, 446 Category-5 rows, immutable
  dataset order, no category filter or random subsampling.
- Extraction model: `gpt-3.5-turbo`; existing v4 conversation Entity cache
  and question Entity cache were reused, with zero new Entity calls.
- Embedding: pinned separate DRAGON query/context encoders, revisions
  `2d3808c…12cee` and `68074e7…0e9d4`, CLS pooling, max length 512, raw
  float32 vectors, no L2 normalization, raw dot product, dimension 768.
- Query artifact: `locomo10_047d8e25_dragon_raw_v2.npz`, SHA
  `5a8b96c…ebf81`, query role, 1,986 ordered rows / 1,974 unique questions.
- Retrieval: B, top-k 25, Entity/Semantic weights `0.30/0.70`, query-local
  min-max semantic calibration with equal scores mapped to zero, sequence
  expansion on, sequence secondary scale `0.5`, Entity threshold `0.5`,
  Entity top-k/key `20`, who-only dampening `0.25`, degree discount on,
  full-pool forcing off, score then dialog-id tie breaking.
- Answer generation: frozen `QARecall`, requested `gpt-3.5-turbo`, system
  role, temperature 0, max completion tokens 32, batch size 1, unchanged
  unseeded upstream Category-5 option ordering.
- Evaluation: frozen `code/locomo_eval`, upstream commit
  `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`; no local judge.

## Graph extraction and construction

The graph was not regenerated for O2. Ten existing complete-B graphs were
reused read-only. Their v4 LLM extraction consumes only session date/time,
dialog id, speaker, dialog text, and image caption. It extracts normalized
conversation Entities and links them to Memory/dialog nodes. Deterministic
speaker Entities, time annotations, captions, and chronological sequence
edges remain enabled.

The graph is an Entity–Memory bipartite structure augmented by chronological
Memory sequence edges. QA questions, answers, evidence annotations, category
labels, judge outputs, previous predictions, and question-driven ledgers are
excluded from construction. The mandatory conversation-only graph constraint
passes.

## Recall and answer path

At retrieval time only, the current question is mapped to cached question
Entities and the immutable query-role DRAGON vector. Entity relevance gates
the candidate pool. Raw query/context dot products are calibrated within the
current query, fused with Entity scores, degree-adjusted, expanded along
sequence edges, and filled from the independently calibrated unused Memory
pool until top-k 25. Retrieved conversation-built dialog nodes are formatted
as dated context and passed to the frozen Reader.

The query artifact recorded 1,997 lookups, 1,997 hits, zero misses, and zero
live embedding requests. The extra 11 lookups are validation/preflight
accesses; all 1,986 required QA rows are covered.

## Results

| Metric | O2 local DRAGON | Primary local B | Descriptive difference |
|---|---:|---:|---:|
| Overall F1 | 42.4419% | 42.5680% | -0.1260 points |
| `recall_acc` | 81.4261% | 84.4842% | -3.0582 points |
| Categories 1–4 subset F1 | 51.7466% | 51.9740% | -0.2275 points |
| Categories 1–4 subset recall | 83.3521% | not used for the O2 claim | descriptive only |

Category F1 is C1 `41.2177%`, C2 `41.9888%`, C3 `22.2000%`, C4
`62.3742%`, and C5 `10.3139%`. Category `recall_acc` is C1 `66.5078%`, C2
`89.7717%`, C3 `57.1896%`, C4 `89.5364%`, and C5 `74.7758%`.

This cross-stack comparison is descriptive, not inferential: the primary B
uses `text-embedding-3-small` L2/cosine-style vectors and a different frozen
query artifact, while O2 uses raw pinned DRAGON vectors and query-local
min-max calibration. The graph profile, B gating/fusion weights, sequence
settings, top-k, Reader, and evaluator are aligned. The semantic embedding,
score calibration, runtime, cache identities, and source commits differ.

## Cost and resource gates

The warm formal run reused all graphs and indexes. Retrieval took
`34.9598s`. Answer generation took `2081.7038s`, made 1,986 requests, and
used 2,824,310 input plus 16,464 output tokens. These remain below the frozen
3.5M input, 63,552 output, 1,986 request, 7,200s wall, and 100MB condition
limits. Graph construction, Entity extraction, Memory embedding, and query
embedding made zero provider requests.

This warm telemetry is not the final cold/warm cost comparison; a matched
preregistered cold probe remains required.

## Validation and cache safety

- Embedded formal validator: pass.
- Independent validator: pass.
- Regression suite: 109/109.
- Frozen evaluator manifest: 16/16.
- Output directory absent at start; no resume or overwrite.
- Prompt scaffold: 2,410/5,000 characters.
- Prediction SHA: `10b1f63e…0937`.
- Stats SHA: `670704bf…74d2`.
- Audit SHA: `49cc27b7…ca3b`.
- Graph files: 70; unchanged set SHA `6cc96ee6…1ab3`.
- Original Memory indexes: 30; unchanged set SHA `e8c0c14a…48b0`.
- New isolated O2 raw indexes: 10; set SHA `414ba2fa…6e70`.
- Total Memory indexes: 40; set SHA `e5af612f…02ed`.

No old graph, index, query artifact, result, or other cache was deleted,
overwritten, or rebuilt.

## Conclusion and next action

O2 shows that replacing the primary semantic channel with pinned raw DRAGON
plus query-local min-max calibration leaves final-answer F1 nearly unchanged
but lowers evidence recall descriptively. This does not validate an official
DRAGON comparison and does not supersede the primary B result.

Publication gate: `continue_to_cost_and_final_audit`; `paper_ready=false`.
Next: commit and push v75, complete the matched cold/warm cost measurement,
then run the final publication claim/evidence audit before manuscript drafting.
