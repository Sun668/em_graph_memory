# P0 Table-3 style compare (Entity→Memory Dialog-family)

Retrieval: extract-v4, fusion **0.30E+0.70Embed**, dialog turns.
F1@25 from existing **deepseek-v4-flash** answers (not paper gpt-3.5).
Recall@k from offline re-retrieve top-50 (same fusion).

## Ours vs paper Dialog-RAG (Overall)

| k | Ours recall_acc | Ours hit | Paper Dialog R@k | ΔR (pp) | Paper Dialog F1 | Ours F1 (deepseek) |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 61.08 | 67.05 | 56.7 | +4.38 | 38.8 | — |
| 10 | 72.13 | 78.25 | 66.2 | +5.93 | 39.7 | — |
| 25 | 82.14 | 87.94 | 76.7 | +5.44 | 41.0 | 43.73 |
| 50 | 88.17 | 92.73 | 82.7 | +5.47 | 40.5 | — |

Paper Observation best F1: **43.3** (@5).
Paper Summary @10: F1 32.0, R 84.7.

## Ours recall_acc by category (re-retrieve)

### k=5

| cat | name | n | recall_acc | hit_rate |
|---:|---|---:|---:|---:|
| all | Overall | 1982 | 61.08 | 67.05 |
| 1 | Multi-hop | 282 | 31.59 | 61.70 |
| 2 | Temporal | 321 | 75.93 | 78.50 |
| 3 | Open-domain | 92 | 31.25 | 39.13 |
| 4 | Single-hop | 841 | 70.33 | 71.94 |
| 5 | Adversarial | 446 | 57.74 | 58.74 |

### k=10

| cat | name | n | recall_acc | hit_rate |
|---:|---|---:|---:|---:|
| all | Overall | 1982 | 72.13 | 78.25 |
| 1 | Multi-hop | 282 | 43.28 | 73.40 |
| 2 | Temporal | 321 | 83.49 | 86.29 |
| 3 | Open-domain | 92 | 37.65 | 48.91 |
| 4 | Single-hop | 841 | 82.28 | 83.71 |
| 5 | Adversarial | 446 | 70.18 | 71.30 |

### k=25

| cat | name | n | recall_acc | hit_rate |
|---:|---|---:|---:|---:|
| all | Overall | 1982 | 82.14 | 87.94 |
| 1 | Multi-hop | 282 | 58.82 | 88.30 |
| 2 | Temporal | 321 | 90.19 | 92.21 |
| 3 | Open-domain | 92 | 51.13 | 61.96 |
| 4 | Single-hop | 841 | 90.13 | 91.32 |
| 5 | Adversarial | 446 | 82.40 | 83.63 |

### k=50

| cat | name | n | recall_acc | hit_rate |
|---:|---|---:|---:|---:|
| all | Overall | 1982 | 88.17 | 92.73 |
| 1 | Multi-hop | 282 | 70.99 | 93.62 |
| 2 | Temporal | 321 | 93.98 | 95.64 |
| 3 | Open-domain | 92 | 58.74 | 69.57 |
| 4 | Single-hop | 841 | 94.37 | 95.36 |
| 5 | Adversarial | 446 | 89.24 | 89.91 |

## F1@25 by category (deepseek, frozen answers)

| cat | name | n | F1% |
|---:|---|---:|---:|
| 1 | Multi-hop | 282 | 40.14 |
| 2 | Temporal | 321 | 50.89 |
| 3 | Open-domain | 92 | 24.55 |
| 4 | Single-hop | 840 | 64.16 |
| 5 | Adversarial | 447 | 6.40 |
| all | Overall | 1982 | 43.73 |

## Constraint audit

- Graph: conversation-only extract-v4 EM graphs.
- QA/judge/evidence annotations excluded from graph construction.
- Answer F1 uses graph-retrieved dialog evidence (top25).
- Reader **not** yet aligned to paper gpt-3.5 (see P1).

