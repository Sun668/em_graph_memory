# v94 — v93 graph/index progress and question authorization gate

## Valid progress

v93 has completed 20/128 staged transactions from its fresh isolated paths:
all ten cold conversation graphs and all ten cold Memory embedding indexes.
The checkpoint has no `in_progress` operation and is valid to continue with
`cold:retrieve:conv-26:0:50`.

The ten graphs contain all 5,882 expected Memory nodes. Conversation Entity
extraction made 5,873 provider requests and recorded 3,731,393 input plus
425,637 output tokens. Memory-index construction made 591 embedding requests
and recorded 214,229 input tokens. Ten graph files and ten index files exist.

## Authorization gate

The first cold retrieval transaction was rejected before process creation by
external-action review. Nothing was sent and the checkpoint/cache did not
change. The reviewer requires an explicit user authorization that LoCoMo QA
question text may be sent to the configured external model for question
Entity extraction.

Only the question string is required. QA answers, evidence annotations,
categories, judge outputs, and prior predictions remain excluded. Question
Entities are query-time retrieval features and are not graph-construction
inputs. Warm replay must use the resulting cache and make zero new provider
requests.

Changing B to full-pool retrieval would avoid question Entity calls but would
change the preregistered scientific condition and invalidate comparison with
the matched formal B@25 result, so it is not an acceptable workaround.

## Compliance

Graph construction used only session timestamps, dialog ids, speakers, dialog
text, and captions. It excluded every QA/judge/prediction field. The prompt
scaffold remains 2,410 characters, below the 5,000-character limit. No answer
generation, judging, F1, or `recall_acc` evaluation ran.

This intermediate result is reproducible but not paper-eligible because cold
and warm retrieval, complete query-use parity, and the final report remain
unfinished. The exact checkpoint and cache identities are frozen in
`parameters.json`.

## Authorization received

At 2026-07-30 08:07:35 +08:00, the user explicitly stated:
“批准发送问题文本用于检索实体抽取。” The exact scope and exclusions are
recorded in `authorization.json`. v93 may therefore continue from its clean
20/128 checkpoint without changing the preregistered B@25 condition.
