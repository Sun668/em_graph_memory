"""ChatGPT-subscription Codex CLI completion helper.

Uses `codex exec` with the local ChatGPT login cache (~/.codex).
Does NOT use OPENAI_API_KEY / Platform billing. The subprocess env strips
OPENAI_API_KEY so Codex stays on auth_mode=chatgpt.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional


def _codex_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    # Avoid interactive / dumb-terminal surprises in automation.
    env.setdefault("TERM", "dumb")
    env.setdefault("NO_COLOR", "1")
    return env


def run_codex_completion(
    query: str,
    model: str = "gpt-5.5",
    timeout: int = 300,
    max_retries: int = 3,
    wait_time: float = 2.0,
    sandbox: str = "read-only",
) -> str:
    """Run a single text completion via Codex CLI.

    The prompt is passed on stdin. Working directory is an empty temp dir so
    the agent has nothing useful to read or edit. Final message is captured
    with ``-o``.
    """
    if not str(query or "").strip():
        raise ValueError("empty Codex prompt")

    wrapped = (
        "You are a pure text-completion engine for an offline evaluation script.\n"
        "Rules:\n"
        "1. Do not use tools, shell, search, or read any files.\n"
        "2. Do not explain your process.\n"
        "3. Reply with ONLY the completion requested by the user prompt.\n"
        "4. If the user prompt asks for JSON, return JSON only.\n\n"
        f"<user_prompt>\n{query}\n</user_prompt>\n"
    )

    last_err: Optional[str] = None
    for attempt in range(1, max_retries + 1):
        with tempfile.TemporaryDirectory(prefix="codex_llm_") as td:
            out_path = Path(td) / "last_message.txt"
            cmd = [
                "codex",
                "exec",
                "-m",
                model,
                "--sandbox",
                sandbox,
                "--skip-git-repo-check",
                "--ephemeral",
                "--ignore-user-config",
                "-C",
                td,
                "-o",
                str(out_path),
                "-",  # read prompt from stdin
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    input=wrapped,
                    capture_output=True,
                    text=True,
                    env=_codex_env(),
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                last_err = f"timeout after {timeout}s"
                print(f"Codex timeout (retry {attempt}/{max_retries}): {last_err}")
                time.sleep(min(wait_time * attempt, 30))
                continue

            text = ""
            if out_path.exists():
                text = out_path.read_text(encoding="utf-8", errors="replace").strip()
            if proc.returncode != 0 or not text:
                stderr = (proc.stderr or proc.stdout or "").strip()
                last_err = f"exit={proc.returncode}; {stderr[-800:]}"
                print(f"Codex failed (retry {attempt}/{max_retries}): {last_err}")
                time.sleep(min(wait_time * attempt, 30))
                continue
            return text

    raise RuntimeError(f"Codex completion failed after {max_retries} retries: {last_err}")


def is_codex_model(model: Optional[str]) -> bool:
    """Return True when the model should be routed through Codex CLI."""
    name = (model or "").strip().lower()
    if not name:
        return False
    # Platform API key path (e.g. env_gpt.sh → api.openai.com + sk-*).
    if os.environ.get("FORCE_OPENAI_API", "").strip() in {"1", "true", "yes"}:
        return False
    if os.environ.get("FORCE_CODEX_LLM", "").strip() in {"1", "true", "yes"}:
        return True
    base = (os.environ.get("OPENAI_BASE_URL") or "").lower()
    key = os.environ.get("OPENAI_API_KEY") or ""
    if "api.openai.com" in base and key.startswith("sk-"):
        return False
    # Explicit opt-in prefixes for subscription-path models.
    return name.startswith(("gpt-5.5", "gpt-5.4", "gpt-5.6", "gpt-4o", "o3", "o4"))
