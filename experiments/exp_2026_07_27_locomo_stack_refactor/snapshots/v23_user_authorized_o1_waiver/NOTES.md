# v23 — user-authorized O1 waiver

Base commit: `795a86c08a3d4a3993dab6d5eadd6edd6a2f8b1b`.
Exact plan and notes are committed with this snapshot.

## Decision

On 2026-07-27, after reviewing why v22 stopped, the user explicitly instructed:

> 继续实验，只要后续的实验证明我们更优就先忽略这条约束

This waives only the O1 Recall@25 ±1 exact-reproduction stop for the already
recorded v22 result. It does not change the result:

- local dependency-matched O1 Recall@25: `78.113293%`;
- official Table 3 Dialog Recall@25: `76.7%`;
- absolute difference: `1.413293` points;
- O1 accepted: false.

The official table is now external-reference-only. No manuscript may describe
v22 as an exact reproduction or a controlled official-baseline comparison.
O2-B, if run, is a matched local DRAGON-stack diagnostic.

## Gates that remain active

Formal all-10 M1 is now the next stage. Before any secondary experiment:

1. M1-A and M1-B must individually pass the formal validator, mandatory graph
   audit, exact sample/QA/context checks, prompt budget, clean-source and
   isolated-output gates.
2. M1-B must have overall F1 at least `49.6` and Recall@25 at least `75.7`.
3. B versus A must support the paper's core claim under the predeclared
   paired-QA and conversation-cluster bootstrap analyses.
4. A/B_embed must later pass exact per-QA ordered context-id equality.

Any failure above remains a terminal condition. No parameter is changed by
this waiver: primary top-k is 25, B weights are entity 0.3 / semantic 0.7,
sequence scale 0.5, entity threshold 0.5, entity top-k 20,
who-only dampening 0.25, and degree discount enabled.

No model call, graph build, prediction, metric, or source-code change occurred
in this decision snapshot. `code/locomo_eval/` remains unchanged.

Publication gate: `continue`, `paper_ready=false`. The next action is formal
all-10 M1-A, followed by its snapshot and commit before M1-B.
