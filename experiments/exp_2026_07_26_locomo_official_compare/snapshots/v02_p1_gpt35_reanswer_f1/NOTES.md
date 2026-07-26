# v02_p1_gpt35_reanswer_f1

## Command

```bash
source env_gpt.sh
export OPENAI_MODEL=gpt-3.5-turbo
export MODEL=gpt-3.5-turbo
python experiments/exp_2026_07_26_locomo_official_compare/run_p1_gpt35_reanswer_f1.py
```

## Result gate: **full_writeup**

- Overall F1%: 46.18
- ex-cat5 F1%: 51.19
- vs paper Dialog@25 (41.0): +5.18 pp
- vs paper Obs best (43.3): +2.88 pp
- same-evidence deepseek F1%: 43.73

## Constraint

PASS: frozen conversation-graph retrieval evidence; short QA prompt only.
Counts toward LoCoMo F1 comparison only if reader is gpt-3.5-turbo.

