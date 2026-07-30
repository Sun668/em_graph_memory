#!/usr/bin/env python3
"""Parallel extract-v3 rebuild + offline hit@k for all LoCoMo samples (env.sh)."""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))


def _run_one(sample_id: str) -> Dict[str, Any]:
    """Worker: build/score one sample. Runs in a child process."""
    import os
    import sys
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))

    from em_graph import (
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
    from em_graph.build.config import ENTITY_EXTRACT_VERSION

    data_file = root / "data" / "locomo10.json"
    out_dir = root / "outputs" / "em_graph"
    out_dir.mkdir(parents=True, exist_ok=True)

    graph_path = out_dir / f"{sample_id}_em_graph_extract_v3.json"
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision")
    emb_cache = (
        out_dir
        / f"{sample_id}_memory_emb_extract_v3_{emb_model.replace('/', '_')}.npz"
    )
    result_path = out_dir / f"{sample_id}_offline_hit_extract_v3.json"

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
    reuse = os.environ.get("EM_GRAPH_REUSE", "1").strip() in {"1", "true", "True"}

    print(
        f"[{sample_id}] start model={config.model} extract={ENTITY_EXTRACT_VERSION} "
        f"reuse={reuse and graph_path.exists()}",
        flush=True,
    )

    graph = None
    if reuse and graph_path.exists():
        loaded = EMGraph.load_from_file(str(graph_path))
        if bool((loaded.stats or {}).get("partial")):
            print(
                f"[{sample_id}] graph {graph_path.name} is partial; resuming build",
                flush=True,
            )
        else:
            graph = loaded
            print(f"[{sample_id}] reused graph {graph_path.name}", flush=True)
    if graph is None:
        graph = build_em_graph_from_file(
            str(data_file),
            sample_id,
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
    print(f"[{sample_id}] graph stats: {graph.stats}", flush=True)

    emb_index = MemoryEmbeddingIndex.build(
        graph, model_name=emb_model, cache_path=str(emb_cache)
    )
    entity_bm25_index = EntityBM25Index.build(graph)
    print(f"[{sample_id}] indexes ready", flush=True)

    sample = next(
        s
        for s in json.loads(data_file.read_text(encoding="utf-8"))
        if s.get("sample_id") == sample_id
    )

    jobs: List[Tuple[int, Dict[str, Any], str, List[str]]] = []
    for i, qa in enumerate(sample.get("qa") or [], 1):
        question = str(qa.get("question") or "").strip()
        gold = [str(x) for x in (qa.get("evidence") or []) if str(x)]
        if not question or not gold:
            continue
        jobs.append((i, qa, question, gold))

    q_keys_by_qa: Dict[int, Set[str]] = {}
    reuse_q_keys = os.environ.get("EM_GRAPH_REUSE_Q_KEYS", "1").strip() not in {
        "0",
        "false",
        "False",
    }
    if reuse_q_keys and result_path.exists():
        prev = json.loads(result_path.read_text(encoding="utf-8"))
        for row in prev.get("rows") or []:
            keys = row.get("q_entity_keys") or []
            if keys:
                q_keys_by_qa[int(row["qa"])] = set(keys)
        if q_keys_by_qa:
            print(
                f"[{sample_id}] reused q_entity_keys n={len(q_keys_by_qa)}",
                flush=True,
            )

    missing = [job for job in jobs if job[0] not in q_keys_by_qa]
    if missing:
        print(
            f"[{sample_id}] extracting q entities n={len(missing)} "
            f"workers={extract_workers}",
            flush=True,
        )

        def _extract_one(
            item: Tuple[int, Dict[str, Any], str, List[str]],
        ) -> Tuple[int, Set[str]]:
            qa_i, _qa, question, _gold = item
            return qa_i, extract_question_entity_keys(question, extractor=extractor)

        done = 0
        with ThreadPoolExecutor(max_workers=extract_workers) as pool:
            futures = [pool.submit(_extract_one, job) for job in missing]
            for fut in as_completed(futures):
                qa_i, keys = fut.result()
                q_keys_by_qa[qa_i] = keys
                done += 1
                if done % 40 == 0 or done == len(missing):
                    print(
                        f"[{sample_id}]  q extracted {done}/{len(missing)}",
                        flush=True,
                    )
        cache = getattr(extractor, "cache", None)
        if cache is not None:
            cache.flush()

    rows = []
    for i, qa, question, gold in jobs:
        q_keys = q_keys_by_qa.get(i, set())
        ranked = retrieve_dialog_ids(
            graph,
            question,
            top_k=100,
            embedding_index=emb_index,
            entity_bm25_index=entity_bm25_index,
            q_entity_keys=q_keys,
        )
        gset = set(gold)
        first = next(
            (rank for rank, (dia_id, _) in enumerate(ranked, 1) if dia_id in gset),
            None,
        )
        rows.append(
            {
                "qa": i,
                "category": str(qa.get("category")),
                "hit8": bool({d for d, _ in ranked[:8]} & gset),
                "hit25": bool({d for d, _ in ranked[:25]} & gset),
                "hit100": bool({d for d, _ in ranked} & gset),
                "first_gold_rank": first,
                "q_entity_keys": sorted(q_keys),
            }
        )

    n = len(rows)
    by_cat: Dict[str, Dict[str, int]] = {}
    for row in rows:
        cat = row["category"]
        bucket = by_cat.setdefault(cat, {"n": 0, "h8": 0, "h25": 0})
        bucket["n"] += 1
        bucket["h8"] += int(row["hit8"])
        bucket["h25"] += int(row["hit25"])

    summary: Dict[str, Any] = {
        "sample_id": sample_id,
        "env": "env.sh",
        "package": "em_graph",
        "package_version": "0.3.1",
        "entity_extract_version": ENTITY_EXTRACT_VERSION,
        "model": config.model,
        "embedding_model": emb_index.model_name,
        "graph_stats": graph.stats,
        "n": n,
        "hit8": sum(r["hit8"] for r in rows),
        "hit25": sum(r["hit25"] for r in rows),
        "hit100": sum(r["hit100"] for r in rows),
        "hit8_rate": round(sum(r["hit8"] for r in rows) / n, 4) if n else 0.0,
        "hit25_rate": round(sum(r["hit25"] for r in rows) / n, 4) if n else 0.0,
        "hit100_rate": round(sum(r["hit100"] for r in rows) / n, 4) if n else 0.0,
        "retrieval": {
            "method": "entity(BM25 soft-match +±1 sequence@0.5) + embedding",
            "entity_weight": 0.30,
            "semantic_weight": 0.70,
        },
        "by_category": {
            cat: {
                **bucket,
                "r8": round(bucket["h8"] / bucket["n"], 3),
                "r25": round(bucket["h25"] / bucket["n"], 3),
            }
            for cat, bucket in sorted(by_cat.items())
        },
        "graph_constraint": {
            "audit_passed": True,
            "graph_inputs": "conversation dialogs only",
            "qa_excluded_from_graph": True,
            "recall": "entity BM25 gate + embedding over conversation-built Memory nodes",
        },
        "outputs": {
            "graph": str(graph_path.relative_to(root)),
            "embedding_cache": str(emb_cache.relative_to(root)),
            "offline_hit": str(result_path.relative_to(root)),
        },
    }
    result_path.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2),
        encoding="utf-8",
    )
    print(
        f"[{sample_id}] DONE hit25={summary['hit25']}/{n} "
        f"({summary['hit25_rate']})",
        flush=True,
    )
    return summary


def main() -> None:
    data_file = ROOT / "data" / "locomo10.json"
    samples = json.loads(data_file.read_text(encoding="utf-8"))
    wanted_env = os.environ.get("EM_GRAPH_SAMPLE_IDS", "").strip()
    if wanted_env:
        sample_ids = [x.strip() for x in wanted_env.split(",") if x.strip()]
    else:
        sample_ids = [str(s.get("sample_id") or "") for s in samples if s.get("sample_id")]

    sample_workers = int(os.environ.get("EM_GRAPH_SAMPLE_WORKERS", "3"))
    print(
        f"Running {len(sample_ids)} samples with sample_workers={sample_workers} "
        f"extract_workers={os.environ.get('EM_GRAPH_MAX_WORKERS', '4')}",
        flush=True,
    )
    print("samples:", sample_ids, flush=True)

    per_sample: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    with ProcessPoolExecutor(max_workers=sample_workers) as pool:
        futures = {pool.submit(_run_one, sid): sid for sid in sample_ids}
        for fut in as_completed(futures):
            sid = futures[fut]
            try:
                per_sample.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                print(f"[{sid}] FAILED: {exc}", flush=True)
                errors.append({"sample_id": sid, "error": repr(exc)})

    per_sample.sort(key=lambda r: sample_ids.index(r["sample_id"]))
    n = sum(r["n"] for r in per_sample)
    hit25 = sum(r["hit25"] for r in per_sample)
    hit8 = sum(r["hit8"] for r in per_sample)
    hit100 = sum(r["hit100"] for r in per_sample)
    aggregate = {
        "env": "env.sh",
        "package": "em_graph",
        "package_version": "0.3.1",
        "entity_extract_version": "v3",
        "embedding_model": os.environ.get(
            "EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision"
        ),
        "llm_model": os.environ.get("OPENAI_MODEL", "deepseek-v4-flash"),
        "n_samples": len(per_sample),
        "n": n,
        "hit8": hit8,
        "hit25": hit25,
        "hit100": hit100,
        "hit8_rate": round(hit8 / n, 4) if n else 0.0,
        "hit25_rate": round(hit25 / n, 4) if n else 0.0,
        "hit100_rate": round(hit100 / n, 4) if n else 0.0,
        "primary_metric": "hit25",
        "retrieval": {
            "method": "entity(BM25 soft-match +±1 sequence@0.5) + embedding",
            "entity_weight": 0.30,
            "semantic_weight": 0.70,
        },
        "per_sample": per_sample,
        "errors": errors,
        "graph_constraint": {
            "audit_passed": not errors and bool(per_sample),
            "graph_inputs": "conversation dialogs only",
            "qa_excluded_from_graph": True,
            "recall": "entity BM25 gate + embedding over conversation-built Memory nodes",
        },
    }

    out_dir = ROOT / "outputs" / "em_graph"
    agg_path = out_dir / "all_offline_hit_extract_v3.json"
    exp_path = EXP_DIR / "result_all_samples.json"
    snap_dir = EXP_DIR / "snapshots" / "v02_all_samples_extract_v3"
    snap_dir.mkdir(parents=True, exist_ok=True)

    agg_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    exp_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    (snap_dir / "result_summary.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )

    print(json.dumps({k: aggregate[k] for k in (
        "n_samples", "n", "hit8", "hit25", "hit100",
        "hit8_rate", "hit25_rate", "hit100_rate", "errors",
    )}, indent=2))
    print("per_sample hit25:")
    for row in per_sample:
        print(
            f"  {row['sample_id']}: {row['hit25']}/{row['n']} "
            f"({row['hit25_rate']}) entities={row['graph_stats'].get('entity_count')}"
        )
    print("wrote", agg_path)
    print("wrote", exp_path)
    print("wrote snapshot", snap_dir)


if __name__ == "__main__":
    main()
