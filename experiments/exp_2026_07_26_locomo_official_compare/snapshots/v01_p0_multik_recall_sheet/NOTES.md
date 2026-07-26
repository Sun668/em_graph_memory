# v01_p0_multik_recall_sheet

## Command

```bash
source env_ark.sh
python experiments/exp_2026_07_26_locomo_official_compare/run_p0_multik_recall_sheet.py
```

## Settings

- extract-v4, fusion 0.30/0.70, emb=doubao-embedding-vision
- retrieval unit: dialog turns
- F1 from existing deepseek top25 answers

## Mandatory graph constraint

PASS for retrieval sheet (conversation-built graphs; QA excluded).
F1 reader not paper-aligned yet → do not claim F1 SOTA until P1.

## Counts toward target?

Recall comparison: yes as diagnostic vs paper Dialog R@k.
F1 claim: **not yet** (await P1 gpt-3.5).

