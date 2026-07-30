# v20 — O1 runtime and Reader identity gate

Base commit: `3c017e78915c80e3e6f5bedaa8e8b935fa1a89f8`.
Exact source is committed with this snapshot.

Source SHA-256 values:

- `official_dragon.py`:
  `710e036d008af7c77f9e866c12ea4156df2daabecb169479260e575f511335b5`
- `validate_formal_result.py`:
  `b377427f8a14f8db57d2ec3b24e78b5c9554fcfe34882bd017deebf7b511cb63`
- `test_official_dragon.py`:
  `f4f872bae1eab1f6917d1993f51bf3e7bda1c2290a58116065a13575a2bccb16`
- `test_validate_formal_result.py`:
  `42016e193dbcd72621269744b0d49e0350f4da0ba7879b15955850f50579d82f`
- `requirements_o1_official.txt`:
  `26f3dc915ba2c067d0e200bbfb6b102b1ec34671824afa94d0625f13e46af4d1`
- unchanged `code/common/llm.py` telemetry source:
  `80fc09b8b06f288733797c9347eaef6605f47af6a900e0ebb4247e191744e6a7`
- frozen vendor manifest:
  `e65f16906ca342a6a81f626742a0461846a2477d2c0191352cfd47dd3d46035f`

## Implemented identity gates

- Cache schema advanced from v2 to v3 and uses a distinct filename. No old
  cache is automatically migrated or silently skipped.
- Query/tokenizer revision is pinned to
  `2d3808c087119b953f8494b7638c216c71712cee`; context revision is pinned to
  `68074e7406bb0061b0d049b58592acafae00e9d4`.
- Cache creation and loading require Python 3.9.18, PyTorch 2.0.1,
  Transformers 4.35.0, tokenizers 0.14.1, and NumPy 1.26.0.
- Stable cache metadata also binds platform, device, full torch build, and
  torch CUDA build. Any difference fails before retrieval.
- Formal O1 collects provider telemetry without changing prompts or response
  text. A complete run requires one chat response per QA, a single actual
  Reader model, and an actual model equal to or versioned under the requested
  `gpt-3.5-turbo` family.
- `provider_usage.json` is a formal artifact. The external validator checks
  its request count, requested/actual identity, and agreement with
  `run_config.json`.

The frozen files under `code/locomo_eval/` are unchanged. No graph code,
prompt, metric, Dialog text, query text, pooling, normalization, dot product,
ranking, context wrapper, or Category-5 behavior changed.

## Verification

```bash
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  -m unittest discover \
  -s experiments/exp_2026_07_27_locomo_stack_refactor \
  -p 'test_*.py' -v

PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  -m unittest \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_official_dragon.py \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_validate_formal_result.py \
  -v
```

Results: 61/61 full experiment tests and 19/19 focused tests passed. The
vendor-manifest test checked 16/16 pinned files. Syntax, JSON/diff formatting,
and frozen-directory checks passed.

Negative tests prove that dependency-version, Hugging Face revision, device,
Reader request-count, multiple-model, provider-substitution, and
run-config/artifact identity differences fail.

## Compliance and publication decision

This is a source-only milestone with no model call and no metric. O1 remains a
non-graph reference condition; it cannot count as an EM-Graph result. The
mandatory graph constraint for later graph conditions is unchanged. No prompt
scaffold was added.

Publication gate: `continue_tooling_only`, `paper_ready=false`. O1 from v19
remains unaccepted. The only authorized next step is to build the pinned
runtime and perform the fresh-cache corrective O1-25 rerun. M1 remains blocked.
