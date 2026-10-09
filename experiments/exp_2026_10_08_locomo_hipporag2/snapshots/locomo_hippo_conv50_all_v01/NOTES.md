# locomo_hippo_conv50_all_v01

Frozen before API calls. Mode: full; user: conv-50; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed all 568 original conversation turns and 204 QA, each with 25
unique original dialog IDs. OpenIE covered every passage; one entity list
was empty and no triple list was empty. `result_summary.json` binds result
and index hashes, usage, graph counts, prompt lengths and identities. Graph
construction used only conversation time, speaker, text and caption;
questions entered after indexing and QA answers/evidence/categories, judge
data, predictions, summaries and observations were excluded. Retrieval used
the upstream graph. No answer or judge ran. Prompt scaffolds were
554/1,836/3,808 characters, all under 5,000. This completes the ten
frozen HippoRAG conditions, pending paired audit.
