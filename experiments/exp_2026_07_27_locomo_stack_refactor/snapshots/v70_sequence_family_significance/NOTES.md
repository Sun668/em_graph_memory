# v70 — valid sequence-family Holm inference

Decision date: 2026-07-29 Asia/Shanghai. Locked tooling source commit:
`020891c56fc6832600dca89bdbd5d06301cdd72a`.

The report compares complete B at scale `0.25` and `1.0` against primary
scale `0.5`, with 10,000 paired-QA and conversation-cluster bootstrap
resamples, seed `20260727`, and Holm correction separately by metric and
estimator.

All scientific identity fields other than sequence scale match exactly. The
report records ten complete graph/index identities and the immutable query
artifact SHA `bef99a…6f9f`. Dataset/order, graph profile, models, fusion,
gating, top-k, Reader, evaluator, and aggregation are identical.

Results:

- scale `0.25`: F1 `-0.0530` points, recall `-0.3821` points; no raw or
  adjusted test rejects;
- scale `1.0`: F1 `+0.5540` points, recall `+0.6767` points;
- the only raw rejection is scale-1.0 conversation-cluster F1
  (p=`0.0406`), which becomes p=`0.0812` after Holm and no longer rejects;
- every other adjusted p-value also exceeds `0.05`.

Therefore no overall F1 or `recall_acc` difference across the preregistered
0.25–1.0 sequence-scale range is statistically supported after family
correction. Scale `1.0` may be reported as the highest descriptive mean, not
as a significant optimum or improvement.

The report was regenerated independently and is byte-identical. SHA:
`1f0d5710…4543`; fingerprint `cc6e5d19…ef69`. It performs no metric
recalculation, API request, or cache/result mutation. Graphs remain 70 and
Memory indexes 30.

Publication gate remains `continue`, `paper_ready=false`: commit/push v70,
then complete O2 diagnostic, cost consolidation, final claim audit, and paper
materials.
