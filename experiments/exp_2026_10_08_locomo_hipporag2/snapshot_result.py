#!/usr/bin/env python3
"""Write a compact committed snapshot pointer for one completed condition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()
    base = ROOT / "outputs/locomo_hipporag2/conditions" / args.run_id
    snapshot = EXP / "snapshots" / args.run_id
    if not snapshot.is_dir():
        raise FileNotFoundError("frozen pre-run snapshot is missing")
    result_file = base / "result.json"
    result = json.loads(result_file.read_text(encoding="utf-8"))
    if result["status"] != "complete" or result["run_id"] != args.run_id:
        raise ValueError("condition is incomplete")
    openie_file = base / "index/openie_results_ner_gpt-3.5-turbo-0125.json"
    docs = json.loads(openie_file.read_text(encoding="utf-8"))["docs"]
    keys = ("status", "classification", "run_id", "source_commit",
            "parameter_snapshot_sha256", "graph_input_sha256", "retrieval_input_sha256",
            "rerank_prompt_sha256", "turn_count", "qa_count", "top_k",
            "prompt_scaffold_chars", "graph_nodes", "graph_edges", "entity_count",
            "fact_count", "usage", "elapsed_seconds", "graph_constraint", "answer_judge")
    summary = {key: result[key] for key in keys}
    summary.update({
        "result_sha256": hashlib.sha256(result_file.read_bytes()).hexdigest(),
        "openie_sha256": hashlib.sha256(openie_file.read_bytes()).hexdigest(),
        "openie_doc_count": len(docs),
        "openie_empty_entity_docs": sum(not doc["extracted_entities"] for doc in docs),
        "openie_empty_triple_docs": sum(not doc["extracted_triples"] for doc in docs),
        "top25_all_unique": all(len(row["context_ids"]) == 25 and
                            len(set(row["context_ids"])) == 25 for row in result["rows"]),
    })
    if len(docs) != result["turn_count"] or not summary["top25_all_unique"]:
        raise ValueError("OpenIE or retrieval coverage failed")
    output = snapshot / "result_summary.json"
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        for key, value in existing.items():
            if key in summary and summary[key] != value:
                raise ValueError(f"existing snapshot differs at {key}")
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
