# Standalone Graph Memory

This directory extracts the graph-memory pipeline from the original repository
so it can become its own repo.  It includes the graph builders, data models,
entity/triple extractors, retrievers, temporal helpers, fact index, and a small
CLI for LoCoMo-style datasets.

## What Was Extracted

- `graph_memory/`: the reusable Python package.
- `code/`: the three-part LoCoMo stack: official evaluation, EM-graph
  construction/recall/cache, and shared model clients.
- `graph_memory/core/llm_client.py`: a small replacement for the original
  repository-level `global_methods.py` dependency.
- `graph_memory/cli.py`: build/query/smoke-test commands that do not depend on
  `task_eval` or other repository modules.
- `experiments/`: experiment bundles. Shared runners live in
  `experiments/shared/`. As of 2026-07-22, historical `exp_*` dirs live under
  `experiments/archive/` (including the pre-purify `graph_memory` snapshot).
  New experiments should be created as fresh `experiments/exp_*` at the top
  of `experiments/`.
- `archived_outputs/`: optional local-only archive of large historical
  experiment outputs. It is ignored by git and should not be committed.
- `data/locomo10.json`: a LoCoMo sample file for local smoke tests.
- `pyproject.toml` and `requirements.txt`: minimal standalone packaging files.

## Package Layout

```text
code/
  common/       Shared model/API clients
  em_graph/     Conversation graph build, recall, and cache
  locomo_eval/  Pinned official LoCoMo evaluator and QA-recall interface
graph_memory/
  core/        Data models, config, cache, text processing, temporal helpers, LLM adapter
  extraction/  Entity and triple extractors
  builders/    Entity graph and triple graph builders
  retrieval/   Graph retrievers, question routing, IRIS/phase-2/3 retrieval helpers
  facts/       Atomic fact extraction, fact edges, fact index
  storage/     SQLite-backed fact store
  cli.py       Standalone command line interface
```

## Experiment Layout

```text
experiments/
  shared/       Reusable runners, embedding helpers, and offline judge
  exp_*/        Active experiment dirs (create new ones here)
  archive/      Historical exp_* + graph_memory_pre_purify_* snapshots
```

This standalone repository does not own LoCoMo dataset generation. Historical
data-prep scripts are archived rather than active entry points.

## Quick Start

```bash
cd graph_memory
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run an offline smoke test against the bundled LoCoMo file:

```bash
python -m graph_memory.cli smoke-locomo \
  --data-file data/locomo10.json \
  --sample-id conv-26 \
  --session-num 1 \
  --extractor rule
```

Build a full graph with an LLM extractor:

```bash
export OPENAI_API_KEY=...
python -m graph_memory.cli build \
  --data-file data/locomo10.json \
  --sample-id conv-26 \
  --output outputs/conv-26_v2_graph.json \
  --version v2 \
  --extractor gpt-4o-mini
```

Query an existing graph:

```bash
python -m graph_memory.cli query \
  --graph outputs/conv-26_v2_graph.json \
  --data-file data/locomo10.json \
  --sample-id conv-26 \
  --question "What did Caroline talk about?"
```

## Notes For Turning This Into A Separate Repository

- Copy this directory as the new repo root.
- Bring your dataset separately, or point `--data-file` at a LoCoMo JSON file.
- `--extractor rule` is deterministic and offline; it is intended for smoke
  tests, not benchmark-quality extraction.
- LLM extraction uses the official `openai` Python SDK and honors
  `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`.
- Optional quality dependencies such as `spacy`, `nltk`, and
  `sentence-transformers` are used when installed. The offline smoke path avoids
  requiring model downloads.
