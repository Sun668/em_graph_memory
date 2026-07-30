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

## Breaking Changes From The 2026-07-27 LoCoMo Refactor

The LoCoMo/Entity–Memory experiment stack was structurally replaced rather
than kept backward compatible. Historical snapshots remain valid records of
what was run, but their source paths, caches, result schemas, and metric labels
must not be treated as the current implementation.

| Area | Previous behavior | Current behavior | Impact and required migration |
|---|---|---|---|
| Active source location | The standalone EM package lived at top-level `em_graph/`. | The active three-part stack lives under `code/common/`, `code/em_graph/`, and `code/locomo_eval/`. The old top-level `em_graph/` tree was removed. | Install the repository with `pip install -e .` or add `<repo>/code` to `PYTHONPATH`. Do not recreate or import the deleted top-level package. |
| EM module imports | Callers imported root implementation modules such as `em_graph.builder`, `em_graph.retrieval`, and `em_graph.embedding_index`. | Concrete implementations live only under `em_graph.build`, `em_graph.recall`, or `em_graph.cache`; `em_graph.__init__` is the sole root facade. | Old direct-module imports fail and must be migrated to the facade or the appropriate subpackage. |
| Matched-stack runner | `experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py` contained the complete intertwined graph, QA, prompt, cache, and metric implementation. | That file is now a compatibility entry point for `experiments/exp_2026_07_27_locomo_stack_refactor/run.py`. | Do not patch the compatibility wrapper as if it were the implementation. Change the owning package or the new runner. |
| LoCoMo evaluation | Locally rewritten `locomo_official_qa.py` and `locomo_official_metrics.py` duplicated official behavior. | QA prompt generation and metric logic execute from the vendored upstream LoCoMo source pinned at commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`; EM graph recall is injected through one interface. | The deleted local evaluator modules are not active APIs. Do not independently reimplement or silently edit vendored prompt/metric logic. |
| Package boundaries | Graph building, retrieval, model calls, QA generation, and evaluation were coupled through experiment code. | `em_graph` owns only graph build/recall/cache, `locomo_eval` owns QA generation/evaluation, and both may use `common`. `locomo_eval` does not import `em_graph`. | Preserve dependency direction. Evaluators receive a `QARecall` implementation; graph packages must not calculate LoCoMo F1 or recall aggregates. |
| Memory schema and image fields | Memory/runtime text could include raw `text`, normalized text, `speaker`, `blip_caption`, image-search `query`, and an `img_caption` fallback. | A Memory stores raw/normalized dialog text and official `blip_caption`; `query`, `img_url`, and the non-official `img_caption` fallback are excluded from graph construction and retrieval text. | Old graphs and embeddings contain different information and are not comparable or reusable. Image-search `query` must never become runtime evidence. |
| Dialog normalization | The old normalizer replaced first/second-person pronouns and could corrupt wording and contractions. | `normalize_dialog_text` preserves the original utterance and only appends deterministic annotations to supported relative-time phrases. | Entity extraction text and embeddings changed for the full dataset. All artifacts derived from the old normalizer are incompatible. |
| Memory embedding text | Multiple fields were concatenated, sometimes duplicating dialog text and including `query`. | The canonical string is `{speaker} said, "{text_normalized}"`, followed by ` and shared {blip_caption}` only when a caption exists. | Embedding caches and indexes from the previous string format must be deleted before a new formal run. |
| Memory sequence | NEXT/PREV edges followed session/dialog-number order. | Memories are ordered by parsed real `session_*_date_time`; session and turn order are deterministic tie-breakers/fallbacks. | Sequence expansion can retrieve different neighbors. Rebuild graphs before measuring variants that use sequence edges. |
| Dense ranking | Negative cosine values were clipped to zero and candidates with non-positive entity and semantic scores could be discarded. | Signed cosine values are retained and the available pool is sorted directly; top-k is returned even when some scores are negative, matching official dense `argsort` behavior. | Recall lists can change, especially at the tail or for weak queries. Old recall and answer artifacts are not current-stack results. |
| Cache identity | Question caches could depend on truncated question text or QA index alone; answer checkpoints did not identify the complete generation protocol. | Question entity keys include sample ID, QA index, full-question SHA-256, extraction model, and protocol namespace. Graph/index paths include conversation, normalization, model, and retrieval-text identities. | Do not add automatic legacy-schema fallback. When a protocol or schema changes, delete the exact incompatible cache/output files and rebuild them. |
| Answer protocol | Some local calls used a `user` message and larger/default completion budgets. | The official GPT-3.5 batch-size-1 path sends the complete prompt as a `system` message with `temperature=0` and `max_tokens=32`. Existing evaluator outputs resume unless the exact output is deleted or `--overwrite` is supplied. | A role, prompt, model, temperature, or token-budget change invalidates answers/checkpoints even when retrieved context is unchanged. |
| Metrics | Local set-token F1, `hit@k`, and the label `official ex-cat5 F1` appeared in older reports. | Formal LoCoMo runs use official category-aware per-QA F1 and `recall_acc`, including official three-decimal per-row serialization. `hit@k` is removed. The locally derived Category 1–4 mean is named **Categories 1–4 subset F1**, never an official metric. | Historical JSON fields containing `ex_cat5` are legacy aliases only. Do not compare old local F1 directly with a new official-stack run or call the subset aggregation official. |
| Dataset counts | Some documentation called 288 timestamp keys “288 sessions.” | LoCoMo-10 contains 272 dialog-bearing sessions and 288 `session_*_date_time` keys; 16 timestamp keys have no corresponding dialog list. | Graph construction processes 272 actual dialog sessions. Reports must distinguish session lists from timestamp-key counts. |
| Result status | Pre-refactor A/B numbers were sometimes presented next to the intended aligned protocol. | The refactor has unit/parity validation but has not itself produced a formal all-10 A/B/ablation metric rerun. | Never relabel historical metrics as new-stack results. Run conv-26 as a preflight, then rerun all-10 under the frozen current protocol before making paper claims. |

The immutable migration record is
`experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/`. Large generated
artifacts belong under `outputs/` or `archived_outputs/`, not inside the source
packages.

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
