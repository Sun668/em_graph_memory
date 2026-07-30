# v10 pre-publish protocol-lock recovery snapshot

This snapshot preserves the exact active source before the publish-readiness
protocol changes requested after the completed conv-26 B multi-k run.

- Repository HEAD: `7a3cc68`
- Metric state preserved separately in
  `snapshots/v09_conv26_B_official_multik/`.
- The source copy includes the three active packages, active experiment runner
  and tests, repository instructions, plans, and packaging configuration.
- No post-v09 metric is claimed by this snapshot.

The pending source changes are expected to invalidate answer/retrieval outputs:

1. fill a nonempty Entity-gated pool to exactly `top_k` with unused full-pool
   dense results;
2. make official Category-5 option placement deterministic and identical across
   variants;
3. bind outputs to a complete protocol identity and pinned dataset hash;
4. record model/runtime metadata and add release-gate parity validation;
5. add mechanism-isolating gate-only variants.

The existing graph, question-entity, and text-embedding caches may be reused
only when their existing full identities continue to validate. Existing
answer, recall, and aggregate result files do not count under the new protocol.

Historical clarification: the plan above records the state at the instant this
recovery snapshot was created. The subsequent review rejected changes to
`code/locomo_eval/`. The active implementation therefore preserves the
official Category-5 random behavior and does not add protocol identity,
resume guards, dataset adapters, reporting, or top-k validation inside the
frozen evaluator. Formal output isolation and post-run validation are external
experiment-orchestration requirements defined in the repository `AGENTS.md`.
