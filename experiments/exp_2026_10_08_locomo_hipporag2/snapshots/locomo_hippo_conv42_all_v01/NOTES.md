# locomo_hippo_conv42_all_v01

Frozen before API calls. Mode: full; user: conv-42; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed with 629/629 conversation passages and 260/260 retrieval questions;
all context lists contain 25 unique source IDs. `result_summary.json` records
the result/index hashes, source and parameter identity, usage, graph counts,
OpenIE coverage, and prompt lengths. OpenIE had 25 passages with empty entity
lists but none with empty triple lists; this is a measured extraction quality
limitation, not a missing passage. Graph construction used only session time,
speaker, text, and official captions. Questions entered after indexing;
answers, evidence, category labels, judge output, predictions, summaries and
observations were excluded. Upstream graph retrieval returned source IDs.
No answer or judge ran. Prompt scaffolds were 554/1,836/3,808 characters,
within the 5,000-character cap. The condition is reproducible but is not a
full-dataset comparison by itself.
