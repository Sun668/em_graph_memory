# v05_final_refactor

Final source checkpoint for the requested three-part architecture.

## Outcome

- `locomo_eval`: pinned byte-identical official LoCoMo QA source, modern model
  transport adapter, and one injected `QARecall` boundary.
- `em_graph`: build, recall, and cache subpackages only.
- `common`: single active LLM/embedding client implementation.
- Package/wheel version: `standalone-graph-memory 0.2.0`;
  `em_graph.__version__ == 0.4.0`.

## Validation

- 12/12 refactor, cache, official prompt, official metric, and boundary tests.
- 17/17 normalization and real-datetime sequence regressions.
- 16/16 vendored upstream SHA-256 checks.
- Python syntax checks pass.
- Wheel build and content inspection pass; vendor source, manifest, and license
  are packaged.
- Active duplicate LoCoMo metric functions outside vendor: zero.

## Full-data audit

- LoCoMo samples: 10.
- Dialogs / Memory nodes: 5882.
- Dialog-bearing sessions: 272.
- Session timestamp keys: 288.
- Directed chronological Memory edges: 11744.
- Extraction input: exactly `text_normalized` plus optional
  `[Image: blip_caption]`.
- `query` and `img_url` in active Memory schema: no.
- Entity prompt scaffold: 2410/5000 characters.
- Mandatory graph constraint: pass.

## Metric status

No model-backed QA experiment was run in this refactor. There is no new F1 or
recall claim. The next valid action is the requested conv-26 A/B/ablation
preflight using this snapshot, followed by all-10 only after that preflight is
clean.
