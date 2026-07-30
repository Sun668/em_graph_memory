"""Model/role/text-addressed embedding cache."""

from __future__ import annotations

import atexit
import hashlib
import os
import threading
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np

TEXT_EMBEDDING_CACHE_VERSION = "v2_full_sha256"


def text_digest(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


class TextEmbeddingCache:
    """Disk KV: cache version + model + role + full text SHA-256 → vector."""

    def __init__(self, cache_file: Optional[str] = None, flush_every: int = 20):
        if cache_file is None:
            cache_file = str(
                Path(os.environ.get("EM_GRAPH_CACHE_DIR", "outputs/em_graph"))
                / "text_embed_cache.npz"
            )
        self.cache_file = os.path.abspath(cache_file)
        self.flush_every = max(int(flush_every), 1)
        self._dirty = 0
        self._cache: Dict[str, np.ndarray] = {}
        self._lock = threading.Lock()
        self._load()
        atexit.register(self.flush)

    @staticmethod
    def cache_key(text: str, model: str, role: str) -> str:
        return (
            f"{TEXT_EMBEDDING_CACHE_VERSION}::{model}::{role}::"
            f"{text_digest(text)}"
        )

    def _load(self) -> None:
        path = Path(self.cache_file)
        if not path.exists():
            return
        try:
            data = np.load(path, allow_pickle=True)
            keys = [str(value) for value in data["keys"].tolist()]
            vectors = np.asarray(data["vectors"], dtype=np.float32)
            if keys and (
                vectors.ndim != 2 or vectors.shape[0] != len(keys)
            ):
                raise ValueError(
                    f"bad text cache shape keys={len(keys)} "
                    f"vectors={vectors.shape}"
                )
            for key, vector in zip(keys, vectors):
                self._cache[key] = np.asarray(
                    vector, dtype=np.float32
                ).reshape(-1)
        except Exception as exc:
            print(f"Warning: failed to load text embed cache: {exc}")
            self._cache = {}

    def flush(self) -> None:
        with self._lock:
            if self._dirty <= 0:
                return
            path = Path(self.cache_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            keys = list(self._cache.keys())
            if keys:
                dim = int(next(iter(self._cache.values())).shape[0])
                vectors = np.zeros((len(keys), dim), dtype=np.float32)
                for index, key in enumerate(keys):
                    vector = self._cache[key]
                    if int(vector.shape[0]) != dim:
                        raise ValueError(
                            f"mixed embedding dims: {dim} vs "
                            f"{vector.shape[0]}"
                        )
                    vectors[index] = vector
            else:
                vectors = np.zeros((0, 0), dtype=np.float32)
            np.savez_compressed(
                path,
                keys=np.array(keys, dtype=object),
                vectors=vectors,
            )
            self._dirty = 0

    def get(self, text: str, model: str, role: str) -> Optional[np.ndarray]:
        key = self.cache_key(text, model, role)
        with self._lock:
            cached = self._cache.get(key)
        if cached is None:
            return None
        return np.asarray(cached, dtype=np.float32).copy()

    def set(
        self,
        text: str,
        model: str,
        role: str,
        vector: np.ndarray,
    ) -> None:
        self.set_many(
            [text],
            model,
            role,
            np.asarray(vector, dtype=np.float32),
        )

    def set_many(
        self,
        texts: Sequence[str],
        model: str,
        role: str,
        vectors: np.ndarray,
    ) -> None:
        array = np.asarray(vectors, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        if len(texts) != array.shape[0]:
            raise ValueError("texts/vectors length mismatch")
        with self._lock:
            for text, vector in zip(texts, array):
                self._cache[self.cache_key(text, model, role)] = np.asarray(
                    vector, dtype=np.float32
                ).reshape(-1)
            self._dirty += len(texts)
            should_flush = self._dirty >= self.flush_every
        if should_flush:
            self.flush()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
