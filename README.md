# em_graph_memory

Entity–Memory bipartite graphs for LoCoMo **Dialog** retrieval.

This repository is a self-contained snapshot so others can reproduce the matched-stack **A / B / ablation** experiments:

| System | Meaning |
|---|---|
| **A** | Plain Dialog embedding RAG (full Memory pool, no entity gate) |
| **B** | Entity→Memory fusion `0.30E + 0.70Embed` + ±1 sequence |
| **B_entity** | Entity scores only |
| **B_embed** | Dense-only on EM Memories (full pool) |
| **B_noseq** | Same fusion as B, sequence expansion off |

**Stack:** `gpt-3.5-turbo` extract-v4 + `text-embedding-3-small` + `gpt-3.5-turbo` short QA  
**Metrics:** token-F1@25 + recall_acc@k (LoCoMo-style; not Mem0 judge)  
**Paper LaTeX:** [`paper/arxiv/`](paper/arxiv/)  
**Published numbers:** [`experiments/exp_2026_07_26_locomo_official_compare/TABLE_GPT35_TES_COMPARE.md`](experiments/exp_2026_07_26_locomo_official_compare/TABLE_GPT35_TES_COMPARE.md)

Headline (n=1986): **A** F1 44.99 / R@25 78.53 → **B** F1 **46.48** / R@25 **82.54**.

---

## Repository layout

```text
em_graph/                         # Entity–Memory package
data/locomo10.json                # LoCoMo-10 conversations + QA
experiments/shared/llm_client.py  # answer LLM helper
experiments/exp_2026_07_26_locomo_official_compare/
  run_publish_stack.py            # A / B / ablation / summarize runner
  result_gpt35_tes_*.json         # committed metric summaries
  snapshots/v04_gpt35_tes_ab_ablation/
outputs/em_graph/                 # gpt35_tes graphs, embeddings, qkeys, answer ckpts
paper/arxiv/                      # arXiv LaTeX
env.example.sh                    # API env template (no secrets)
```

---

## Setup

```bash
git clone https://github.com/Sun668/em_graph_memory.git
cd em_graph_memory
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp env.example.sh env.sh
# edit env.sh: set OPENAI_API_KEY (and optional OPENAI_BASE_URL)
source env.sh
```

Python path: run commands from the repo root so `em_graph` and `experiments` import cleanly.

---

## Reproduce A / B / ablations

Prebuilt **gpt35_tes** graphs + `text-embedding-3-small` Memory embeddings + question entity keys are under `outputs/em_graph/`.  
Answer checkpoints are also included so answer generation can resume.

### 1) Rebuild graphs only if needed

```bash
source env.sh
export EM_GRAPH_EMBED_WAIT=0.05 EM_GRAPH_MAX_WORKERS=8
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py build-graphs
```

Skip if `outputs/em_graph/*_em_graph_extract_v4_gpt35_tes.json` already exist.

### 2) System A (plain Dialog embed)

```bash
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py A
```

### 3) System B (EM 0.3/0.7 + sequence)

```bash
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py B
```

### 4) Ablations

```bash
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py ablation
# equivalent to: B_entity, B_embed, B_noseq
```

### 5) Compare table

```bash
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py summarize
# writes TABLE_GPT35_TES_COMPARE.md + result_gpt35_tes_compare_summary.json
```

### Offline check of committed metrics

Without API calls, open:

- `experiments/exp_2026_07_26_locomo_official_compare/result_gpt35_tes_plain_dialog_embed.json`
- `result_gpt35_tes_em_full_0.3_0.7.json`
- `result_gpt35_tes_em_entity_only.json`
- `result_gpt35_tes_em_embed_fullpool.json`
- `result_gpt35_tes_em_full_noseq.json`
- `TABLE_GPT35_TES_COMPARE.md`

---

## Constraint

Graphs are built from **conversation only** (dialogs, speakers, captions, session times).  
QA answers / evidence / category / judge outputs are **not** used in graph construction.  
Answers are generated from graph-retrieved dialog turns.

---

## Citation / data

Please cite LoCoMo: Maharana et al., ACL 2024.  
`data/locomo10.json` is redistributed here for reproducibility of this snapshot; follow the original dataset license/terms for downstream use.

Code URL: https://github.com/Sun668/em_graph_memory
