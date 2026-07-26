"""Diagnostic retrieval audit (not on the production ranking path).

Use ``retrieve_dialog_ids_with_audit`` from fail-case / viz tools only.
Production callers should use ``em_graph.retrieval.retrieve_dialog_ids``.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from em_graph.embedding_index import MemoryEmbeddingIndex
from em_graph.entity_bm25_index import EntityBM25Index
from em_graph.entity_extractor import EntityExtractor
from em_graph.models import EMGraph
from em_graph.retrieval import (
    _DEFAULT_ENTITY_WEIGHT,
    _DEFAULT_SEMANTIC_WEIGHT,
    _degree_weight,
    _entity_degrees,
    _entity_memory_scores,
    _normalize_q_entity_keys,
    expand_sequence_neighbors,
)


def retrieve_dialog_ids_with_audit(
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
) -> Tuple[List[Tuple[str, float]], Dict[str, object]]:
    """Rank Memory nodes and return per-step audit for diagnostics.

    Audit includes extracted q keys, BM25-selected entities with match
    scores, and per-ranked-dialog entity / embedding / fusion scores.
    """
    if not graph.memories:
        return [], {
            "q_entity_keys": [],
            "bm25_matched_entities": [],
            "gated": False,
            "entity_weight": float(entity_weight),
            "semantic_weight": float(semantic_weight),
            "ranked": [],
        }

    q_keys = _normalize_q_entity_keys(
        question, extractor=extractor, q_entity_keys=q_entity_keys
    )
    if entity_bm25_index is None:
        entity_bm25_index = EntityBM25Index.build(graph)

    entity_to_q_scores = (
        entity_bm25_index.match_q_keys(q_keys) if q_keys else {}
    )
    degrees = _entity_degrees(graph)
    denom = float(
        len({qk for scores in entity_to_q_scores.values() for qk in scores}) or 1
    )
    bm25_entities: List[Dict[str, object]] = []
    for eid, q_scores in sorted(
        entity_to_q_scores.items(),
        key=lambda item: (
            -sum(float(v) for v in item[1].values()),
            item[0],
        ),
    ):
        ent = graph.entities.get(eid)
        strength = sum(float(v) for v in q_scores.values()) / denom
        degree = int(degrees.get(eid, 1))
        bm25_entities.append(
            {
                "entity_id": eid,
                "value": ent.value if ent is not None else "",
                "type": ent.type if ent is not None else "",
                "key": ent.key if ent is not None else "",
                "match_scores": {
                    str(qk): float(sc) for qk, sc in sorted(q_scores.items())
                },
                "best_match_score": float(max(q_scores.values()) if q_scores else 0.0),
                "match_strength": float(strength),
                "degree": degree,
                "degree_weight": float(_degree_weight(degree)),
                "entity_raw_score": float(strength * _degree_weight(degree)),
            }
        )

    seed_scores = _entity_memory_scores(
        graph,
        q_keys,
        entity_bm25_index=entity_bm25_index,
    )
    entity_scores = expand_sequence_neighbors(seed_scores, graph)
    candidate_ids = set(entity_scores.keys())
    gated = bool(candidate_ids)
    score_ids = candidate_ids if gated else None

    semantic_scores = embedding_index.scores(question, memory_ids=score_ids)
    pool_ids = candidate_ids if gated else set(graph.memories.keys())

    ranked_rows: List[Dict[str, object]] = []
    ranked: List[Tuple[str, float]] = []
    for mid in pool_ids:
        memory = graph.memories.get(mid)
        if memory is None:
            continue
        seed_e = float(seed_scores.get(mid, 0.0))
        e = float(entity_scores.get(mid, 0.0))
        s = float(semantic_scores.get(mid, 0.0))
        if e <= 0.0 and s <= 0.0:
            continue
        score = float(entity_weight) * e + float(semantic_weight) * s
        ranked.append((memory.dia_id, score))
        ranked_rows.append(
            {
                "dia_id": memory.dia_id,
                "memory_id": mid,
                "fusion_score": score,
                "entity_score": e,
                "seed_entity_score": seed_e,
                "embedding_score": s,
                "via_sequence_only": bool(seed_e <= 0.0 and e > 0.0),
                "speaker": memory.speaker,
                "text": memory.text_normalized or memory.text,
            }
        )

    ranked.sort(key=lambda item: (-item[1], item[0]))
    ranked_rows.sort(
        key=lambda row: (
            -float(row["fusion_score"]),
            str(row["dia_id"]),
        )
    )
    top_n = max(int(top_k), 0)
    ranked = ranked[:top_n]
    for i, row in enumerate(ranked_rows[:top_n], 1):
        row["rank"] = i
    audit: Dict[str, object] = {
        "q_entity_keys": sorted(q_keys),
        "bm25_matched_entities": bm25_entities,
        "gated": gated,
        "candidate_memory_count": int(len(candidate_ids)),
        "entity_weight": float(entity_weight),
        "semantic_weight": float(semantic_weight),
        "ranked": ranked_rows[:top_n],
    }
    return ranked, audit
