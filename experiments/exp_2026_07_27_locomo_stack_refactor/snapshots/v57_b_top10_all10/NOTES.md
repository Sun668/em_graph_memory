# v57 — formal all-10 B top-k 10 robustness pair

Decision date: 2026-07-29 Asia/Shanghai.
Formal source commit: `35691fb56809a3faeaa0a7cf77e25b3b9da29424`.
Formal source tree: `0a454f65dab5c9d1987a2bf6efb2bb78c58c5c63`.
Frozen parameter SHA-256:
`98db5a8d0022c39f7eaeae17b78a112c17c00ca34bb0921d514c19e168620cda`.
Frozen command SHA-256:
`e5ef17b3b5ed6e4b81206c12fd05419a6c8f4af50895c3a973bd98865e6073c9`.
Dataset SHA-256:
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.

## Outcome

The preregistered complete Entity–Memory `B` condition completed at
`top_k=10` from the absent isolated directory:

```text
outputs/locomo_formal/formal_all10_M4_B_top10_54ae6a9_qfrozen_run01/
```

Across 10 conversations, 1,986 QA rows, and 446 Category-5 rows:

- official serialized-row mean F1: `42.1412%`;
- official evidence `recall_acc`: `74.4847%`;
- local Categories 1–4 subset F1: `50.5795%`;
- local Categories 1–4 subset recall: `75.2771%`.

Against matched A@10, B changes F1 by `+0.3805` points; paired-QA CI
`[-0.8822, +1.6599]` and conversation-cluster CI
`[-0.7099, +1.5111]` both cross zero. Evidence recall increases by
`+5.5702` points; paired-QA CI `[+4.2928, +6.8624]` and
conversation-cluster CI `[+4.2365, +6.7522]` are both above zero
(both p=`0.0002`).

Relative to complete B@25, the descriptive cutoff changes are `-0.4268` F1
points and `-9.9995` recall points. Top-k 25 remains primary. The supported
top-k-10 claim is retrieval-only; A/B@50 is still required to close the
declared cutoff-range matrix.

## Exact command

```bash
RESEARCH_RUN_CLASS=formal \
RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v57_b_top10_all10/parameters.json \
RESEARCH_CONDITION_DIR=outputs/locomo_formal/formal_all10_M4_B_top10_54ae6a9_qfrozen_run01 \
/bin/zsh -lc 'source ./env_gpt.sh; unset http_proxy https_proxy; export EM_GRAPH_EMBED_WAIT=0.05; export EM_GRAPH_MAX_WORKERS=8; export PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache; .venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M4_B_top10_54ae6a9_qfrozen_run01 --scope all10 --variant B --top-k 10 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir outputs/em_graph --output-root outputs/locomo_formal'
```

Statistical command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/graph_memory_pycache \
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py compare \
  --a-dir outputs/locomo_formal/formal_all10_M4_A_top10_0eee9b8_qfrozen_run01 \
  --b-dir outputs/locomo_formal/formal_all10_M4_B_top10_54ae6a9_qfrozen_run01 \
  --resamples 10000 --seed 20260727 \
  --output outputs/locomo_analysis/b_top10_vs_a_top10_35691fb_seed20260727_10000.json
```

## Complete behavior comparison

| Dimension / parameter | Side A: A@10 | Side B: B@10 | Expected impact of the difference |
|---|---|---|---|
| Dataset / scope | LoCoMo-10 SHA `047d8e…d74`; 10 conversations; 1,986 QA; 446 Category 5 | Exact same bytes, order, rows, and denominators | No sampling or aggregation effect |
| Construction inputs | Session anchors, dialog ids, speakers, time-annotated dialog text, captions; QA/judge fields excluded | Exactly the same conversation-only inputs | No input-profile confound |
| Graph | 5,882 Memory nodes and chronology; no Entity retrieval | Same Memories plus 12,808 conversation-extracted Entities, 36,227 Entity–Memory edges, deterministic speaker incidence | Tests the Entity graph contribution |
| Memory indexes | Ten canonical `text-embedding-3-small` indexes | Exact same paths and hashes reused read-only | No Memory-vector effect |
| Query vectors | Artifact SHA `bef99a…986f9f`; ordered 1,986 QA; L2 float32; 1,536 dimensions | Exact same artifact; 1,990 hits, 0 misses, 0 live requests | No query-vector effect |
| Query Entity channel | Disabled | Existing full-question Entity cache, threshold `0.5`, top 20/key, who-only dampening `0.25`, degree discount enabled; zero live requests | Adds conversation-graph candidate evidence |
| Retrieval | Full-pool signed cosine; weights `0/1`; no sequence; top-k 10 | Gated dense fill; Entity/semantic weights `0.30/0.70`; sequence ±1 at secondary scale `0.5`; top-k 10 | Can change ranking, evidence coverage, and answers |
| Reader | Frozen `gpt-3.5-turbo`; system role; temperature 0; 32 tokens; batch 1; upstream Category-5 randomness unchanged | Exactly the same | No intended generation-protocol effect |
| Metrics | Frozen official category-aware F1 and `recall_acc`, three-decimal per-row serialization | Exactly the same definitions and aggregation | Observed differences arise downstream of retrieval |
| Output | Validated isolated v56 directory | New absent isolated v57 directory; no resume/overwrite | No cross-condition contamination |

Exactly aligned: dataset/order, Memory inputs/text/vectors, immutable dense
query vectors, top-k budget, Reader, evaluator, serialization, and
aggregation. Functionally similar but not identical: both retrieve
conversation-built graph Memories, while B additionally uses Entity incidence,
fusion, gating, and sequence expansion. The intended differences are precisely
those B components; no difference is known to have no effect on this dataset.

No old graph, index, query vector, answer, metric, or comparison is
invalidated. New B@10 contexts, answers, metrics, telemetry, and paired
statistics are the only artifacts created. A/B@50 must be rerun as new
condition-specific outputs; earlier cutoffs remain valid.

## Graph extraction, construction, recall, answer, and judge logic

The reused complete-B graph was extracted one normalized conversation Memory
at a time using the bounded `gpt-3.5-turbo` Entity prompt. Entity keys were
normalized, merged, deduplicated, filtered, and linked to Memory nodes;
speakers were added as deterministic Entities. Memory nodes also carry
chronological links. Construction used only session anchors, dialog ids,
speakers, normalized/time-annotated dialog text, and official captions. QA
questions, answers, evidence annotations, categories, judge outputs, previous
predictions, and question-driven ledgers were excluded.

For recall, the full question supplies the frozen dense vector and the
pre-existing question-Entity keys. B gates candidates through matching graph
Entities, fuses Entity and signed-cosine semantic scores at `0.30/0.70`,
applies degree discount, expands chronological neighbors at scale `0.5`, and
uses dense fallback to return exactly ten unique dialog ids. Those
conversation-built graph Memories are formatted as Reader evidence.

The frozen LoCoMo Reader receives the question and retrieved context with
system role, temperature 0, 32 completion tokens, and batch size 1. The judge
is not applicable: this condition uses frozen official category-aware F1 and
evidence `recall_acc`, not the local EvoEmo LLM-as-Judge.

## Cache, prompt, and cost audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.

- graph files remained exactly `70`;
- Memory embedding indexes remained exactly `30`;
- all ten complete-B graphs and canonical Memory indexes were reused read-only;
- graph construction, conversation Entity extraction, Memory embedding, and
  query-Entity external request counts were all zero;
- immutable query use was 1,990 hits, 0 misses, 0 live embedding requests;
- answer recall used conversation-built Entity–Memory graph nodes and edges;
- non-data Entity prompt scaffold was `2,410/5,000` characters; no oversized,
  ineffective, or harmful prompt component was introduced.

Warm telemetry records 30.2918 seconds retrieval, 1,986 answer requests,
1,197,437 answer input tokens, 14,779 answer output tokens, and 2,048.6374
seconds answer-generation wall time. Provider-resolved model revision,
hardware identity, and monetary price remain unknown.

## Validation and reproducibility

Both in-run and independent validators pass with
`paper_metric_eligible=true`, `graph_claim_eligible=true`, exact official
aggregation, complete contexts, and expected counts. The directory did not
exist at start; `resume=false`, `overwrite=false`.

- prediction SHA: `ff7b98981ec7806a15e085c75863c6986603e0422029e1b03e49ed7609e4dae1`;
- stats SHA: `c5f16cc9c3956385799449d332375ae22c2e169f4a975102c688fcbcf6d16c94`;
- audit SHA: `c6ae75a9e58516adad8979db8d6925b172d16907bca7fcf3ea5b5597699980e0`;
- query-usage SHA: `50912a23c98177d2919a961a6f1dd7fbac67608eed8ea3fa08d19709b2555d76`;
- in-run validation SHA: `1ae20f4895c47e8065219338815c18a86c192ab5319158044eea08f93e8a0c6c`;
- independent validation SHA: `2fe0211b8446a256cf10541aed0a259a76ccb1c12b755ea38b2c447a4bad31f6`;
- byte-identical significance report SHA: `80f6252844f1717d285bdbb92f5e84fce4632974127798bbda5d1f7fe6db3aa9`;
- 77/77 tests and 16/16 frozen vendor hashes pass;
- `code/locomo_eval/` has no diff.

Source hashes: `formal_graph.py` `20eabf21…a10af`, `run.py`
`6624d995…68d7`, `validate_formal_result.py` `c0cf9c0e…d5ff`,
`code/em_graph/build/builder.py` `a35cd8fa…be80`, and
`code/em_graph/recall/retrieval.py` `ca19ff96…94ff`.

## Publication decision

This result is valid, reproducible, conversation-only, graph-claim eligible,
and counts as B@10 in the paper robustness matrix. Together with A@10 it
supports a statistically significant `+5.5702`-point evidence-recall
advantage for complete B at top-k 10, but no significant final-answer F1
effect.

Publication gate remains `continue`, `paper_ready=false`. Commit and push v57,
then preregister matched A@50 without modifying shared caches.
