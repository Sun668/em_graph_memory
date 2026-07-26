#!/usr/bin/env python3
"""P0: Table-3 style multi-k recall sheet for Entity→Memory Dialog-family RAG.

1) Frozen top-25 contexts from all-10 predictions → recall/hit @5/10/25 + F1@25
   (aligned with the deepseek answer run).
2) Offline re-retrieve top-50 (extract-v4, 0.3/0.7) → recall/hit @5/10/25/50.

No answer generation. No Mem0 judge.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from em_graph import (  # noqa: E402
    EMGraph,
    EntityBM25Index,
    MemoryEmbeddingIndex,
    assert_bipartite,
    ensure_memory_sequence_edges,
    retrieve_dialog_ids,
)

ENTITY_WEIGHT = 0.30
SEMANTIC_WEIGHT = 0.70
KS = (5, 10, 25, 50)
CAT_NAMES = {
    1: "Multi-hop",
    2: "Temporal",
    3: "Open-domain",
    4: "Single-hop",
    5: "Adversarial",
}
PRED_KEY = "em_graph_v4_locomo_rag_top25_prediction"
CONTEXT_KEY = PRED_KEY + "_context"
F1_KEY = PRED_KEY + "_token_f1"

PAPER_DIALOG = {
    5: {"f1": 38.8, "r": 56.7},
    10: {"f1": 39.7, "r": 66.2},
    25: {"f1": 41.0, "r": 76.7},
    50: {"f1": 40.5, "r": 82.7},
}
PAPER_OBS_BEST = {"k": 5, "f1": 43.3, "note": "Observation-RAG best F1 in Table 3"}
PAPER_SUMMARY_R10 = {"k": 10, "f1": 32.0, "r": 84.7}


def recall_acc(gold: List[str], retrieved: List[str]) -> float:
    if not gold:
        return 1.0
    ctx = set(retrieved)
    return float(sum(1 for ev in gold if ev in ctx)) / float(len(gold))


def hit_any(gold: List[str], retrieved: List[str]) -> bool:
    if not gold:
        return True
    return bool(set(gold) & set(retrieved))


def empty_bucket() -> Dict[str, Any]:
    return {
        "n": 0,
        "recall_sum": 0.0,
        "hit": 0,
        "f1_sum": 0.0,
        "f1_n": 0,
    }


def add_row(
    buckets: Dict[str, Dict[str, Any]],
    *,
    cat: int,
    ra: float,
    hit: bool,
    f1: Optional[float] = None,
) -> None:
    for key in ("overall", str(cat)):
        b = buckets.setdefault(key, empty_bucket())
        b["n"] += 1
        b["recall_sum"] += float(ra)
        b["hit"] += int(bool(hit))
        if f1 is not None:
            b["f1_sum"] += float(f1)
            b["f1_n"] += 1


def finalize(buckets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, b in buckets.items():
        n = max(int(b["n"]), 1)
        row = {
            "n": b["n"],
            "recall_acc": round(b["recall_sum"] / n, 4),
            "hit_rate": round(b["hit"] / n, 4),
            "hit": b["hit"],
        }
        if b["f1_n"]:
            row["token_f1"] = round(b["f1_sum"] / b["f1_n"], 4)
            row["token_f1_pct"] = round(100.0 * b["f1_sum"] / b["f1_n"], 2)
            row["f1_n"] = b["f1_n"]
        if key != "overall":
            row["name"] = CAT_NAMES.get(int(key), key)
        out[key] = row
    return out


def load_q_keys(sample_id: str, out_dir: Path) -> Dict[int, Set[str]]:
    for name in (
        f"{sample_id}_offline_locomo_recall_acc_extract_v4_e03s07.json",
        f"{sample_id}_offline_locomo_recall_acc_extract_v4.json",
    ):
        path = out_dir / name
        if not path.exists():
            continue
        prev = json.loads(path.read_text(encoding="utf-8"))
        out: Dict[int, Set[str]] = {}
        for row in prev.get("rows") or []:
            keys = row.get("q_entity_keys") or []
            if keys:
                out[int(row["qa"])] = set(keys)
        return out
    return {}


def score_frozen_top25(pred_path: Path, data_file: Path) -> Dict[str, Any]:
    preds = json.loads(pred_path.read_text(encoding="utf-8"))
    data = {s["sample_id"]: s for s in json.loads(data_file.read_text(encoding="utf-8"))}
    by_k: Dict[int, Dict[str, Dict[str, Any]]] = {k: {} for k in (5, 10, 25)}
    for sample in preds:
        sid = sample["sample_id"]
        gold_by_q = {
            str(qa.get("question") or ""): qa
            for qa in (data[sid].get("qa") or [])
        }
        for qa in sample.get("qa") or []:
            q = str(qa.get("question") or "")
            ctx = list(qa.get(CONTEXT_KEY) or [])
            if not ctx:
                continue
            src = gold_by_q.get(q) or qa
            gold = [str(x) for x in (src.get("evidence") or []) if str(x)]
            if not gold:
                continue
            cat = int(src.get("category") or qa.get("category") or 0)
            f1 = qa.get(F1_KEY)
            f1_v = float(f1) if f1 is not None else None
            for k in (5, 10, 25):
                top = ctx[:k]
                add_row(
                    by_k[k],
                    cat=cat,
                    ra=recall_acc(gold, top),
                    hit=hit_any(gold, top),
                    f1=f1_v if k == 25 else None,
                )
    return {
        "source": str(pred_path),
        "note": "Truncated frozen top-25 context_ids from deepseek answer run; F1 only at k=25",
        "by_k": {str(k): finalize(by_k[k]) for k in (5, 10, 25)},
    }


def retrieve_all_top50(out_dir: Path, data_file: Path) -> Dict[str, Any]:
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision")
    workers = int(os.environ.get("EM_GRAPH_MAX_WORKERS", "6"))
    samples = json.loads(data_file.read_text(encoding="utf-8"))
    by_k: Dict[int, Dict[str, Dict[str, Any]]] = {k: {} for k in KS}
    n_scored = 0
    ranking_dump: List[Dict[str, Any]] = []

    for sample in samples:
        sid = str(sample.get("sample_id") or "")
        graph_path = out_dir / f"{sid}_em_graph_extract_v4.json"
        emb_cache = (
            out_dir / f"{sid}_memory_emb_extract_v4_{emb_model.replace('/', '_')}.npz"
        )
        if not graph_path.exists():
            raise FileNotFoundError(graph_path)
        if not emb_cache.exists():
            raise FileNotFoundError(emb_cache)

        graph = EMGraph.load_from_file(str(graph_path))
        ensure_memory_sequence_edges(graph)
        assert_bipartite(graph)
        emb_index = MemoryEmbeddingIndex.build(
            graph, model_name=emb_model, cache_path=str(emb_cache)
        )
        entity_bm25 = EntityBM25Index.build(graph)
        q_keys = load_q_keys(sid, out_dir)

        jobs: List[Tuple[int, Dict[str, Any], List[str]]] = []
        for i, qa in enumerate(sample.get("qa") or [], 1):
            gold = [str(x) for x in (qa.get("evidence") or []) if str(x)]
            q = str(qa.get("question") or "").strip()
            if not q or not gold:
                continue
            jobs.append((i, qa, gold))

        print(f"[{sid}] retrieve top50 n={len(jobs)} emb={emb_model}", flush=True)

        def _one(item: Tuple[int, Dict[str, Any], List[str]]):
            i, qa, gold = item
            ranked = retrieve_dialog_ids(
                graph,
                str(qa.get("question") or ""),
                top_k=50,
                embedding_index=emb_index,
                entity_bm25_index=entity_bm25,
                q_entity_keys=q_keys.get(i, set()),
                entity_weight=ENTITY_WEIGHT,
                semantic_weight=SEMANTIC_WEIGHT,
            )
            dias = [d for d, _ in ranked]
            return i, qa, gold, dias

        with ThreadPoolExecutor(max_workers=min(workers, 4)) as pool:
            futs = [pool.submit(_one, job) for job in jobs]
            done = 0
            for fut in as_completed(futs):
                i, qa, gold, dias = fut.result()
                cat = int(qa.get("category") or 0)
                for k in KS:
                    top = dias[:k]
                    add_row(
                        by_k[k],
                        cat=cat,
                        ra=recall_acc(gold, top),
                        hit=hit_any(gold, top),
                    )
                ranking_dump.append(
                    {
                        "sample_id": sid,
                        "qa": i,
                        "category": cat,
                        "n_evidence": len(gold),
                        "retrieved50": dias,
                    }
                )
                n_scored += 1
                done += 1
                if done % 40 == 0 or done == len(jobs):
                    print(f"[{sid}] {done}/{len(jobs)}", flush=True)

    return {
        "embedding_model": emb_model,
        "fusion": f"{ENTITY_WEIGHT}/{SEMANTIC_WEIGHT}",
        "entity_extract_version": "v4",
        "n_scored": n_scored,
        "by_k": {str(k): finalize(by_k[k]) for k in KS},
        "ranking_rows": ranking_dump,
    }


def paper_compare_table(retr: Dict[str, Any], frozen: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for k in KS:
        ours = retr["by_k"][str(k)]["overall"]
        paper = PAPER_DIALOG.get(k, {})
        row = {
            "k": k,
            "ours_recall_acc": ours["recall_acc"],
            "ours_hit_rate": ours["hit_rate"],
            "paper_dialog_R": paper.get("r"),
            "paper_dialog_F1": paper.get("f1"),
            "delta_R_vs_paper_dialog": round(
                100.0 * ours["recall_acc"] - float(paper["r"]), 2
            )
            if paper.get("r") is not None
            else None,
        }
        if k <= 25:
            fr = frozen["by_k"][str(k)]["overall"]
            row["frozen_top25_trunc_recall_acc"] = fr["recall_acc"]
            row["frozen_top25_trunc_hit_rate"] = fr["hit_rate"]
        if k == 25 and "token_f1_pct" in frozen["by_k"]["25"]["overall"]:
            row["ours_F1_deepseek_top25"] = frozen["by_k"]["25"]["overall"]["token_f1_pct"]
        rows.append(row)
    return rows


def main() -> None:
    out_dir = ROOT / "outputs" / "em_graph"
    data_file = ROOT / "data" / "locomo10.json"
    pred_path = out_dir / "all10_locomo_rag_extract_v4_top25_predictions.json"
    result_path = EXP_DIR / "result_p0_multik_recall_sheet.json"
    ranking_path = out_dir / "all10_em_v4_e03s07_retrieved50.json"
    sheet_md = EXP_DIR / "TABLE3_COMPARE_P0.md"
    snap_dir = EXP_DIR / "snapshots" / "v01_p0_multik_recall_sheet"

    print("[p0] scoring frozen top25 contexts", flush=True)
    frozen = score_frozen_top25(pred_path, data_file)
    print("[p0] re-retrieving top50 all-10", flush=True)
    retr = retrieve_all_top50(out_dir, data_file)
    ranking_rows = retr.pop("ranking_rows")
    ranking_path.write_text(
        json.dumps(
            {
                "fusion": retr["fusion"],
                "embedding_model": retr["embedding_model"],
                "entity_extract_version": "v4",
                "n": len(ranking_rows),
                "rows": ranking_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    compare = paper_compare_table(retr, frozen)
    f1_25 = frozen["by_k"]["25"]["overall"]
    payload = {
        "experiment": "exp_2026_07_26_locomo_official_compare",
        "phase": "P0",
        "metric": "locomo_table3_style_dialog_family",
        "package": "em_graph",
        "retrieval_unit": "dialog_turn",
        "reader_for_f1": "deepseek-v4-flash (existing answers; not paper gpt-3.5)",
        "paper_anchors": {
            "dialog": PAPER_DIALOG,
            "observation_best_f1": PAPER_OBS_BEST,
            "summary_r10": PAPER_SUMMARY_R10,
            "human_f1": 87.9,
            "gpt4_turbo_longctx_f1": 51.6,
        },
        "frozen_top25_answer_run": frozen,
        "rereanked_top50": retr,
        "compare_vs_paper_dialog": compare,
        "f1_top25_deepseek": {
            "overall_pct": f1_25.get("token_f1_pct"),
            "by_category": {
                k: v
                for k, v in frozen["by_k"]["25"].items()
                if k != "overall"
            },
        },
        "outputs": {
            "result": str(result_path),
            "ranking50": str(ranking_path),
            "sheet_md": str(sheet_md),
        },
        "graph_constraint_audit": {
            "graph_inputs": "conversation dialogs/captions/speakers/session anchors only (extract-v4 EM graphs)",
            "qa_excluded_from_graph": True,
            "answer_uses_graph_retrieval": True,
            "f1_reader_aligned_to_paper": False,
        },
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# P0 Table-3 style compare (Entity→Memory Dialog-family)",
        "",
        "Retrieval: extract-v4, fusion **0.30E+0.70Embed**, dialog turns.",
        "F1@25 from existing **deepseek-v4-flash** answers (not paper gpt-3.5).",
        "Recall@k from offline re-retrieve top-50 (same fusion).",
        "",
        "## Ours vs paper Dialog-RAG (Overall)",
        "",
        "| k | Ours recall_acc | Ours hit | Paper Dialog R@k | ΔR (pp) | Paper Dialog F1 | Ours F1 (deepseek) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in compare:
        f1 = row.get("ours_F1_deepseek_top25")
        f1_s = f"{f1:.2f}" if f1 is not None else "—"
        lines.append(
            f"| {row['k']} | {100*row['ours_recall_acc']:.2f} | "
            f"{100*row['ours_hit_rate']:.2f} | {row['paper_dialog_R']} | "
            f"{row['delta_R_vs_paper_dialog']:+.2f} | {row['paper_dialog_F1']} | {f1_s} |"
        )
    lines += [
        "",
        f"Paper Observation best F1: **{PAPER_OBS_BEST['f1']}** (@{PAPER_OBS_BEST['k']}).",
        f"Paper Summary @10: F1 {PAPER_SUMMARY_R10['f1']}, R {PAPER_SUMMARY_R10['r']}.",
        "",
        "## Ours recall_acc by category (re-retrieve)",
        "",
    ]
    for k in KS:
        lines.append(f"### k={k}")
        lines.append("")
        lines.append("| cat | name | n | recall_acc | hit_rate |")
        lines.append("|---:|---|---:|---:|---:|")
        block = retr["by_k"][str(k)]
        o = block["overall"]
        lines.append(
            f"| all | Overall | {o['n']} | {100*o['recall_acc']:.2f} | {100*o['hit_rate']:.2f} |"
        )
        for cat in ("1", "2", "3", "4", "5"):
            b = block[cat]
            lines.append(
                f"| {cat} | {b['name']} | {b['n']} | "
                f"{100*b['recall_acc']:.2f} | {100*b['hit_rate']:.2f} |"
            )
        lines.append("")
    lines += [
        "## F1@25 by category (deepseek, frozen answers)",
        "",
        "| cat | name | n | F1% |",
        "|---:|---|---:|---:|",
    ]
    for cat in ("1", "2", "3", "4", "5", "overall"):
        b = frozen["by_k"]["25"][cat if cat != "overall" else "overall"]
        name = b.get("name", "Overall")
        lines.append(
            f"| {cat if cat!='overall' else 'all'} | {name} | {b.get('f1_n', b['n'])} | "
            f"{b.get('token_f1_pct', float('nan')):.2f} |"
        )
    lines += [
        "",
        "## Constraint audit",
        "",
        "- Graph: conversation-only extract-v4 EM graphs.",
        "- QA/judge/evidence annotations excluded from graph construction.",
        "- Answer F1 uses graph-retrieved dialog evidence (top25).",
        "- Reader **not** yet aligned to paper gpt-3.5 (see P1).",
        "",
    ]
    sheet_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "phase": "P0",
                "compare_vs_paper_dialog": compare,
                "f1_top25_deepseek": payload["f1_top25_deepseek"],
                "rereanked_top50_overall": {
                    str(k): retr["by_k"][str(k)]["overall"] for k in KS
                },
                "graph_constraint_audit": payload["graph_constraint_audit"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (snap_dir / "source_run_p0_multik_recall_sheet.py").write_text(
        Path(__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (snap_dir / "TABLE3_COMPARE_P0.md").write_text(
        sheet_md.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (snap_dir / "NOTES.md").write_text(
        "\n".join(
            [
                "# v01_p0_multik_recall_sheet",
                "",
                "## Command",
                "",
                "```bash",
                "source env_ark.sh",
                "python experiments/exp_2026_07_26_locomo_official_compare/run_p0_multik_recall_sheet.py",
                "```",
                "",
                "## Settings",
                "",
                "- extract-v4, fusion 0.30/0.70, emb=doubao-embedding-vision",
                "- retrieval unit: dialog turns",
                "- F1 from existing deepseek top25 answers",
                "",
                "## Mandatory graph constraint",
                "",
                "PASS for retrieval sheet (conversation-built graphs; QA excluded).",
                "F1 reader not paper-aligned yet → do not claim F1 SOTA until P1.",
                "",
                "## Counts toward target?",
                "",
                "Recall comparison: yes as diagnostic vs paper Dialog R@k.",
                "F1 claim: **not yet** (await P1 gpt-3.5).",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"compare": compare, "f1_25": f1_25}, indent=2), flush=True)
    print(f"wrote {result_path}", flush=True)
    print(f"wrote {sheet_md}", flush=True)
    print(f"snapshot {snap_dir}", flush=True)


if __name__ == "__main__":
    main()
