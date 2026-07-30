# AGENTS.md

This file defines mandatory working rules for future agents working in this
repository.

## Directory Structure

The current project layout must be preserved.

- `code/`: active three-part LoCoMo stack source root.
- `code/common/`: shared model/API clients.
- `code/em_graph/`: standalone Entity–Memory bipartite graph build, recall,
  and cache package.
- `code/locomo_eval/`: pinned official LoCoMo evaluator plus the QA recall
  interface.
- `graph_memory/`: legacy standalone graph-memory source package
  (**no cross-imports** with `code/em_graph/`).
- `data/`: project input data and small committed datasets.
- `experiments/`: experiment bundles and experiment support code.
- `experiments/exp_*`: one directory per experiment.
- `experiments/shared/`: reusable experiment runners and helper modules.
- `experiments/archive/`: legacy documents and scripts kept for reference.
- `outputs/`: generated experiment outputs, logs, caches, and bulky artifacts.
- `archived_outputs/`: archived generated outputs and logs.
- `PLAN.md`: overall optimization plan and completion status.
- `TODO.md`: detailed progress for the current optimization.

Do not create new top-level directories unless the user explicitly asks for a
structural change. Keep the three active LoCoMo stack packages under `code/`;
do not move active source code, data, or experiment bundles out of the
directories above without explicit approval.

Within `code/em_graph/`, concrete implementation modules belong exclusively
under `build/`, `recall/`, or `cache/`. Keep only `__init__.py` as the root
Python facade; do not recreate compatibility modules such as
`em_graph.builder` or `em_graph.retrieval`.

Before changing or explaining the active LoCoMo stack, read
`README.md` section **Breaking Changes From The 2026-07-27 LoCoMo Refactor**.
Treat that section as the migration boundary between immutable historical
experiments and the current implementation.

Keep `PLAN.md` and `TODO.md` up to date while optimizing. `PLAN.md` records the
overall plan, milestones, and completion status so the long-running direction is
not lost between sessions. `TODO.md` records the detailed state of the current
optimization, including what is in progress, what was tried, and what remains.

## Experiment Rules

## Mandatory Graph Constraint

All optimization work that is retained as a valid result must satisfy both
conditions:

- The memory graph must be constructed only from conversation data, including
  session anchors, dialog ids, speakers, dialog text, and image captions. Graph
  construction must not use QA questions, QA answers, QA evidence annotations,
  QA category labels, judge results, or question-driven ledger artifacts.
- Answer recall must use graph retrieval. Prompts, LLM extractors,
  normalizers, rerankers, routing rules, and validators are allowed only when
  they increase the information density of the conversation-built graph or
  improve retrieval, validation, or answer generation over graph nodes and
  edges.

Experiments that do not satisfy this constraint may be kept only as diagnostic
references and must not be reported as compliant baselines.

At the end of every experiment, explicitly audit whether the run satisfies the
mandatory graph constraint. The experiment notes or result file must state:

- which inputs were used to construct the graph;
- whether QA questions, QA answers, QA evidence annotations, QA category
  labels, judge results, previous predictions, or question-driven ledger
  artifacts were excluded from graph construction;
- whether answer recall used graph retrieval over conversation-built graph
  nodes and edges;
- whether any prompts, extractors, normalizers, rerankers, routing rules, or
  validators were used only to improve graph information density, retrieval,
  validation, or answer generation over graph evidence.

If this audit does not pass, the experiment result does not count toward the
target accuracy, even if its judged score is high. Non-compliant runs may be
kept only as diagnostic references and must be labeled as non-compliant in
the experiment notes.

## Metric Priority

Unless the user explicitly defines a different target for a specific run,
LLM-as-Judge is the primary optimization and promotion metric for EvoEmo /
ES-MemEval work. F1 is a secondary diagnostic metric used to understand answer
surface-form drift, extraction brittleness, and regressions, but it is not a
hard promotion gate by default.

Do not discard or down-rank a compliant result only because F1 is lower if the
LLM-as-Judge score improves. Preserve the result, inspect the tradeoff, and
decide the next step from judge quality first. If a user-specified F1 floor is
active for a particular experiment, record that floor in the experiment
snapshot and conclusion; otherwise treat F1 as diagnostic context.

The current repository LLM-as-Judge prompt is a local evaluator rubric, not an
official benchmark-provided judge prompt. It is defined in
`experiments/shared/evo_emo_eval.py` and copied into experiment checkpoint
judge scripts. It scores `Question + Gold Answer + Model Answer` with a simple
`0/1/2` rubric and requests `Score: X`. When reporting results, describe this
as the local LLM-as-Judge score unless a future experiment explicitly imports
and documents an official benchmark judge prompt.

For EvoEmo / ES-MemEval optimization after 2026-07-06, any metric-bearing test
used for comparison, promotion, or claimed progress must include at least 100 QA
items. Smaller runs may be used only as API, syntax, wiring, or audit preflights
and must be labeled as non-metric diagnostics. Do not report a sub-100 run as a
score improvement or regression.

For EvoEmo / ES-MemEval experiments, every candidate must first be tested on a
200-QA evaluation slice before it is considered for full-dataset regression. If
the 200-QA slice reaches an LLM-as-Judge score above `1.4/2`, immediately run a
full-dataset regression using the same committed candidate settings. During the
full regression, checkpoint judge quality after every 300 judged QA items. If
three consecutive 300-row checkpoints are below `1.3/2` and continue a
downward trend, stop the full regression and mark the candidate rejected for
full promotion. Interrupted/stopped full regressions may be used as diagnostics
only; they must not be reported as final full-dataset scores.

Every experiment must have its own directory under `experiments/`.

## Prompt Budget

Do not let prompts for graph-node generation, episode selection, reranking,
answer generation, validation, repair, or judging-support helpers grow without
bound. Runtime prompts used by retained experiments must be intentionally
bounded and inspected before metric-bearing runs.

Hard limit: the non-data prompt scaffold that is manually written or
mechanically concatenated into any non-judge runtime prompt for graph-node
generation, retrieval assistance, or answer generation must be at most `5000`
characters. This limit applies to fixed instructions, schemas, rubric text,
handwritten examples, selector descriptions, helper explanations, repeated
prompt fragments, and any other prompt text introduced by the runner itself.
It does not count the current test question, retrieved conversation text,
conversation-built graph nodes, conversation-derived facts, source-session
evidence, or other inserted test-data evidence. Metric-bearing traces or
summaries should record scaffold length separately from inserted data/evidence
length. Do not rely on the external model or API to truncate oversized prompts.

Delete or disable prompt components, generated node types, guards, rerankers,
validators, repair steps, and evidence expansions that are invalid, redundant,
non-compliant, repeatedly ineffective, or have a measured negative effect on
LLM-as-Judge. Do not keep failed components active merely because they are
available in older runners.

Every metric-bearing experiment conclusion must state whether prompt budgets
were checked and whether any oversized, ineffective, or harmful prompt
components were removed or disabled.

## Experiment Result Summaries

Whenever an experiment result is summarized—in chat, `conclusion.md`,
`README.md`, snapshot `NOTES.md`, or any other experiment note—the summary
must be detailed enough that a later reader can reconstruct what was run
without opening the runner source. Do not report only headline metrics.

Every such summary must explicitly cover:

1. **Parameters and settings**
   - dataset / conversation slice (e.g. conv id, QA count, category filters);
   - model names for extraction, answer generation, embedding, and judge;
   - retrieval / fusion / ranking hyperparameters (top-k, weights, thresholds,
     temperature, max tokens, cache keys, random seeds if any);
   - exact command line and env-facing settings (excluding secrets);
   - which runner / snapshot / source files produced the result.

2. **Graph extraction logic**
   - what units are extracted (entities, SVO triples, facts, dialog nodes,
     captions, etc.);
   - which extractor (LLM prompt vs rule / heuristic) and on which
     conversation fields;
   - normalization, dedup, filtering, and any schema constraints.

3. **Graph construction logic**
   - node types, edge types, and how they are linked;
   - whether the graph is bipartite, multi-layer, or otherwise structured;
   - which conversation-only inputs were used, and confirmation that QA /
     judge / evidence annotations were excluded from construction;
   - any post-build densification or indexing steps.

4. **Recall / retrieval logic**
   - query formation from the question;
   - how candidates are scored and fused (embedding, BM25, graph walk,
     entity match, etc.);
   - top-k cutoffs, rerankers, validators, and how retrieved nodes/edges
     become answer evidence;
   - answer-generation prompt role relative to retrieved graph evidence.

5. **Judge logic**
   - which judge prompt / rubric was used (local LLM-as-Judge vs official);
   - judge model, score scale (e.g. 0/1/2), and aggregation
     (mean, by-category, top-k evidence variant);
   - whether F1 or other diagnostics were also reported, and that
     LLM-as-Judge remains the primary promotion metric unless overridden.

If any of the above is unknown or not applicable, say so explicitly rather
than omitting the section. Metric tables alone are not a valid experiment
summary.

## Explanation and Comparison Protocol

The following rules are mandatory whenever answering a question about how the
repository works, why two runs differ, whether this implementation matches a
paper or upstream repository, or what effect a proposed logic change will
have.

### Reinspect sources before explaining

- Do not answer from memory, earlier chat summaries, generated prose, or an
  old snapshot alone. Reopen the current implementation that owns the behavior.
- If the question involves a comparison, reopen both sides before answering:
  the exact current source and the exact comparison source. The comparison
  source may be a pinned vendored upstream file, a paper passage, a historical
  snapshot, a result artifact, or another active implementation.
- For an upstream or “official” claim, verify the pinned upstream commit and
  inspect the original prompt/code being compared. Do not infer official
  behavior from local wrapper names.
- State the inspected paths, symbols, versions/commits, and result artifacts.
  If one side cannot be inspected, identify that limitation and do not claim
  complete alignment.
- Keep observations from source separate from inferences about likely runtime
  or metric effects.

### Explain the complete logic and every effective parameter

An explanation must cover the end-to-end path relevant to the question, not
only the line that appears different. Include every effective parameter and
state its value, source, default/override precedence, unit, and scope. If a
parameter is unknown or not applicable, say so explicitly.

As applicable, inspect and explain:

1. dataset file, sample/conversation filter, QA count, category filter, and
   random seed/order;
2. conversation fields consumed, dialog normalization, caption/image handling,
   extraction unit, extractor prompt/model, temperature, token budget, retry
   behavior, normalization, filtering, merging, and deduplication;
3. node/edge schema, edge direction, graph-build inputs, chronological ordering
   and tie-break/fallback rules;
4. question/query formation, question extraction model and prompt, candidate
   pool/gating, BM25/embedding/graph-walk scores, fusion weights, thresholds,
   sequence expansion, fallback behavior, signed-score treatment, tie-breaking,
   and top-k;
5. cache location, cache key fields, schema/protocol versions, SHA-256 inputs,
   validation on load, resume/overwrite behavior, and exactly which change
   invalidates which artifact;
6. recalled-context formatting, evidence ordering/truncation, answer prompt
   text, message roles, answer model, temperature, completion-token limit,
   decoding and retry behavior;
7. per-QA metric definition, category-specific branches, normalization,
   rounding/serialization, aggregation denominator, subset filters, confidence
   interval/significance procedure, and reporting aliases;
8. graph-constraint compliance, prompt budget, expected API/model-call cost,
   reproducibility, and whether existing experiment results remain comparable.

Do not hide defaults behind phrases such as “standard settings” or “the same
configuration.” Enumerate the values that make the settings the same.

### Required comparison format

Every behavioral comparison must include a table with at least these columns:

| Dimension / parameter | Side A: exact behavior | Side B: exact behavior | Expected impact of the difference |
|---|---|---|---|
| Example | Source, value, and execution stage | Source, value, and execution stage | Retrieval, answer, metric, cache, cost, or no practical effect |

Use one row per logically independent difference. Cover identical parameters
too when they are important to establishing a fair comparison. After the
table, state:

- which behaviors are exactly aligned;
- which are only functionally similar;
- which differ;
- which differences have no effect on the present dataset and why;
- which differences invalidate caches, answers, metrics, or prior comparisons;
- which experiments must be rerun to measure the effect.

When discussing a proposed modification, trace its downstream consequences
through graph construction, cache identities, retrieval, context, generation,
evaluation, cost, and paper comparability. Never say a change is harmless
without checking those consumers.

### Metric terminology

- Distinguish metric definition, answer-generation protocol, per-row
  serialization, aggregation, and reporting; matching one layer does not prove
  complete evaluation alignment.
- Use **Categories 1–4 subset F1** for the repository-defined mean of official
  per-QA F1 scores restricted to Categories 1–4. Never call it an official
  LoCoMo metric. Historical `ex_cat5` JSON keys are immutable legacy aliases.
- Use `recall_acc` only for the official evidence-recall definition. Do not
  reintroduce or report `hit@k` as a formal metric.
- Do not claim “fully aligned,” “identical,” or “paper-comparable” until the
  two original implementations/prompts have been inspected, all effective
  parameters have been compared, and relevant parity tests or reruns pass.

## External Model Authorization

As of 2026-07-09 Asia/Shanghai, the user has authorized all future experiment
versions to send conversation-derived prompts to the external model API
configured by `env.sh`, and has authorized judge evaluation to send
question/gold-answer/prediction rows to that same configured external API.

This authorization does not relax the mandatory graph constraint. Runtime
answer generation must still build graphs only from conversation data and recall
answers through graph retrieval. QA answers, QA evidence annotations,
capability/category labels, judge outputs, previous predictions, and official
summary/observation/event timeline/social relationship fields remain forbidden
runtime inputs for answer generation.

Use the naming pattern:

```text
experiments/exp_YYYY_MM_DD_short_description/
```

Each experiment directory must include enough information to reproduce and
understand the run:

- `README.md`: purpose, hypothesis, run commands, important settings.
- run scripts or commands used for the experiment.
- `result.json` or another explicit result file when machine-readable results
  are available.
- `conclusion.md`: summary, interpretation, and next action.
- `next_steps.md`: experiment-specific follow-up actions and recommended next
  experiments.
- `snapshots/`: immutable per-run and per-progress snapshots for every
  reported experiment result and meaningful intermediate progress.

Every reported experiment result and every meaningful progress point must have
its own snapshot before any follow-up edit is made to the runner, prompt,
retriever, graph builder, evaluator wrapper, or shared experiment logic. This
includes completed runs, partial runs that reveal useful signal, aborted runs
whose source may be continued later, and source changes that may affect future
results. Use a stable directory name such as:

```text
experiments/exp_YYYY_MM_DD_short_description/snapshots/v01_label/
```

Each snapshot must include:

- the exact runner/source files used for that result, or a patch plus base
  commit if the runner lives in shared code;
- the exact command line and important environment/model settings, excluding
  secrets;
- the strict graph/no-test audit output or a pointer to the committed audit
  file;
- the metric/result files for that run, or small committed summaries pointing
  to bulky generated outputs under `outputs/`;
- a short note stating whether the snapshot satisfies the mandatory graph
  constraint, whether LLM-as-Judge improved, and whether the result counts
  toward the target.

If a result has metrics but no matching source snapshot, label it as
incomplete/non-reproducible in the experiment notes. It may be used for
diagnosis, but must not be promoted as a reproducible best result until the
source snapshot is restored and rerun.

If source changes are made without a snapshot, stop and create a recovery
snapshot immediately before continuing. Future agents must treat missing
snapshots as a process violation, not as harmless bookkeeping.

Generated logs, embedding caches, model outputs, and other large artifacts must
go to `outputs/` or `archived_outputs/`. Do not commit bulky generated files
unless the user explicitly asks for them.

## Commit Rules

After each experiment is completed, commit the code and experiment notes.

The commit should include:

- source changes needed for the experiment;
- the experiment directory under `experiments/exp_*`;
- concise result and conclusion files.

The commit should not include:

- API keys, secrets, or credentials;
- generated caches or bulky model outputs;
- unrelated user changes.

Before committing, inspect `git status` and only stage files that belong to the
completed experiment or requested change.

After every successful commit, push the current branch to its configured
remote. If pushing fails or requires user action, report that explicitly before
continuing further experiment work.

## Working Rules

- Follow the existing code style and experiment layout.
- Prefer extending `experiments/shared/` for reusable experiment logic.
- Do not stay trapped in incremental tweaks when a direction repeatedly fails.
  If small optimizations along one path do not improve the target metric or
  expose a structural limitation, stop that path, search the current frontier
  of relevant papers/projects/benchmarks again, compare their methods against
  the current implementation, and design a new compliant approach from first
  principles when warranted. A new approach may fully replace the current graph
  generation, retrieval, runner, or answerer design as long as it satisfies the
  mandatory graph constraint and keeps its implementation and experiment notes
  inside its own `experiments/exp_*` directory.
- Keep each experiment self-contained enough that later readers can understand
  what changed, what was run, and what happened.
- If a task requires changing this structure, ask the user first and document
  the reason in the relevant experiment notes or commit message.
