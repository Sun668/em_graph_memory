"""Versioned cache for conversation-derived entity extraction."""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from em_graph.build.config import ENTITY_EXTRACT_VERSION


class EntityCache:
    """JSON cache keyed by extract version, model, and full text digest."""

    def __init__(self, cache_file: Optional[str] = None, flush_every: int = 20):
        if cache_file is None:
            cache_file = str(
                Path(os.environ.get("EM_GRAPH_CACHE_DIR", "outputs/em_graph"))
                / "entity_cache.json"
            )
        self.cache_file = os.path.abspath(cache_file)
        self.flush_every = max(int(flush_every), 1)
        self._dirty = 0
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load()
        atexit.register(self.flush)

    def _load(self) -> None:
        if not os.path.exists(self.cache_file):
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as handle:
                self._cache = json.load(handle)
        except Exception as exc:
            print(f"Warning: failed to load EM entity cache: {exc}")
            self._cache = {}

    def flush(self) -> None:
        with self._lock:
            if self._dirty <= 0:
                return
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as handle:
                json.dump(self._cache, handle, indent=2, ensure_ascii=False)
            self._dirty = 0

    @staticmethod
    def _key(
        text: str,
        model: str,
        version: str = ENTITY_EXTRACT_VERSION,
    ) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{version}::{model}::{digest}"

    def get(self, text: str, model: str) -> Optional[List[Dict[str, str]]]:
        with self._lock:
            cached = self._cache.get(self._key(text, model))
        return cached if isinstance(cached, list) else None

    def set(
        self,
        text: str,
        model: str,
        entities: List[Dict[str, str]],
    ) -> None:
        with self._lock:
            self._cache[self._key(text, model)] = entities
            self._dirty += 1
            should_flush = self._dirty >= self.flush_every
        if should_flush:
            self.flush()
