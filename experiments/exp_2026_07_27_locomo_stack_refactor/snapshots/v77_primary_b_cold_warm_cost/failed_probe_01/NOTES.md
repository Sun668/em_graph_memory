# Failed cost probe 01

Status: **invalid cost measurement; diagnostic evidence only**.

The frozen v77 command was launched from clean commit
`c2108ecea9ff1abfe297687f380b8b849e19e7ea` and wrote only to the new,
isolated cache root:

```text
outputs/locomo_cost/primary_b_v77_cache
```

It was interrupted with `SIGINT` / exit code `130` during the cold retrieval
pass, before either `primary_b_v77_events.json` or
`primary_b_v77_report.json` was created.

## Observed evidence

- All ten conversation graphs and ten Memory embedding indexes had completed.
- During question extraction, `question_entities.json` grew to 160 entries
  for the first conversation and then fell to 20 entries when the next
  conversation flushed. The same behavior was visible in
  `question_extraction_raw.json`.
- At interruption, both question-cache files contained 199 entries belonging
  to `conv-30`; entries from the preceding `conv-26` pass were absent.
- `cost_probe._measure_state()` called `_load_recall()` once per sample
  without supplying `question_cache` or `question_extractor`.
- `_load_recall()` therefore constructed one `QuestionEntityCache` per
  conversation, while every instance targeted the same
  `entities/question_entities.json` path.
- `QuestionEntityCache.flush()` wrote the instance-local whole-file mapping
  directly. It did not reload and merge another instance's additions.

These source observations prove a stale in-memory whole-file overwrite in the
cost-probe orchestration. Continuing would have caused the nominal warm pass
to repeat question-extraction requests and would not have measured a complete
warm cache.

## Audit

| Check | Evidence | State |
|---|---|---|
| Frozen parameters | `../parameters.json`, SHA-256 `207f7dbb…f34e` | pass |
| Source/run identity | clean commit `c2108ec`; runner SHA-256 `26b0a7c7…ebe2` | pass |
| Output isolation | only the absent v77 cost cache root was created | pass |
| Old formal/cache mutation | `outputs/em_graph` was never a write target | pass |
| Cold graph/index completion | 10 graphs and 10 indexes in isolated cache | pass |
| Shared question-cache integrity | per-conversation instances overwrote the same file | fail |
| Complete cold measurement | interrupted during retrieval | fail |
| Valid warm measurement | never started; predicted cache misses follow directly from missing keys | fail |
| Cost report | not created | fail |
| Paper eligibility | no valid result exists | fail |

## Reuse and rerun scope

The frozen design, existing primary-B warm answer telemetry, source inspection,
and this diagnostic remain reusable. The partial v77 cache is not reusable for
a formal cold/warm measurement. No metric or paper claim is supported by this
probe.

Before any source repair, this snapshot preserves the failure. The replacement
must use a new run id and a new absent cache/output path, inject one shared
question extractor and one shared `QuestionEntityCache` into every Recall
instance, test multi-conversation cache retention, and rerun both cold and warm
passes.

Maximum defensible claim: the first v77 probe exposed and localized an
orchestration-level shared-cache violation; it produced no cost result.
