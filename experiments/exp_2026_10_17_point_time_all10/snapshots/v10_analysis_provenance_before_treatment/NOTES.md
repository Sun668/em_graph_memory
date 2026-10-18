# Provenance check revised before treatment

The B control `pt_all10_B_v02` completed and was independently validated,
snapshotted, committed and pushed at commit `6fde9c56`. Repository rules
require closing a condition before launching the next condition. This
documentation-only commit necessarily changes the full Git commit/tree
recorded by the formal runner, although the executable source and experiment
inputs remain unchanged. The original predeclared comparison code is
preserved at `../v08_analysis_v02_ids/compare.py` (SHA-256
`a3fff66c90218759e923533646feeb564a9db2724890520b253b955009e0570c`).

This source-only revision, made **before treatment answer generation**,
replaces strict full-commit/tree equality with an audited Git changed-path
allowlist for experiment notes/snapshots, plan files and this analysis script.
It rejects changes to the formal runner, frozen evaluator, graph package,
dataset, treatment transformer, caches or other executable/input paths.
The exact paired graph/index/query identities, model, answer protocol,
Top25 IDs and official recall rows still have independent checks.

No F1 selection, estimator, bootstrap draw count/seed, claim gate, active-row
definition or category scope changed. The treatment remains
`pt_all10_T_v02` under its already committed frozen parameter snapshot
and exact command. `compare.py` in this snapshot is the exact analysis
source intended for the all-ten pair; SHA-256 `7f7e7992ae85e8e006918ebad9e543416c8c24f89ad4e21db4b6bf6d498f9e8f`.
This snapshot contains no new metric result and does not alter B outputs.
