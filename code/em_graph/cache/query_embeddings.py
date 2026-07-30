"""Immutable, dataset-bound query embedding artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from em_graph.cache.text_embeddings import text_digest

QUERY_EMBEDDING_ARTIFACT_SCHEMA = "query_embedding_artifact_v1"
QUERY_EMBEDDING_ARTIFACT_SCHEMA_V2 = "query_embedding_artifact_v2"
QUERY_EMBEDDING_NORMALIZATION = "l2_float32_v1"
QUERY_EMBEDDING_NO_NORMALIZATION = "none_float32_v1"
QUERY_EMBEDDING_NORMALIZATIONS = {
    QUERY_EMBEDDING_NORMALIZATION,
    QUERY_EMBEDDING_NO_NORMALIZATION,
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def ordered_question_records(
    samples: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    return [
        {
            "sample_id": str(sample.get("sample_id") or ""),
            "qa_index": qa_index,
            "question_sha256": text_digest(str(qa.get("question") or "")),
        }
        for sample in samples
        for qa_index, qa in enumerate(sample.get("qa") or [])
    ]


@dataclass
class QueryEmbeddingArtifact:
    dataset_sha256: str
    model_name: str
    role: str
    qa_records: List[Dict[str, Any]]
    question_digests: List[str]
    vectors: np.ndarray
    normalization: str = QUERY_EMBEDDING_NORMALIZATION
    protocol_identity: Dict[str, Any] = field(default_factory=dict)
    _by_digest: Dict[str, np.ndarray] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    hits: int = field(default=0, init=False)
    misses: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.normalization not in QUERY_EMBEDDING_NORMALIZATIONS:
            raise ValueError(
                f"unsupported query normalization {self.normalization!r}"
            )
        self.protocol_identity = dict(self.protocol_identity or {})
        if (
            self.normalization == QUERY_EMBEDDING_NORMALIZATION
            and self.protocol_identity
        ):
            raise ValueError(
                "v1 L2 query artifacts cannot carry protocol_identity"
            )
        if (
            self.normalization == QUERY_EMBEDDING_NO_NORMALIZATION
            and not self.protocol_identity
        ):
            raise ValueError(
                "raw query artifacts require protocol_identity"
            )
        self.vectors = np.asarray(self.vectors, dtype=np.float32)
        if self.vectors.ndim != 2:
            raise ValueError("query embedding vectors must be a matrix")
        if len(self.question_digests) != int(self.vectors.shape[0]):
            raise ValueError("query digest/vector length mismatch")
        if len(set(self.question_digests)) != len(self.question_digests):
            raise ValueError("duplicate unique-question digest")
        if not np.isfinite(self.vectors).all():
            raise ValueError("query embedding artifact has non-finite vectors")
        if (
            self.vectors.size
            and self.normalization == QUERY_EMBEDDING_NORMALIZATION
        ):
            norms = np.linalg.norm(self.vectors.astype(np.float64), axis=1)
            if not np.allclose(norms, 1.0, rtol=0.0, atol=1e-4):
                raise ValueError("query embedding vectors are not L2 normalized")
        available = set(self.question_digests)
        missing = [
            record["question_sha256"]
            for record in self.qa_records
            if record.get("question_sha256") not in available
        ]
        if missing:
            raise ValueError(
                f"query artifact QA coverage missing {len(missing)} rows"
            )
        self._by_digest = {
            digest: np.asarray(vector, dtype=np.float32).reshape(-1)
            for digest, vector in zip(self.question_digests, self.vectors)
        }

    @property
    def vector_dimension(self) -> int:
        return int(self.vectors.shape[1]) if self.vectors.ndim == 2 else 0

    @property
    def ordered_qa_sha256(self) -> str:
        return _canonical_sha256(self.qa_records)

    @property
    def artifact_schema(self) -> str:
        return (
            QUERY_EMBEDDING_ARTIFACT_SCHEMA
            if self.normalization == QUERY_EMBEDDING_NORMALIZATION
            else QUERY_EMBEDDING_ARTIFACT_SCHEMA_V2
        )

    def validate_exact_dataset(
        self,
        samples: Sequence[Mapping[str, Any]],
        *,
        dataset_sha256: str,
        model_name: str,
        role: str,
        normalization: str = QUERY_EMBEDDING_NORMALIZATION,
        protocol_identity: Optional[Mapping[str, Any]] = None,
    ) -> None:
        expected_records = ordered_question_records(samples)
        failures = []
        if self.dataset_sha256 != str(dataset_sha256):
            failures.append("dataset SHA-256")
        if self.model_name != str(model_name):
            failures.append("embedding model")
        if self.role != str(role):
            failures.append("embedding role")
        if self.normalization != str(normalization):
            failures.append("normalization")
        if (
            protocol_identity is not None
            and self.protocol_identity != dict(protocol_identity)
        ):
            failures.append("protocol identity")
        if self.qa_records != expected_records:
            failures.append("ordered QA/question digests")
        if failures:
            raise ValueError(
                "query embedding artifact identity mismatch: "
                + ", ".join(failures)
            )

    def get(self, text: str, model: str, role: str) -> np.ndarray:
        if str(model) != self.model_name or str(role) != self.role:
            self.misses += 1
            raise RuntimeError(
                "query embedding artifact model/role mismatch: "
                f"want {self.model_name}/{self.role}, got {model}/{role}"
            )
        digest = text_digest(str(text or ""))
        vector = self._by_digest.get(digest)
        if vector is None:
            self.misses += 1
            raise RuntimeError(
                f"query embedding artifact miss for SHA-256 {digest}"
            )
        self.hits += 1
        return vector.copy()

    def usage(
        self,
        *,
        qa_count: int,
        required_lookup_count: int,
    ) -> Dict[str, Any]:
        return {
            "schema": "query_embedding_usage_v1",
            "qa_count": int(qa_count),
            "required_lookup_count": int(required_lookup_count),
            "lookup_count": int(self.hits + self.misses),
            "cache_hits": int(self.hits),
            "cache_misses": int(self.misses),
            "live_embedding_requests": 0,
            "status": (
                "pass"
                if self.misses == 0
                and self.hits >= int(required_lookup_count)
                else "fail"
            ),
        }

    def identity(self, path: Path) -> Dict[str, Any]:
        resolved = path.resolve()
        identity = {
            "schema": self.artifact_schema,
            "path": str(resolved),
            "sha256": _sha256_file(resolved),
            "dataset_sha256": self.dataset_sha256,
            "embedding_model": self.model_name,
            "role": self.role,
            "normalization": self.normalization,
            "qa_count": len(self.qa_records),
            "unique_question_count": len(self.question_digests),
            "vector_dimension": self.vector_dimension,
            "ordered_qa_sha256": self.ordered_qa_sha256,
        }
        if self.protocol_identity:
            identity["protocol_identity"] = dict(self.protocol_identity)
        return identity

    def save(self, path: Path) -> None:
        path = path.resolve()
        if path.exists():
            raise FileExistsError(
                f"query embedding artifact already exists: {path}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        sample_ids = [record["sample_id"] for record in self.qa_records]
        qa_indices = [record["qa_index"] for record in self.qa_records]
        qa_digests = [
            record["question_sha256"] for record in self.qa_records
        ]
        temp_path = None
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
                    schema=np.asarray(self.artifact_schema),
                    dataset_sha256=np.asarray(self.dataset_sha256),
                    model_name=np.asarray(self.model_name),
                    role=np.asarray(self.role),
                    normalization=np.asarray(self.normalization),
                    protocol_identity_json=np.asarray(
                        json.dumps(
                            self.protocol_identity,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                    ),
                    qa_sample_ids=np.asarray(sample_ids),
                    qa_indices=np.asarray(qa_indices, dtype=np.int64),
                    qa_question_digests=np.asarray(qa_digests),
                    question_digests=np.asarray(self.question_digests),
                    vectors=self.vectors,
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    @classmethod
    def load(cls, path: Path) -> "QueryEmbeddingArtifact":
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(
                f"query embedding artifact does not exist: {path}"
            )
        with np.load(path, allow_pickle=False) as data:
            required = {
                "schema",
                "dataset_sha256",
                "model_name",
                "role",
                "normalization",
                "qa_sample_ids",
                "qa_indices",
                "qa_question_digests",
                "question_digests",
                "vectors",
            }
            missing = sorted(required - set(data.files))
            if missing:
                raise ValueError(
                    f"query embedding artifact missing fields: {missing}"
                )
            schema = str(data["schema"])
            if schema not in {
                QUERY_EMBEDDING_ARTIFACT_SCHEMA,
                QUERY_EMBEDDING_ARTIFACT_SCHEMA_V2,
            }:
                raise ValueError(
                    f"unsupported query artifact schema {schema!r}; "
                    "delete the exact artifact and rebuild it"
                )
            if (
                schema == QUERY_EMBEDDING_ARTIFACT_SCHEMA_V2
                and "protocol_identity_json" not in data.files
            ):
                raise ValueError(
                    "v2 query artifact missing protocol_identity_json"
                )
            sample_ids = [str(value) for value in data["qa_sample_ids"]]
            qa_indices = [
                int(value) for value in data["qa_indices"].tolist()
            ]
            qa_digests = [
                str(value) for value in data["qa_question_digests"]
            ]
            if not (
                len(sample_ids) == len(qa_indices) == len(qa_digests)
            ):
                raise ValueError("query artifact ordered QA arrays mismatch")
            records = [
                {
                    "sample_id": sample_id,
                    "qa_index": qa_index,
                    "question_sha256": digest,
                }
                for sample_id, qa_index, digest in zip(
                    sample_ids,
                    qa_indices,
                    qa_digests,
                )
            ]
            normalization = str(data["normalization"])
            if (
                schema == QUERY_EMBEDDING_ARTIFACT_SCHEMA
                and normalization != QUERY_EMBEDDING_NORMALIZATION
            ):
                raise ValueError(
                    "v1 query artifact must use l2_float32_v1"
                )
            protocol_identity = (
                json.loads(str(data["protocol_identity_json"]))
                if schema == QUERY_EMBEDDING_ARTIFACT_SCHEMA_V2
                else {}
            )
            if not isinstance(protocol_identity, dict):
                raise ValueError(
                    "query artifact protocol_identity must be an object"
                )
            return cls(
                dataset_sha256=str(data["dataset_sha256"]),
                model_name=str(data["model_name"]),
                role=str(data["role"]),
                normalization=normalization,
                protocol_identity=protocol_identity,
                qa_records=records,
                question_digests=[
                    str(value) for value in data["question_digests"]
                ],
                vectors=np.asarray(data["vectors"], dtype=np.float32),
            )
