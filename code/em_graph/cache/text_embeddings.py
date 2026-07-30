"""Model/role/text-addressed embedding cache."""

from __future__ import annotations

import atexit
import fcntl
import hashlib
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional, Sequence

import numpy as np

TEXT_EMBEDDING_CACHE_VERSION = "v2_full_sha256"
_PATH_LOCKS: Dict[str, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


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
        self._pending: Dict[str, np.ndarray] = {}
        self._lock = threading.Lock()
        self._load()
        atexit.register(self.flush)

    @staticmethod
    def cache_key(text: str, model: str, role: str) -> str:
        return (
            f"{TEXT_EMBEDDING_CACHE_VERSION}::{model}::{role}::"
            f"{text_digest(text)}"
        )

    @staticmethod
    def _read_path(path: Path) -> Dict[str, np.ndarray]:
        if not path.exists():
            return {}
        with np.load(path, allow_pickle=True) as data:
            if "keys" not in data.files or "vectors" not in data.files:
                raise ValueError(
                    f"text embedding cache missing keys/vectors: {path}"
                )
            keys = [str(value) for value in data["keys"].tolist()]
            vectors = np.asarray(data["vectors"], dtype=np.float32)
        if len(set(keys)) != len(keys):
            raise ValueError(f"duplicate text embedding cache keys: {path}")
        if vectors.ndim != 2 or vectors.shape[0] != len(keys):
            raise ValueError(
                f"bad text cache shape keys={len(keys)} "
                f"vectors={vectors.shape}: {path}"
            )
        if not np.isfinite(vectors).all():
            raise ValueError(f"non-finite text embedding vector: {path}")
        return {
            key: np.asarray(vector, dtype=np.float32).reshape(-1)
            for key, vector in zip(keys, vectors)
        }

    def _load(self) -> None:
        self._cache = self._read_path(Path(self.cache_file))

    @staticmethod
    def _path_lock(path: Path) -> threading.Lock:
        resolved = str(path.resolve())
        with _PATH_LOCKS_GUARD:
            lock = _PATH_LOCKS.get(resolved)
            if lock is None:
                lock = threading.Lock()
                _PATH_LOCKS[resolved] = lock
            return lock

    @staticmethod
    @contextmanager
    def _file_lock(path: Path) -> Iterator[None]:
        lock_path = path.with_suffix(f"{path.suffix}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _write_atomic(
        path: Path,
        values: Dict[str, np.ndarray],
    ) -> None:
        keys = sorted(values)
        if keys:
            dim = int(values[keys[0]].shape[0])
            vectors = np.zeros((len(keys), dim), dtype=np.float32)
            for index, key in enumerate(keys):
                vector = np.asarray(values[key], dtype=np.float32).reshape(-1)
                if int(vector.shape[0]) != dim:
                    raise ValueError(
                        f"mixed embedding dims: {dim} vs {vector.shape[0]}"
                    )
                if not np.isfinite(vector).all():
                    raise ValueError(f"non-finite embedding for cache key {key}")
                vectors[index] = vector
        else:
            vectors = np.zeros((0, 0), dtype=np.float32)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                np.savez_compressed(
                    handle,
                    keys=np.asarray(keys, dtype=object),
                    vectors=vectors,
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def flush(self) -> None:
        with self._lock:
            if not self._pending:
                return
            path = Path(self.cache_file)
            pending = {
                key: np.asarray(value, dtype=np.float32).copy()
                for key, value in self._pending.items()
            }
        path_lock = self._path_lock(path)
        with path_lock, self._file_lock(path):
            merged = self._read_path(path)
            for key, vector in pending.items():
                existing = merged.get(key)
                if existing is not None:
                    if not np.array_equal(existing, vector):
                        raise ValueError(
                            "conflicting vectors for existing text embedding "
                            f"cache key {key}"
                        )
                    continue
                merged[key] = vector
            self._write_atomic(path, merged)
        with self._lock:
            self._cache = merged
            for key, vector in pending.items():
                current = self._pending.get(key)
                if current is not None and np.array_equal(current, vector):
                    self._pending.pop(key, None)
            self._dirty = len(self._pending)

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
                key = self.cache_key(text, model, role)
                resolved = np.asarray(vector, dtype=np.float32).reshape(-1)
                if not np.isfinite(resolved).all():
                    raise ValueError(f"non-finite embedding for cache key {key}")
                existing = self._cache.get(key)
                if existing is not None and not np.array_equal(
                    existing, resolved
                ):
                    raise ValueError(
                        "conflicting vectors for existing text embedding "
                        f"cache key {key}"
                    )
                self._cache[key] = resolved
                self._pending[key] = resolved
            self._dirty = len(self._pending)
            should_flush = self._dirty >= self.flush_every
        if should_flush:
            self.flush()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
