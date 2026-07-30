# v03_query_free_full_audit

Final source checkpoint after removing `query` and `img_url` from the active
Memory schema.

- Metric-bearing: no.
- Mandatory graph constraint: pass.
- LoCoMo-10 audit: 10 samples, 5882 dialogs, 272 dialog-bearing sessions, 288
  timestamp keys, 11744 directed chronological Memory edges.
- Every entity-extraction input exactly matched `text_normalized` plus optional
  `[Image: blip_caption]`.
- `query`/`img_url` serialized fields: zero.
- Entity prompt scaffold: 2410/5000 characters.
- Active local LoCoMo F1/recall implementations outside the pinned vendor:
  zero.

Validation commands are documented in the parent experiment README and
`source/result.json`. This snapshot is the source base for the next conv-26
metric preflight.
