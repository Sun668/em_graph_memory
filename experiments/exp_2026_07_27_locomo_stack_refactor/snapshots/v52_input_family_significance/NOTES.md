# v52 — raw-text input-family Holm significance

Decision date: 2026-07-28 Asia/Shanghai. Locked source commit/tree:
`fff582e11b8ff80b8589840c079d5cc85b7ced7b` /
`aec8bf137ac0322a934e9e0cde8e0176dd3a3706`.

The locked v51 tool generated
`outputs/locomo_analysis/input_family_fff582e_seed20260727.json` from three
independently validated formal inputs: corrected B, A_raw_text, and
B_raw_text. All contain 10 conversations, 1,986 paired QA rows, and the same
dataset, top-k 25, embedding model, Reader protocol, and official metric
protocol.

Exact command:

```bash
.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/input_family_report.py \
  --b-dir outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01 \
  --a-raw-text-dir outputs/locomo_formal/formal_all10_M3_A_raw_text_top25_57a5f28_qfrozen_run01 \
  --b-raw-text-dir outputs/locomo_formal/formal_all10_M3_B_raw_text_top25_4965acd_qfrozen_run01 \
  --data-file data/locomo10.json --resamples 10000 --seed 20260727 \
  --output outputs/locomo_analysis/input_family_fff582e_seed20260727.json
```

The family contains two predeclared hypotheses: B_raw_text minus B for time
annotation inside complete B, and B_raw_text minus A_raw_text for B over A
under matched raw text. Holm correction is applied across these two
hypotheses separately within official overall F1 and Recall@25 and separately
for paired-QA and whole-conversation cluster bootstrap.

For time annotation inside B, F1 changes by +0.2407 points and recall by
-0.2472 points. Neither outcome is significant before or after Holm. Thus the
data do not establish that deterministic relative-time annotation changes
complete B's aggregate F1 or recall.

Under matched raw text, B exceeds A by +0.3508 F1 points and +4.9522
Recall@25 points. F1 is not significant. Recall remains significant after
Holm for both estimators: paired-QA and conversation-cluster raw p=`0.0002`,
Holm-adjusted p=`0.0004`; both 95% intervals are strictly above zero.

The report SHA-256 is
`7e7fa9a5a9deb07e238a8e7df020f33da6f9152368d130b14d2c069a9438f630`;
fingerprint
`73d87f690e845cec8534978d8eddb2165477640adf61115e7590e9c86682257c`.
An independent second generation is byte-identical with the same SHA.

The tool reads immutable formal artifacts and does not recalculate official
metrics. No graph, embedding index, extraction cache, query artifact, Reader
output, or old result was modified or deleted. Mandatory graph compliance is
inherited from and revalidated for all three formal conditions.

Publication gate: `continue`, `paper_ready=false`. This supports the
family-wise claim that B improves retrieval recall over A under raw-text
input, but it does not support an F1 improvement or a time-annotation effect.
Commit/push v52 before preregistering B_no_speaker.
