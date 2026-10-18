# Treatment run ID changed before treatment generation

The existing `pt_all10_T_v02` frozen snapshot was rejected at preflight
because completed B evidence and its prerequisite analysis note were
committed after the old freeze. The output directory did not exist, and
no treatment answer or provider call occurred. Preserve v02 untouched.

A new treatment snapshot will use `pt_all10_T_v03` on the current clean
commit. This update changes only the `TREAT_ID` constant in the
pre-treatment comparison script from v02 to v03. F1 estimator,
conversation-cluster bootstrap, seed, claim gate, active-row definition,
provenance allowlist and all parity checks remain identical.
The exact source SHA-256 is `fed53cd9c08ca19304349268b0e2589432f0ce46c59fd49a51b2e4a0cdac7241`.
