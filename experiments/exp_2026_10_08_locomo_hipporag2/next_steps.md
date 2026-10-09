# Next steps

The requested retrieval-only LoCoMo comparison is complete. For a paper
claim, report it as an **adapted** external graph baseline with the pinned
upstream commit, two-example fact-filter prompt, 1,986-QA top-25 evidence
metric, conversation-cluster interval, and call/token counts. Do not label
this an unmodified HippoRAG 2 reproduction or an answer-accuracy result.

If a reviewer needs a method-only causal comparison, align and freeze the
extraction model snapshot, passage/text normalization and query-embedding
protocols, then rerun affected conditions from empty outputs. If answer
quality is needed, run a separate matched answerer experiment with its own
frozen protocol and isolated outputs. Neither extension is part of this
completed retrieval-only task.
