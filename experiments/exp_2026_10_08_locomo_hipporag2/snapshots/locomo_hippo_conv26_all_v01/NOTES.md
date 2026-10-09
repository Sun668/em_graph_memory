# locomo_hippo_conv26_all_v01

Frozen before API calls. Mode: full; user: conv-26; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed with the frozen source, command and parameters in this snapshot.
`result_summary.json` binds the raw result SHA-256 at
`outputs/locomo_hipporag2/conditions/locomo_hippo_conv26_all_v01/`.
All 419 conversation turns and 199 QA completed, each with 25 unique original
dialog IDs. The graph has 1,067 nodes and 2,700 edges; the exact OpenIE
coverage and empty-extraction counts are in the summary. There were 1,037
live chat calls, 511,634 input/43,032 output chat tokens, and 139 embedding
requests with 47,042 input tokens. The non-data NER/triple/fact-filter prompt
scaffolds were 554/1,836/3,808 characters, all below 5,000.

The graph used only conversation session time, speakers, text and official
captions; QA, gold evidence, category labels, judge data, predictions,
summaries and observations were excluded. Upstream graph retrieval produced
the evidence IDs. No answer generation or judge ran. This condition passes
the graph and prompt audits but supports a comparative claim only after all
ten conversations and the paired audit complete.
