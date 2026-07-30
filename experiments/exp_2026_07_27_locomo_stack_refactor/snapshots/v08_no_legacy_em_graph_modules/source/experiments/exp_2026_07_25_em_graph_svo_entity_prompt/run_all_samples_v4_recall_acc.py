#!/usr/bin/env python3
"""Rebuild all LoCoMo samples with extract-v4 and score official recall_acc.

Locks fusion to 0.40E+0.60S to match the extract-v3 all-10 baseline
(recall_acc@25 = 0.7997, n=1982). Reuses completed non-partial v4 graphs and
v3 memory-embedding caches (same Memory digests). Fresh v4 question-entity keys.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

ENTITY_WEIGHT = 0.40
SEMANTIC_WEIGHT = 0.60
V3_BASELINE = {
    "recall_acc8": 0.6348,
    "recall_acc25": 0.7997,
    "recall_acc100": 0.9195,
    "hit25": 1692,
    "hit25_rate": 0.8537,
    "n": 1982,
    "n_samples": 10,
}


def _locomo_recall_acc(gold: List[str], retrieved: List[str]) -> float:
    if not gold:
        return 1.0
    ctx = set(retrieved)
    return float(sum(1 for ev in gold if ev in ctx)) / float(len(gold))


def _run_one(sample_id: str) -> Dict[str, Any]:
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

    graph_path = out_dir / f"{sample_id}_em_graph_extract_v4.json"
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision")
    emb_cache_v3 = (
        out_dir
        / f"{sample_id}_memory_emb_extract_v3_{emb_model.replace('/', '_')}.npz"
    )
    emb_cache_v4 = (
        out_dir
        / f"{sample_id}_memory_emb_extract_v4_{emb_model.replace('/', '_')}.npz"
    )
    result_path = out_dir / f"{sample_id}_offline_locomo_recall_acc_extract_v4.json"

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
        f"[{sample_id}] start extract={ENTITY_EXTRACT_VERSION} "
        f"model={config.model} embed={emb_model} "
        f"reuse={reuse and graph_path.exists()}",
        flush=True,
    )
    if ENTITY_EXTRACT_VERSION != "v4":
        raise RuntimeError(
            f"expected ENTITY_EXTRACT_VERSION=v4, got {ENTITY_EXTRACT_VERSION!r}"
        )

    graph = None
    if reuse and graph_path.exists():
        loaded = EMGraph.load_from_file(str(graph_path))
        if bool((loaded.stats or {}).get("partial")):
            print(
                f"[{sample_id}] graph partial; resuming build",
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

    emb_cache = emb_cache_v3 if emb_cache_v3.exists() else emb_cache_v4
    emb_index = MemoryEmbeddingIndex.build(
        graph, model_name=emb_model, cache_path=str(emb_cache)
    )
    if emb_cache == emb_cache_v3 and not emb_cache_v4.exists():
        try:
            shutil.copy2(emb_cache_v3, emb_cache_v4)
        except OSError:
            pass
    entity_bm25 = EntityBM25Index.build(graph)
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
    reuse_q = os.environ.get("EM_GRAPH_REUSE_Q_KEYS", "1").strip() in {
        "1",
        "true",
        "True",
    }
    if reuse_q and result_path.exists():
        prev = json.loads(result_path.read_text(encoding="utf-8"))
        for row in prev.get("rows") or []:
            keys = row.get("q_entity_keys") or []
            if keys:
                q_keys_by_qa[int(row["qa"])] = set(keys)
        if q_keys_by_qa:
            print(
                f"[{sample_id}] reused v4 q_entity_keys n={len(q_keys_by_qa)}",
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

    rows: List[Dict[str, Any]] = []
    print(f"[{sample_id}] scoring n={len(jobs)}", flush=True)
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

    by_cat: Dict[str, Dict[str, float]] = {}
    for row in rows:
        cat = row["category"]
        b = by_cat.setdefault(cat, {"n": 0, "ra25_sum": 0.0, "h25": 0})
        b["n"] += 1
        b["ra25_sum"] += float(row["recall_acc25"])
        b["h25"] += int(row["hit25"])

    summary: Dict[str, Any] = {
        "sample_id": sample_id,
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
        "by_category": {
            cat: {
                "n": int(b["n"]),
                "recall_acc25": round(b["ra25_sum"] / b["n"], 4),
                "hit25_rate": round(b["h25"] / b["n"], 4),
            }
            for cat, b in sorted(by_cat.items())
        },
        "retrieval": {
            "method": "entity(BM25 soft-match +±1 sequence@0.5) + embedding",
            "entity_weight": ENTITY_WEIGHT,
            "semantic_weight": SEMANTIC_WEIGHT,
        },
        "outputs": {
            "graph": str(graph_path.relative_to(root)),
            "embedding_cache": str(Path(emb_cache).relative_to(root)),
            "offline_recall_acc": str(result_path.relative_to(root)),
        },
    }
    result_path.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2),
        encoding="utf-8",
    )
    print(
        f"[{sample_id}] DONE recall_acc@25={summary['recall_acc25']} "
        f"binary_hit25={summary['hit25']}/{n}",
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
        sample_ids = [
            str(s.get("sample_id") or "") for s in samples if s.get("sample_id")
        ]

    sample_workers = int(os.environ.get("EM_GRAPH_SAMPLE_WORKERS", "2"))
    print(
        f"LoCoMo extract-v4 recall_acc: {len(sample_ids)} samples, "
        f"sample_workers={sample_workers}, "
        f"extract_workers={os.environ.get('EM_GRAPH_MAX_WORKERS', '4')}, "
        f"fusion={ENTITY_WEIGHT}/{SEMANTIC_WEIGHT}",
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
    n = sum(int(r["n"]) for r in per_sample)

    def _wmean(key: str) -> float:
        if not n:
            return 0.0
        return round(
            sum(float(r[key]) * int(r["n"]) for r in per_sample) / n, 4
        )

    aggregate = {
        "env": "env_ark.sh",
        "metric": "locomo_recall_acc",
        "package": "em_graph",
        "entity_extract_version": "v4",
        "embedding_model": os.environ.get(
            "EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision"
        ),
        "llm_model": os.environ.get("OPENAI_MODEL", "deepseek-v4-flash"),
        "n_samples": len(per_sample),
        "n": n,
        "recall_acc8": _wmean("recall_acc8"),
        "recall_acc25": _wmean("recall_acc25"),
        "recall_acc100": _wmean("recall_acc100"),
        "hit8": sum(int(r["hit8"]) for r in per_sample),
        "hit25": sum(int(r["hit25"]) for r in per_sample),
        "hit100": sum(int(r["hit100"]) for r in per_sample),
        "hit8_rate": round(sum(int(r["hit8"]) for r in per_sample) / n, 4)
        if n
        else 0.0,
        "hit25_rate": round(sum(int(r["hit25"]) for r in per_sample) / n, 4)
        if n
        else 0.0,
        "hit100_rate": round(sum(int(r["hit100"]) for r in per_sample) / n, 4)
        if n
        else 0.0,
        "primary_metric": "recall_acc25",
        "baseline_v3": V3_BASELINE,
        "delta_vs_v3": {
            "recall_acc25": round(_wmean("recall_acc25") - V3_BASELINE["recall_acc25"], 4),
            "hit25": int(
                sum(int(r["hit25"]) for r in per_sample) - V3_BASELINE["hit25"]
            ),
            "hit25_rate": round(
                (
                    sum(int(r["hit25"]) for r in per_sample) / n
                    if n
                    else 0.0
                )
                - V3_BASELINE["hit25_rate"],
                4,
            ),
        },
        "retrieval": {
            "method": "entity(BM25 soft-match +±1 sequence@0.5) + embedding",
            "entity_weight": ENTITY_WEIGHT,
            "semantic_weight": SEMANTIC_WEIGHT,
        },
        "prompt_budget": {
            "checked": True,
            "note": "extract v4 scaffold only; no answer-generation prompt",
        },
        "per_sample": per_sample,
        "errors": errors,
        "graph_constraint": {
            "audit_passed": not errors and bool(per_sample),
            "graph_inputs": "conversation dialogs only",
            "qa_excluded_from_graph": True,
            "recall": "LoCoMo recall_acc over conversation-built Memory retrieval",
        },
    }

    out_dir = ROOT / "outputs" / "em_graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    agg_path = out_dir / "all_offline_locomo_recall_acc_extract_v4.json"
    exp_path = EXP_DIR / "result_all_samples_v4_recall_acc.json"
    snap_dir = EXP_DIR / "snapshots" / "v04_all10_v4_recall_acc"
    snap_dir.mkdir(parents=True, exist_ok=True)

    agg_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    exp_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    (snap_dir / "result_summary.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )
    shutil.copy2(Path(__file__), snap_dir / "source_run_all_samples_v4_recall_acc.py")
    shutil.copy2(
        ROOT / "em_graph" / "config.py", snap_dir / "source_em_graph_config.py"
    )

    print(
        json.dumps(
            {
                k: aggregate[k]
                for k in (
                    "n_samples",
                    "n",
                    "recall_acc8",
                    "recall_acc25",
                    "recall_acc100",
                    "hit25_rate",
                    "delta_vs_v3",
                    "errors",
                )
            },
            indent=2,
        )
    )
    print("per_sample recall_acc@25 / binary hit@25:")
    for row in per_sample:
        print(
            f"  {row['sample_id']}: ra25={row['recall_acc25']} "
            f"hit25={row['hit25']}/{row['n']} "
            f"entities={row['graph_stats'].get('entity_count')}"
        )
    print("wrote", agg_path)
    print("wrote", exp_path)
    print("wrote snapshot", snap_dir)


if __name__ == "__main__":
    main()
