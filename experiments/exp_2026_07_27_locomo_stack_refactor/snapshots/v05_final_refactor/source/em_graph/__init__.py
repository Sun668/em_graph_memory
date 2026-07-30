"""
EM Graph — Entity–Memory conversation graph.

Layer 1:
  - normalize_dialog_text(text, dialog_time, time_words)
  - Memory nodes (1:1 with dia)
  - Entity nodes (extracted after evidence-preserving normalization)
  - Mentions edges Entity ↔ Memory
  - Sequence edges Memory ↔ Memory (NEXT/PREV by parsed session datetime)

Retrieval: Entity BM25 soft-match gate (+±1 sequence) fused with embedding
as ``0.30 * entity + 0.70 * semantic``.

Independent of ``graph_memory``.
"""

from em_graph.build.builder import (
    assert_bipartite,
    build_em_graph,
    build_em_graph_from_file,
    ensure_memory_sequence_edges,
)
from em_graph.build.config import EMGraphConfig
from em_graph.build.entity_extractor import EntityExtractor, ExtractedEntity
from em_graph.build.models import (
    EMEdge,
    EMGraph,
    EdgeType,
    EntityNode,
    MemoryEdge,
    MemoryNode,
    NodeType,
)
from em_graph.build.replace_pronouns import (
    DIALOG_NORMALIZATION_VERSION,
    normalize_dialog_text,
    replace_pronouns,
    resolve_time_word,
)
from em_graph.cache import (
    EMGraphArtifactStore,
    EntityCache,
    QuestionEntityCache,
    TextEmbeddingCache,
)
from em_graph.recall.embedding_index import MemoryEmbeddingIndex
from em_graph.recall.entity_bm25_index import EntityBM25Index
from em_graph.recall.tokenize import MEMORY_SEARCH_TEXT_VERSION, normalize_entity_key
from em_graph.recall.retrieval import (
    RETRIEVAL_SCORE_VERSION,
    expand_sequence_neighbors,
    extract_question_entity_keys,
    retrieve_dialog_ids,
)
from em_graph.recall.retrieval_audit import retrieve_dialog_ids_with_audit
from em_graph.recall.service import (
    EMGraphRecall,
    EMGraphRecallRouter,
    RecallResult,
    format_dialog,
    format_recalled_context,
)

__all__ = [
    "EMGraph",
    "EMGraphConfig",
    "MemoryNode",
    "EntityNode",
    "EMEdge",
    "MemoryEdge",
    "NodeType",
    "EdgeType",
    "EntityExtractor",
    "ExtractedEntity",
    "MemoryEmbeddingIndex",
    "TextEmbeddingCache",
    "EntityBM25Index",
    "EntityCache",
    "EMGraphArtifactStore",
    "QuestionEntityCache",
    "EMGraphRecall",
    "EMGraphRecallRouter",
    "RecallResult",
    "DIALOG_NORMALIZATION_VERSION",
    "MEMORY_SEARCH_TEXT_VERSION",
    "RETRIEVAL_SCORE_VERSION",
    "normalize_dialog_text",
    "replace_pronouns",
    "resolve_time_word",
    "build_em_graph",
    "build_em_graph_from_file",
    "ensure_memory_sequence_edges",
    "assert_bipartite",
    "extract_question_entity_keys",
    "format_dialog",
    "format_recalled_context",
    "normalize_entity_key",
    "expand_sequence_neighbors",
    "retrieve_dialog_ids",
    "retrieve_dialog_ids_with_audit",
]

__version__ = "0.4.0"
