# v77 primary-B cold/warm cost

Status: **invalid; diagnostic-only**.

The parameter inventory was frozen and committed before launch. The first
probe was then stopped during cold QA retrieval after it exposed a
multi-instance whole-file question-cache overwrite. No cost event manifest or
cost report was produced, so v77 does not support any runtime, request-count,
token, disk-cost, cold/warm, or paper-readiness claim.

The complete source observations, artifact identities, audit table, and rerun
scope are in `failed_probe_01/NOTES.md` and
`failed_probe_01/evidence.json`.

The failed cache remains quarantined at
`outputs/locomo_cost/primary_b_v77_cache`. It must not be resumed or used as a
cold-start input. Existing `outputs/em_graph` artifacts and formal result
directories were not write targets and were not deleted, overwritten, or
rebuilt.

Decision: preserve v77, repair the cost-runner orchestration under a new frozen
run id, and rerun from a different absent cache/output path.
