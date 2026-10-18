# Frozen treatment v03 before answer generation

The T v02 snapshot is preserved but unused. Formal preflight rejected it
before output creation or model calls because required B result/analysis
commits followed its source base. T v03 was frozen from clean committed
source `149040c4e2d16c945b6f7ee58e63cc8439163382`; its output directory
`outputs/locomo_formal/pt_all10_T_v03` was absent at freeze.
Parameter SHA-256: `b761fe5899959d07e70c6f2bfd106f920f27779929ed21daddbed70f0620c528`.
Command-file byte SHA-256: `c9f33a97de207fb0f7932e24dad7e1e24ad2cf61646ad59ec2866a888c1df54e`.
The canonical command hash is stored in `parameters.json`.

The exact secret-free command is `command.txt` and begins with a literal
worktree `cd` for both guards. It sources the approved main
`env_gpt.sh`, records no secret, and uses the same conversation-only B
graphs, index, complete ordered query artifact, Top25 graph recall,
`gpt-3.5-turbo` official answer path, frozen evaluator, 1,986 QA,
resource ceilings and prompt-budget limit as B v02. The only intended
condition difference is `--reader-context-mode point_time_first`.
The treatment may rewrite a supported relative point time in the first
retrieved Memory's Reader text on `when` or `how long` questions;
`last week` and `last weekend` remain unchanged. It does not alter
graph construction, candidates, Top25 IDs or evaluator behavior. Graph
construction excludes QA questions/answers/evidence/categories,
judge outputs and previous predictions, and answer recall uses
conversation-built graph nodes and edges. This is a frozen plan;
no treatment metric has been observed.
