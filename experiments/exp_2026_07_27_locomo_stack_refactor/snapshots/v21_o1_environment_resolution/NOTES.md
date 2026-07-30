# v21 — O1 Python 3.9 environment resolution

Base commit: `b10b2d4de572a85bfbfa65d7280dbdae1fcd0358`.
Exact source is committed with this snapshot.

The isolated runtime target
`outputs/runtime_envs/o1_official_py3918_b10b2d4` was created successfully
with CPython 3.9.18. The first `uv pip install` resolved no environment and
installed no packages because the source-only v20 requirements carried
`nltk==3.10.0`, which requires Python 3.10.

The pinned upstream LoCoMo requirements instead specify:

- NLTK 3.8.1;
- regex 2022.10.31;
- tqdm 4.64.1.

`requirements_o1_official.txt` now uses those exact upstream-compatible
versions. The retrieval-critical pins remain Python 3.9.18, NumPy 1.26.0,
PyTorch 2.0.1, Transformers 4.35.0, and tokenizers 0.14.1. OpenAI 2.45.0 is
retained solely because the repository's audited compatibility wrapper uses
the modern `OpenAI` client; provider response identity is independently
validated as GPT-3.5 Turbo.

No model request, embedding, retrieval, prediction, or metric was produced.
No package was installed by the failed solve. The frozen evaluator remains
unchanged.

Verification:

```bash
PYTHONPYCACHEPREFIX=/tmp/graph_memory_pycache .venv/bin/python \
  -m unittest \
  experiments/exp_2026_07_27_locomo_stack_refactor/test_official_dragon.py -v
```

Publication gate: `continue_tooling_only`, `paper_ready=false`. O1 remains
unaccepted and M1 remains blocked. The next step is to retry the isolated
install and validate the complete runtime identity before building any cache.
