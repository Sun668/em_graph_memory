# v01 launch denied before execution

2026-10-17. The v01 B command was submitted with the worktree as the tool's
working directory, but the PreToolUse payload supplied the main repository as
`cwd` and omitted `tool_input.workdir`. The project guard therefore resolved
the wrong repository and denied the launch with `preflight_exception`.
Neither v01 condition output directory exists; no model call or F1 result was
produced. Replaying the exact v01 command in a simulated hook payload with
the worktree as `cwd` passed. Prefixing a literal `cd <worktree> &&` in the
simulated main-cwd payload reached the intended worktree and was denied only
for expected `command_binding`, proving the revised launch needs new frozen
snapshots and run IDs. The v01 snapshots remain immutable abandoned records.
The revised command will keep all project and personal preflight checks.
