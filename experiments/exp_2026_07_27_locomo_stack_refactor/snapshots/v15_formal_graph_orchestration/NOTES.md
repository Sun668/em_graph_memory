# v15 — formal graph orchestration

Source-only milestone based on commit
`cc1a5680fa6e25ae6347caf1acaaa735dc9df7e6`.

- Runner: `formal_graph.py`
- SHA-256:
  `d960ea2b8570f83ddf72dc08a4e9f89b1d3c568125c2e9ea2b62884ea92d478c`
- Tests: `test_formal_graph.py`
- SHA-256:
  `9adbb5b9ff6bfef5fb21e263d0ac81273fda57ffd8c1a6af1e5851312a68b452`
- Exact source is committed with this snapshot.

The runner requires a clean committed worktree, pinned dataset, explicit
all-10/preflight scope, absent condition directory, and identity-matched
graph/index caches. It records the exact command, source, models, retrieval
parameters, graph profile, answer protocol, cache hashes, and condition
fingerprint. It writes graph/prompt audits, evaluates one conversation at a
time without resume/overwrite, produces frozen official stats, and invokes
the external validator.

Graph construction inputs are session date-time, dialog id, speaker, dialog
text, and optional caption only. QA question entities exist only at recall
time in separate caches. QA answers, evidence, categories, judge output, prior
predictions, and question-ledger artifacts are excluded. Answer recall uses
the conversation-built graph. Prompt scaffold is 0 for A or 2410 for entity
variants, within the 5000 limit.

Verification: 3 focused / 46 combined tests passed; `code/locomo_eval/`
remained clean and vendor manifest passed 16/16. No API call or metric result.

Publication decision: `continue_tooling_only`. No blocker was found in this
source step, but it does not make the paper ready. Subsequent work must stop
on the fixed protocol, official-performance, significance, graph/formal, or
dense-control failures in `PUBLICATION_PLAN.md`.
