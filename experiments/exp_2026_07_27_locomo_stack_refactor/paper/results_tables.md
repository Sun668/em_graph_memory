# Results tables

Values are percentages. Bracketed ranges are 95% bootstrap intervals for the
B−A difference in percentage points. All conditions contain 1,986 QA rows
from ten conversations.

## Table 1. Primary matched comparison at top-k 25

| Condition | Retrieval | Overall F1 | `recall_acc` | Categories 1–4 subset F1 | Categories 1–4 subset recall |
|---|---|---:|---:|---:|---:|
| A | Dense semantic Memory retrieval | 42.0681 | 79.7468 | 51.2645 | 82.8099 |
| B_embed | Dense semantic retrieval over B’s Memory nodes | 42.0677 | 79.7468 | 51.2640 | 82.8099 |
| B | Entity–Memory fusion with sequence expansion | 42.5680 | 84.4842 | 51.9740 | 85.0232 |

B−A overall F1 was `+0.4998` points (paired-QA interval
`[−0.5745, 1.5514]`; conversation-cluster interval
`[−0.1773, 1.2711]`). B−A `recall_acc` was `+4.7374` points
(`[3.6504, 5.8425]`; `[3.5286, 6.0124]`; both two-sided
`p = 0.0002`). B_embed and A had zero ordered-context mismatches across all
1,986 QA rows.

## Table 2. Matched cutoff analysis

| top-k | A F1 | B F1 | B−A F1 | A `recall_acc` | B `recall_acc` | B−A recall | Paired-QA recall interval | Conversation-cluster recall interval |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 39.9053 | 39.8264 | −0.0790 | 59.3584 | 64.1667 | +4.8083 | [3.3450, 6.2808] | [2.8809, 6.6134] |
| 10 | 41.7607 | 42.1412 | +0.3805 | 68.9145 | 74.4847 | +5.5702 | [4.2928, 6.8624] | [4.2365, 6.7522] |
| 25 | 42.0681 | 42.5680 | +0.4998 | 79.7468 | 84.4842 | +4.7374 | [3.6504, 5.8425] | [3.5286, 6.0124] |
| 50 | 42.0782 | 41.7832 | −0.2950 | 86.7148 | 90.3306 | +3.6159 | [2.7754, 4.4735] | [2.4603, 4.6426] |

Every recall interval is above zero. Every matched F1 interval includes zero.

## Table 3. Component and input evidence at top-k 25

| Contrast (treatment minus control) | Overall F1 difference | `recall_acc` difference | Family-corrected conclusion |
|---|---:|---:|---|
| B − B_noseq | +0.5137 | +1.6728 | Recall supported; F1 not supported |
| B − B_gate_seq | +0.8014 | +4.7626 | Recall supported; F1 not supported |
| B_gate_seq − B_gate | −0.0609 | +0.4364 | Recall supported; F1 not supported |
| B − B_entity | +5.0780 | +17.4634 | F1 and recall supported |
| B_raw_text − B | +0.2407 | −0.2472 | Neither metric supported |
| B_raw_text − A_raw_text | +0.3508 | +4.9522 | Recall supported; F1 not supported |
| B − B_no_speaker | +0.2415 | +1.4822 | Recall supported; F1 not supported |

Component and input families used Holm correction by outcome and bootstrap
estimator. The speaker comparison used its separately preregistered matched
ablation.

## Table 4. Parameter sensitivity

| Family | Contrast | Overall F1 difference | `recall_acc` difference | Conclusion |
|---|---|---:|---:|---|
| Fusion | 0.10/0.90 − 0.30/0.70 | −0.3639 | −2.3062 | Recall lower after Holm; F1 not supported |
| Fusion | 0.50/0.50 − 0.30/0.70 | −0.3240 | −0.1562 | Neither metric supported |
| Sequence | 0.25 − 0.50 | see v67/v70 | see v67/v70 | Neither metric supported after Holm |
| Sequence | 1.00 − 0.50 | see v68/v70 | see v68/v70 | Neither metric supported after Holm |

The absence of a corrected difference is not an equivalence test. The allowed
sequence-scale statement is that no overall F1 or `recall_acc` contrast
survived correction over the tested range.

## Table 5. Primary-B cold and warm system cost

| Stage | Cold requests | Cold input/output tokens | Cold wall or per-QA latency | Warm requests | Warm wall or per-QA latency |
|---|---:|---:|---:|---:|---:|
| Conversation-Entity extraction | 5,873 | 3,731,393 / 425,637 | 9,792.76 s summed provider-call time | 0 | 0.00 s |
| Memory embedding index | 591 | 214,229 / 0 | 443.38 s | 0 | 1.29 s cache load |
| Question-Entity extraction | 1,974 | 1,214,259 / 104,272 | 2,970.83 s | 0 | 0.00 s |
| Retrieval, 1,986 QA | 0 | 0 / 0 | mean 1.5123 s; p95 2.6132 s | 0 | mean 0.004886 s; p95 0.006270 s |

The warm replay used the complete cold cache and made no new provider request
before answer generation. The cold-to-warm retrieval speedup was 309.48×. This
zero-request result applies to the same question set with complete graph,
index, query-vector, and question-Entity caches; unseen questions may require
new provider calls. The validated cache-independent answer trace contains
1,986 requests, 2,744,099 input tokens, and 16,269 output tokens and is attached
identically to both states rather than rerun. Including that trace, the cold
path uses 8,450,158 total tokens, or 4,254.9 tokens per question. The answer
stage accounts for 1,389.9 tokens per question. Stage wall times overlap and
must not be summed as end-to-end latency. Graphs occupy 21,689,931 bytes,
Memory indexes 29,946,660 bytes, and Entity/question caches 3,411,176 bytes.
At public prices accessed on 1 August 2026, the measured model and embedding
usage corresponds to an illustrative $4.67, or $0.00235 per question. This is
not a frozen experimental metric and excludes the separately built query-vector
artifact, storage, platform fees, and unrecorded external charges.
