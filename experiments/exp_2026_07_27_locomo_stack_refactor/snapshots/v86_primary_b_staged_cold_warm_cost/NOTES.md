# v86 preflight failure: formal cost run not started

## Outcome

The v86 primary-B cold/warm cost condition was parameter-locked but was not
initialized. Both direct and configured-proxy live API checks failed before a
provider response with usage metadata was returned. The four v86 output
targets remained absent, so no graph, Memory index, retrieval batch, cost
event, answer, or metric was produced.

This snapshot is a reproducible not-started diagnostic. It supplies no cost or
paper evidence.

## Frozen scientific and measurement identity

The complete intended settings are in `parameters.json` (SHA-256
`78ab5dd2b5c311668799ff7f13ce16111099218171ddc706ee162d39d508a104`).
The intended run used all ten `data/locomo10.json` conversations and all 1,986
ordered QA rows; complete-B retrieval at top-k 25; Entity/semantic weights
`0.30/0.70`; sequence scale `0.5`; Entity threshold `0.5`; top-20 Entity
matches per key; who-only dampening `0.25`; and degree discount enabled.
Conversation and question Entity extraction were locked to
`gpt-3.5-turbo`, Memory embeddings to `text-embedding-3-small`, and query
vectors to the read-only formal artifact SHA
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.

Had it started, graph construction would have consumed only timestamps,
dialog ids, speakers, dialog text, and official captions. QA questions,
answers, evidence, categories, judge outputs, and previous predictions were
excluded from graph construction. No graph construction occurred in this
preflight failure.

## Checks and observed failure

The bounded chat check sent only `Reply exactly OK.` with temperature `0`,
four requested output tokens, a 30-second timeout, and two attempts. It failed
with `openai.APIConnectionError` both with the `env_gpt.sh` proxy retained and
with lower-case `http_proxy`/`https_proxy` unset.

The bounded embedding check used one short connectivity string and also failed
with `openai.APIConnectionError` before provider usage was returned.

After activating the already-installed FlClash application, the configured
endpoint `127.0.0.1:7890` was confirmed listening. A no-credential HTTP-header
check reached the proxy and received `HTTP/1.1 200 Connection established`,
but TLS to `api.openai.com:443` then failed with
`LibreSSL SSL_connect: SSL_ERROR_SYSCALL`. This isolates the immediate blocker
to external connectivity beyond the local cost runner.

Representative commands, with secrets excluded:

```text
source ./env_gpt.sh
.venv/bin/python -c '<bounded run_chatgpt OK preflight>'

source ./env_gpt.sh
unset http_proxy https_proxy
.venv/bin/python -c '<bounded chat or embedding preflight>'

source ./env_gpt.sh
curl -I --max-time 20 https://api.openai.com/v1/models
```

## Artifact and cache audit

At the final check, all four exact targets were absent:

- `outputs/locomo_cost/primary_b_v86_checkpoint.json`
- `outputs/locomo_cost/primary_b_v86_cache`
- `outputs/locomo_cost/primary_b_v86_events.json`
- `outputs/locomo_cost/primary_b_v86_report.json`

The quarantined v77, v79, and v83 artifacts and all formal graph, index,
query-vector, answer, and metric artifacts were left untouched. Nothing was
deleted or overwritten.

## Decision

Do not initialize v86 while either provider interface fails its bounded live
check. Retry only after network/TLS recovery. Before the first paid operation,
require:

1. one chat response with nonzero provider-reported usage;
2. one embedding response with nonzero provider-reported usage;
3. exact agreement between embedding observer and native counters; and
4. re-verification that all four v86 targets remain absent.

Prompt budget was checked in the frozen parameters (`2,410 < 5,000`
characters), but no runtime prompt completed. There is no judge logic,
official metric, F1, or `recall_acc` in this cost-only preflight.
