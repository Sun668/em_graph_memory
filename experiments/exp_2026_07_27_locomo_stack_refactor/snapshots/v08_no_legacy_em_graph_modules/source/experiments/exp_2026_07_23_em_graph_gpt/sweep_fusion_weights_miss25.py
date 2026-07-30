#!/usr/bin/env python3
"""Sweep entity/embed fusion weights for miss@25 recovery.

Memory BM25 was removed from mainline retrieval; this sweep uses
``entity + embedding`` channels only (BM25 channel fixed at 0).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import EMGraph, EntityBM25Index  # noqa: E402
from em_graph.build import normalize_entity_key  # noqa: E402
from em_graph.recall import MemoryEmbeddingIndex  # noqa: E402
from em_graph.recall.retrieval import (  # noqa: E402
    _entity_memory_scores,
    expand_sequence_neighbors,
)

EXP_DIR = Path(__file__).resolve().parent
HIT_PATH = ROOT / "outputs" / "em_graph_gpt" / "conv-26_offline_hit.json"
GRAPH_PATH = ROOT / "outputs" / "em_graph_gpt" / "conv-26_em_graph.json"
DATA_PATH = ROOT / "data" / "locomo10.json"
OUT_PATH = EXP_DIR / "weight_sweep_miss25.json"
BASE = (0.40, 0.0, 0.60)


def best_gold_rank(
    channels: Dict[str, Tuple[float, float, float]],
    gold_dias: List[str],
    we: float,
    wb: float,
    ws: float,
) -> Optional[int]:
    if not gold_dias:
        return None
    scored = []
    for dia, (e, b, s) in channels.items():
        if e <= 0 and b <= 0 and s <= 0:
            continue
        scored.append((dia, we * e + wb * b + ws * s))
    scored.sort(key=lambda x: (-x[1], x[0]))
    gset = set(gold_dias)
    for i, (dia, _) in enumerate(scored, 1):
        if dia in gset:
            return i
    return None


def precompute_row(
    graph: EMGraph,
    entity_bm25: EntityBM25Index,
    emb: MemoryEmbeddingIndex,
    question: str,
    q_keys: List[str],
    evidence: List[str],
) -> Dict[str, Any]:
    keys = {normalize_entity_key(k) for k in q_keys if k}
    seeds = _entity_memory_scores(graph, keys, entity_bm25_index=entity_bm25)
    entity_scores = expand_sequence_neighbors(seeds, graph)
    candidate_ids = set(entity_scores.keys())
    gated = bool(candidate_ids)
    score_ids = candidate_ids if gated else None
    pool_ids = candidate_ids if gated else set(graph.memories.keys())
    sem_scores = emb.scores(question, memory_ids=score_ids)

    channels: Dict[str, Tuple[float, float, float]] = {}
    for mid in pool_ids:
        m = graph.memories[mid]
        channels[m.dia_id] = (
            float(entity_scores.get(mid, 0.0)),
            0.0,
            float(sem_scores.get(mid, 0.0)),
        )
    gold_dias = [d for d in evidence if d]
    return {
        "channels": channels,
        "gold_in_pool": [d for d in gold_dias if d in channels],
        "gold_out_of_pool": [d for d in gold_dias if d not in channels],
        "pool_size": len(channels),
    }


def main() -> None:
    hit = json.loads(HIT_PATH.read_text(encoding="utf-8"))
    sample = next(
        s
        for s in json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if s.get("sample_id") == "conv-26"
    )
    qa_list = sample.get("qa") or []
    graph = EMGraph.load_from_file(str(GRAPH_PATH))
    emb = MemoryEmbeddingIndex.build(
        graph,
        model_name="text-embedding-3-small",
        cache_path=str(
            ROOT
            / "outputs"
            / "em_graph_gpt"
            / "conv-26_memory_emb_text-embedding-3-small.npz"
        ),
    )
    entity_bm25 = EntityBM25Index.build(graph)

    print("precomputing channel scores for all QAs ...", flush=True)
    all_rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(hit.get("rows") or [], 1):
        qa_i = int(row["qa"])
        qa = qa_list[qa_i - 1]
        question = str(qa.get("question") or "")
        evidence = [str(x) for x in (qa.get("evidence") or []) if str(x)]
        pack = precompute_row(
            graph,
            entity_bm25,
            emb,
            question,
            list(row.get("q_entity_keys") or []),
            evidence,
        )
        all_rows.append(
            {
                "qa": qa_i,
                "category": str(qa.get("category")),
                "question": question,
                "gold": qa.get("answer"),
                "evidence": evidence,
                "default_rank": row.get("first_gold_rank"),
                "hit25_file": bool(row.get("hit25")),
                "q_entity_keys": list(row.get("q_entity_keys") or []),
                **pack,
            }
        )
        if idx % 40 == 0 or idx == len(hit["rows"]):
            print(f"  {idx}/{len(hit['rows'])}", flush=True)

    miss = [r for r in all_rows if not r["hit25_file"]]
    print(f"miss@25={len(miss)} / {len(all_rows)}", flush=True)

    # entity/embed only: wb fixed at 0
    steps = [i / 20 for i in range(0, 21)]
    grid = sorted(
        {(round(we, 2), 0.0, round(1.0 - we, 2)) for we in steps}
    )
    print(f"grid={len(grid)} (entity+embed only)", flush=True)

    def hit_count(rows: List[Dict[str, Any]], we: float, wb: float, ws: float) -> int:
        n = 0
        for r in rows:
            rank = best_gold_rank(r["channels"], r["gold_in_pool"], we, wb, ws)
            if rank is not None and rank <= 25:
                n += 1
        return n

    best_by_case: Dict[int, Dict[str, Any]] = {}
    for we, wb, ws in grid:
        for r in miss:
            if not r["gold_in_pool"]:
                continue
            rank = best_gold_rank(r["channels"], r["gold_in_pool"], we, wb, ws)
            if rank is None:
                continue
            prev = best_by_case.get(r["qa"])
            if prev is None or rank < prev["rank"]:
                best_by_case[r["qa"]] = {
                    "rank": rank,
                    "weights": [we, wb, ws],
                }

    scored_grid = []
    for we, wb, ws in grid:
        h_all = hit_count(all_rows, we, wb, ws)
        h_miss = hit_count(miss, we, wb, ws)
        scored_grid.append(
            {
                "weights": [we, wb, ws],
                "hit25_all": h_all,
                "hit25_all_rate": round(h_all / len(all_rows), 4) if all_rows else 0.0,
                "hit25_on_prior_miss": h_miss,
            }
        )
    scored_grid.sort(
        key=lambda x: (-x["hit25_all"], -x["hit25_on_prior_miss"], x["weights"])
    )

    base_hit = hit_count(all_rows, *BASE)
    payload = {
        "n": len(all_rows),
        "miss25": len(miss),
        "base_weights": list(BASE),
        "base_hit25": base_hit,
        "best_grid": scored_grid[:20],
        "oracle_best_rank_by_miss_qa": best_by_case,
        "note": "Memory BM25 channel removed; wb fixed at 0",
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in payload if k != "oracle_best_rank_by_miss_qa"}, indent=2))
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
