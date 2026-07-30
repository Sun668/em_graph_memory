# v78 cost-probe shared-cache fix

Status: **validated source-only tooling repair; no metric or cost result**.

Base commit: `00d926e` (failed v77 evidence already frozen and pushed).

The defect was isolated to `cost_probe._measure_state()`. Unlike the formal
evaluation path in `run.command_evaluate()`, the probe did not pass shared
cache objects to `_load_recall()`. It now constructs exactly one
`TextEmbeddingCache`, one question `EntityExtractor`, and one
`QuestionEntityCache` per measured cache state and injects those same objects
into every conversation-specific Recall instance.

The graph builder, retrieval scoring, Reader, evaluator, metrics, formal
outputs, and cache implementations are unchanged. No file under
`code/locomo_eval/` was edited.

Regression coverage uses two conversations and records one question key from
each through the shared object. After flush, the one JSON cache contains both
entries. It also asserts object identity for the text cache, question
extractor, and question cache passed to both Recall instances.

Validation:

- focused cost tests: 7/7;
- current refactor experiment suite: 90/90;
- historical official-comparison suite: 17/17;
- frozen evaluator manifest: 16/16;
- `git diff --check`: pass.

The failed `outputs/locomo_cost/primary_b_v77_cache` remains quarantined and
untouched. Existing `outputs/em_graph`, O2 artifacts, and formal result
directories were not write targets.

Decision: commit/push this source-only repair, then freeze a new v79 cost run
against a new absent cache and output pair. v78 itself supports no paper
result.
