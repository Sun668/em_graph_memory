# Matched stack compare (gpt-3.5 extract + text-embedding-3-small + gpt-3.5 F1)

**Gate:** `publish_ok_method_helps`  
**Snapshot:** `snapshots/v04_gpt35_tes_ab_ablation/`  
**Runner:** `run_publish_stack.py` (tag `gpt35_tes`)

## Main table

| Variant | F1@25 | ex-cat5 F1 | recall_acc@25 | hit@25 | R@5 | R@10 | R@50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A (plain_dialog_embed) | 44.99 | 50.2 | 78.53 | 83.69 | 56.95 | 67.21 | 85.61 |
| B (em_full_0.3_0.7) | 46.48 | 51.68 | 82.54 | 87.56 | 62.82 | 72.92 | 88.82 |
| B_entity (em_entity_only) | 40.78 | 45.27 | 65.99 | 71.75 | 41.98 | 52.37 | 73.41 |
| B_embed (em_embed_fullpool) | 44.83 | 49.99 | 78.53 | 83.69 | 56.95 | 67.26 | 85.56 |
| B_noseq (em_full_noseq) | 46.2 | 51.05 | 80.77 | 85.95 | 60.70 | 70.62 | 86.72 |

- ΔF1 (B−A) = **+1.49** pp; Δrecall@25 = **+4.01** pp

## 1. Parameters and settings

| Item | Value |
|---|---|
| Dataset | locomo10 all-10, n=1986 QA (Overall includes cat5) |
| Extract model | `gpt-3.5-turbo` (`OPENAI_MODEL`, extract-v4) |
| Embedding | `text-embedding-3-small` |
| Answer | `gpt-3.5-turbo`, LoCoMo short QA (+ cat5 refusal, temporal suffix) |
| Fusion (B) | `0.30` entity + `0.70` embedding; sequence ±1 @0.5 |
| Top-k | F1 primary @25; recall @5/10/25/50 |
| Env | `source env_gpt.sh`; `EM_GRAPH_EMBED_WAIT=0.05`; `EM_GRAPH_MAX_WORKERS=8` |
| Artifacts | `outputs/em_graph/*_gpt35_tes*` (graphs/emb/qkeys/answer ckpts) |
| Results | `result_gpt35_tes_*.json`, `result_gpt35_tes_compare_summary.json` |

**A:** memory-only graphs (no entity LLM), full-pool embed retrieve, no sequence.  
**B:** EM extract-v4 graphs, entity BM25 soft-match gate + fusion + sequence.  
**Ablations:** entity-only / embed full-pool / full no-sequence.

## 2. Graph extraction logic

- Units: Memory (dialog turn + optional caption) + Entity mentions (SVO-oriented extract-v4).
- Extractor: LLM `EntityExtractor` on conversation text after `replace_pronouns`.
- Dedup/normalize via package entity keys; bipartite assert; no QA fields.

## 3. Graph construction logic

- Node types: Memory, Entity; edges: Mentions + Memory NEXT/PREV sequence.
- Bipartite Entity↔Memory; conversation-only inputs.
- QA / evidence / category / judge / ledger **excluded** from construction.
- A uses a parallel memory-only graph (no entities) for fair Dialog-embed baseline.

## 4. Recall / retrieval logic

- Query: question text → (B) LLM q-entity keys + embed; (A) embed only.
- Score: cosine on Memory embeddings; B fuses entity BM25 soft-match (+ optional ±1 sequence) with embedding.
- Top-25 dialog ids → context for short answer; also score recall_acc/hit @5/10/25/50 vs gold evidence dias.

## 5. Judge / metrics

- **Primary:** official-style **token-F1** @25 + **recall_acc** @k.
- No LLM-as-Judge / Mem0 J-score in this table.
- Paper Table 3 anchors cited only (DRAGON retriever ≠ TES).

## Paper Table 3 anchors (DRAGON + gpt-3.5; not same embedder)

- Dialog F1@25 / R@25: 41.0 / 76.7
- Observation best F1: 43.3
- Summary F1@10: 32.0

## Fair claim

- **A vs B** is the matched-stack comparison (same embedder + reader).
- Paper rows are cited only; retriever differs (DRAGON vs text-embedding-3-small).
- Doubao-era P1 F1 46.18 is **not** this stack’s headline.

## Constraint audit

PASS. Conversation-built graphs; answer via graph-retrieved dialogs; prompts
only for extract/retrieve/answer over graph evidence. Prompt scaffolds under
5000-char limit.

## Ablation figure (text)

```
F1@25
B full 0.3/0.7+seq     ████████████████████████ 46.48
B_noseq                ███████████████████████░ 46.20
A plain Dialog         ██████████████████████░░ 44.99
B_embed full-pool      ██████████████████████░░ 44.83
B_entity only          ████████████████░░░░░░░░ 40.78
paper Dialog (cite)    ████████████████████░░░░ 41.0
```
