# All-ten retrieval/context preflight passed

2026-10-17. The exact source and compact result are copied beside this note.
Command from this worktree:

`PYTHONDONTWRITEBYTECODE=1 /Users/sun/Documents/git/graph_memory/.venv/bin/python experiments/exp_2026_10_17_point_time_all10/preflight.py`

The locked Python 3.9.6 / NumPy 2.0.2 environment was necessary for exact
saved-B ordered Top25 parity; system Python 3.13.5 / NumPy 2.3.4 changed
rankings and was rejected before this run. The complete 10-conversation,
1,986-QA original-order dataset and read-only query artifact matched their
predeclared SHA-256 values. B used GPT-3.5 cached question Entities, the
existing conversation-only B graph, `text-embedding-3-small` Memory/query
vectors, Entity weight .30, semantic weight .70, relative Entity threshold
.5, top20 per key, Who-only dampening .25, degree discount, sequence scale
.5 and Top25. No new extractor, embedding, answer or judge call occurred.

All 1,986 B ordered Top25 lists matched validated saved formal B; all 1,986
treatment lists remained identical. The first-Memory-only context audit
passed on every row; 99 questions changed context across ten conversations.
The 3,994 query-vector lookups (B plus treatment, with repeated wrapper
lookup) all hit the same complete read-only artifact; zero misses and zero
live embedding requests. No answer F1 has been measured, and this preflight
does not count as an all-ten improvement result.

Graph construction remains based on conversation session timestamps, dialog
IDs/speakers/text and official captions only. QA answers, evidence labels,
categories, judge outputs and previous predictions are excluded. Questions
are used only for retrieval and the fixed `when`/`how long` Reader route.
Answer recall traverses the conversation-built graph. Graph constraint
passes for this no-model retrieval check. Added prompt scaffold: zero;
answer prompt budget remains a formal-run preflight requirement.
