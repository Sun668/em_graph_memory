# v28 — M2 B_embed dense-control failure

Decision date: 2026-07-28 Asia/Shanghai.
Formal run source commit: `ceebbd5d64b06585cd837391cf5301ac9d3fc156`.
Formal run source tree: `56f46efe1f7aebe2663b9e74fe1e66db28026289`.

This snapshot freezes the completed all-10 B_embed run and the mandatory
dense-control failure discovered before any cache or runner source change.
The run is useful only as a diagnostic. It is not an accepted structural
ablation and its metrics must not be promoted.

## Exact commands and environment-facing settings

The first sandboxed attempt failed before predictions because DNS access to the
configured model endpoint was unavailable. Its exact incomplete output files
were inspected and then deleted; no old checkpoint was skipped or resumed.
The successful run started from an absent directory:

```text
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id formal_all10_M2_embed_top25_ceebbd5_run01 --scope all10 --variant B_embed --top-k 25 --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --cache-dir outputs/em_graph --output-root outputs/locomo_formal
```

Independent formal validation:

```text
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/validate_formal_result.py outputs/locomo_formal/formal_all10_M2_embed_top25_ceebbd5_run01 --data-file data/locomo10.json
```

Mandatory dense-control command:

```text
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py dense-control --a-dir outputs/locomo_formal/formal_all10_M1_A_top25_3e3a33b_run01 --b-embed-dir outputs/locomo_formal/formal_all10_M2_embed_top25_ceebbd5_run01 --data-file data/locomo10.json --output outputs/locomo_analysis/m2_embed_vs_a_dense_control.json
```

The dense-control command failed before writing its output:

```text
ValueError: dense-control context order mismatch at conv-30[10]
```

## Conditions and parameters

The run covers all 10 pinned LoCoMo conversations, 1,986 QA rows, and 446
Category-5 rows. B_embed builds the complete Entity–Memory graph with
`gpt-3.5-turbo` conversation Entity extraction but disables every Entity
retrieval effect: Entity weight `0.0`, semantic weight `1.0`, full candidate
pool, no sequence expansion, and top-k `25`. It uses
`text-embedding-3-small` for Memory and question embeddings and
`gpt-3.5-turbo` for answer generation. Reader temperature is `0`, maximum
answer tokens are `32`, batch size is `1`, and the official Category-5 option
ordering remains unchanged and unseeded.

All ten B_embed Memory embedding-index files are byte-identical to the
corresponding M1-A indexes. The only intended graph difference is that A has a
Memory-only graph while B_embed packages the same Memory nodes inside the
complete Entity–Memory graph.

## Graph extraction and construction

Each dialog becomes one Memory node. The v4 LLM Entity extractor receives
only conversation-derived normalized dialog text plus optional
`blip_caption`; speakers are added as Entity nodes. Entity keys are normalized,
deduplicated, and schema checked. Entity–Memory edges represent mentions and
Memory NEXT/PREV edges follow parsed conversation `date_time`.

Graph construction uses only session time, dialog ids, speakers, dialog text,
and image captions. It excludes QA questions, answers, evidence annotations,
categories, judge results, previous predictions, and question-driven ledgers.
Questions are used only at retrieval time. The entity-extraction prompt
scaffold is `2,410/5,000` characters.

## Retrieval and answer logic

B_embed forms the dense query from the raw QA question, obtains a normalized
`text-embedding-3-small` query vector, computes signed cosine scores against
the shared normalized Memory vectors, and sorts by descending score with
dialog id as the deterministic tie break. It retrieves exactly 25 unique
Memory/dialog ids for every QA and formats their raw dialog text and captions
for the frozen official Reader.

No Entity gate, Entity score, or sequence expansion contributes to B_embed
retrieval. Therefore every per-QA ordered context-id list must be exactly equal
to A. This equality is a control-validity requirement, not a performance
threshold.

## Formal metrics and failed control

The standalone formal validator passes all 29 checks, including exact
10/1986/446 counts, dataset/sample/QA order, 25 unique valid contexts per row,
official stats parity, isolated/no-resume output, graph constraint, and prompt
budget.

The diagnostic metrics are:

- overall token-F1 `41.5877%`;
- official-contribution Recall@25 `79.7468%`;
- local Categories 1–4 F1 `50.9695%`;
- local Categories 1–4 Recall@25 `82.8099%`.

Recall is numerically identical to A, but ordered retrieval is not. Exact
comparison finds `61/1986` mismatched rows: 51 retain the same top-25 set with
different order, while 10 change at least one top-25 id. Mismatches occur in
eight conversations: conv-30 `2`, conv-41 `11`, conv-42 `6`, conv-43 `10`,
conv-44 `6`, conv-47 `8`, conv-48 `8`, and conv-49 `10`.

## Root-cause evidence

`formal_graph.py` creates all ten recall objects before evaluation, and
`run.py::_load_recall` creates a separate `TextEmbeddingCache` object for each
conversation. Every object loads the same whole-file cache snapshot. When a
later conversation adds query vectors, `flush()` rewrites the entire NPZ from
that object's stale in-memory dictionary, overwriting additions made through
the other objects. The lock in `TextEmbeddingCache` is instance-local and
cannot prevent this lost-update pattern.

The current cache contains 6,707 vectors but only 838 of the 1,986 dataset
question lookups; 1,148 question lookups miss. All 838 currently recoverable
question vectors reproduce B_embed's ordered contexts exactly. This, the
byte-identical Memory indexes, unchanged retrieval source, and absence of
retrieval-parameter differences isolate the failure to the unbound,
whole-file query-vector cache.

The formal run config records every Memory embedding-index hash but not the
query-vector cache content hash or coverage. Its warm cost telemetry also
reports zero embedding requests because retrieval-time query embedding calls
are outside the current embedding-stage counter. Both audit gaps must be fixed
before rerunning.

## Metric and judge logic

Token-F1, Category-5 generation, `recall_acc`, three-decimal per-row rounding,
and official aggregation come from the frozen pinned LoCoMo evaluator. For
analysis, evidence-empty rows contribute zero recall while all QA remain in the
denominator. No LLM-as-Judge is used for this LoCoMo experiment.

## Compliance and decision

- Mandatory graph constraint: pass.
- Frozen `code/locomo_eval/`: unchanged.
- Formal result validation: pass.
- Prompt budget: pass at `2,410/5,000`.
- Dense-control exact ordered-context equality: **fail**.
- Regression verification: 62/62 experiment tests and all 16 frozen vendor
  hashes pass.
- Snapshot reproducibility: source is recoverable from the committed base
  commit; bulky output remains under `outputs/` with hashes in `result.json`.
- Ineffective or harmful prompt components: none introduced.

Publication gate: `stop_for_control_repair`, `paper_ready=false`. This is a
validity failure, so no dependent structural ablation may start. The next
action is to bind one complete immutable query-embedding cache to the formal
condition, test against lost updates, and rerun matched A and B_embed from
absent directories. Because historical M1-A and M1-B did not bind the query
cache, the corrected primary A/B pair must also be rerun before final
significance and paper claims.
