# v80 primary-B cold/warm cost

Status: **not started; diagnostic-only**.

The frozen `nohup` launch command returned a child PID, but the hosting tool
immediately reaped the detached process tree. No `cost_probe.py` process,
cache directory, event manifest, report, or exit-status file was created. The
only artifact was a zero-byte log, preserved as
`outputs/locomo_cost/primary_b_v80_launch_attempt01_empty.log`.

Therefore v80 made no model request and produced no experiment observation.
It neither supports nor contradicts the shared-cache repair and has no paper
eligibility.

A local no-network persistence test established that macOS `launchctl submit`
survives the Codex command lifetime. Because submitted jobs use KeepAlive, a
second 12-second test also established that the job must call
`launchctl remove <exact-label>` after writing its exit status; the
self-removing test wrote its marker once and the service was absent afterward.

Decision: preserve v80 as not-started, freeze v81 with new absent paths and an
exact self-removing launchd label, then run the complete cold/warm probe.
