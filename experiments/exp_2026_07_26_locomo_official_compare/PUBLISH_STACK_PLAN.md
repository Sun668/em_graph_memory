# Complete Plan — LoCoMo fair stack (gpt-3.5 + text-embedding-3-small)

Last updated: 2026-07-26

## Goal

Produce a **publication-ready LoCoMo Table-3 style comparison** under one fixed stack:

| Role | Model / setting |
|---|---|
| Entity extract | `gpt-3.5-turbo` (`OPENAI_MODEL` via `env_gpt.sh`) |
| Embedding | `text-embedding-3-small` |
| Answer | `gpt-3.5-turbo` + LoCoMo short QA prompt |
| Metrics | official **token-F1** + **recall_acc / R@k** |
| Dataset | locomo10 **all-10** |

**Out of scope for this plan:** Mem0 J-score, self-build Obs/Summary, Event/multimodal tasks.

**Claim to support:** Entity→Memory Dialog retrieval improves over plain Dialog embedding RAG under the *same* embedder and reader; also report vs paper Table 3 cited numbers (DRAGON), with an explicit caveat that paper retriever differs.

---

## Environment

```bash
source env_gpt.sh
# Expected:
#   OPENAI_MODEL=gpt-3.5-turbo
#   MODEL=gpt-3.5-turbo
#   JUDGE_MODEL=gpt-3.5-turbo   # unused for main F1 track
#   EM_GRAPH_EMBED_MODEL=text-embedding-3-small
```

Artifact naming convention (avoid clobbering Ark/doubao runs):

```text
outputs/em_graph/{sample}_em_graph_extract_v4_gpt35.json
outputs/em_graph/{sample}_memory_emb_extract_v4_gpt35_text-embedding-3-small.npz
outputs/em_graph/all10_gpt35_tes_* ...
```

Experiment home: `experiments/exp_2026_07_26_locomo_official_compare/`  
Snapshots: `snapshots/v04_…`, `v05_…`, …

---

## Phase 0 — Freeze protocol (0.5 day)

- [x] Set `env_gpt.sh` to gpt-3.5-turbo + text-embedding-3-small
- [x] Record protocol card in snapshot NOTES (`v04_gpt35_tes_ab_ablation`)
- [x] Do **not** reuse doubao graphs or F1 46.18 as this stack’s headline

**Exit:** protocol written; naming fixed.

---

## Phase 1 — Rebuild graphs (extract = gpt-3.5) (1–2 days API)

### 1.1 Smoke: conv-26 only

- [x] Build `conv-26_em_graph_extract_v4_gpt35_tes.json` (via all-10 runner)
- [x] Sanity: bipartite, non-partial (see `result_build_graphs_gpt35_tes.json`)

### 1.2 All-10 graphs

- [x] Build all 10 samples (gpt-3.5 extract-v4, tag `gpt35_tes`)
- [x] Aggregate graph stats in `result_build_graphs_gpt35_tes.json`

**Exit:** 10 complete gpt-3.5 extract-v4 graphs on disk.

**Cost note:** entity extract is the expensive step; checkpoint per sample.

---

## Phase 2 — Embedding indexes (text-embedding-3-small) (0.5–1 day)

- [x] Per-sample Memory emb caches (`*_gpt35_tes_text-embedding-3-small.npz`)
- [x] Shared text cache disabled (dim mix risk); per-sample npz resume OK
- [x] Cache reuse confirmed on ablations

**Exit:** 10 `.npz` memory emb caches ready.

---

## Phase 3 — System B: Entity→Memory (main method) (1–2 days)

### 3.1 Recall sheet

- [x] Multi-k recall_acc + hit in `result_gpt35_tes_em_full_0.3_0.7.json`
- [x] Overall + by category

### 3.2 Answer + F1 @25

- [x] top-25 → gpt-3.5 short QA → token-F1
- [x] Overall F1 **46.48**; ex-cat5 **51.68**; recall_acc@25 **82.54%**

### 3.3 Snapshot

- [x] Folded into `v04_gpt35_tes_ab_ablation` with A + ablations

**Primary headline numbers come from Phase 3 (B) vs Phase 4 (A).**

---

## Phase 4 — System A: Plain Dialog embedding RAG (fair baseline) (1 day)

Same embedder, same reader, **no entity graph retrieval**:

- [x] Memory-only Dialog embed RAG (variant A)
- [x] F1@25 **44.99**; recall_acc@25 **78.53%**

Snapshot: folded into `v04_gpt35_tes_ab_ablation`

**Key comparison:** B − A = **+1.49 F1 / +4.01 R@25** (Entity→Memory helps).

---

## Phase 5 — Ablations on B (optional but recommended) (1 day)

All with gpt-3.5 extract graphs + text-embedding-3-small + gpt-3.5 answer @25:

| Ablation | Setting |
|---|---|
| B-embed | entity_weight=0, semantic=1 (≈ near A if same candidate pool; document difference) |
| B-entity | entity_weight=1, semantic=0 |
| B-full | 0.3 / 0.7 (default) |
| B-noseq | full fusion, sequence expand off |

Minimum viable ablation: **B-entity vs B-full vs A**.  
- [x] All ablations done; snapshot `v04_gpt35_tes_ab_ablation`

---

## Phase 6 — Paper table assembly (0.5 day)

- [x] `TABLE_GPT35_TES_COMPARE.md` + `result_gpt35_tes_compare_summary.json`
- [x] Gate recorded: **`publish_ok_method_helps`**
- [x] `conclusion.md` / `README.md` updated

---

## Phase 7 — Writing / arXiv (parallel after Phase 4)

- [ ] One-sentence contribution (LoCoMo-only, no Mem0)
- [ ] Abstract + Intro + Method + Experiments + Limitations
- [ ] Reproducibility appendix: `source env_gpt.sh` + exact commands
- [ ] Related work: LoCoMo paper baselines; optional brief note that industrial Judge protocols are out of scope
- [ ] Hang arXiv (Phases 1–6 done)

---

## Phase 8 — Stretch (not blocking arXiv)

- [ ] Long-context no-retrieval gpt-3.5 or gpt-4o (Table 2 style ceiling)
- [ ] Second benchmark (LongMemEval) for IEEE long paper
- [ ] Error analysis HTML for OD / Adv fails under B

---

## What not to do

- Mix Mem0 J-score into main LoCoMo table
- Claim oracle Obs/Summary as our system
- Report doubao F1 46.18 as this stack’s result
- Rebuild Obs/Summary self-extract (P3 already stopped)

---

## Timeline (indicative)

| Phase | Calendar |
|---|---|
| 0 Protocol | same day |
| 1 Graph rebuild | 1–2 days |
| 2 Embeddings | 0.5–1 day |
| 3 System B | 1–2 days |
| 4 System A | 1 day |
| 5 Ablations | 1 day (optional) |
| 6 Tables | 0.5 day |
| 7 arXiv draft | 3–7 days writing |

**Critical path to a fair claim:** Phase 1 → 2 → 3 → 4 → 6.

---

## Immediate next action

Phases 1–6 **done**. Next: Phase 7 arXiv draft using A/B gpt35_tes as the fair
claim; cite paper Table 3 with DRAGON caveat; keep Mem0 out of the main table.

---

## Success criteria (publish gate)

1. A and B both finished all-10 with matched stack.  
2. B clearly ≥ A on F1 or recall (preferably both), with numbers in a snapshot.  
3. Main text cites paper Table 3 with DRAGON caveat.  
4. Graph constraint audit passes.  
5. No Mem0 metrics in the main claim table.
