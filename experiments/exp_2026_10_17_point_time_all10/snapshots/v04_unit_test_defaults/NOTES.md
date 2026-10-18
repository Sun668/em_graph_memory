# Existing formal-runner unit test failure

2026-10-17. The 21 existing `unittest` cases ran in the project Python 3.9
environment. Two failed before any model call because their synthetic
`SimpleNamespace` args omitted the new optional `reader_context_mode` field;
19 passed. The exact failed formal runner source is copied here. Repair the
config and audit helpers to use the parser's `raw` default for synthetic old
args, and use `None` for omitted optional resource ceilings. This does not
change the CLI parser's resolved defaults or the fixed treatment rule. No
all-ten answer F1 or model-cost observation exists yet.
