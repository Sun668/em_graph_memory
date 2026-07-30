# v90 — primary-B staged cold/warm cost lock

v90 is the clean rerun after the v86 batch-level query-hit assertion failure
and the v89 measurement repair. It retains the complete v86 scientific
configuration and starts from four absent v90-specific output paths. No v86
graph, index, entity, question, checkpoint, event, or report artifact may be
loaded or copied.

The only protocol change is measurement validation. Each retrieval batch must
read the immutable query artifact at least once per QA, while the complete
cold and warm states must each reproduce the matched formal B@25 count of
exactly 1,997 read-only hits over 1,986 QA, with zero misses and zero live
query embeddings. The formal query-usage input is separately SHA-bound.

The run remains cost-only. It builds ten conversation-only Entity–Memory
graphs, ten Memory indexes, 44 cold retrieval batches, and then replays the
same 64 operations warm. It does not generate answers, judge predictions, F1,
or `recall_acc`; the matched answer-stage provider telemetry is reused and
explicitly disclosed.

Launch is permitted only after this parameter snapshot is committed and
pushed, its SHA-256 is passed to every command, all four v90 targets are still
absent, and the live chat/embedding telemetry preflights pass.
