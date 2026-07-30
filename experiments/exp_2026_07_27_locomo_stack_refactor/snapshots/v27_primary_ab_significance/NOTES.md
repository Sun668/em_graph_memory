# v27 — primary M1-B versus M1-A significance

Decision date: 2026-07-28 Asia/Shanghai.
Analysis source commit: `453c591cfe9bb779d7f26af45a00a1546dec1c48`.
Analysis source tree: `4ce53b5ef13ace48178cf117870871b153903256`.

This snapshot records the predeclared primary comparison after the immutable
formal all-10 M1-A and M1-B runs. It changes no prediction, metric, graph,
retriever, prompt, or frozen evaluator source.

## Exact analysis command

```text
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/significance_report.py compare --a-dir outputs/locomo_formal/formal_all10_M1_A_top25_3e3a33b_run01 --b-dir outputs/locomo_formal/formal_all10_M1_B_top25_484ccf0_run01 --data-file data/locomo10.json --resamples 10000 --seed 20260727 --output outputs/locomo_analysis/m1_b_vs_a_significance_10000_seed20260727.json
```

No external model call was made for this analysis. The analysis runner SHA-256
is `f69c2c72aea62dc2364aae05ccd8e58a9eded9d823c81c1787e698c988765a24`.
The complete generated report remains under `outputs/` and has SHA-256
`5fff462148f24199607a5333e83d72485f6d5671be9cbb2e533bd70cb51f597c`.

## Conditions and parameters

Both conditions use all 10 LoCoMo conversations, 1,986 QA rows, the frozen
official answer protocol, top-k 25, temperature 0, max answer tokens 32,
batch size 1, and `gpt-3.5-turbo` as Reader. Both use
`text-embedding-3-small` Memory embeddings over the same normalized,
caption-inclusive, time-aware Memory search text.

- M1-A source `3e3a33b`: pure Memory graph, no Entity extraction,
  signed-cosine full-pool dense retrieval, semantic weight 1.0, Entity weight
  0.0, and no sequence expansion.
- M1-B source `484ccf0`: conversation/query Entity extraction by
  `gpt-3.5-turbo`, Entity/semantic fusion 0.3/0.7, Entity relevance threshold
  0.5, up to 20 Entity candidates per key, who-only dampening 0.25, degree
  discount enabled, chronological sequence expansion enabled at secondary
  scale 0.5.

The category-5 option ordering remains the unchanged upstream unseeded
`random.random()` behavior. The bootstrap analysis itself uses seed
`20260727` and 10,000 resamples for both paired-QA and whole-conversation
cluster estimators.

## Graph extraction and construction

M1-A contains 5,882 Memory nodes, no Entity nodes, and 11,744 chronological
NEXT/PREV edges. M1-B contains 5,882 Memory nodes, 12,808 conversation-derived
Entity nodes, 36,227 Entity–Memory edges, and 11,744 chronological edges.
Memory units come from dialog text, speakers, session/time annotations, dialog
ids, and image captions. B's Entity extractor uses only those conversation
fields; it normalizes and deduplicates the extracted Entity keys under the
committed v4 schema.

No QA question, answer, evidence annotation, category label, judge result,
previous prediction, or question-driven ledger is used to build either graph.
Questions are used only at retrieval time. Answer recall is over Memory nodes
and graph edges, and the frozen Reader sees only the ordered retrieved graph
evidence plus the current question.

## Metric and statistical logic

The report consumes the immutable official per-row serialized token-F1 and
`recall_acc`; it does not recalculate either metric. For mean, bootstrap,
category, and per-conversation recall, a row contributes its serialized recall
only when evidence is non-empty and contributes zero otherwise. All QA rows
remain in the denominator. Both A and B have four empty-evidence Category-3
rows; the analysis aggregation exactly matches each formal `stats.json`.

The primary difference direction is B minus A. No multiple-comparison
correction is applied to this single predeclared comparison. Category-level
results are descriptive unless separately corrected; Categories 1–4 is
explicitly local and non-official. No LLM-as-Judge is used in LoCoMo scoring.

## Results

Overall Recall@25 increases from `79.7468%` to `84.3415%`, a difference of
`+4.5947` points. Its paired-QA 95% CI is `[+3.5241, +5.7012]` points and its
conversation-cluster 95% CI is `[+3.2593, +5.9514]` points; both two-sided
bootstrap p-values are `0.0002`.

Overall F1 increases from `42.2642%` to `42.6772%`, a difference of `+0.4130`
points. Its paired-QA 95% CI is `[-0.6824, +1.4990]` points with `p=0.4524`;
its conversation-cluster 95% CI is `[-0.3519, +1.2114]` points with
`p=0.3008`. The overall F1 gain is not statistically significant.

The local Categories 1–4 subset has F1 `+1.2469` points with paired CI
`[+0.0552, +2.4543]`, `p=0.0384`, and cluster CI
`[+0.5391, +2.0351]`, `p=0.0002`. Its Recall@25 gain is `+2.0618` points;
both C1–4 recall intervals exclude zero. Category 5 gains `+13.3408` recall
points but loses `2.4664` F1 points; the Category-5 F1 cluster interval is
negative, while its paired interval ends at zero.

Recall improves in every conversation. F1 improves in six conversations and
decreases in four, consistent with the overall interval crossing zero.

## Compliance and decision

- Mandatory graph constraint: pass.
- Frozen official evaluator/prompt/dataset: unchanged.
- Formal input validation and official recall aggregation parity: pass for A
  and B.
- Prompt budget: inherited verified scaffolds, A `0/5000` and B
  `2410/5000`; no prompt was introduced by the analysis.
- Oversized, ineffective, or harmful prompt components: none introduced; not
  applicable to this post-hoc analysis.
- Snapshot lifecycle: pass; the full generated report is retained under
  `outputs/`, with its hash and compact committed result recorded here.
- Regression verification: 62/62 experiment tests pass, including the
  16-file frozen vendor manifest check and the three exact ordered-context
  dense-control cases.

The experiment supports a statistically significant retrieval improvement but
not a statistically significant overall final-answer F1 improvement. Per the
user's 2026-07-28 instruction, this is not an early-stop condition. Continue
to structural ablations and defer the paper claim until the full matrix is
complete.

Publication gate: `continue`, `paper_ready=false`.
