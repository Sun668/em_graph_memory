# Common infrastructure

`code/common/` is the single active implementation of shared model clients;
its installed/imported Python package name remains `common`.

- `common.llm`: OpenAI-compatible chat and embedding calls.
- `common.codex`: optional Codex subscription-path completion support.

`em_graph` uses the user-role helper for extraction. The LoCoMo runtime adapter
preserves the upstream protocol: the `chatgpt` alias sends the complete QA
prompt as a system message, while GPT-4-family calls use a user message.

The old `experiments.shared.llm_client` and `codex_llm_client` modules are
compatibility re-exports only.
