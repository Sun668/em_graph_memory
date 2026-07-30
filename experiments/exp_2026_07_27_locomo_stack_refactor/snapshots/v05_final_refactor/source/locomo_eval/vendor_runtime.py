"""Load the byte-identical vendored LoCoMo modules with optional deps stubbed."""

from __future__ import annotations

import importlib
import sys
import types
from functools import lru_cache
from pathlib import Path
from typing import Any, Tuple

from common.llm import run_chatgpt

UPSTREAM_REPOSITORY = "https://github.com/snap-research/locomo"
UPSTREAM_COMMIT = "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376"
VENDOR_ROOT = Path(__file__).resolve().parent / "vendor" / "locomo"


class _NoopEncoding:
    def encode(self, _text: str) -> list:
        return []


def _install_runtime_adapters() -> None:
    root = str(VENDOR_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)

    if "bert_score" not in sys.modules:
        bert_score = types.ModuleType("bert_score")

        def _unsupported_bert_score(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("BERTScore is outside the LoCoMo QA F1 path")

        bert_score.score = _unsupported_bert_score  # type: ignore[attr-defined]
        sys.modules["bert_score"] = bert_score

    if "tiktoken" not in sys.modules:
        tiktoken = types.ModuleType("tiktoken")
        tiktoken.encoding_for_model = (  # type: ignore[attr-defined]
            lambda _model: _NoopEncoding()
        )
        sys.modules["tiktoken"] = tiktoken

    def _official_run_chatgpt(
        query: str,
        num_gen: int = 1,
        num_tokens_request: int = 1000,
        model: str = "chatgpt",
        use_16k: bool = False,
        temperature: float = 1.0,
        wait_time: float = 1,
    ) -> str:
        """Adapt the modern client while preserving upstream message roles."""
        return run_chatgpt(
            query,
            num_gen=num_gen,
            num_tokens_request=num_tokens_request,
            model=model,
            use_16k=use_16k,
            temperature=temperature,
            wait_time=wait_time,
            message_role="system" if model == "chatgpt" else "user",
        )

    global_methods = types.ModuleType("global_methods")
    global_methods.run_chatgpt = _official_run_chatgpt  # type: ignore[attr-defined]
    sys.modules["global_methods"] = global_methods

    rag_utils = types.ModuleType("task_eval.rag_utils")

    def _recall_must_be_injected(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Use the injected QARecall interface")

    rag_utils.get_embeddings = _recall_must_be_injected  # type: ignore[attr-defined]
    sys.modules["task_eval.rag_utils"] = rag_utils


@lru_cache(maxsize=1)
def load_official_modules() -> Tuple[Any, Any, Any]:
    _install_runtime_adapters()
    evaluation = importlib.import_module("task_eval.evaluation")
    evaluation_stats = importlib.import_module("task_eval.evaluation_stats")
    gpt_utils = importlib.import_module("task_eval.gpt_utils")
    return evaluation, evaluation_stats, gpt_utils
