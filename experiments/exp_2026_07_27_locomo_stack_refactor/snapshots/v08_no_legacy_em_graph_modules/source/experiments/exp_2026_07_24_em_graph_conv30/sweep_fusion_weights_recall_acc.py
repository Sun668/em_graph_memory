#!/usr/bin/env python3
"""Sweep entity/embedding fusion weights; score official LoCoMo recall_acc@k.

Precomputes per-QA (entity, semantic) channels once (reuse graphs + q_keys +
embedding caches), then fuses offline across weight grids. Uses env_ark models.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

# entity_weight grid; semantic = 1 - entity (normalized fusion)
WEIGHTS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def _locomo_recall_acc(gold: Sequence[str], retrieved: Sequence[str]) -> float:
    if not gold:
        return 1.0
    ctx = set(retrieved)
    return float(sum(1 for ev in gold if ev in ctx)) / float(len(gold))


def _rank_fuse(
    channels: Dict[str, Tuple[float, float]],
    we: float,
    ws: float,
    top_k: int,
) -> List[str]:
    scored: List[Tuple[str, float]] = []
    for dia, (e, s) in channels.items():
        if e <= 0.0 and s <= 0.0:
            continue
        scored.append((dia, we * e + ws * s))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [d for d, _ in scored[:top_k]]


def _precompute_sample(sample_id: str) -> Dict[str, Any]:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))

    from em_graph import EMGraph, EntityBM25Index, MemoryEmbeddingIndex
    from em_graph.build import normalize_entity_key
    from em_graph.recall.retrieval import (
        _entity_memory_scores,
        expand_sequence_neighbors,
    )

    data_file = root / "data" / "locomo10.json"
    out_dir = root / "outputs" / "em_graph"
    graph_path = out_dir / f"{sample_id}_em_graph_extract_v3.json"
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision")
    emb_cache = (
        out_dir
        / f"{sample_id}_memory_emb_extract_v3_{emb_model.replace('/', '_')}.npz"
    )
    keys_path = out_dir / f"{sample_id}_offline_locomo_recall_acc.json"
    if not graph_path.exists():
        raise FileNotFoundError(graph_path)
    if not emb_cache.exists():
        raise FileNotFoundError(emb_cache)
    if not keys_path.exists():
        raise FileNotFoundError(keys_path)

    sample = next(
        s
        for s in json.loads(data_file.read_text(encoding="utf-8"))
        if s.get("sample_id") == sample_id
    )
    prev = json.loads(keys_path.read_text(encoding="utf-8"))
    q_keys_by_qa = {
        int(r["qa"]): [str(k) for k in (r.get("q_entity_keys") or [])]
        for r in prev.get("rows") or []
    }

    print(f"[{sample_id}] loading graph/emb", flush=True)
    graph = EMGraph.load_from_file(str(graph_path))
    emb = MemoryEmbeddingIndex.build(
        graph, model_name=emb_model, cache_path=str(emb_cache)
    )
    entity_bm25 = EntityBM25Index.build(graph)

    rows_out: List[Dict[str, Any]] = []
    jobs = []
    for i, qa in enumerate(sample.get("qa") or [], 1):
        question = str(qa.get("question") or "").strip()
        gold = [str(x) for x in (qa.get("evidence") or []) if str(x)]
        if not question or not gold:
            continue
        jobs.append((i, str(qa.get("category")), question, gold))

    print(f"[{sample_id}] precomputing channels n={len(jobs)}", flush=True)
    for i, cat, question, gold in jobs:
        keys = {
            normalize_entity_key(k)
            for k in q_keys_by_qa.get(i, [])
            if normalize_entity_key(k)
        }
        seeds = _entity_memory_scores(graph, keys, entity_bm25_index=entity_bm25)
        entity_scores = expand_sequence_neighbors(seeds, graph)
        candidate_ids = set(entity_scores.keys())
        gated = bool(candidate_ids)
        score_ids = candidate_ids if gated else None
        pool_ids = candidate_ids if gated else set(graph.memories.keys())
        sem_scores = emb.scores(question, memory_ids=score_ids)

        channels: Dict[str, Tuple[float, float]] = {}
        for mid in pool_ids:
            mem = graph.memories.get(mid)
            if mem is None:
                continue
            e = float(entity_scores.get(mid, 0.0))
            s = float(sem_scores.get(mid, 0.0))
            if e <= 0.0 and s <= 0.0:
                continue
            channels[mem.dia_id] = (e, s)

        rows_out.append(
            {
                "qa": i,
                "category": str(cat),
                "gold": gold,
                "gated": gated,
                "pool_size": len(channels),
                "channels": channels,
            }
        )
        if len(rows_out) % 40 == 0:
            print(f"[{sample_id}]  channels {len(rows_out)}/{len(jobs)}", flush=True)

    cache_path = out_dir / f"{sample_id}_fusion_channels_recall_acc.json"
    # channels dict is large; keep as-is for reuse
    cache_path.write_text(json.dumps({"sample_id": sample_id, "rows": rows_out}), encoding="utf-8")
    print(f"[{sample_id}] wrote {cache_path.name} n={len(rows_out)}", flush=True)
    return {"sample_id": sample_id, "n": len(rows_out), "cache": str(cache_path)}


def _score_from_cache(
    cache_path: Path, weights: Sequence[float]
) -> Dict[str, Any]:
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    rows = payload["rows"]
    n = len(rows)
    per_w: Dict[str, Dict[str, float]] = {}
    for we in weights:
        ws = 1.0 - float(we)
        ra8 = ra25 = ra100 = 0.0
        h8 = h25 = h100 = 0
        for row in rows:
            gold = row["gold"]
            ch = row["channels"]
            r8 = _rank_fuse(ch, we, ws, 8)
            r25 = _rank_fuse(ch, we, ws, 25)
            r100 = _rank_fuse(ch, we, ws, 100)
            ra8 += _locomo_recall_acc(gold, r8)
            ra25 += _locomo_recall_acc(gold, r25)
            ra100 += _locomo_recall_acc(gold, r100)
            gset = set(gold)
            h8 += int(bool(set(r8) & gset))
            h25 += int(bool(set(r25) & gset))
            h100 += int(bool(set(r100) & gset))
        key = f"e{we:.1f}_s{ws:.1f}"
        per_w[key] = {
            "entity_weight": we,
            "semantic_weight": ws,
            "n": n,
            "recall_acc8": round(ra8 / n, 4) if n else 0.0,
            "recall_acc25": round(ra25 / n, 4) if n else 0.0,
            "recall_acc100": round(ra100 / n, 4) if n else 0.0,
            "hit8_rate": round(h8 / n, 4) if n else 0.0,
            "hit25_rate": round(h25 / n, 4) if n else 0.0,
            "hit100_rate": round(h100 / n, 4) if n else 0.0,
            "hit25": h25,
        }
    return {"sample_id": payload["sample_id"], "n": n, "by_weight": per_w}


def main() -> None:
    data_file = ROOT / "data" / "locomo10.json"
    samples = json.loads(data_file.read_text(encoding="utf-8"))
    wanted = os.environ.get("EM_GRAPH_SAMPLE_IDS", "").strip()
    if wanted:
        sample_ids = [x.strip() for x in wanted.split(",") if x.strip()]
    else:
        sample_ids = [str(s.get("sample_id") or "") for s in samples if s.get("sample_id")]

    reuse_channels = os.environ.get("EM_GRAPH_REUSE_CHANNELS", "1").strip() not in {
        "0",
        "false",
        "False",
    }
    sample_workers = int(os.environ.get("EM_GRAPH_SAMPLE_WORKERS", "2"))
    out_dir = ROOT / "outputs" / "em_graph"
    out_dir.mkdir(parents=True, exist_ok=True)

    to_run = []
    caches: Dict[str, Path] = {}
    for sid in sample_ids:
        cache = out_dir / f"{sid}_fusion_channels_recall_acc.json"
        if reuse_channels and cache.exists():
            print(f"[{sid}] reuse channel cache", flush=True)
            caches[sid] = cache
        else:
            to_run.append(sid)

    if to_run:
        print(
            f"Precomputing channels for {len(to_run)} samples, "
            f"workers={sample_workers}",
            flush=True,
        )
        with ProcessPoolExecutor(max_workers=sample_workers) as pool:
            futures = {pool.submit(_precompute_sample, sid): sid for sid in to_run}
            for fut in as_completed(futures):
                sid = futures[fut]
                try:
                    info = fut.result()
                    caches[sid] = Path(info["cache"])
                except Exception as exc:  # noqa: BLE001
                    print(f"[{sid}] FAILED precompute: {exc}", flush=True)
                    raise

    print("Scoring weight grid ...", flush=True)
    per_sample = []
    for sid in sample_ids:
        scored = _score_from_cache(caches[sid], WEIGHTS)
        per_sample.append(scored)

    # aggregate
    aggregate_by_w: Dict[str, Dict[str, Any]] = {}
    for we in WEIGHTS:
        ws = 1.0 - float(we)
        key = f"e{we:.1f}_s{ws:.1f}"
        n = 0
        ra8 = ra25 = ra100 = 0.0
        h8 = h25 = h100 = 0.0
        hit25_count = 0
        for ps in per_sample:
            b = ps["by_weight"][key]
            nn = int(b["n"])
            n += nn
            ra8 += b["recall_acc8"] * nn
            ra25 += b["recall_acc25"] * nn
            ra100 += b["recall_acc100"] * nn
            h8 += b["hit8_rate"] * nn
            h25 += b["hit25_rate"] * nn
            h100 += b["hit100_rate"] * nn
            hit25_count += int(b["hit25"])
        aggregate_by_w[key] = {
            "entity_weight": we,
            "semantic_weight": ws,
            "n": n,
            "recall_acc8": round(ra8 / n, 4),
            "recall_acc25": round(ra25 / n, 4),
            "recall_acc100": round(ra100 / n, 4),
            "hit8_rate": round(h8 / n, 4),
            "hit25_rate": round(h25 / n, 4),
            "hit100_rate": round(h100 / n, 4),
            "hit25": hit25_count,
        }

    baseline = aggregate_by_w["e0.4_s0.6"]
    best_key = max(aggregate_by_w, key=lambda k: aggregate_by_w[k]["recall_acc25"])
    best = aggregate_by_w[best_key]

    result = {
        "env": "env_ark.sh",
        "metric": "locomo_recall_acc",
        "primary": "recall_acc25",
        "baseline": "e0.4_s0.6",
        "baseline_note": "prior default before 0.3/0.7 promotion",
        "baseline_recall_acc25": baseline["recall_acc25"],
        "promoted_default": "e0.3_s0.7",
        "best_weight": best_key,
        "best_recall_acc25": best["recall_acc25"],
        "delta_vs_baseline": round(best["recall_acc25"] - baseline["recall_acc25"], 4),
        "weights": WEIGHTS,
        "aggregate_by_weight": aggregate_by_w,
        "per_sample": per_sample,
        "n_samples": len(per_sample),
        "n": baseline["n"],
    }

    out_json = EXP_DIR / "result_weight_sweep_recall_acc.json"
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    snap = EXP_DIR / "snapshots" / "v05_weight_sweep_recall_acc"
    snap.mkdir(parents=True, exist_ok=True)
    (snap / "result_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (snap / "source_sweep_fusion_weights_recall_acc.py").write_text(
        Path(__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )

    print("\n=== recall_acc@25 by weight (entity / semantic) ===")
    print(f"{'weights':<14} {'ra@8':>8} {'ra@25':>8} {'ra@100':>8} {'hit@25':>8}")
    for we in WEIGHTS:
        ws = 1.0 - float(we)
        key = f"e{we:.1f}_s{ws:.1f}"
        b = aggregate_by_w[key]
        mark = " <-- baseline" if key == "e0.4_s0.6" else ""
        mark = " <-- BEST" if key == best_key else mark
        print(
            f"{key:<14} {b['recall_acc8']:8.4f} {b['recall_acc25']:8.4f} "
            f"{b['recall_acc100']:8.4f} {b['hit25_rate']:8.4f}{mark}"
        )
    print(
        f"\nbest={best_key} recall_acc@25={best['recall_acc25']} "
        f"(delta vs 0.4/0.6: {result['delta_vs_baseline']:+.4f})"
    )
    print("wrote", out_json)


if __name__ == "__main__":
    main()
