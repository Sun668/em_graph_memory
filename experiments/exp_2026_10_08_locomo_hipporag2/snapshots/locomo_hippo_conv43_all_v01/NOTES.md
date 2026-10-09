# locomo_hippo_conv43_all_v01

Frozen before API calls. Mode: full; user: conv-43; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed all 680 conversation turns and 242 QA, with 25 unique original IDs
per result. OpenIE recorded every passage; 21 entity lists were empty and no
triple lists were empty. `result_summary.json` binds the raw result/index
hashes, complete model usage, graph counts, prompt lengths and identity.
Graph construction used conversation time, speaker, text and caption only;
questions were loaded after indexing, while answer/evidence/category/judge,
summary, observation and previous-prediction inputs were excluded. Retrieval
used HippoRAG graph evidence, with no answer or judge stage. Prompt scaffolds
were 554/1,836/3,808 characters, all below 5,000. This condition alone is
not a full-dataset performance result.
