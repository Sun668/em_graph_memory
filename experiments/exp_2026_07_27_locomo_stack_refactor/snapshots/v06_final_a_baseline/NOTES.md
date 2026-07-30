# v06_final_a_baseline

Final source checkpoint.

Compared with v05, this snapshot restores the exact experimental construction
condition for A:

- A: Memory-only graph, 5882 Memory nodes, zero Entity nodes, no entity LLM.
- B/B_entity/B_embed/B_noseq: complete Entity–Memory graph.
- A and B-family indexes use one canonical embedding artifact identity because
  their Memory search text is identical; reuse validates all Memory ids and
  full text SHA-256 digests.
- Official output-file resume and `--overwrite` semantics now match
  `task_eval/evaluate_qa.py`.

Validation:

- 14/14 refactor/parity/cache/resume tests.
- 17/17 normalization and real-datetime tests.
- 16/16 official vendor hashes.
- all-10 no-model graph audit passes.
- final `standalone_graph_memory-0.2.0` wheel builds successfully; SHA-256
  `8018bae645ab4586a4bb8ba5d097c4973d899200805af13d150c21b926ef98db`.

No external QA run and no new F1/recall claim.
