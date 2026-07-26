# LoCoMo Table-3 style compare — Entity→Memory Dialog-family

**Status:** P0 + P1 complete. Gate = **full_writeup**.

## Parameters

| Item | Setting |
|---|---|
| Dataset | locomo10 all-10 |
| Package | `em_graph/` Entity→Memory |
| Extract | v4 SVO entity prompt |
| Fusion | 0.30 entity + 0.70 embedding |
| Retrieval unit | dialog turns (Dialog-family) |
| Evidence for F1 | frozen top-25 `context_ids` |
| Answer prompt | LoCoMo short `QA_PROMPT` / cat5 refusal + temporal suffix |
| P1 reader | **gpt-3.5-turbo** (paper-aligned) |
| Embedding (retrieval) | doubao-embedding-vision |
| n recall | 1982 (QA with evidence) |
| n F1 | 1986 |

## Overall vs paper Dialog-RAG

| k | Ours recall_acc | Ours hit | Paper Dialog R@k | ΔR (pp) | Paper Dialog F1 | Ours F1 (gpt-3.5) |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 61.08 | 67.05 | 56.7 | +4.38 | 38.8 | — |
| 10 | 72.13 | 78.25 | 66.2 | +5.93 | 39.7 | — |
| 25 | 82.14 | 87.94 | 76.7 | +5.44 | 41.0 | **46.18** |
| 50 | 88.17 | 92.73 | 82.7 | +5.47 | 40.5 | — |

Other paper anchors:

| Anchor | Value |
|---|---:|
| Observation-RAG best F1 (Table 3, @5) | 43.3 |
| Summary-RAG @10 F1 / R | 32.0 / 84.7 |
| gpt-4-turbo long-context F1 (Table 2) | 51.6 |
| Human F1 | 87.9 |

**Deltas @25 (gpt-3.5 reader):** vs Dialog F1 **+5.18 pp**; vs Obs best F1 **+2.88 pp**.

Same-evidence deepseek F1 was 43.73 (reader gap +2.45 pp when switching to gpt-3.5).

## F1@25 by category (gpt-3.5, frozen top25)

| cat | name | n | F1% |
|---:|---|---:|---:|
| 1 | Multi-hop | 282 | 38.32 |
| 2 | Temporal | 321 | 42.83 |
| 3 | Open-domain | 96 | 19.58 |
| 4 | Single-hop | 840 | 62.32 |
| 5 | Adversarial | 447 | 28.93 |
| all | Overall | 1986 | **46.18** |
| ex5 | excl. Adv | 1539 | 51.19 |

## Recall@25 by category (re-retrieve 0.3/0.7)

| cat | name | n | recall_acc | hit_rate |
|---:|---|---:|---:|---:|
| 1 | Multi-hop | 282 | 57.16 | 85.11 |
| 2 | Temporal | 321 | 90.50 | 92.83 |
| 3 | Open-domain | 92 | 47.92 | 60.87 |
| 4 | Single-hop | 841 | 90.49 | 91.68 |
| 5 | Adversarial | 446 | 77.35 | 78.03 |
| all | Overall | 1982 | **82.14** | **87.94** |

## Graph / protocol audit

- Graph built from conversation dialogs/captions/speakers/session anchors only (extract-v4).
- QA questions/answers, evidence annotations, category labels, judge outputs excluded from graph construction.
- Answers use graph-retrieved dialog evidence only.
- Prompts are short LoCoMo QA scaffolds over retrieved evidence (not oversized).
- Mem0 J-score is **out of scope** for this table.

## Snapshots

- `snapshots/v01_p0_multik_recall_sheet/`
- `snapshots/v02_p1_gpt35_reanswer_f1/`

## Interpretation

1. **Recall:** hard win vs paper Dialog-RAG at every reported k (~+4.4–5.9 pp recall_acc).
2. **F1:** with paper-aligned gpt-3.5 reader, Overall **46.18** beats Dialog@25 and Observation best; still below Table-2 gpt-4-turbo (51.6) and Human (87.9).
3. Weakest F1 categories remain Open-domain and Adversarial (though Adv improved a lot vs deepseek’s ~6).
4. **P3 Step1 oracle** (dataset obs/summary, text-embedding-3-small, gpt-3.5):
   Obs@25 F1 **32.69**, Summary@10 **30.21** — both far below Dialog **46.18**.
   Gate **stop_p3_main_spend** (no self-build). See `P3_STEP1_ORACLE_COMPARE.md`.
