# exp_2026_07_26_locomo_official_compare

## Purpose

Align Entity→Memory dialog RAG with **official LoCoMo QA** (paper Tables 2–3:
token-F1 + R@k / recall_acc). Separate from Mem0 J-score.

## Matched publish stack (primary claim) — done

Stack: **gpt-3.5-turbo extract-v4 + text-embedding-3-small + gpt-3.5-turbo**
(`env_gpt.sh`). Fair pair A vs B + ablations.

| Variant | F1@25 | recall_acc@25 |
|---|---:|---:|
| A plain Dialog embed | 44.99 | 78.53 |
| **B EM 0.3/0.7 + seq** | **46.48** | **82.54** |
| B_entity / B_embed / B_noseq | 40.78 / 44.83 / 46.20 | 65.99 / 78.53 / 80.77 |

Gate: **`publish_ok_method_helps`** (ΔF1 +1.49, ΔR@25 +4.01).  
Table: [`TABLE_GPT35_TES_COMPARE.md`](TABLE_GPT35_TES_COMPARE.md).  
Snapshot: `snapshots/v04_gpt35_tes_ab_ablation/`.

## Earlier diagnostics (not matched-stack headline)

| Metric | Value | note |
|---|---:|---|
| P0 recall_acc@25 (doubao emb) | 82.14% | snapshot v01 |
| P1 F1@25 (doubao evidence + gpt-3.5) | 46.18% | snapshot v02; **not** gpt35_tes headline |
| P3 oracle Obs/Summary F1 | 32.69 / 30.21 | v03; **stop_p3_main_spend** |

## Snapshots

- `v01_p0_multik_recall_sheet`
- `v02_p1_gpt35_reanswer_f1`
- `v03_p3_step1_oracle_obs_summary`
- `v04_gpt35_tes_ab_ablation` — matched A/B + ablations (**primary**)

## Commands (matched stack)

```bash
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05 EM_GRAPH_MAX_WORKERS=8
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py build-graphs
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py A
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py B
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py ablation
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py summarize
```

Plan checklist: [`PUBLISH_STACK_PLAN.md`](PUBLISH_STACK_PLAN.md).  
arXiv **submission LaTeX**: [`paper/arxiv/`](paper/arxiv/) (`main.tex`).  
Long lab draft: [`paper/ARXIV_DRAFT.md`](paper/ARXIV_DRAFT.md).

## Constraint

Conversation-only EM graphs; answer via retrieved dialogs; no QA leakage into
graph. Mem0 judge not used for promotion claims in this directory.
