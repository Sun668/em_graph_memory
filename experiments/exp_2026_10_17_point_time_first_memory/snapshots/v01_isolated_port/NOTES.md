# v01 isolated port

Source base: `main` at `11e784c435aa6cfba0d7c02d4ba43ddcf31d2e0a`. This snapshot contains the exact modified formal runner, point-time adapter, and local test. SHA-256: formal runner `f763364d10f1f7db4201a93fa40e4bbf226e3ec5de538ce21a07afec7d237a6f`; adapter `c66c442cee29aaea2401203e651f6cb947681bf8cebc91752062db64d9e3ee67`; test `a0b0d8d5750880dc0b3a61cc04194d52d6b1667f35ecf1ef7c071fb9b730ce23`.

Local commands (no model environment or API calls):

```text
python3 -m unittest discover -s experiments/exp_2026_10_17_point_time_first_memory -p 'test_*.py' -v
python3 -m unittest discover -s experiments/exp_2026_07_27_locomo_stack_refactor -p 'test_formal_graph.py' -v
cd code/locomo_eval/vendor && shasum -a 256 -c MANIFEST.sha256
git status --short -- code/locomo_eval
```

Results: 1 adapter test and 5 formal-runner tests passed. All vendored manifest entries passed; the entire frozen `code/locomo_eval/` directory had no uncommitted changes. No metric-bearing run occurred. Historical all-ten F1 improvement is not assigned to this new branch. The graph constraint passes by source inspection: graph construction uses conversation fields only; QA questions, answers, evidence annotations, categories, judge outputs, previous predictions, and question-ledger artifacts are excluded; QARecall still retrieves over Entity–Memory graph nodes and edges. The adapter only changes Reader text downstream of that retrieval. No prompt scaffold change, no new model call, no oversized or ineffective prior exploration component. The formal runner's existing prompt budget check remains active.
