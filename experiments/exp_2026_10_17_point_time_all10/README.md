# All-ten point-time Reader comparison — completed

Status: both fresh all-ten formal conditions independently validated; the
predeclared paired F1 gate passed. The pre-run design history is retained
below, followed by completed-condition and final-result records.

## Fixed hypothesis and scope

The committed point-time-only rule from
`experiments/exp_2026_10_17_point_time_only/run.py` improves answer F1 on
temporal questions by making a relative point time in the first retrieved
Memory explicit. Test all ten conversations and all 1,986 QA rows in the
original `data/locomo10.json` order. Conv26, Conv30 and Conv49 were used for
development/confirmation; the all-ten test is therefore an expanded paired
estimate, not an independent holdout.

Use two fresh, absent-at-start, condition-specific answer directories: B and
point-time treatment. Both must use the same validated conversation-only B
graphs, Memory indexes, complete read-only ordered query-vector artifact,
cached question Entity keys, Top25 IDs/order, frozen answer protocol and
frozen evaluator. The only treatment difference is the first Memory's
reader-facing text on questions beginning `when` or `how long`, when a
supported relative point-time phrase resolves against its conversation
timestamp. `last week` and `last weekend` remain verbatim. The other 24
Memories and every inactive row's context must be byte-identical to B. No
gold answer, evidence annotation or QA category may enter graph construction
or the treatment route.

The dataset SHA-256 is
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
The ordered query artifact SHA-256 is
`bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`.
Expected retrieval parameters are B: Entity weight 0.30, signed semantic
weight 0.70, relative Entity threshold 0.5, Entity top20 per key, Who-only
dampening 0.25, sequence scale 0.5, Top25. Resolve every remaining effective
default, cache identity, model version and exact command from the active
formal runner before freezing snapshots; this draft is not a substitute for
the required `parameters.json` files.

## Outcomes fixed before full answers

Primary: paired difference in Categories 1–4 subset F1 across all 1,540
eligible QA rows, using frozen official per-row F1 values. Report the mean,
per-conversation deltas, and a 95% conversation-cluster bootstrap interval
with 10,000 draws and seed 20261017. A positive full-slice mean and positive
cluster-interval lower bound are required for an all-ten improvement claim.
Report the routed-row difference separately, including wins/losses/ties and
each conversation's routed count. Report inactive-row answer differences as a
generation-noise check. Official overall/category F1 and `recall_acc` are
reported as separate outputs; the latter must have exact paired row parity
because the ordered Top25 IDs are unchanged. Category 5 is descriptive because
option order is unseeded. No local LLM-as-Judge is used.

Before generation, audit the immutable evaluator manifest, clean evaluator
tree, dataset/query SHA-256, 1,986/1,986 query-vector coverage, zero live
query requests, all-row B retrieval parity, first-line-only treatment, graph
constraint, prompt scaffold <=5,000 characters, empty output directories and
one resolved condition per directory. Use two committed frozen parameter
snapshots with distinct run IDs. Validate each completed condition
independently before comparing results. Do not promote partial or invalid
outputs.

Bound each condition to at most 4 hours, 3.5 million answer-input tokens,
50,000 answer-output tokens, one answer request at a time, and 2 GB of new
output storage. These are stop ceilings, not expected usage. The precise
provider price is unavailable and must be reported from observed token
usage and applicable billing data rather than guessed.

The approved `env_gpt.sh` supplies API configuration without saving secrets.
The formal runner now accepts `--reader-context-mode raw|point_time_first` at
the existing `QARecall` boundary. The treatment module copies the exact
Conv26 time-conversion rule; a 500-QA replay against Conv26/30/49 prepared
contexts matched every row. The unmodified Top25 pipeline was then replayed
over all 1,986 QA using the project Python 3.9.6 / NumPy 2.0.2 environment:
1,986/1,986 ordered saved-B ID lists and treatment ID lists matched, all
1,986 first-Memory-only checks passed, 99 contexts changed, 3,994 query
lookups hit with zero misses/live embedding requests. The compact audit is
`outputs/point_time_all10/preflight_run01.json`; exact source and audit copy
are frozen in `snapshots/v03_all10_preflight_pass/`. System Python 3.13.5 /
NumPy 2.3.4 gave different B ranking and is excluded from formal execution.

The formal runner also checks answer input/output token and wall-time stop
ceilings after every conversation. It stores the limits in the condition
fingerprint through `answer_protocol` and the observed counters in
`progress.json`. Exact commands, frozen parameter SHA-256 values and output
paths are frozen in the B v02 and T v03 parameter snapshots.
The 21 existing formal runner/validator `unittest` cases pass in the project
environment. The final source is copied in `snapshots/v05_frozen_formal_source/`.
The paired analysis method was fixed in `compare.py` and copied in
`snapshots/v06_analysis_frozen/` before either answer run. The v01 B launch
was blocked before execution because the hook received the main checkout as
`cwd` without the tool's worktree; see `snapshots/v07_v01_launch_guard_denial/`.
Both v01 snapshots remain untouched and have no output. The revised commands
began with a literal worktree `cd`. B used `pt_all10_B_v02`;
treatment ultimately used `pt_all10_T_v03` after the unused v02 snapshot
failed a post-freeze source-change guard. The run-ID and provenance checks
were frozen before treatment; the F1 estimator, seed and gates stayed fixed.


## B v02 formal control completed

The fresh B condition `pt_all10_B_v02` completed all 10 conversations
and 1,986 QA from `data/locomo10.json`, starting from an absent dedicated
output directory. Independent formal validation passed, including the frozen
LoCoMo evaluator, graph constraint and 2,410/5,000-character prompt scaffold.
The read-only ordered query artifact produced 1,997 hits, zero misses and
zero live query embedding calls. B Categories 1–4 subset F1 is 0.518458442
over 1,540 rows; this alone gives no treatment effect. Generation used
2,744,098 answer-input tokens, 16,243 answer-output tokens and 2,639.9
answer seconds, within all prespecified ceilings. The complete settings,
source, graph/recall/answer/judge logic, command and artifact hashes are
frozen in `snapshots/v09_b_v02_complete/`; bulky predictions remain under
`outputs/locomo_formal/pt_all10_B_v02/`. The paired result appears in the final-result section below.

Before treatment, the analysis source was frozen again in
`snapshots/v10_analysis_provenance_before_treatment/`: the required B
result commit changes full-tree Git identity, so the pair validator now
permits only result-note/snapshot/plan/analysis-file changes between
recorded commits while rejecting any executable or input change. The
paired F1 estimator, bootstrap, gates and other parity checks are unchanged.

The T v02 parameter snapshot was rejected by formal preflight before any
treatment output or model call because B evidence commits followed its
freeze. It remains an unused record. Treatment will use a new T v03
snapshot; the comparison run ID was updated before treatment generation
and frozen in `snapshots/v11_analysis_treatment_v03_id/`. No numeric
analysis method changed.


## T v03 formal treatment completed

The fresh `pt_all10_T_v03` condition completed 10 conversations/1,986 QA
from an absent dedicated output directory. Independent validation passed:
conversation-only graph construction and graph recall, 2,410/5,000-character
prompt scaffold, 1,997 read-only query-vector hits, zero misses/live calls.
Its Categories 1–4 subset F1 is 0.538285714 on 1,540 rows. The paired audit and conversation-cluster uncertainty are reported below.
Usage was 2,744,442 answer-input tokens, 16,250 output tokens and 2,383.1
answer seconds, below all ceilings. Source, parameters, exact command,
formal validation and artifact hashes are in
`snapshots/v12_t_v03_complete/`; large predictions remain under
`outputs/locomo_formal/pt_all10_T_v03/`.


## Final paired outcome and reproducibility

The independent B and treatment formal validators both passed on all
1,986 QA (10 conversations, 1,540 Categories 1–4 rows and 446 Category 5
rows). The same 1,986 ordered Top25 graph Memory ID lists and official
`recall_acc` values matched row for row. The conversation-built graph,
Memory indexes, query-vector artifact, answer model/protocol and frozen
evaluator were the same; only the first retrieved Memory's Reader-facing
relative point time was converted on 99 supported questions (98 in
Categories 1–4). Neither QA gold data nor annotations entered graph
construction. Graph/prompt audits passed, with a 2,410-character
non-data scaffold below the 5,000 limit.

The repository-defined Categories 1–4 subset F1 increased from
**0.518458442 to 0.538285714**, a paired gain of **+0.019827273**
(+1.98 percentage points). The prespecified 10,000-draw,
10-conversation cluster-bootstrap 95% interval is
**[+0.012374900,+0.027652484]**; all 10 conversation deltas are
positive, and the fixed claim gate passes. Routed Categories 1–4
questions gained +0.287602041 on average (58 wins, 11 losses, 29 ties);
inactive questions changed +0.001628988 on average. Category 2 gained
+0.094595, from 0.413754 to 0.508349. An independent recount and
NumPy bootstrap agreed. See `result.json` and
`snapshots/v13_all10_paired_result/`.

Both used cached `gpt-3.5-turbo` Entity extraction, the same
`text-embedding-3-small` ordered query vectors, Entity/semantic
weights 0.30/0.70, threshold 0.5, per-key top20, Who dampening 0.25,
degree discount, sequence scale 0.5 and Top25 relevance order.
Answer generation was the frozen `gpt-3.5-turbo` `system` prompt,
temperature 0, batch size 1 and 32 completion tokens; no local
LLM-as-Judge was used. Frozen official per-row F1 and evidence recall
were used; Categories 1–4 subset F1 is not an official LoCoMo metric.
No new model or embedding call was added. T used 344 more answer-input
tokens and 7 more output tokens than B over all 1,986 answers; no
price is asserted without billing data. Inactive contexts were
byte-identical in the preflight, yet fresh temperature-0 generations
changed 431 inactive answer strings; their F1 mean effect was small
and its separate bootstrap interval crossed zero. Conv26, Conv30
and Conv49 informed development, so all-ten is an expanded paired
test rather than a fully unseen holdout.

Exact secret-free formal commands (the API settings came from the
approved `env_gpt.sh`; no secret is recorded):

```sh
cd /Users/sun/.codex/worktrees/graph-evidence-localization/graph_memory && source /Users/sun/Documents/git/graph_memory/env_gpt.sh && RESEARCH_RUN_CLASS=formal RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_10_17_point_time_all10/snapshots/pt_all10_B_v02/parameters.json RESEARCH_CONDITION_DIR=outputs/locomo_formal/pt_all10_B_v02 /Users/sun/Documents/git/graph_memory/.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id pt_all10_B_v02 --scope all10 --variant B --top-k 25 --data-file data/locomo10.json --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir /Users/sun/Documents/git/graph_memory/outputs/em_graph --output-root outputs/locomo_formal --reader-context-mode raw --max-answer-input-tokens 3500000 --max-answer-output-tokens 50000 --max-answer-wall-seconds 14400
cd /Users/sun/.codex/worktrees/graph-evidence-localization/graph_memory && source /Users/sun/Documents/git/graph_memory/env_gpt.sh && RESEARCH_RUN_CLASS=formal RESEARCH_PARAMETER_SNAPSHOT=experiments/exp_2026_10_17_point_time_all10/snapshots/pt_all10_T_v03/parameters.json RESEARCH_CONDITION_DIR=outputs/locomo_formal/pt_all10_T_v03 /Users/sun/Documents/git/graph_memory/.venv/bin/python experiments/exp_2026_07_27_locomo_stack_refactor/formal_graph.py --run-id pt_all10_T_v03 --scope all10 --variant B --top-k 25 --data-file data/locomo10.json --extract-model gpt-3.5-turbo --embedding-model text-embedding-3-small --answer-model gpt-3.5-turbo --query-artifact outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz --cache-dir /Users/sun/Documents/git/graph_memory/outputs/em_graph --output-root outputs/locomo_formal --reader-context-mode point_time_first --max-answer-input-tokens 3500000 --max-answer-output-tokens 50000 --max-answer-wall-seconds 14400
```

The final paired analysis command was
`PYTHONDONTWRITEBYTECODE=1 /Users/sun/Documents/git/graph_memory/.venv/bin/python experiments/exp_2026_10_17_point_time_all10/compare.py`.
Its exact source and output are frozen in
`snapshots/v13_all10_paired_result/`. The two bulky answer outputs
remain isolated under `outputs/locomo_formal/pt_all10_B_v02/` and
`outputs/locomo_formal/pt_all10_T_v03/`, with hashes in the snapshot.
