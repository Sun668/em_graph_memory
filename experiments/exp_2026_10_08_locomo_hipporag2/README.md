# LoCoMo HippoRAG 2 adapted retrieval comparison

## Question and classification

On the ten LoCoMo conversations, compare HippoRAG 2 with the already validated
top-25 dense Memory control A and EM-Graph B. This experiment measures only
original-dialog evidence recall. It generates no answers and runs no judge.
HippoRAG is an **adapted external retrieval baseline**, not a reproduction of
the HippoRAG paper or a new official LoCoMo answer metric.

The dataset is `data/locomo10.json`, SHA-256
`047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`:
10 conversations, 5,882 dialog turns, and 1,986 QA rows. The valid local
reference outputs are `outputs/locomo_formal/formal_all10_M1_A_top25_76fcf5b_qfrozen_run01`
and `outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01`
in the main worktree. Both have passing `validation.json` and the same frozen
query embedding artifact; the corrected comparison is recorded in
`experiments/exp_2026_07_27_locomo_stack_refactor/snapshots/v40_corrected_primary_ab_significance/`.

## HippoRAG adaptation

Official `OSU-NLP-Group/HippoRAG` commit
`d5c8329422e0a0b834a15874545cb6a74b4f9b26`, package 2.0.0a5. Each
conversation has an independent index. Each original dialog turn is a `Chunk`
with its original `dia_id` as `source_id`; content includes session time,
speaker, text, and official `blip_caption` if present. QA, answers, labels,
evidence annotations, judge data, summaries, and observations are excluded
from indexing. A separate question-only file is loaded after `index()`.
HippoRAG retains its OpenIE graph, passage/entity/fact embeddings, fact filter,
and personalized PageRank retrieval. Its default ten-example fact-filter prompt
exceeds this repository's 5,000-character non-data prompt budget, so the
documented prompt-file option uses the first two upstream examples. This is a
declared adaptation.

Top-k is 25 original dialog turns. OpenIE and fact filter use
`gpt-3.5-turbo-0125`, temperature 0; embedding uses
`text-embedding-3-small`. The complete resolved config, input hashes, exact
command, and source are frozen per condition under `snapshots/` before API use.
The generated graph, cache, and row results go only under
`outputs/locomo_hipporag2/`. No sub-100 QA pilot is a metric result.

## Completed full comparison

All ten frozen conditions completed with 1,986/1,986 QA and 5,882/5,882
OpenIE passage records. Reproduce the read-only paired audit with:

```bash
outputs/hipporag_venv/bin/python \
  experiments/exp_2026_10_08_locomo_hipporag2/compare_results.py
```

The exact per-condition commands/configurations are under
`snapshots/locomo_hippo_conv*_all_v01/`; the paired audit is frozen under
`snapshots/v01_full10_paired/`. Results and limitations are in `result.json`
and `conclusion.md`. Adapted HippoRAG 2 reached 79.7025% top-25 evidence
recall, versus 79.7468% dense A and 84.4841% EM-Graph B. B minus HippoRAG
is +4.7816 points with a 10-conversation cluster 95% interval
[+2.8314,+6.8006] points.

## Run order

```bash
python3 experiments/exp_2026_10_08_locomo_hipporag2/prepare_data.py
python3 experiments/exp_2026_10_08_locomo_hipporag2/freeze_condition.py \
  --user-id conv-26 --mode pilot --run-id locomo_hippo_conv26_pilot01 \
  --max-chat-attempts 60
zsh experiments/exp_2026_10_08_locomo_hipporag2/snapshots/locomo_hippo_conv26_pilot01/command.sh
```

After a successful wiring/cost pilot, freeze one full condition per
conversation, run them from absent directories, validate all 1,986 top-25
lists, then compare paired per-row official-definition `recall_acc` with
conversation-cluster uncertainty. The old A/B outputs are read-only.

## Graph and prompt audit

Graph construction receives only `sample_id` and conversation fields. It
extracts NER entities and RDF triples from the formatted original turns,
links entity/fact nodes to passage nodes, and uses the upstream graph
retrieval path. No question-derived material is built into the graph. The
bounded prompt scaffold is measured by the runner before indexing. There is
no answer-generation or judge prompt in this experiment.

## Public v1.0.9 entry

Portable commands, environment requirements, archive boundaries and migration validation are documented in [the release guide](../exp_2026_10_09_public_reproduction_release/README.md). Historical snapshots retain their original absolute paths; create new snapshots for a new workspace.
