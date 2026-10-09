#!/usr/bin/env python3
"""Separate all published-release QA into conversation, question, and offline gold files."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    samples = json.loads(args.source.read_text())
    if len(samples) != 18 or sum(len(x["qa"]) for x in samples) != 1427:
        raise ValueError("unexpected full-release scope")
    ids = [x["sample_id"] for x in samples]
    if len(set(ids)) != 18:
        raise ValueError("duplicate user")
    graph = [{"sample_id": x["sample_id"], "conversation": x["conversation"]} for x in samples]
    questions = [{"sample_id": x["sample_id"], "qa": [{"question": q["question"]} for q in x["qa"]]} for x in samples]
    retrieval = [{"sample_id": x["sample_id"], "conversation": x["conversation"], "qa": [{"question": q["question"]} for q in x["qa"]]} for x in samples]
    gold = [{"sample_id": x["sample_id"], "qa_index": i, "answer": q["answer"], "capability": q["capability"], "evidence": q["evidence"]} for x in samples for i, q in enumerate(x["qa"])]
    if any(set(x) != {"sample_id", "conversation"} for x in graph):
        raise ValueError("graph-only fields invalid")
    if any(set(q) != {"question"} for x in retrieval for q in x["qa"]):
        raise ValueError("question-only retrieval fields invalid")
    args.output_dir.mkdir(parents=True)
    files = {"graph_inputs.json": graph, "questions.json": questions, "retrieval_inputs.json": retrieval, "gold.json": gold}
    for name, value in files.items():
        write(args.output_dir / name, value)
    direct = Counter()
    for sample in samples:
        dialog_ids = {str(t["dia_id"]) for turns in sample["conversation"].values() if isinstance(turns, list) for t in turns}
        for q in sample["qa"]:
            if q["capability"].lower() != "abstention" and any(str(e) in dialog_ids for e in q["evidence"]):
                direct["eligible_nonabstention"] += 1
            elif q["capability"].lower() == "abstention":
                direct["abstention_excluded"] += 1
            else:
                direct["no_direct_dialog_evidence"] += 1
    manifest = {"source_path": str(args.source.resolve()), "source_sha256": sha(args.source), "sample_ids": ids, "qa_count": len(gold), "turn_count": sum(len(turns) for x in samples for turns in x["conversation"].values() if isinstance(turns, list)), "evidence_scope": dict(direct), "files": {name: sha(args.output_dir / name) for name in files}, "graph_input": "sample_id plus conversation only", "retrieval_input": "conversation plus question text only; no answer/evidence/category", "gold_use": "offline comparison only"}
    write(args.output_dir / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
