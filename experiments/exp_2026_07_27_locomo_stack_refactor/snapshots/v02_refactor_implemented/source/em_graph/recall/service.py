"""Public QA recall service backed only by an Entity–Memory graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Set

from em_graph.build.entity_extractor import EntityExtractor
from em_graph.build.models import EMGraph, MemoryNode
from em_graph.cache.question_entities import QuestionEntityCache
from em_graph.recall.embedding_index import MemoryEmbeddingIndex
from em_graph.recall.entity_bm25_index import EntityBM25Index
from em_graph.recall.retrieval import (
    extract_question_entity_keys,
    retrieve_dialog_ids,
)


@dataclass(frozen=True)
class RecallResult:
    """Reader-ready context and the corresponding dialog evidence ids."""

    context: str
    context_ids: Sequence[str]


def format_dialog(memory: MemoryNode) -> str:
    """Format a retrieved dialog exactly as LoCoMo dialog RAG does."""
    line = f'{memory.speaker} said, "{memory.text}"'
    caption = str(memory.blip_caption or "").strip()
    if caption:
        line += f" and shared {caption}"
    return line


def format_recalled_context(
    graph: EMGraph,
    dialog_ids: Sequence[str],
) -> str:
    """Add the official ``date_time: dialog`` wrapper in retrieval order."""
    by_dialog_id = {
        memory.dia_id: memory for memory in graph.memories.values()
    }
    return "\n".join(
        f"{memory.date_time}: {format_dialog(memory)}"
        for dialog_id in dialog_ids
        if (memory := by_dialog_id.get(dialog_id)) is not None
    )


class EMGraphRecall:
    """Retrieve QA evidence without implementing any evaluation metric."""

    def __init__(
        self,
        graph: EMGraph,
        embedding_index: MemoryEmbeddingIndex,
        *,
        entity_bm25_index: Optional[EntityBM25Index] = None,
        extractor: Optional[EntityExtractor] = None,
        question_cache: Optional[QuestionEntityCache] = None,
        entity_weight: float = 0.30,
        semantic_weight: float = 0.70,
        expand_sequence: bool = True,
        force_full_pool: bool = False,
    ):
        self.graph = graph
        self.embedding_index = embedding_index
        self.entity_weight = float(entity_weight)
        self.semantic_weight = float(semantic_weight)
        self.expand_sequence = bool(expand_sequence)
        self.force_full_pool = bool(force_full_pool)
        self.extractor = extractor
        self.question_cache = question_cache
        if not self.force_full_pool and self.extractor is None:
            raise ValueError(
                "entity-gated recall requires an explicit question extractor"
            )
        self.entity_bm25_index = (
            entity_bm25_index
            if entity_bm25_index is not None
            else (
                EntityBM25Index.build(graph)
                if not self.force_full_pool and graph.entities
                else None
            )
        )

    def _question_keys(
        self,
        sample_id: str,
        qa_index: int,
        question: str,
    ) -> Set[str]:
        if self.force_full_pool:
            return set()
        if self.question_cache is not None:
            cached = self.question_cache.get(
                sample_id,
                qa_index,
                question,
            )
            if cached is not None:
                return cached
        keys = extract_question_entity_keys(
            question,
            extractor=self.extractor,
        )
        if self.question_cache is not None:
            self.question_cache.set(
                sample_id,
                qa_index,
                question,
                keys,
            )
        return keys

    def recall(
        self,
        sample: Mapping[str, Any],
        qa_index: int,
        question: str,
        top_k: int,
    ) -> RecallResult:
        sample_id = str(sample.get("sample_id") or "")
        if sample_id != self.graph.sample_id:
            raise ValueError(
                f"recall sample {sample_id!r} does not match graph "
                f"{self.graph.sample_id!r}"
            )
        question_keys = self._question_keys(
            sample_id,
            int(qa_index),
            question,
        )
        ranked = retrieve_dialog_ids(
            self.graph,
            question,
            top_k=int(top_k),
            embedding_index=self.embedding_index,
            entity_bm25_index=self.entity_bm25_index,
            extractor=self.extractor,
            q_entity_keys=question_keys,
            entity_weight=self.entity_weight,
            semantic_weight=self.semantic_weight,
            expand_sequence=self.expand_sequence,
        )
        dialog_ids = [dialog_id for dialog_id, _score in ranked]
        return RecallResult(
            context=format_recalled_context(self.graph, dialog_ids),
            context_ids=dialog_ids,
        )


class EMGraphRecallRouter:
    """Route each LoCoMo sample to its conversation-specific recall service."""

    def __init__(self, recalls: Mapping[str, EMGraphRecall]):
        self._recalls = dict(recalls)

    def recall(
        self,
        sample: Mapping[str, Any],
        qa_index: int,
        question: str,
        top_k: int,
    ) -> RecallResult:
        sample_id = str(sample.get("sample_id") or "")
        try:
            recall = self._recalls[sample_id]
        except KeyError as exc:
            raise KeyError(f"no EM graph recall registered for {sample_id}") from exc
        return recall.recall(sample, qa_index, question, top_k)
