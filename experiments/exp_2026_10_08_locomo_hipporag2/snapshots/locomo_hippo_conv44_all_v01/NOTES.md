# locomo_hippo_conv44_all_v01

Frozen before API calls. Mode: full; user: conv-44; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed: all 675 conversation turns and 158 questions, each with 25 unique
original source IDs. `result_summary.json` binds the raw result/index hashes,
usage, complete OpenIE passage coverage, graph counts, and prompt budget.
Eleven OpenIE entity lists were empty, while triple lists were present for
every passage. Graph construction used only conversation session time,
speaker, text, and official captions, excluding QA, gold evidence, category,
judge, predictions, summaries and observations. Questions were loaded only
after indexing. Retrieval traversed the HippoRAG graph. No answer or judge
stage ran. Prompt scaffolds were 554/1,836/3,808 characters, all below 5,000.
The condition is a valid component, pending the complete ten-conversation
comparison.
