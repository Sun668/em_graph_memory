"""Memory embedding index: OpenAI-compatible API or local DRAGON dual-encoder."""

from __future__ import annotations

import atexit
import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from em_graph.llm import set_api_key_from_env
from em_graph.models import EMGraph
from em_graph.tokenize import memory_search_text

DEFAULT_MODEL = "doubao-embedding-vision"
_API_BATCH_SIZE = 10  # Volcengine Ark embeddings API max input batch size
_LOCAL_BATCH_SIZE = 16
_MAX_RETRIES = 10
_TEXT_CACHE_VERSION = "v1"
_INDEX_FORMAT_VERSION = "v2"

# Short aliases → (query_encoder_id, context_encoder_id)
_DRAGON_MODELS = {
    "dragon": (
        "facebook/dragon-plus-query-encoder",
        "facebook/dragon-plus-context-encoder",
    ),
    "dragon+": (
        "facebook/dragon-plus-query-encoder",
        "facebook/dragon-plus-context-encoder",
    ),
    "dragon-plus": (
        "facebook/dragon-plus-query-encoder",
        "facebook/dragon-plus-context-encoder",
    ),
    "dragon-roberta": (
        "facebook/dragon-roberta-query-encoder",
        "facebook/dragon-roberta-context-encoder",
    ),
}


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return (vectors / norms).astype(np.float32)


def _batch_wait() -> float:
    return float(os.environ.get("EM_GRAPH_EMBED_WAIT", "1.0"))


def _text_digest(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:32]


def _resolve_dragon(model_name: str) -> Optional[Tuple[str, str]]:
    key = str(model_name or "").strip()
    if key in _DRAGON_MODELS:
        return _DRAGON_MODELS[key]
    if key.startswith("facebook/dragon-plus"):
        return _DRAGON_MODELS["dragon-plus"]
    if key.startswith("facebook/dragon-roberta"):
        return _DRAGON_MODELS["dragon-roberta"]
    return None


class TextEmbeddingCache:
    """Disk KV for L2-normalized embeddings: model + role + text hash → vector.

    Stored as one ``.npz`` with string ``keys`` and float32 ``vectors`` (n, d).
    """

    def __init__(self, cache_file: Optional[str] = None, flush_every: int = 20):
        if cache_file is None:
            cache_file = os.path.join(
                os.path.dirname(__file__), "cache", "text_embed_cache.npz"
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
        return f"{_TEXT_CACHE_VERSION}::{model}::{role}::{_text_digest(text)}"

    def _load(self) -> None:
        path = Path(self.cache_file)
        if not path.exists():
            return
        try:
            data = np.load(path, allow_pickle=True)
            keys = [str(x) for x in data["keys"].tolist()]
            vectors = np.asarray(data["vectors"], dtype=np.float32)
            if keys and (vectors.ndim != 2 or vectors.shape[0] != len(keys)):
                raise ValueError(
                    f"bad text cache shape keys={len(keys)} vectors={vectors.shape}"
                )
            for key, vec in zip(keys, vectors):
                self._cache[key] = np.asarray(vec, dtype=np.float32).reshape(-1)
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
                for i, key in enumerate(keys):
                    vec = self._cache[key]
                    if int(vec.shape[0]) != dim:
                        raise ValueError(
                            f"mixed embedding dims in text cache: {dim} vs {vec.shape[0]}"
                        )
                    vectors[i] = vec
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

    def set(self, text: str, model: str, role: str, vector: np.ndarray) -> None:
        self.set_many([text], model, role, np.asarray(vector, dtype=np.float32))

    def set_many(
        self,
        texts: Sequence[str],
        model: str,
        role: str,
        vectors: np.ndarray,
    ) -> None:
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if len(texts) != arr.shape[0]:
            raise ValueError("texts/vectors length mismatch")
        with self._lock:
            for text, vec in zip(texts, arr):
                self._cache[self.cache_key(text, model, role)] = np.asarray(
                    vec, dtype=np.float32
                ).reshape(-1)
            self._dirty += len(texts)
            should_flush = self._dirty >= self.flush_every
        if should_flush:
            self.flush()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


@dataclass
class MemoryEmbeddingIndex:
    memory_ids: List[str]
    vectors: np.ndarray  # (n, d) L2-normalized
    model_name: str
    text_digests: List[str] = field(default_factory=list)
    use_text_cache: bool = True
    _client: Any = field(default=None, repr=False, compare=False)
    _dragon: Any = field(default=None, repr=False, compare=False)
    _text_cache: Any = field(default=None, repr=False, compare=False)

    def _is_dragon(self) -> bool:
        return _resolve_dragon(self.model_name) is not None

    def _get_client(self):
        if self._client is None:
            set_api_key_from_env()
            from openai import OpenAI

            self._client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=os.environ.get("OPENAI_BASE_URL") or None,
                timeout=float(os.environ.get("EM_GRAPH_EMBED_TIMEOUT", "180")),
            )
        return self._client

    def _get_dragon(self):
        if self._dragon is not None:
            return self._dragon
        resolved = _resolve_dragon(self.model_name)
        if resolved is None:
            raise RuntimeError(f"Not a DRAGON model: {self.model_name}")
        q_id, c_id = resolved
        import torch
        from transformers import AutoModel, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading DRAGON on {device}: query={q_id}", flush=True)
        tokenizer = AutoTokenizer.from_pretrained(q_id)
        query_encoder = AutoModel.from_pretrained(q_id).to(device).eval()
        context_encoder = AutoModel.from_pretrained(c_id).to(device).eval()
        self._dragon = {
            "tokenizer": tokenizer,
            "query": query_encoder,
            "context": context_encoder,
            "device": device,
            "torch": torch,
        }
        return self._dragon

    def _get_text_cache(self) -> TextEmbeddingCache:
        if self._text_cache is None:
            self._text_cache = TextEmbeddingCache()
        return self._text_cache

    def _embed_batch_api(self, batch: Sequence[str]) -> np.ndarray:
        from openai import APIConnectionError, APITimeoutError, RateLimitError

        client = self._get_client()
        last_err: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = client.embeddings.create(
                    model=self.model_name, input=list(batch)
                )
                ordered = sorted(resp.data, key=lambda row: row.index)
                return np.asarray(
                    [row.embedding for row in ordered], dtype=np.float32
                )
            except (RateLimitError, APIConnectionError, APITimeoutError) as exc:
                last_err = exc
                sleep_s = min(45.0, (2**attempt) * 0.75)
                print(
                    f"  embed retry {attempt + 1}/{_MAX_RETRIES} "
                    f"({type(exc).__name__}); sleep {sleep_s:.1f}s",
                    flush=True,
                )
                time.sleep(sleep_s)
        raise RuntimeError(
            f"Embedding failed after {_MAX_RETRIES} retries"
        ) from last_err

    def _embed_batch_dragon(
        self, batch: Sequence[str], *, role: str
    ) -> np.ndarray:
        pack = self._get_dragon()
        torch = pack["torch"]
        encoder = pack["query"] if role == "query" else pack["context"]
        tokenizer = pack["tokenizer"]
        device = pack["device"]
        inputs = tokenizer(
            list(batch),
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = encoder(**inputs).last_hidden_state[:, 0, :]
        return out.detach().cpu().numpy().astype(np.float32)

    def _embed_texts(
        self,
        texts: Sequence[str],
        *,
        role: str = "context",
        show_progress: bool = False,
        text_cache: Optional[TextEmbeddingCache] = None,
    ) -> np.ndarray:
        """Embed texts; fill from ``text_cache`` when provided."""
        cleaned = [str(t or " ").strip() or " " for t in texts]
        if not cleaned:
            return np.zeros((0, 0), dtype=np.float32)

        out: List[Optional[np.ndarray]] = [None] * len(cleaned)
        miss_idx: List[int] = []
        for i, text in enumerate(cleaned):
            hit = (
                text_cache.get(text, self.model_name, role)
                if text_cache is not None
                else None
            )
            if hit is not None:
                out[i] = hit
            else:
                miss_idx.append(i)

        if show_progress:
            n_hit = len(cleaned) - len(miss_idx)
            print(
                f"  text-cache hits {n_hit}/{len(cleaned)}; "
                f"embedding {len(miss_idx)} misses",
                flush=True,
            )

        if miss_idx:
            local = self._is_dragon()
            batch_size = _LOCAL_BATCH_SIZE if local else _API_BATCH_SIZE
            wait_s = 0.0 if local else _batch_wait()
            for start in range(0, len(miss_idx), batch_size):
                batch_ids = miss_idx[start : start + batch_size]
                batch = [cleaned[i] for i in batch_ids]
                raw = (
                    self._embed_batch_dragon(batch, role=role)
                    if local
                    else self._embed_batch_api(batch)
                )
                normed = _l2_normalize(raw)
                for j, i in enumerate(batch_ids):
                    out[i] = normed[j]
                if text_cache is not None:
                    text_cache.set_many(batch, self.model_name, role, normed)
                done = min(start + len(batch_ids), len(miss_idx))
                if show_progress:
                    print(
                        f"  embedded misses {done}/{len(miss_idx)}",
                        flush=True,
                    )
                if wait_s > 0 and done < len(miss_idx):
                    time.sleep(wait_s)
            if text_cache is not None:
                text_cache.flush()

        return np.stack(
            [np.asarray(v, dtype=np.float32) for v in out], axis=0
        ).astype(np.float32)

    def _embed_query(self, query: str) -> np.ndarray:
        text = str(query or "")
        role = "query" if self._is_dragon() else "context"
        cache = self._get_text_cache() if self.use_text_cache else None
        if cache is not None:
            hit = cache.get(text, self.model_name, role)
            if hit is not None:
                return hit
        q = self._embed_texts([text], role=role, text_cache=cache)[0]
        if not self._is_dragon():
            wait_s = _batch_wait()
            if wait_s > 0:
                time.sleep(min(wait_s, 0.35))
        return q

    def _seed_text_cache(
        self,
        texts: Sequence[str],
        text_cache: TextEmbeddingCache,
        *,
        role: str = "context",
    ) -> None:
        """Copy index vectors into the shared text cache (misses only)."""
        if (
            self.vectors.size == 0
            or len(texts) != len(self.memory_ids)
            or len(texts) != int(self.vectors.shape[0])
        ):
            return
        miss_texts: List[str] = []
        miss_vecs: List[np.ndarray] = []
        for text, vec in zip(texts, self.vectors):
            if text_cache.get(text, self.model_name, role) is None:
                miss_texts.append(str(text))
                miss_vecs.append(np.asarray(vec, dtype=np.float32))
        if not miss_texts:
            return
        text_cache.set_many(
            miss_texts, self.model_name, role, np.stack(miss_vecs, axis=0)
        )
        text_cache.flush()

    def matches(
        self,
        *,
        model_name: str,
        memory_ids: Sequence[str],
        text_digests: Sequence[str],
    ) -> bool:
        return (
            self.model_name == model_name
            and self.memory_ids == list(memory_ids)
            and self.text_digests == list(text_digests)
            and len(self.text_digests) == len(self.memory_ids)
            and int(self.vectors.shape[0]) == len(self.memory_ids)
        )

    @classmethod
    def build(
        cls,
        graph: EMGraph,
        *,
        model_name: str = DEFAULT_MODEL,
        cache_path: Optional[str] = None,
        text_cache: Optional[TextEmbeddingCache] = None,
        use_text_cache: bool = True,
    ) -> "MemoryEmbeddingIndex":
        memories = sorted(graph.memories.values(), key=lambda m: m.id)
        texts = [memory_search_text(m) or m.dia_id for m in memories]
        memory_ids = [m.id for m in memories]
        digests = [_text_digest(t) for t in texts]
        shared_cache = text_cache
        if shared_cache is None and use_text_cache:
            shared_cache = TextEmbeddingCache()

        if cache_path and Path(cache_path).exists():
            loaded = cls.load(cache_path)
            if loaded is not None and loaded.matches(
                model_name=model_name,
                memory_ids=memory_ids,
                text_digests=digests,
            ):
                loaded.use_text_cache = use_text_cache
                loaded._text_cache = shared_cache
                if shared_cache is not None:
                    loaded._seed_text_cache(texts, shared_cache, role="context")
                print(f"Reusing embedding cache {cache_path}", flush=True)
                return loaded
            print(
                f"Embedding cache stale ({cache_path}); rebuilding",
                flush=True,
            )

        print(f"Embedding {len(texts)} memories with {model_name} ...", flush=True)
        index = cls(
            memory_ids=memory_ids,
            vectors=np.zeros((0, 0), dtype=np.float32),
            model_name=model_name,
            text_digests=digests,
            use_text_cache=use_text_cache,
            _text_cache=shared_cache,
        )
        index.vectors = index._embed_texts(
            texts,
            role="context",
            show_progress=True,
            text_cache=shared_cache,
        )
        if cache_path:
            index.save(cache_path)
            print(f"wrote embedding cache {cache_path}", flush=True)
        return index

    def save(self, path: str) -> None:
        if len(self.text_digests) != len(self.memory_ids):
            raise ValueError("text_digests must align with memory_ids")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            format_version=np.array(_INDEX_FORMAT_VERSION),
            memory_ids=np.array(self.memory_ids, dtype=object),
            vectors=self.vectors,
            model_name=np.array(self.model_name),
            text_digests=np.array(self.text_digests, dtype=object),
        )

    @classmethod
    def load(cls, path: str) -> Optional["MemoryEmbeddingIndex"]:
        """Load a v2 index snapshot; return None if format is unsupported."""
        try:
            data = np.load(path, allow_pickle=True)
        except Exception as exc:
            print(f"Warning: failed to load embedding index {path}: {exc}")
            return None
        version = (
            str(data["format_version"])
            if "format_version" in data.files
            else ""
        )
        if version != _INDEX_FORMAT_VERSION:
            print(
                f"Warning: unsupported embedding index format "
                f"{version!r} at {path} (want {_INDEX_FORMAT_VERSION})",
                flush=True,
            )
            return None
        if "text_digests" not in data.files:
            print(
                f"Warning: embedding index missing text_digests: {path}",
                flush=True,
            )
            return None
        memory_ids = [str(x) for x in data["memory_ids"].tolist()]
        digests = [str(x) for x in data["text_digests"].tolist()]
        return cls(
            memory_ids=memory_ids,
            vectors=np.asarray(data["vectors"], dtype=np.float32),
            model_name=str(data["model_name"]),
            text_digests=digests,
        )

    def scores(
        self,
        query: str,
        memory_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, float]:
        """Cosine scores vs query; optionally restrict to memory_ids."""
        q = self._embed_query(query)

        if memory_ids is None:
            target_ids = self.memory_ids
            mat = self.vectors
        else:
            allowed = {str(mid) for mid in memory_ids}
            if not allowed:
                return {}
            id_to_idx = {mid: i for i, mid in enumerate(self.memory_ids)}
            idxs = [id_to_idx[mid] for mid in allowed if mid in id_to_idx]
            if not idxs:
                return {}
            target_ids = [self.memory_ids[i] for i in idxs]
            mat = self.vectors[np.asarray(idxs, dtype=np.int64)]

        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            sims = mat @ q
        sims = np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)
        return {
            mid: float(max(0.0, float(sim)))
            for mid, sim in zip(target_ids, sims)
        }
