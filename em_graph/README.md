# EM Graph (Entity–Memory)

Standalone package (sibling of `graph_memory/`). **No imports from `graph_memory`.**

## Layer 1 — graph construction

```
dialog turn (dia)
  → replace_pronouns(speaker + relative time)
  → Memory node (raw + normalized text + time)
  → LLM entity extract on normalized text
  → Entity nodes
  → edges Entity --mentions--> Memory
  → edges Memory --next/prev--> Memory (conversation order, bidirectional)
```

### `replace_pronouns`

```python
from em_graph import replace_pronouns

text = replace_pronouns(
    "I went to a LGBTQ support group yesterday",
    speaker="Caroline",
    previous_speaker="Melanie",
    dialog_time="1:56 pm on 8 May, 2023",
    time_words=["yesterday"],  # optional; omit to auto-detect
)
# → "Caroline went to a LGBTQ support group 7 May 2023"
```

### Build

```python
from em_graph import build_em_graph_from_file

graph = build_em_graph_from_file(
    "data/locomo10.json",
    sample_id="conv-26",
    session_num=1,  # optional
)
graph.save_to_file("outputs/em_graph/conv-26_session1.json")
```

### Invariants

- Node types: `memory`, `entity`
- Mentions edges: entity ↔ memory only (`mentions`)
- Sequence edges: consecutive memories linked with `next` + `prev`
- No entity–entity edges

### Retrieval

1. **Entity BM25 soft-match** question keys → Entity→Memory seeds
2. Expand each seed to ±1 dialog-order neighbor at half entity weight
3. Embedding over the candidate pool (full corpus if gate empty)
4. Fuse ``0.30 * entity + 0.70 * embedding``
