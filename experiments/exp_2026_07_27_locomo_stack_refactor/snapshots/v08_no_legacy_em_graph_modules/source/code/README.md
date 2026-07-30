# Active LoCoMo stack source

This directory groups the three active source packages:

- `common`: shared model/API clients;
- `em_graph`: conversation-only graph build, recall, and cache;
- `locomo_eval`: pinned official LoCoMo evaluation with one QA-recall
  interface.

`code/` is a source root, not a Python package: it intentionally has no
`__init__.py`. Import the packages directly (`import em_graph`, for example)
after installing the project, or use `PYTHONPATH=code` for local one-off
commands.

Dependency direction:

```text
locomo_eval ─┐
             ├──> common
em_graph ────┘
```

`locomo_eval` and `em_graph` do not import each other. The experiment runner
injects `em_graph`'s QA recall implementation into `locomo_eval`.
