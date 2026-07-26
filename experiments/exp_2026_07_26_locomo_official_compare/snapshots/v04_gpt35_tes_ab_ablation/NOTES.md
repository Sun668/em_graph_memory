# v04_gpt35_tes_ab_ablation

Matched publish stack: **gpt-3.5-turbo extract-v4 + text-embedding-3-small +
gpt-3.5-turbo short QA**. Fair A vs B + ablations. Gate:
**`publish_ok_method_helps`**.

## Commands

```bash
source env_gpt.sh
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8

python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py build-graphs
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py A
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py B
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py ablation
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py summarize
```

Env: `OPENAI_MODEL=MODEL=JUDGE_MODEL=gpt-3.5-turbo`,
`EM_GRAPH_EMBED_MODEL=text-embedding-3-small`. Artifact tag `gpt35_tes`.

## Headline (n=1986 all-10)

| Variant | F1@25 | ex-cat5 F1 | recall_acc@25 |
|---|---:|---:|---:|
| A plain Dialog embed | 44.99 | 50.20 | 78.53 |
| **B EM 0.3/0.7 + seq** | **46.48** | **51.68** | **82.54** |
| B_entity only | 40.78 | 45.27 | 65.99 |
| B_embed full-pool | 44.83 | 49.99 | 78.53 |
| B_noseq (no ±1) | 46.20 | 51.05 | 80.77 |

- Δ(B−A): **+1.49 F1 pp**, **+4.01 recall@25 pp**
- vs paper Dialog (DRAGON, cite only): B F1 46.48 > 41.0; B R@25 82.54 > 76.7
- vs paper Obs best F1 43.3: B +3.18 pp (different retriever caveat)

## Ablation reading

- Entity-only insufficient (F1 40.78 ≪ B).
- Embed-only on EM graph ≈ A (44.83 ≈ 44.99); gain needs entity fusion.
- Sequence ±1 helps modestly (B − B_noseq: +0.28 F1, +1.77 R@25).

## Graph constraint audit

**PASS** (counts toward target).

- Graph inputs: conversation dialogs + captions; extract-v4 entities; Memory
  sequence edges. Paths:
  `outputs/em_graph/{sample}_em_graph_extract_v4_gpt35_tes.json`
- QA questions/answers/evidence/category/judge/ledger **excluded** from graph
  construction. Q-entity keys extracted at query time only for retrieval.
- Answer recall: graph retrieval → top-25 dialog Memory nodes → short QA.
- Prompts/extractors used only to densify conversation graph and retrieve /
  answer over graph evidence.

## Prompt budget

LoCoMo short QA templates + extract-v4 scaffold (~2430 chars). Checked; under
5000-char non-data scaffold limit. No oversized/harmful prompt components added.

## Package note

`em_graph/retrieval.py`: `expand_sequence` flag; skip BM25 when `q_keys` empty
(fixes memory-only / empty-entity ZeroDivisionError).

## Counts toward target?

**Yes** — matched-stack A/B fair claim + ablations. Do **not** cite doubao-era
F1 46.18 as this stack’s headline (different embed/extract).
