"""Fact-centric retrieval: Entity boost + Fact BM25 + Fact embedding.

Path:
  Question
    → match Entity (BM25 soft-match on q entities)
    → match Fact text (embedding + BM25)
    → Fact set with Entity boost (via Fact.derived_from → Memory ← Entity)
    → optional Memory text append for top facts' source dialogs
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

from em_graph.build import EMGraph, EntityExtractor
from em_graph.recall import (
    EntityBM25Index,
    MemoryEmbeddingIndex,
)
from em_graph.recall.retrieval import (
    _entity_memory_scores,
    _normalize_q_entity_keys,
    expand_sequence_neighbors,
)
from em_graph.recall.tokenize import tokenize_for_bm25


def _peak_norm(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    peak = max(scores.values())
    if peak <= 0.0:
        return {k: 0.0 for k in scores}
    return {k: float(v) / peak for k, v in scores.items()}


@dataclass
class FactBM25Index:
    fact_ids: List[str]
    _bm25: BM25Okapi

    @classmethod
    def build(cls, facts: Sequence[Dict[str, Any]]) -> "FactBM25Index":
        fact_ids = [str(f["fact_id"]) for f in facts]
        corpus: List[List[str]] = []
        for fact in facts:
            toks = tokenize_for_bm25(str(fact.get("text") or ""))
            corpus.append(toks if toks else ["_empty"])
        return cls(fact_ids=fact_ids, _bm25=BM25Okapi(corpus))

    def scores(self, query: str) -> Dict[str, float]:
        q_tokens = tokenize_for_bm25(query)
        if not q_tokens:
            return {fid: 0.0 for fid in self.fact_ids}
        raw = list(self._bm25.get_scores(q_tokens))
        return _peak_norm(
            {fid: float(s) for fid, s in zip(self.fact_ids, raw)}
        )


@dataclass
class FactEmbeddingIndex:
    fact_ids: List[str]
    vectors: np.ndarray
    model_name: str
    _embedder: MemoryEmbeddingIndex

    @classmethod
    def build(
        cls,
        facts: Sequence[Dict[str, Any]],
        *,
        model_name: str,
        cache_path: str,
    ) -> "FactEmbeddingIndex":
        from pathlib import Path

        fact_ids = [str(f["fact_id"]) for f in facts]
        texts = [str(f.get("text") or "") for f in facts]
        embedder = MemoryEmbeddingIndex(
            memory_ids=[],
            vectors=np.zeros((0, 0), dtype=np.float32),
            model_name=model_name,
        )
        path = Path(cache_path)
        if path.exists():
            data = np.load(path, allow_pickle=True)
            cached_ids = [str(x) for x in data["fact_ids"].tolist()]
            cached_vecs = np.asarray(data["vectors"], dtype=np.float32)
            if cached_ids == fact_ids and cached_vecs.shape[0] == len(fact_ids):
                print(f"loaded fact emb cache {path.name}", flush=True)
                return cls(fact_ids, cached_vecs, model_name, embedder)

        print(f"embedding n_facts={len(texts)} model={model_name}", flush=True)
        vectors = embedder._embed_texts(
            texts,
            role="context",
            show_progress=True,
            text_cache=embedder._get_text_cache(),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            fact_ids=np.array(fact_ids, dtype=object),
            vectors=vectors,
        )
        print(f"wrote {path}", flush=True)
        return cls(fact_ids, vectors, model_name, embedder)

    def scores(self, query: str) -> Dict[str, float]:
        if self.vectors.size == 0:
            return {}
        q = self._embedder._embed_query(query)
        raw = self.vectors @ q.reshape(-1)
        return _peak_norm(
            {fid: float(s) for fid, s in zip(self.fact_ids, raw)}
        )


def _memory_to_facts(
    facts: Sequence[Dict[str, Any]],
) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = defaultdict(list)
    for fact in facts:
        mid = str(fact.get("memory_id") or "")
        fid = str(fact.get("fact_id") or "")
        if mid and fid:
            out[mid].append(fid)
    return out


def entity_fact_scores(
    graph: EMGraph,
    q_entity_keys: Set[str],
    *,
    entity_bm25_index: EntityBM25Index,
    memory_to_facts: Dict[str, List[str]],
    expand_memory_neighbors: bool = True,
) -> Dict[str, float]:
    """Propagate Entity→Memory scores onto Facts via derived_from."""
    mem_scores = _entity_memory_scores(
        graph,
        q_entity_keys,
        entity_bm25_index=entity_bm25_index,
    )
    if expand_memory_neighbors:
        mem_scores = expand_sequence_neighbors(mem_scores, graph)

    fact_scores: Dict[str, float] = {}
    for mid, score in mem_scores.items():
        if score <= 0.0:
            continue
        for fid in memory_to_facts.get(mid, []):
            fact_scores[fid] = max(fact_scores.get(fid, 0.0), float(score))
    return _peak_norm(fact_scores)


def retrieve_facts(
    question: str,
    *,
    graph: EMGraph,
    facts: Sequence[Dict[str, Any]],
    fact_embed_index: FactEmbeddingIndex,
    fact_bm25_index: FactBM25Index,
    entity_bm25_index: EntityBM25Index,
    top_k: int = 25,
    q_entity_keys: Optional[Set[str]] = None,
    extractor: Optional[EntityExtractor] = None,
    entity_weight: float = 0.25,
    fact_bm25_weight: float = 0.25,
    fact_embed_weight: float = 0.50,
    expand_memory_neighbors: bool = True,
) -> List[Tuple[str, float]]:
    """Rank facts by fused Entity boost + Fact BM25 + Fact embedding."""
    if not facts:
        return []

    q_keys = _normalize_q_entity_keys(
        question, extractor=extractor, q_entity_keys=q_entity_keys
    )
    mem2facts = _memory_to_facts(facts)

    e_scores = entity_fact_scores(
        graph,
        q_keys,
        entity_bm25_index=entity_bm25_index,
        memory_to_facts=mem2facts,
        expand_memory_neighbors=expand_memory_neighbors,
    )
    b_scores = fact_bm25_index.scores(question)
    s_scores = fact_embed_index.scores(question)

    ranked: List[Tuple[str, float]] = []
    for fact in facts:
        fid = str(fact["fact_id"])
        e = float(e_scores.get(fid, 0.0))
        b = float(b_scores.get(fid, 0.0))
        s = float(s_scores.get(fid, 0.0))
        if e <= 0.0 and b <= 0.0 and s <= 0.0:
            continue
        score = (
            float(entity_weight) * e
            + float(fact_bm25_weight) * b
            + float(fact_embed_weight) * s
        )
        ranked.append((fid, score))

    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[: max(int(top_k), 0)]


def build_fact_context(
    ranked: List[Tuple[str, float]],
    facts_by_id: Dict[str, Dict[str, Any]],
    graph: EMGraph,
    *,
    append_source_memory: bool = True,
    max_extra_memories: int = 8,
) -> Tuple[str, List[str], List[str]]:
    """Format Fact lines; optionally append source Memory dialog text."""
    lines: List[str] = []
    fact_ids: List[str] = []
    dia_ids: List[str] = []
    seen_dia: Set[str] = set()
    source_mids: List[str] = []
    seen_mid: Set[str] = set()

    lines.append("Retrieved facts:")
    for fid, _score in ranked:
        fact = facts_by_id.get(fid)
        if fact is None:
            continue
        lines.append(
            f'- {fact.get("date_time", "")}: {fact.get("speaker", "")} — '
            f'{fact.get("text", "")}'
        )
        fact_ids.append(fid)
        dia = str(fact.get("dia_id") or "")
        if dia and dia not in seen_dia:
            seen_dia.add(dia)
            dia_ids.append(dia)
        mid = str(fact.get("memory_id") or "")
        if mid and mid not in seen_mid:
            seen_mid.add(mid)
            source_mids.append(mid)

    if append_source_memory and source_mids:
        lines.append("")
        lines.append("Source dialog snippets:")
        dia_to_mem = {m.dia_id: m for m in graph.memories.values()}
        added = 0
        for mid in source_mids:
            if added >= int(max_extra_memories):
                break
            mem = graph.memories.get(mid)
            if mem is None:
                continue
            line = f'{mem.speaker} said, "{mem.text}"'
            caption = str(mem.blip_caption or "").strip()
            if caption:
                line += f" and shared {caption}"
            lines.append(f"- {mem.date_time}: {line}")
            if mem.dia_id and mem.dia_id not in seen_dia:
                seen_dia.add(mem.dia_id)
                dia_ids.append(mem.dia_id)
            added += 1

    return "\n".join(lines), fact_ids, dia_ids
