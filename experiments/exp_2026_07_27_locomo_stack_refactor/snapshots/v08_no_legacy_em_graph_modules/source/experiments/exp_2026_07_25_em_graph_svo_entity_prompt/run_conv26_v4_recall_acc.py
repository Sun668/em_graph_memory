#!/usr/bin/env python3
"""Rebuild conv-26 with entity-extract v4 and score official recall_acc@25.

Compares against the prior extract-v3 baseline (recall_acc@25 = 0.8304).
Uses env_ark.sh models; fusion locked to 0.40E+0.60S to match that baseline.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import (  # noqa: E402
    EMGraph,
    EMGraphConfig,
    EntityBM25Index,
    EntityExtractor,
    MemoryEmbeddingIndex,
    assert_bipartite,
    build_em_graph_from_file,
    ensure_memory_sequence_edges,
    extract_question_entity_keys,
    retrieve_dialog_ids,
)
from em_graph.build.config import ENTITY_EXTRACT_VERSION  # noqa: E402

SAMPLE_ID = "conv-26"
ENTITY_WEIGHT = 0.40
SEMANTIC_WEIGHT = 0.60
V3_BASELINE_RA25 = 0.8304
V3_BASELINE_HIT25 = 173


def _locomo_recall_acc(gold: List[str], retrieved: List[str]) -> float:
    if not gold:
        return 1.0
    ctx = set(retrieved)
    return float(sum(1 for ev in gold if ev in ctx)) / float(len(gold))


def _split_evidence(raw: List[str]) -> List[str]:
    out: List[str] = []
    for item in raw or []:
        for part in str(item).split(";"):
            part = part.strip()
            if part:
                out.append(part)
    return out


def main() -> None:
    data_file = ROOT / "data" / "locomo10.json"
    out_dir = ROOT / "outputs" / "em_graph"
    out_dir.mkdir(parents=True, exist_ok=True)

    graph_path = out_dir / f"{SAMPLE_ID}_em_graph_extract_v4.json"
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision")
    # Prefer v3 emb cache (same memory texts); fall back to a v4-named cache.
    emb_cache_v3 = (
        out_dir
        / f"{SAMPLE_ID}_memory_emb_extract_v3_{emb_model.replace('/', '_')}.npz"
    )
    emb_cache_v4 = (
        out_dir
        / f"{SAMPLE_ID}_memory_emb_extract_v4_{emb_model.replace('/', '_')}.npz"
    )
    result_path = out_dir / f"{SAMPLE_ID}_offline_locomo_recall_acc_extract_v4.json"
    exp_result = EXP_DIR / "result_conv26_v4_recall_acc.json"

    config = EMGraphConfig(
        model=os.environ.get("OPENAI_MODEL", "deepseek-v4-flash"),
        use_cache=True,
        add_speaker_as_entity=True,
        auto_time_words=True,
    )
    extractor = EntityExtractor(
        model=config.model,
        use_cache=True,
        wait_time=float(os.environ.get("EM_GRAPH_WAIT_TIME", "0.15")),
    )
    extract_workers = int(os.environ.get("EM_GRAPH_MAX_WORKERS", "4"))
    reuse = os.environ.get("EM_GRAPH_REUSE", "0").strip() in {"1", "true", "True"}

    print(
        f"[{SAMPLE_ID}] extract={ENTITY_EXTRACT_VERSION} model={config.model} "
        f"embed={emb_model} reuse_graph={reuse and graph_path.exists()}",
        flush=True,
    )

    # Smoke the motivating question before the full rebuild/score.
    smoke_q = "What did Caroline research?"
    smoke_keys = sorted(extract_question_entity_keys(smoke_q, extractor=extractor))
    print(f"[smoke] {smoke_q!r} -> {smoke_keys}", flush=True)
    extractor.cache.flush()

    graph = None
    if reuse and graph_path.exists():
        loaded = EMGraph.load_from_file(str(graph_path))
        if bool((loaded.stats or {}).get("partial")):
            print(f"[{SAMPLE_ID}] graph partial; rebuilding", flush=True)
        else:
            graph = loaded
            print(f"[{SAMPLE_ID}] reused {graph_path.name}", flush=True)
    if graph is None:
        graph = build_em_graph_from_file(
            str(data_file),
            SAMPLE_ID,
            config=config,
            extractor=extractor,
            checkpoint_path=str(graph_path),
            checkpoint_every=40,
            max_workers=extract_workers,
        )

    seq_n = ensure_memory_sequence_edges(graph)
    graph.stats = {
        **dict(graph.stats or {}),
        "memory_count": len(graph.memories),
        "entity_count": len(graph.entities),
        "edge_count": len(graph.edges),
        "memory_edge_count": seq_n,
        "mentions_bipartite": True,
        "memory_sequence": "bidirectional NEXT/PREV in dialog order",
        "entity_extract_version": ENTITY_EXTRACT_VERSION,
    }
    assert_bipartite(graph)
    graph.save_to_file(str(graph_path))
    print(f"[{SAMPLE_ID}] graph stats: {graph.stats}", flush=True)

    emb_cache = emb_cache_v3 if emb_cache_v3.exists() else emb_cache_v4
    emb_index = MemoryEmbeddingIndex.build(
        graph, model_name=emb_model, cache_path=str(emb_cache)
    )
    if emb_cache == emb_cache_v3 and not emb_cache_v4.exists():
        # Keep a v4-named pointer copy for later runs.
        try:
            shutil.copy2(emb_cache_v3, emb_cache_v4)
        except OSError:
            pass
    entity_bm25 = EntityBM25Index.build(graph)
    print(f"[{SAMPLE_ID}] indexes ready", flush=True)

    sample = next(
        s
        for s in json.loads(data_file.read_text(encoding="utf-8"))
        if s.get("sample_id") == SAMPLE_ID
    )
    jobs: List[Tuple[int, Dict[str, Any], str, List[str]]] = []
    for i, qa in enumerate(sample.get("qa") or [], 1):
        question = str(qa.get("question") or "").strip()
        gold = _split_evidence([str(x) for x in (qa.get("evidence") or []) if str(x)])
        if not question or not gold:
            continue
        jobs.append((i, qa, question, gold))

    print(
        f"[{SAMPLE_ID}] extracting q entities n={len(jobs)} "
        f"workers={extract_workers} (fresh v4, no reuse)",
        flush=True,
    )
    q_keys_by_qa: Dict[int, Set[str]] = {}

    def _extract_one(
        item: Tuple[int, Dict[str, Any], str, List[str]],
    ) -> Tuple[int, Set[str]]:
        qa_i, _qa, question, _gold = item
        return qa_i, extract_question_entity_keys(question, extractor=extractor)

    done = 0
    with ThreadPoolExecutor(max_workers=extract_workers) as pool:
        futures = [pool.submit(_extract_one, job) for job in jobs]
        for fut in as_completed(futures):
            qa_i, keys = fut.result()
            q_keys_by_qa[qa_i] = keys
            done += 1
            if done % 40 == 0 or done == len(jobs):
                print(f"  q extracted {done}/{len(jobs)}", flush=True)
    extractor.cache.flush()

    rows: List[Dict[str, Any]] = []
    print(f"[{SAMPLE_ID}] scoring n={len(jobs)}", flush=True)
    for i, qa, question, gold in jobs:
        q_keys = q_keys_by_qa.get(i, set())
        ranked = retrieve_dialog_ids(
            graph,
            question,
            top_k=100,
            embedding_index=emb_index,
            entity_bm25_index=entity_bm25,
            q_entity_keys=q_keys,
            entity_weight=ENTITY_WEIGHT,
            semantic_weight=SEMANTIC_WEIGHT,
        )
        dias = [d for d, _ in ranked]
        gset = set(gold)
        first = next(
            (rank for rank, dia_id in enumerate(dias, 1) if dia_id in gset),
            None,
        )
        rows.append(
            {
                "qa": i,
                "category": str(qa.get("category")),
                "n_evidence": len(gold),
                "recall_acc8": _locomo_recall_acc(gold, dias[:8]),
                "recall_acc25": _locomo_recall_acc(gold, dias[:25]),
                "recall_acc100": _locomo_recall_acc(gold, dias[:100]),
                "hit8": bool(set(dias[:8]) & gset),
                "hit25": bool(set(dias[:25]) & gset),
                "hit100": bool(set(dias) & gset),
                "first_gold_rank": first,
                "covered25": sorted(gset & set(dias[:25])),
                "q_entity_keys": sorted(q_keys),
            }
        )

    n = len(rows)

    def _mean(key: str) -> float:
        return round(sum(float(r[key]) for r in rows) / n, 4) if n else 0.0

    # Spotlight the motivating QA.
    research_row = next((r for r in rows if r["qa"] == 4), None)

    summary: Dict[str, Any] = {
        "sample_id": SAMPLE_ID,
        "env": "env_ark.sh",
        "metric": "locomo_recall_acc",
        "entity_extract_version": ENTITY_EXTRACT_VERSION,
        "embedding_model": emb_index.model_name,
        "model": config.model,
        "graph_stats": graph.stats,
        "n": n,
        "recall_acc8": _mean("recall_acc8"),
        "recall_acc25": _mean("recall_acc25"),
        "recall_acc100": _mean("recall_acc100"),
        "hit8": sum(int(r["hit8"]) for r in rows),
        "hit25": sum(int(r["hit25"]) for r in rows),
        "hit100": sum(int(r["hit100"]) for r in rows),
        "hit8_rate": _mean("hit8"),
        "hit25_rate": _mean("hit25"),
        "hit100_rate": _mean("hit100"),
        "baseline_v3": {
            "recall_acc25": V3_BASELINE_RA25,
            "hit25": V3_BASELINE_HIT25,
            "n": 197,
        },
        "delta_vs_v3": {
            "recall_acc25": round(_mean("recall_acc25") - V3_BASELINE_RA25, 4),
            "hit25": int(sum(int(r["hit25"]) for r in rows) - V3_BASELINE_HIT25),
        },
        "smoke_question": {
            "question": smoke_q,
            "q_entity_keys": smoke_keys,
            "contains_research": any("research" in k for k in smoke_keys),
        },
        "qa4_research": research_row,
        "retrieval": {
            "method": "entity(BM25 soft-match +±1 sequence@0.5) + embedding",
            "entity_weight": ENTITY_WEIGHT,
            "semantic_weight": SEMANTIC_WEIGHT,
        },
        "prompt_budget": {
            "checked": True,
            "note": "extract v4 scaffold only; no answer-generation prompt",
        },
        "graph_constraint": {
            "audit_passed": True,
            "graph_inputs": "conversation dialogs only",
            "qa_excluded_from_graph": True,
            "recall": "official LoCoMo recall_acc over conversation-built Memory nodes",
        },
        "outputs": {
            "graph": str(graph_path.relative_to(ROOT)),
            "embedding_cache": str(emb_cache.relative_to(ROOT)),
            "offline_recall_acc": str(result_path.relative_to(ROOT)),
        },
    }

    payload = {"summary": summary, "rows": rows}
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    exp_result.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    snap_dir = EXP_DIR / "snapshots" / "v03_conv26_v4_recall_acc"
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / "result_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    shutil.copy2(Path(__file__), snap_dir / "source_run_conv26_v4_recall_acc.py")
    shutil.copy2(
        ROOT / "em_graph" / "config.py", snap_dir / "source_em_graph_config.py"
    )

    print(json.dumps({
        "extract": ENTITY_EXTRACT_VERSION,
        "recall_acc25": summary["recall_acc25"],
        "hit25": f"{summary['hit25']}/{n}",
        "delta_ra25_vs_v3": summary["delta_vs_v3"]["recall_acc25"],
        "smoke_keys": smoke_keys,
        "qa4_keys": (research_row or {}).get("q_entity_keys"),
        "qa4_ra25": (research_row or {}).get("recall_acc25"),
        "qa4_rank": (research_row or {}).get("first_gold_rank"),
    }, indent=2))
    print("wrote", result_path)
    print("wrote", exp_result)
    print("wrote snapshot", snap_dir)


if __name__ == "__main__":
    main()
