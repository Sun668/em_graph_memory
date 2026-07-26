"""BM25 index over Entity keys for soft-matching question entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from em_graph.models import EMGraph
from em_graph.tokenize import normalize_entity_key, tokenize_for_bm25

_DEFAULT_MIN_REL = 0.5
_DEFAULT_TOP_K = 20


def _entity_doc_text(key: str, value: str) -> str:
    key = str(key or "").strip()
    value = str(value or "").strip()
    if key and value and key.lower() != value.lower():
        return f"{key} {value}"
    return key or value


@dataclass
class EntityBM25Index:
    """Short-document BM25 over graph Entity nodes."""

    entity_ids: List[str]
    entity_keys: List[str]
    _bm25: object

    @classmethod
    def build(cls, graph: EMGraph) -> "EntityBM25Index":
        from rank_bm25 import BM25Okapi

        entities = sorted(graph.entities.values(), key=lambda e: e.id)
        entity_ids = [e.id for e in entities]
        entity_keys = [
            str(e.key or "").strip() or str(e.value or "").strip().lower()
            for e in entities
        ]
        corpus: List[List[str]] = []
        for ent in entities:
            toks = tokenize_for_bm25(_entity_doc_text(ent.key, ent.value))
            corpus.append(toks if toks else ["_empty"])
        return cls(
            entity_ids=entity_ids,
            entity_keys=entity_keys,
            _bm25=BM25Okapi(corpus),
        )

    def scores_for_query(self, query: str) -> Dict[str, float]:
        """Peak-normalized BM25 scores for one query string over all entities."""
        q_tokens = tokenize_for_bm25(query)
        if not q_tokens:
            return {eid: 0.0 for eid in self.entity_ids}
        raw = list(self._bm25.get_scores(q_tokens))
        scored = {eid: float(score) for eid, score in zip(self.entity_ids, raw)}
        peak = max(scored.values()) if scored else 0.0
        if peak <= 0.0:
            return {eid: 0.0 for eid in scored}
        return {eid: score / peak for eid, score in scored.items()}

    def match_q_keys(
        self,
        q_keys: Iterable[str],
        *,
        min_rel_score: float = _DEFAULT_MIN_REL,
        top_k_per_key: Optional[int] = _DEFAULT_TOP_K,
    ) -> Dict[str, Dict[str, float]]:
        """Map ``entity_id → {q_key: match_score}``.

        Scores are peak-normalized per q_key. Keep matches with
        ``score >= min_rel_score``. Exact normalized key equality scores 1.0.
        """
        out: Dict[str, Dict[str, float]] = {}
        threshold = float(min_rel_score)
        key_norm_to_eids: Dict[str, List[str]] = {}
        for eid, ek in zip(self.entity_ids, self.entity_keys):
            nk = normalize_entity_key(ek)
            if nk:
                key_norm_to_eids.setdefault(nk, []).append(eid)

        for raw_qk in q_keys:
            qk = normalize_entity_key(raw_qk)
            if not qk:
                continue

            scored = self.scores_for_query(qk)
            for eid in key_norm_to_eids.get(qk, []):
                scored[eid] = max(float(scored.get(eid, 0.0)), 1.0)

            pairs: List[Tuple[str, float]] = [
                (eid, sc) for eid, sc in scored.items() if sc >= threshold
            ]
            pairs.sort(key=lambda item: (-item[1], item[0]))
            if top_k_per_key is not None:
                pairs = pairs[: max(int(top_k_per_key), 0)]

            for eid, sc in pairs:
                bucket = out.setdefault(eid, {})
                bucket[qk] = max(float(bucket.get(qk, 0.0)), float(sc))
        return out
