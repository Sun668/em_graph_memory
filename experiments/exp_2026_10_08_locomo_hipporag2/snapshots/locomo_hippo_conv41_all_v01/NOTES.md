# locomo_hippo_conv41_all_v01

Frozen before API calls. Mode: full; user: conv-41; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed all 663 conversation passages and 193 QA. Every top-25 result has
25 unique original dialog IDs; OpenIE has one entity/triple record per
passage with no empty extraction lists. `result_summary.json` binds raw result
and index hashes, usage, graph counts, prompt lengths, and source identity.
Construction used only conversation time, speaker, text, and official caption;
QA, evidence, answers, category, judge data, summaries, observations, and
predictions were excluded. Query handling was retrieval-time graph traversal.
No answer/judge was run. Prompt scaffolds were 554/1,836/3,808 characters,
below the 5,000-character cap. This condition is one component of the pending
ten-conversation comparison.
