# locomo_hippo_conv30_all_v01

Frozen before API calls. Mode: full; user: conv-30; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed with the frozen source/command/parameters in this snapshot.
`result_summary.json` binds the raw output SHA-256 and audit counts under
`outputs/locomo_hipporag2/conditions/locomo_hippo_conv30_all_v01/`. All 369
original conversation turns and 105 questions completed; each question has
25 unique original dialog IDs. OpenIE returned 369 records (3 with empty
entity lists, zero with empty triple lists), and the graph has 900 nodes and
2,149 edges. The non-data NER/triple/fact-filter prompt scaffolds are
554/1,836/3,808 characters, all below 5,000. There were 843 chat attempts,
842 live calls, 1 cache hit, 0 errors, 372,438 chat input and 30,528 output
tokens, plus 109 embedding requests and 37,205 embedding input tokens.

The graph was constructed only from session time, speaker, utterance, and
official caption; questions were loaded after indexing. Answers, evidence,
categories, judge outputs, prior predictions, and summaries were excluded.
Answer recall used upstream graph retrieval. No answer model or judge ran.
This condition passes graph and prompt audits. It counts toward a comparison
only if all ten conversations complete and the paired full-dataset audit
passes; it alone does not establish a performance claim.
