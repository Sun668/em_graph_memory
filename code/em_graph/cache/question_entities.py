"""Persistent cache for entities extracted from evaluation questions."""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Dict, Iterable, Optional, Set


QUESTION_ENTITY_CACHE_VERSION = "v1_full_question_sha256"


def question_digest(question: str) -> str:
    return hashlib.sha256(str(question or "").encode("utf-8")).hexdigest()


class QuestionEntityCache:
    """Cache question entity keys without allowing QA-index-only reuse."""

    def __init__(
        self,
        cache_file: Optional[str] = None,
        *,
        namespace: str = "",
        flush_every: int = 20,
    ):
        if cache_file is None:
            cache_root = Path(
                os.environ.get("EM_GRAPH_CACHE_DIR", "outputs/em_graph")
            )
            cache_file = str(cache_root / "question_entities.json")
        self.cache_file = Path(cache_file).resolve()
        self.namespace = str(namespace or "default")
        self.flush_every = max(int(flush_every), 1)
        self._dirty = 0
        self._cache: Dict[str, list[str]] = {}
        self._lock = threading.Lock()
        self._load()
        atexit.register(self.flush)

    @staticmethod
    def cache_key(
        sample_id: str,
        qa_index: int,
        question: str,
        namespace: str = "default",
    ) -> str:
        return (
            f"{QUESTION_ENTITY_CACHE_VERSION}::{namespace}::{sample_id}::"
            f"qa{int(qa_index)}::{question_digest(question)}"
        )

    def _load(self) -> None:
        if not self.cache_file.exists():
            return
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self._cache = {
                    str(key): [str(value) for value in values]
                    for key, values in payload.items()
                    if isinstance(values, list)
                }
        except Exception as exc:
            print(f"Warning: failed to load question entity cache: {exc}")
            self._cache = {}

    def flush(self) -> None:
        with self._lock:
            if self._dirty <= 0:
                return
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._dirty = 0

    def get(
        self,
        sample_id: str,
        qa_index: int,
        question: str,
    ) -> Optional[Set[str]]:
        key = self.cache_key(
            sample_id,
            qa_index,
            question,
            self.namespace,
        )
        with self._lock:
            values = self._cache.get(key)
            return set(values) if values is not None else None

    def set(
        self,
        sample_id: str,
        qa_index: int,
        question: str,
        entity_keys: Iterable[str],
    ) -> None:
        key = self.cache_key(
            sample_id,
            qa_index,
            question,
            self.namespace,
        )
        values = sorted({str(value) for value in entity_keys if str(value)})
        with self._lock:
            self._cache[key] = values
            self._dirty += 1
            should_flush = self._dirty >= self.flush_every
        if should_flush:
            self.flush()
