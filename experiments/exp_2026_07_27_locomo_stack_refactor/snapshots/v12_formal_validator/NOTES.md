# v12 — external formal-result validator

## Purpose and source

This snapshot records the external formal-result validator before any DRAGON,
runner, significance, or cost implementation is changed.

- Base commit: `e6c252853b7c051df343962f624346be998ff5e3`
- Validator:
  `experiments/exp_2026_07_27_locomo_stack_refactor/validate_formal_result.py`
- Validator SHA-256:
  `6fe51de19cb8c1aba7af6214733a09c2d5f99cc033cfdcb87800ebb82db0f14b`
- Tests:
  `experiments/exp_2026_07_27_locomo_stack_refactor/test_validate_formal_result.py`
- Test SHA-256:
  `829a635653ee4b120256e8e139c11e62e40ef035e0a9517ab384ed1b9a2f9cda`
- Exact new source is committed in the same commit as this snapshot; no
  generated metric output is copied into git.

## Implemented gates

- run schema, run id, source commit, command, start time, models, retrieval
  parameters, graph profile, answer protocol, artifact map, and complete
  condition SHA-256 fingerprint;
- output directory name/identity, asserted empty start, no existing prediction,
  no resume, no overwrite, and exact single-condition contents;
- pinned dataset SHA-256, ordered sample ids, ordered QA source fields, exact
  all-10 `10/1986/446` counts, and explicit preflight labeling;
- prediction, F1, `recall_acc`, and context fields on every QA;
- exact `min(top_k, available_dialogs)` contexts, no duplicates, and no unknown
  dialog ids;
- official stats key/count/F1-sum/recall-mean consistency using serialized
  official fields only;
- graph/no-test audit and prompt budget for graph methods;
- honest graph-constraint failure and non-compliant labeling for official
  Dialog references.

The validator never imports the frozen official evaluation module and never
calculates token-F1 or evidence recall from answers/evidence.

## Verification

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache \
  .venv/bin/python -m unittest \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_validate_formal_result.py \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_refactor.py
```

Result: 25/25 passed (9 validator, 16 refactor).

Covered positive fixtures:

- dataset-faithful all-10: 10 conversations, 1986 QA, 446 Category 5;
- conv-26 preflight: passes validation but is not paper-metric eligible;
- official Dialog reference: passes reference validation but is not
  graph-claim eligible.

Covered negative fixtures:

- resume/overwrite and false empty-start claims;
- QA reorder, missing metric fields, and official stats mismatch;
- short, duplicate, and unknown context ids;
- condition-fingerprint drift and unexpected files/directories;
- missing artifacts, graph-constraint failure, and prompt-budget failure.

The existing isolated conv-26 DRAGON output was used only as a CLI failure
check. It was correctly rejected because it predates formal
`run_config.json`; no metric was changed or reported from that check.

## Compliance

- `code/locomo_eval/`: unchanged and clean.
- Vendored files: 16/16 manifest entries passed.
- Mandatory graph constraint: no metric run in this stage; the validator
  enforces graph-method versus official-reference status.
- Prompt budget: no runtime prompt added; the validator enforces the 5000-char
  audit.
- Formal output isolation: no formal condition executed; synthetic fixtures
  used temporary directories.
- External model/API calls: zero.
- Metric claim: none.
