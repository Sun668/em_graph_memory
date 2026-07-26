# P3 Step1 — Oracle Obs / Summary (dataset fields)

**Label:** `oracle_dataset_fields=true` — not a system claim.
Embed: `text-embedding-3-small` · Reader: `gpt-3.5-turbo` · Dialog P1 F1: **46.18**
Gate: **stop_p3_main_spend**

| Variant | k | F1% | ex-cat5 F1% | vs Dialog P1 (pp) | beats Dialog? |
|---|---:|---:|---:|---:|---|
| obs_oracle | 5 | 31.43 | 38.24 | -14.75 | False |
| obs_oracle | 25 | 32.69 | 38.99 | -13.49 | False |
| summary_oracle | 10 | 30.21 | 34.03 | -15.97 | False |

Paper anchors (gpt-3.5 + DRAGON): Obs best F1 43.3 (@5); Summary @10 F1 32.0; Dialog @25 F1 41.0.

## Decision rule

- If best oracle Obs F1 > Dialog 46.18 → consider self-build Obs.
- Else → stop major P3 spend; Dialog remains preferred memory form.

