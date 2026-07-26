# Conclusion

## Verdict (matched publish stack)

**Gate: `publish_ok_method_helps`.** Under a single fixed stack
(gpt-3.5-turbo extract-v4 + text-embedding-3-small + gpt-3.5-turbo short QA),
Entity→Memory Dialog retrieval (**B**) beats plain Dialog embedding RAG (**A**)
on both token-F1@25 and recall_acc@25. Ablations show the gain needs **entity
fusion**, not embed-only or entity-only alone; sequence ±1 helps modestly.

| Metric | A | B | Δ |
|---|---:|---:|---:|
| token-F1@25 | 44.99 | **46.48** | **+1.49** |
| ex-cat5 F1@25 | 50.20 | **51.68** | +1.48 |
| recall_acc@25 | 78.53 | **82.54** | **+4.01** |
| hit@25 | 83.69 | 87.56 | +3.87 |

Ablations (same stack): B_entity 40.78 / B_embed 44.83 / B_noseq 46.20 F1@25.

Vs paper Table 3 (cite only; DRAGON ≠ TES): B F1 46.48 > Dialog 41.0 and Obs
best 43.3; B R@25 82.54 > Dialog 76.7. Snapshot
`snapshots/v04_gpt35_tes_ab_ablation/`. Table: `TABLE_GPT35_TES_COMPARE.md`.

## What was run (matched stack)

1. **build-graphs:** all-10 EM extract-v4 with gpt-3.5 → `*_gpt35_tes.json`
2. **A:** memory-only Dialog embed RAG + gpt-3.5 F1
3. **B:** EM 0.3/0.7 + sequence + gpt-3.5 F1
4. **ablation:** B_entity / B_embed / B_noseq
5. **summarize:** compare table + gate

Runner: `run_publish_stack.py`. Package: `em_graph/retrieval.py` adds
`expand_sequence` and empty-`q_keys` BM25 guard.

## Graph extraction / construction / retrieval / metrics

1. **Parameters:** locomo10 all-10 n=1986; extract/answer gpt-3.5-turbo; emb
   text-embedding-3-small; top25 F1; multi-k recall; fusion 0.3/0.7.
2. **Extraction:** LLM extract-v4 (SVO) on conversation after pronoun/time norm.
3. **Graph:** Entity↔Memory bipartite + Memory sequence; conversation-only.
4. **Retrieval:** A = full-pool embed; B = entity BM25 soft-match (+±1 seq) fused
   with embedding over EM graph.
5. **Metrics:** official-style token-F1 + recall_acc (no Mem0 judge).

## Constraint audit

PASS. Graphs conversation-only; answers from graph-retrieved dialogs; q-entity
keys are query-time only. Prompt scaffolds under 5000-char limit.

## Prompt budget

Checked. Short LoCoMo QA + extract-v4 scaffold (~2430). No oversized/harmful
components retained for this run.

## Earlier tracks (not matched-stack headline)

- P0/P1 doubao-emb evidence: F1 46.18 / R@25 82.14 (v01/v02) — different emb.
- P3 oracle Obs/Summary: stop_p3_main_spend (v03).

## Next

- Phase 7: arXiv draft using **A/B gpt35_tes** as fair claim; cite paper with
  DRAGON caveat; no Mem0 in main table.
- Optional: long-context ceiling; error analysis on OD/Adv.
