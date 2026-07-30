# v31 — retrieval-only gate stopped by unnecessary context-cache seeding

Decision date: 2026-07-28 Asia/Shanghai.
Source commit: `ef092c6`.

The first corrected all-10 retrieval-only A/B_embed gate used immutable query
artifact SHA `bef99a…6f9f`, shared each conversation's identical Memory index,
and made no answer call. Conv-26, 30, 41, 42, 43, 44, and 47 passed exact
ordered equality for all 1,347 QA processed.

Before conv-48 retrieval, loading its existing index attempted to seed index
vectors into the newly empty general text cache. A Memory text SHA already
seeded from an earlier conversation had a different historical index vector,
so the new conflict guard correctly raised:

```text
ValueError: conflicting vectors for existing text embedding cache key
v2_full_sha256::text-embedding-3-small::context::
5bfe34863566cfb75a96078806f612f16250849eb08ad0ce0ac9bb1246e63cbe
```

This does not show an A/B_embed difference: both conditions use the same
hash-bound index within each conversation. It shows that reverse-seeding
already-built indexes into a mutable cross-conversation text cache is
unnecessary and ambiguous when historical provider calls produced different
vectors for identical text.

Graph compliance and the frozen evaluator remain unchanged. No answer,
metric, or live query embedding was generated. Publication gate:
`stop_for_control_repair`, `paper_ready=false`. Next: formal strict-query runs
must disable writable context-cache use when loading existing Memory indexes,
then repeat the all-10 retrieval-only gate from the beginning.
