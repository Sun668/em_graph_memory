# v58 — A@50 completed but failed the preregistered resource gate

Decision date: 2026-07-29 Asia/Shanghai. Source commit:
`c015b964643bdb51888aa984928b2739193def53`. Parameter SHA:
`d006213dc223afdb808dc5e22cdd50bf0e47dd280facf6c525d45e3cc8e619d7`.

## Outcome and exact command

The all-10 pure-Memory A@50 condition completed from the absent isolated
directory `outputs/locomo_formal/formal_all10_M4_A_top50_deb2ff2_qfrozen_run01`.
The exact command is the frozen `binding.canonical_argv` in `parameters.json`.
It used LoCoMo-10 SHA `047d8e…d74`, 10 conversations, 1,986 QA rows, and 446
Category-5 rows.

Both validators pass, as do 77/77 tests, 16/16 vendor hashes, official
aggregation, graph constraint, output isolation, and immutable query use.
Diagnostic metrics are F1 `42.0064%`, `recall_acc` `86.7148%`, local
Categories 1–4 F1 `52.1590%`, and local Categories 1–4 recall `89.4906%`.

However, answer input usage was 5,188,935 tokens, exceeding the frozen
3,500,000-token maximum. The condition therefore has `status=fail` and is
diagnostic only. Its metrics must not enter the paper matrix or be compared
inferentially with B@50.

## Behavior and graph audit

Relative to corrected A@25, the only intended behavior change was top-k
25→50. Dataset/order, conversation-only Memory construction, ten canonical
Memory indexes, immutable query vectors, signed-cosine ranking, frozen Reader
(`gpt-3.5-turbo`, system role, temperature 0, 32 tokens, batch 1), official
metric definitions, serialization, and aggregation were identical. The
larger context increased evidence and Reader input length; that downstream
token increase caused the resource-gate failure.

The Memory graph used only session anchors, dialog ids, speakers,
time-annotated dialog text, and captions. QA questions, answers, evidence,
categories, judge outputs, and predictions were excluded from construction.
Recall used graph Memory nodes. No Entity extraction, reranker, validator, or
answer-side non-data prompt change was active; scaffold use was `0/5000`.
No judge was used.

## Cache and reproducibility audit

No old cache or result was deleted, overwritten, rebuilt, or rewritten.
Graph files stayed `70`; Memory indexes stayed `30`; all ten A artifacts were
reused read-only. Query use was 1,986 hits, 0 misses, 0 live requests.
Retrieval took 4.8371 seconds. Answer generation made 1,986 requests, used
5,188,935 input and 16,976 output tokens, and took 2,100.3499 seconds.

Prediction SHA is `6a421498…8ee3e`, stats SHA `eeef8468…67c86`, and
independent-validation SHA `8081868a…e6be6a`. Provider revision, hardware,
and monetary price remain unknown.

## Decision

This snapshot preserves a meaningful failed formal run before any new
parameter decision. It supports no paper metric claim. The next valid action
is a newly named, newly preregistered A@50 rerun with an evidence-based token
ceiling and another absent output directory. The old v58 output and every
shared cache remain preserved.
