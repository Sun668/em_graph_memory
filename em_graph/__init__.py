"""
EM Graph — Entity–Memory conversation graph.

Layer 1:
  - replace_pronouns(text, speaker, dialog_time, time_words)
  - Memory nodes (1:1 with dia)
  - Entity nodes (extracted after replace_pronouns)
  - Mentions edges Entity ↔ Memory
  - Sequence edges Memory ↔ Memory (NEXT/PREV in dialog order)

Retrieval: Entity BM25 soft-match gate (+±1 sequence) fused with embedding
as ``0.30 * entity + 0.70 * semantic``.

Independent of ``graph_memory``.
"""

from em_graph.builder import (
    assert_bipartite,
    build_em_graph,
    build_em_graph_from_file,
    ensure_memory_sequence_edges,
)
from em_graph.config import EMGraphConfig
from em_graph.embedding_index import MemoryEmbeddingIndex, TextEmbeddingCache
from em_graph.entity_bm25_index import EntityBM25Index
from em_graph.entity_extractor import EntityExtractor, ExtractedEntity
from em_graph.models import (
    EMEdge,
    EMGraph,
    EdgeType,
    EntityNode,
    MemoryEdge,
    MemoryNode,
    NodeType,
)
from em_graph.replace_pronouns import replace_pronouns, resolve_time_word
from em_graph.tokenize import normalize_entity_key
from em_graph.retrieval import (
    expand_sequence_neighbors,
    extract_question_entity_keys,
    retrieve_dialog_ids,
)
from em_graph.retrieval_audit import retrieve_dialog_ids_with_audit

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
    "replace_pronouns",
    "resolve_time_word",
    "build_em_graph",
    "build_em_graph_from_file",
    "ensure_memory_sequence_edges",
    "assert_bipartite",
    "extract_question_entity_keys",
    "normalize_entity_key",
    "expand_sequence_neighbors",
    "retrieve_dialog_ids",
    "retrieve_dialog_ids_with_audit",
]

__version__ = "0.3.5"
