# Isolated first-Memory point-time Reader context

Public code release `v1.0.10` includes this isolated implementation and the
original formal comparison's source, settings, and small results under
`experiments/exp_2026_10_17_point_time_all10/`. This tag lets readers inspect
and rerun the current B method; the recorded F1 values were measured at the
historical source commits identified below. No answer generation was run as
part of packaging this public tag.

This branch starts at `main` commit `11e784c435aa6cfba0d7c02d4ba43ddcf31d2e0a` and ports only the point-time Reader-context treatment. It does not inherit the earlier exploratory branch or its chronological ordering, question-pair recall, entity-weight sweeps, answer resource guards, or alternate graph variants.

## Hypothesis and mechanism

For a question beginning with `when` or `how long`, replace supported relative-time wording in the **first ranked Memory's** Reader text using the Memory's conversation timestamp. The remaining 24 Reader lines, ordered Top25 context ids, graph, embeddings, retrieval scores, and evaluator are unchanged. The adapter validates conversation-derived normalizer annotations before using them; `last week` and `last weekend` stay verbatim. It also handles `last year`, `last summer`, and `two days ago` from the same timestamp. No model call is added.

The graph uses only conversation sessions, dialog ids, speakers, dialog text, session timestamps, and official image captions. Memory nodes connect to Entity nodes through MENTIONS, and neighboring Memories through NEXT/PREV. Entity extraction uses `gpt-3.5-turbo` on conversation text, with deduplication and cache logic in the active `code/em_graph/build/` package. No QA answer, evidence label, category, judge output, or previous prediction enters construction. At query time, question-derived Entity keys and a frozen query embedding rank graph Memories; the adapter receives the resulting `QARecall` context and ids. The answer model reads that graph evidence through the frozen LoCoMo evaluator.

## Settings and status

The prior all-ten paired experiment is an existing, validated result, recorded with its original source provenance in `result.json`. Moving the treatment to this branch does not invalidate that result or itself require another full F1 run. It ran on the old exploration branch, not on this new commit. Its dataset was `data/locomo10.json` (SHA-256 `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`), ten conversations, 1,986 QA, 1,540 Category 1–4 QA, dataset order, no category filter. It used B at Top25: Entity weight 0.30, semantic weight 0.70, sequence scale 0.50, Entity relative threshold 0.50, Entity Top20 per key, who-only dampening 0.25, degree discount enabled, signed semantic scores, relevance order, and no Reader annotations before this treatment. Query vectors used `text-embedding-3-small`; extraction and answer generation used `gpt-3.5-turbo`. The frozen answer path used a system message, temperature 0, max 32 output tokens, batch size 1. No judge model or judge rubric applied; Categories 1–4 subset F1 is the repository-defined mean of official per-QA F1, not an official LoCoMo aggregate. The official evidence measure is `recall_acc`.

The original runs were `pt_all10_B_v02` (raw) and `pt_all10_T_v03` (point-time), with distinct empty output directories, the same query artifact SHA-256 `bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f`, and zero live query embeddings. The original exact commands and complete parameter snapshots remain at Git commits `f455bbac23d665ec35c9ecc146e5ae25c7a8a9e8` and `d2e678cc27329c79cf254ece953035a28167a760` in `experiments/exp_2026_10_17_point_time_all10/snapshots/`. Those historical files were deliberately not carried into this branch.

A fresh formal rerun is optional. It is needed only for a score specifically measured at this commit or if a later parity audit finds a material behavioral difference. Such a run would use the formal runner with `--scope all10 --variant B --top-k 25 --reader-context-mode raw` and then `point_time_first`, each with a fresh unique `--run-id`, a separate empty condition directory, and the same complete read-only query artifact. Source the authorized `env_gpt.sh` before launch; do not commit credentials. The formal runner writes the exact resolved command and configuration into each condition output. Run the repository's formal preflight and validation gates for each new run. Attribute existing metrics to their original source commits.

## Local validation and graph audit

`python3 -m unittest discover -s experiments/exp_2026_10_17_point_time_first_memory -p 'test_*.py' -v` checks first-Memory-only rewriting and ordered-id preservation without API calls. `python3 -m unittest discover -s experiments/exp_2026_07_27_locomo_stack_refactor -p 'test_formal_graph.py' -v` checks runner config, audit, and protocol helpers. No metric-bearing run was executed on this isolated branch. Graph constraint: pass by source inspection; graph construction remains conversation-only, QA-derived fields stay outside graph construction, and answer recall continues through graph retrieval. Prompt scaffold: unchanged and bounded by the existing formal runner audit. No ineffective older exploration component is active in this branch.
