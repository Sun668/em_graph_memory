# v16 — provider usage telemetry

Source-only milestone based on commit
`be903dd21fdcd5315302cc48b0e3b93a86aa0672`.

- `code/common/llm.py` SHA-256:
  `80fc09b8b06f288733797c9347eaef6605f47af6a900e0ebb4247e191744e6a7`
- `code/common/__init__.py` SHA-256:
  `68ab2e41d8e6ccddbc9322d647e0952df30480402918b886e26f7094f4679097`
- Test SHA-256:
  `286ef3ca1218873214837655e637c6b2b4d2d0224cfeb6346bcd7c5255efeb3c`

The observer is disabled by default. Formal orchestration may enable it for a
named stage. Successful chat and embedding requests report requested/actual
model, provider response input/output/total tokens, request count, and
`perf_counter` wall time. It does not alter any prompt, request parameter,
response content, vector, retry policy, or evaluator logic. Missing provider
usage remains missing and must fail the strict cost reporter rather than be
estimated.

Three focused tests verify unchanged chat text and embedding vectors, exact
usage capture, and nested-context restoration. Full result: 49/49 tests pass;
frozen evaluator clean; vendor 16/16. No external API call or metric occurred.

Publication decision: `continue_tooling_only`; paper-ready is false. The next
step is cold/warm formal cost orchestration, followed by another gate.
