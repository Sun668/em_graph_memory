# Multiline Reader preflight failure

2026-10-17. No answer-model calls were made. The first all-ten offline
retrieval preflight used the approved project Python 3.9 virtual environment,
validated query-artifact identity, and matched the saved B Top25 IDs for all
199 Conv26 and 105 Conv30 QA. The fixed treatment changed 17 and 8 of those
rows respectively. It stopped at Conv41 QA index 22 with `Reader context line
count mismatch`: a Memory contains an embedded newline, so splitting the
context into physical lines does not give one line per retrieved Memory.

The exact failed `point_time_context.py` source is copied beside this note.
The repair must compare the canonical first-Memory prefix and the unchanged
remaining-Memory suffix, preserving the previously frozen time conversion,
question route and Top25 IDs. This is a no-model-call wiring failure, not an
F1 or recall result. Graph-construction inputs remain conversation-only;
prompt budget was not exercised by answer generation.
