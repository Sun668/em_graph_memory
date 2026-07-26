"""Minimal OpenAI-compatible chat client for EM entity extraction."""

from __future__ import annotations

import os
import time
from typing import Optional


def set_api_key_from_env() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Configure OPENAI_API_KEY / OPENAI_BASE_URL "
            "before using the EM entity extractor."
        )


def _uses_max_completion_tokens(model: str) -> bool:
    name = str(model or "").lower()
    return name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3")


def run_chat(
    query: str,
    model: Optional[str] = None,
    num_tokens_request: int = 2500,
    temperature: float = 0.3,
    wait_time: float = 0.2,
) -> str:
    set_api_key_from_env()
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The openai package is required for LLM extraction."
        ) from exc

    resolved = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
        timeout=float(os.environ.get("EM_GRAPH_LLM_TIMEOUT", "180")),
    )
    kwargs: dict = {
        "model": resolved,
        "messages": [{"role": "user", "content": query}],
    }
    if _uses_max_completion_tokens(resolved):
        # gpt-5 / o-series: max_tokens unsupported; reasoning may consume budget.
        kwargs["max_completion_tokens"] = num_tokens_request
    else:
        kwargs["max_tokens"] = num_tokens_request
        kwargs["temperature"] = temperature
    response = client.chat.completions.create(**kwargs)
    if wait_time:
        time.sleep(wait_time)
    message = response.choices[0].message
    content = message.content or ""
    if not str(content).strip():
        raise RuntimeError(
            f"Empty content for model={resolved}; raise num_tokens_request "
            f"(current={num_tokens_request})."
        )
    return content
