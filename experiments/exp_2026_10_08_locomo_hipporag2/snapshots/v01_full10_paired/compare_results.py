#!/usr/bin/env python3
"""Compare adapted HippoRAG retrieval with validated LoCoMo A/B contexts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_ROOT = ROOT.parents[1]
EXP = Path(__file__).resolve().parent
DATA = ROOT / "outputs/locomo_hipporag2/data"
HIPPO = ROOT / "outputs/locomo_hipporag2/conditions"
FORMAL = REFERENCE_ROOT / "outputs/locomo_formal"
CONDITIONS = {
    "A": "formal_all10_M1_A_top25_76fcf5b_qfrozen_run01",
    "B": "formal_all10_M1_B_top25_41a7812_qfrozen_run01",
}
DATASET_SHA = "047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74"
HIPPO_COMMIT = "d5c8329422e0a0b834a15874545cb6a74b4f9b26"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recall(context: list[str], evidence: list[str]) -> float:
    # Official aggregate treatment: empty-evidence rows contribute zero.
    return sum(item in context for item in evidence) / len(evidence) if evidence else 0.0


def main() -> None:
    if sha(ROOT / "data/locomo10.json") != DATASET_SHA:
        raise ValueError("dataset changed")
    labels = read(DATA / "offline_labels.json")
    questions = read(DATA / "retrieval_inputs.json")
    graph = read(DATA / "graph_inputs.json")
    if not (len(labels) == len(questions) == len(graph) == 10):
        raise ValueError("sample coverage differs")
    ref = {}
    query_shas = set()
    ref_identities = {}
    for side, name in CONDITIONS.items():
        directory = FORMAL / name
        config = read(directory / "run_config.json")
        validation = read(directory / "validation.json")
        prediction_path = directory / "predictions.json"
        if validation["status"] != "pass" or config["dataset_sha256"] != DATASET_SHA:
            raise ValueError(f"invalid {side} reference")
        if validation["artifact_hashes"]["prediction"]["sha256"] != sha(prediction_path):
            raise ValueError(f"changed {side} predictions")
        if config["retrieval"]["top_k"] != 25:
            raise ValueError(f"wrong {side} top-k")
        usage = read(directory / "query_cache_usage.json")
        if usage["cache_misses"] or usage["live_embedding_requests"] or usage["qa_count"] != 1986:
            raise ValueError(f"non-frozen {side} query vectors")
        query_shas.add(config["cache_identity"]["query_embedding_artifact"]["sha256"])
        ref[side] = {s["sample_id"]: s for s in read(prediction_path)}
        ref_identities[side] = {"run_id": name, "prediction_sha256": sha(prediction_path),
                                "query_artifact_sha256": config["cache_identity"]["query_embedding_artifact"]["sha256"]}
    if query_shas != {"bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f"}:
        raise ValueError("A/B query artifact mismatch")

    rows = []
    hippo_runs = []
    for lab, query, sample in zip(labels, questions, graph, strict=True):
        sid = lab["sample_id"]
        if query["sample_id"] != sid or sample["sample_id"] != sid:
            raise ValueError("sample order mismatch")
        run_id = f"locomo_hippo_{sid.replace('-', '')}_all_v01"
        result_path = HIPPO / run_id / "result.json"
        result = read(result_path)
        parameters = read(EXP / "snapshots" / run_id / "parameters.json")
        valid_ids = {t["dia_id"] for key, turns in sample["conversation"].items()
                     if key.startswith("session_") and isinstance(turns, list) for t in turns}
        if result["status"] != "complete" or result["mode"] != "full" or result["source_commit"] != HIPPO_COMMIT:
            raise ValueError(f"incomplete HippoRAG run {sid}")
        if result["classification"] != "adapted_local_retrieval_only" or result["top_k"] != 25:
            raise ValueError("HippoRAG protocol changed")
        if result["graph_input_sha256"] != sha(DATA / "graph_inputs.json") or result["retrieval_input_sha256"] != sha(DATA / "retrieval_inputs.json"):
            raise ValueError("HippoRAG data changed")
        if result["parameter_snapshot_sha256"] != sha(EXP / "snapshots" / run_id / "parameters.json"):
            raise ValueError("HippoRAG parameters changed")
        if parameters["dataset_sha256"] != DATASET_SHA or parameters["top_k"] != 25:
            raise ValueError("HippoRAG parameter identity changed")
        if max(result["prompt_scaffold_chars"].values()) > 5000 or not result["graph_constraint"].startswith("pass:"):
            raise ValueError("HippoRAG audit failed")
        if result["turn_count"] != len(valid_ids) or result["qa_count"] != len(lab["qa"]) or len(result["rows"]) != len(lab["qa"]):
            raise ValueError("HippoRAG row coverage failed")
        openie_path = HIPPO / run_id / "index/openie_results_ner_gpt-3.5-turbo-0125.json"
        openie_docs = read(openie_path)["docs"]
        if len(openie_docs) != result["turn_count"] or len({item["idx"] for item in openie_docs}) != result["turn_count"]:
            raise ValueError("HippoRAG OpenIE passage coverage failed")
        hippo_runs.append({"run_id": run_id, "sha256": sha(result_path), "usage": result["usage"],
                           "turn_count": result["turn_count"], "qa_count": result["qa_count"],
                           "graph_nodes": result["graph_nodes"], "graph_edges": result["graph_edges"],
                           "openie_doc_count": len(openie_docs),
                           "openie_empty_entity_docs": sum(not item["extracted_entities"] for item in openie_docs),
                           "openie_empty_triple_docs": sum(not item["extracted_triples"] for item in openie_docs),
                           "elapsed_seconds": result["elapsed_seconds"]})
        for i, (gold, q, h) in enumerate(zip(lab["qa"], query["qa"], result["rows"], strict=True)):
            if h["sample_id"] != sid or h["qa_index"] != i:
                raise ValueError("HippoRAG order differs")
            contexts = {"HippoRAG2": h["context_ids"]}
            for side in ("A", "B"):
                a = ref[side][sid]["qa"][i]
                if a["question"] != q["question"] or a["evidence"] != gold["evidence"] or a["category"] != gold["category"]:
                    raise ValueError(f"reference {side} QA mismatch")
                contexts[side] = a["gpt-3.5-turbo_dialog_top_25_prediction_context"]
            for side, ids in contexts.items():
                if len(ids) != 25 or len(set(ids)) != 25 or set(ids) - valid_ids:
                    raise ValueError(f"invalid {side} top-25 IDs for {sid} QA {i}")
            scores = {side: recall(ids, gold["evidence"]) for side, ids in contexts.items()}
            rows.append({"sample_id": sid, "qa_index": i, "category": gold["category"],
                         "evidence_count": len(gold["evidence"]), "scores": scores})
    if len(rows) != 1986:
        raise ValueError("wrong QA denominator")

    names = ("A", "B", "HippoRAG2")
    overall = {name: mean(row["scores"][name] for row in rows) for name in names}
    for side, name in CONDITIONS.items():
        stats = read(FORMAL / name / "stats.json")["gpt-3.5-turbo_dialog_top_25"]
        serialized_mean = sum(stats["recall_by_category"][category] * count
                              for category, count in stats["category_counts"].items()) / 1986
        if abs(overall[side] - serialized_mean) > 0.0005:
            raise ValueError(f"{side} offline recall diverges from frozen official stats")
    by_category = {str(c): {name: mean(row["scores"][name] for row in rows if row["category"] == c)
                             for name in names} for c in (1, 2, 3, 4, 5)}
    by_conversation = {sid: {name: mean(row["scores"][name] for row in rows if row["sample_id"] == sid)
                              for name in names} for sid in [sample["sample_id"] for sample in graph]}
    clusters = {sid: [row for row in rows if row["sample_id"] == sid] for sid in by_conversation}
    rng = random.Random(20261008)
    pairs = (("B", "A"), ("HippoRAG2", "A"), ("HippoRAG2", "B"))
    draws = {f"{left}-{right}": [] for left, right in pairs}
    ids = list(clusters)
    for _ in range(10000):
        selected = [row for _sid in rng.choices(ids, k=len(ids)) for row in clusters[_sid]]
        for left, right in pairs:
            draws[f"{left}-{right}"].append(mean(row["scores"][left] - row["scores"][right] for row in selected))
    paired = {}
    for left, right in pairs:
        key = f"{left}-{right}"
        ordered = sorted(draws[key])
        paired[key] = {"difference": overall[left] - overall[right],
                       "cluster_bootstrap_95_ci": [ordered[249], ordered[9749]],
                       "conversation_improved_count": sum(by_conversation[sid][left] > by_conversation[sid][right] for sid in ids)}
    total_usage = {key: sum(run["usage"].get(key, 0) for run in hippo_runs) for key in hippo_runs[0]["usage"] if isinstance(hippo_runs[0]["usage"][key], int)}
    report = {"schema": "locomo_hipporag2_adapted_retrieval_v1", "classification": "adapted_local_retrieval_only",
              "dataset_sha256": DATASET_SHA, "qa_count": len(rows), "conversation_count": len(ids),
              "top_k": 25, "metric": "official-definition per-QA evidence fraction, empty evidence contributes zero; no answer generation",
              "reference": ref_identities, "hipporag_upstream_commit": HIPPO_COMMIT,
              "hipporag_runs": hippo_runs, "total_usage": total_usage,
              "overall": overall, "by_category": by_category, "by_conversation": by_conversation,
              "paired_differences": paired, "bootstrap_seed": 20261008, "bootstrap_resamples": 10000,
              "empty_evidence_rows": sum(not row["evidence_count"] for row in rows)}
    output = EXP / "result.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "outputs/locomo_hipporag2/paired_rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"overall": overall, "paired_differences": paired, "total_usage": total_usage}, indent=2))


if __name__ == "__main__":
    main()
