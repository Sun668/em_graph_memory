# EM Graph (Entity–Memory)

Standalone package under `code/` (separate from the legacy `graph_memory/`
package). It contains graph construction and recall only—no LoCoMo answer
prompt or metric code.

## Package boundary

```text
code/em_graph/
├── build/   conversation-only nodes, edges, normalization, extraction
├── recall/  indexes, ranking, context formatting, public QA recall service
└── cache/   graph/index paths and entity/embedding/question caches
```

Root-level modules such as `em_graph.builder` are compatibility re-exports.
New code imports from the three subpackages.

`em_graph` does not import `locomo_eval`, `experiments`, or `graph_memory`.
Evaluation consumes only `EMGraphRecall.recall(...)`.

## Graph construction

```
dialog turn (dia)
  → evidence-preserving relative-time annotation
  → Memory node (raw + normalized text + time)
  → LLM entity extract on normalized text
  → Entity nodes
  → edges Entity --mentions--> Memory
  → edges Memory --next/prev--> Memory (parsed date_time, bidirectional)
```

`query`, QA questions, QA answers, QA evidence, category labels, judge outputs,
and previous predictions are never graph-construction inputs.

### Text normalization

```python
from em_graph.build import normalize_dialog_text

text = normalize_dialog_text(
    "I went to a LGBTQ support group yesterday",
    dialog_time="1:56 pm on 8 May, 2023",
)
# → "I went to a LGBTQ support group yesterday [7 May 2023]"
```

### Build

```python
from em_graph.build import build_em_graph_from_file

graph = build_em_graph_from_file(
    "data/locomo10.json",
    sample_id="conv-26",
    session_num=1,  # optional
)
graph.save_to_file("outputs/em_graph/conv-26_session1.json")
```

`build_memory_graph(sample)` constructs the dense Dialog baseline with the
same Memory text/caption normalization but no entity extraction.

### Invariants

- Node types: `memory`, `entity`
- Mentions edges: entity ↔ memory only (`mentions`)
- Sequence edges: chronological memories linked with `next` + `prev`; session
  timestamp first, then session/turn order as the tie-break/fallback
- No entity–entity edges

## Recall

1. **Entity BM25 soft-match** question keys → Entity→Memory seeds
2. Expand each seed to ±1 chronological neighbor at half entity weight
3. Embedding over the candidate pool (full corpus if gate empty)
4. Fuse ``0.30 * entity + 0.70 * embedding``

```python
from em_graph.recall import EMGraphRecall

recall = EMGraphRecall(
    graph,
    embedding_index,
    extractor=question_extractor,
    question_cache=question_cache,
)
result = recall.recall(sample, qa_index=0, question="Where?", top_k=25)
```

The returned context uses raw dialog text and the official reader format:

```text
date_time: speaker said, "text" and shared blip_caption
```

Normalized text and captions are used for graph extraction/embeddings; image
search `query` is not used.
