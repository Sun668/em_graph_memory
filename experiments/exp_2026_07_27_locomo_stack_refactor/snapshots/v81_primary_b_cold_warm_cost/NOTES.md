# v81 primary-B cold/warm cost

Status: **not started; diagnostic-only**.

The self-removing launchd protocol was tested with `/private/tmp`, but the
formal v81 launch showed that a user launchd service cannot access this
repository under macOS privacy controls. The durable log contains only:

- `source ./env_gpt.sh`: operation not permitted;
- virtualenv realpath: operation not permitted;
- zsh `status`: read-only variable.

Python never started. The exact launchd label was immediately removed before
it could continue retrying. There were zero model requests and no cache,
events, report, or exit-status artifact. The 134-byte log is preserved at
`outputs/locomo_cost/primary_b_v81.log`, SHA-256
`94094cd4…197e`.

Thus v81 has no scientific or cost observation and no paper eligibility. The
launchd mechanism is rejected for workspace experiments. A user Terminal
session is the next persistence candidate because it runs in the interactive
user context that already has repository access; it must first pass a local
no-network persistence probe and be frozen under a new run id.
