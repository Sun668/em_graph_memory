# v93 — primary-B staged cold/warm cost lock

v93 is the fresh rerun after the v90 connectivity interruption and the v92
provider-recovery repair. It preserves the complete B@25 scientific condition
and starts from four absent v93-only output paths. No graph, Memory index,
Entity cache, question cache, checkpoint event, or partial measurement from
v86 or v90 may be copied, loaded, or resumed.

The run builds ten full conversation-only Entity–Memory graphs, ten Memory
embedding indexes, and 44 retrieval batches over all 1,986 QA, then replays the
same 64 operations warm. “Ten graphs” means one graph for each of the ten
LoCoMo conversations, not ten repeated full-dataset extractions. The 44
retrieval batches are only transaction-sized partitions of the 1,986 ordered
questions; they are not 44 experimental conditions.

The v89 query-usage repair remains active: every batch requires at least one
immutable query-vector hit per QA, and each complete cold/warm state must
exactly reproduce the matched formal B@25 total of 1,997 hits with zero misses
and zero live query embeddings.

The v92 recovery policy permits six additional attempts only when the shared
chat client has exhausted its own retries. Recovery stays within the same QA,
process, and transaction. Successful-attempt latency is reported normally;
fully failed attempt time and inter-attempt waiting are excluded from that
distribution and disclosed separately. Nonmatching errors still fail closed.

This remains a cost-only measurement. It does not generate answers, run a
judge, calculate F1, or calculate `recall_acc`. The matched formal answer-stage
provider telemetry is reused and explicitly identified.

Launch is permitted only after this snapshot is committed and pushed, its
SHA-256 is supplied to every command, all four v93 targets remain absent, the
unauthenticated connectivity check succeeds, and the live chat/embedding
telemetry preflights pass.

`quarantine_manifest.json` freezes deterministic directory-manifest hashes for
all five prior cost-cache roots plus exact hashes for the three existing staged
checkpoints. The same method must reproduce every value after v93 before the
old-cache non-mutation gate passes.
