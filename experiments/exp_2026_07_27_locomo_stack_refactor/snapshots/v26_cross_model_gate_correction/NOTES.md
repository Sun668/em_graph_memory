# v26 — correct the cross-model F1 gate and resume the experiment matrix

Decision date: 2026-07-28 Asia/Shanghai.
Base commit: `e608e86008352fc5a74706112a7dad0c61394117`.
Base tree: `f01cd7ad98f3a2e9d5021246208bd00cec9ac74e`.

This snapshot records a protocol correction requested by the user after
checking the final LoCoMo paper. It changes no prediction, metric, graph,
retriever, answer prompt, or frozen evaluator source.

## Evidence

The official LoCoMo PDF published in the upstream repository was checked
directly:

```text
https://raw.githubusercontent.com/snap-research/locomo/main/static/paper/locomo.pdf
SHA-256: a72c82117d01d8e304a24364a189afb91d25bf5e871b023f1e8172d6bdf64025
creation metadata: 2024-08-13
```

Page 7 separates two different QA settings:

- Table 2: `gpt-4-turbo`, 128K long-context, no RAG retrieval, overall F1
  `51.6`;
- Table 3: RAG-based `gpt-3.5-turbo` with DRAGON retrieval; Dialog at
  `top-k=25` has overall F1 `41.0` and Recall@25 `76.7`.

Formal M1-A/M1-B use a `gpt-3.5-turbo` Reader with retrieved top-25 contexts.
Consequently, the previous M1-B F1 floor of `49.6 = 51.6 - 2` compared
different Reader models and inference settings. It is not a valid matched
publication stop gate.

## Corrected interpretation

The immutable v25 metric result remains valid:

- M1-A: F1 `42.2642%`, Recall@25 `79.7468%`;
- M1-B: F1 `42.6772%`, Recall@25 `84.3415%`;
- descriptive B-minus-A: F1 `+0.4130` points, Recall@25 `+4.5947` points.

Only v25's go/no-go interpretation is superseded. M1-B did not fail a valid
same-model official-performance gate. The official `51.6` value may be cited
only as a cross-model long-context reference, not as an M1 terminal threshold.

The official Dialog `41.0`/`76.7` values are the relevant same-Reader-class
external references. They remain external rather than controlled comparisons
because O1 did not meet its exact local reproduction tolerance. A strict
method claim continues to rest first on matched B versus A, followed by the
planned local DRAGON-stack O2 diagnostic.

## User decision and execution policy

The user directed the experiment track to:

1. record this correction now;
2. complete the planned experiment matrix;
3. revisit the overall publication interpretation only after all experiments
   are complete.

Intermediate performance outcomes, including the primary significance report,
must therefore be recorded but are not early-stop conditions. The following
validity gates remain active and may pause execution until corrected:

- frozen official prompt/metric/dataset protocol;
- mandatory conversation-only graph construction and graph retrieval;
- isolated formal-output validation and exact source/config identity;
- prompt budget and reproducible snapshot lifecycle;
- A/B_embed per-QA ordered context-id exact equality.

O1 remains `o1_accepted=false` and official-table-only. No paper-ready or
official-SOTA claim is authorized before the final cross-result review.

Publication gate: `continue`, `paper_ready=false`.
Next action: run the predeclared 10,000-resample paired-QA and
conversation-cluster B-versus-A significance report, snapshot, commit, and
push it before launching structural ablations.
