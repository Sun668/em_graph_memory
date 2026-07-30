# v79 primary-B cold/warm cost

Status: **incomplete; diagnostic-only**.

The replacement probe launched from clean commit `d231b80` after all frozen
preflights passed. It completed all ten cold conversation graphs and six of
ten Memory embedding indexes. The hosting execution session then disappeared
across an automatic goal continuation. No `cost_probe.py` process remained,
no Python traceback was captured, and neither the event manifest nor the cost
report existed.

This is an execution-host interruption, not evidence that the shared-cache
repair passed or failed at full scale: QA retrieval and question-cache use had
not started. The partial cache therefore cannot validate warm-cache retention.

## Audit

| Check | Evidence | State |
|---|---|---|
| Frozen parameters | SHA-256 `2961a515…bccb` | pass |
| Source identity | runner SHA-256 `e3bc1f82…a6bc`; commit `d231b80` | pass |
| Output isolation | only new `primary_b_v79_cache` was written | pass |
| Cold graph construction | 10/10 graph files | pass |
| Cold Memory indexes | 6/10 index files | fail/incomplete |
| Cold QA retrieval | not reached | incomplete |
| Shared question-cache retention | not exercised at full scale | unknown |
| Warm pass | not reached | incomplete |
| Event manifest/report | both absent | fail/incomplete |
| Paper eligibility | no complete cost result | fail |

The partial cache set SHA-256 is `13e8cf78…da26` and its size at freeze is
58,524 KiB. It remains quarantined at
`outputs/locomo_cost/primary_b_v79_cache`; it must not be resumed or deleted.

Reusable evidence: the frozen design, clean source identity, successful
preflights, and confirmation that the repaired runner can complete cold graph
construction and begin isolated index construction. Invalidated/missing
evidence: all cold/warm stage totals, request/token totals, disk totals,
retrieval latency, shared-cache retention at all10 scale, and every cost claim.

Rerun scope: the entire cold and warm cost probe from a new run id and a new
absent cache/output set. Use a detached process with an explicit log and exit
status artifact so an application continuation cannot terminate or orphan the
measurement.

Maximum defensible claim: v79 made partial isolated progress but produced no
cost result.
