"""Version-addressed paths for graph and recall artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


def _identity_digest(identity: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(identity),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_name(value: str) -> str:
    cleaned = "".join(
        character if character.isalnum() or character in "-_." else "_"
        for character in str(value)
    )
    return cleaned.strip("._") or "unnamed"


@dataclass(frozen=True)
class EMGraphArtifactStore:
    """Centralize generated artifact locations outside source packages."""

    root: Path

    @classmethod
    def from_env(cls, root: Optional[str] = None) -> "EMGraphArtifactStore":
        configured = root or os.environ.get(
            "EM_GRAPH_CACHE_DIR",
            "outputs/em_graph",
        )
        return cls(Path(configured).resolve())

    def graph_path(
        self,
        sample_id: str,
        *,
        identity: Mapping[str, Any],
    ) -> Path:
        digest = _identity_digest(identity)
        return (
            self.root
            / "graphs"
            / f"{_safe_name(sample_id)}_{digest}.json"
        )

    def embedding_index_path(
        self,
        sample_id: str,
        *,
        identity: Mapping[str, Any],
    ) -> Path:
        digest = _identity_digest(identity)
        return (
            self.root
            / "embedding_indexes"
            / f"{_safe_name(sample_id)}_{digest}.npz"
        )

    def text_embedding_cache_path(self, model: str) -> Path:
        return (
            self.root
            / "text_embeddings"
            / f"{_safe_name(model)}.npz"
        )

    def entity_cache_path(self) -> Path:
        return self.root / "entities" / "conversation_entities.json"

    def question_extraction_cache_path(self) -> Path:
        return self.root / "entities" / "question_extraction_raw.json"

    def question_entity_cache_path(self) -> Path:
        return self.root / "entities" / "question_entities.json"
