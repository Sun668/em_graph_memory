"""Layer-1 retrieval: Entity BM25 gate + embedding over Memory nodes.

Default fusion: ``0.30 * entity + 0.70 * embedding``.

Diagnostic audit lives in ``em_graph.retrieval_audit`` so this module stays
focused on the production ranking path.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from em_graph.embedding_index import MemoryEmbeddingIndex
from em_graph.entity_bm25_index import EntityBM25Index
from em_graph.entity_extractor import EntityExtractor, ExtractedEntity
from em_graph.models import EMGraph
from em_graph.tokenize import normalize_entity_key

_WHO_ONLY_DAMPEN = 0.25
_SEQUENCE_SECONDARY_SCALE = 0.5
_DEFAULT_ENTITY_WEIGHT = 0.30
_DEFAULT_SEMANTIC_WEIGHT = 0.70


def entity_keys_from_extracted(entities: Iterable[ExtractedEntity]) -> Set[str]:
    keys: Set[str] = set()
    for entity in entities:
        key = normalize_entity_key(entity.value)
        if key:
            keys.add(key)
    return keys


def extract_question_entity_keys(
    question: str,
    extractor: Optional[EntityExtractor] = None,
) -> Set[str]:
    text = str(question or "").strip()
    if not text:
        return set()
    extractor = extractor or EntityExtractor()
    return entity_keys_from_extracted(extractor.extract(text))


def _entity_degrees(graph: EMGraph) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for edge in graph.edges:
        counts[edge.entity_id] += 1
    return dict(counts)


def _is_who_entity(entity_type: str) -> bool:
    return str(entity_type or "").strip().lower() == "who"


def _degree_weight(degree: int) -> float:
    return 1.0 / math.log1p(float(max(int(degree), 1)))


def _normalize_q_entity_keys(
    question: str,
    *,
    extractor: Optional[EntityExtractor],
    q_entity_keys: Optional[Set[str]],
) -> Set[str]:
    if q_entity_keys is None:
        return extract_question_entity_keys(question, extractor=extractor)
    return {
        normalize_entity_key(k) for k in q_entity_keys if normalize_entity_key(k)
    }


def _entity_memory_scores(
    graph: EMGraph,
    q_entity_keys: Set[str],
    *,
    entity_bm25_index: EntityBM25Index,
) -> Dict[str, float]:
    """BM25 soft-match q keys → entities → Memory seed scores."""
    if not q_entity_keys:
        return {}

    entity_to_q_scores = entity_bm25_index.match_q_keys(q_entity_keys)
    if not entity_to_q_scores:
        return {}

    effective = {qk for scores in entity_to_q_scores.values() for qk in scores}
    if not effective:
        return {}

    denom = float(len(effective))
    degrees = _entity_degrees(graph)
    entity_raw: Dict[str, float] = {}
    for eid, q_scores in entity_to_q_scores.items():
        strength = sum(float(v) for v in q_scores.values()) / denom
        entity_raw[eid] = strength * _degree_weight(degrees.get(eid, 1))

    who_q_keys: Set[str] = set()
    for eid, q_scores in entity_to_q_scores.items():
        ent = graph.entities.get(eid)
        if ent is not None and _is_who_entity(ent.type):
            who_q_keys |= set(q_scores.keys())

    who_scores: Dict[str, float] = defaultdict(float)
    content_scores: Dict[str, float] = defaultdict(float)
    for edge in graph.edges:
        e_score = entity_raw.get(edge.entity_id)
        if not e_score:
            continue
        scored = float(e_score) * float(edge.weight or 1.0)
        ent = graph.entities.get(edge.entity_id)
        matched_qs = set(entity_to_q_scores.get(edge.entity_id, {}))
        who_like = (ent is not None and _is_who_entity(ent.type)) or (
            bool(matched_qs) and matched_qs <= who_q_keys
        )
        if who_like:
            who_scores[edge.memory_id] = max(who_scores[edge.memory_id], scored)
        else:
            content_scores[edge.memory_id] = max(
                content_scores[edge.memory_id], scored
            )

    out: Dict[str, float] = {}
    for mid in set(who_scores) | set(content_scores):
        content_e = content_scores.get(mid, 0.0)
        who_e = who_scores.get(mid, 0.0)
        if content_e > 0.0:
            out[mid] = max(content_e, who_e)
        else:
            out[mid] = who_e * _WHO_ONLY_DAMPEN
    return out


def _memory_adjacency(graph: EMGraph) -> Dict[str, List[str]]:
    adj: Dict[str, List[str]] = defaultdict(list)
    for edge in graph.memory_edges:
        if edge.src_memory_id in graph.memories and edge.dst_memory_id in graph.memories:
            adj[edge.src_memory_id].append(edge.dst_memory_id)
    return adj


def expand_sequence_neighbors(
    seed_scores: Dict[str, float],
    graph: EMGraph,
    *,
    secondary_scale: float = _SEQUENCE_SECONDARY_SCALE,
) -> Dict[str, float]:
    """Add ±1 dialog-order neighbors of seeds at half weight (one hop)."""
    if not seed_scores:
        return {}
    scale = float(secondary_scale)
    if scale <= 0.0:
        return dict(seed_scores)

    adj = _memory_adjacency(graph)
    out = dict(seed_scores)
    for mid, score in seed_scores.items():
        if score <= 0.0:
            continue
        secondary = float(score) * scale
        for neigh in adj.get(mid, []):
            out[neigh] = max(out.get(neigh, 0.0), secondary)
    return out


def retrieve_dialog_ids(
    graph: EMGraph,
    question: str,
    top_k: int = 8,
    *,
    embedding_index: MemoryEmbeddingIndex,
    entity_bm25_index: Optional[EntityBM25Index] = None,
    extractor: Optional[EntityExtractor] = None,
    q_entity_keys: Optional[Set[str]] = None,
    entity_weight: float = _DEFAULT_ENTITY_WEIGHT,
    semantic_weight: float = _DEFAULT_SEMANTIC_WEIGHT,
    expand_sequence: bool = True,
) -> List[Tuple[str, float]]:
    """
    Rank Memory nodes via Entity BM25 gate + embedding fusion.

    1. Soft-match q keys → Entity→Memory seeds
    2. Optionally expand ±1 conversation-order neighbors at half entity weight
    3. Score the candidate pool with embeddings (full corpus if gate empty)
    4. Fuse ``entity_weight * E + semantic_weight * S``
    """
    if not graph.memories:
        return []

    q_keys = _normalize_q_entity_keys(
        question, extractor=extractor, q_entity_keys=q_entity_keys
    )
    if q_keys:
        if entity_bm25_index is None:
            entity_bm25_index = EntityBM25Index.build(graph)
        seed_scores = _entity_memory_scores(
            graph,
            q_keys,
            entity_bm25_index=entity_bm25_index,
        )
    else:
        seed_scores = {}
    entity_scores = (
        expand_sequence_neighbors(seed_scores, graph)
        if expand_sequence
        else dict(seed_scores)
    )
    candidate_ids = set(entity_scores.keys())
    gated = bool(candidate_ids)
    score_ids = candidate_ids if gated else None

    semantic_scores = embedding_index.scores(question, memory_ids=score_ids)
    pool_ids = candidate_ids if gated else set(graph.memories.keys())

    ranked: List[Tuple[str, float]] = []
    for mid in pool_ids:
        memory = graph.memories.get(mid)
        if memory is None:
            continue
        e = float(entity_scores.get(mid, 0.0))
        s = float(semantic_scores.get(mid, 0.0))
        if e <= 0.0 and s <= 0.0:
            continue
        score = float(entity_weight) * e + float(semantic_weight) * s
        ranked.append((memory.dia_id, score))

    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[: max(int(top_k), 0)]
