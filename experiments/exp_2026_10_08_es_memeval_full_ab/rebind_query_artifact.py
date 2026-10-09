#!/usr/bin/env python3
"""Bind already frozen vectors to an identical ordered QA set in retrieval input."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from em_graph import QueryEmbeddingArtifact
from em_graph.cache import ordered_question_records


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-artifact", type=Path, required=True)
    p.add_argument("--source-data", type=Path, required=True)
    p.add_argument("--target-data", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("target artifact/report must be absent")
    source = QueryEmbeddingArtifact.load(args.source_artifact)
    source_rows = json.loads(args.source_data.read_text())
    target_rows = json.loads(args.target_data.read_text())
    source.validate_exact_dataset(source_rows, dataset_sha256=sha(args.source_data), model_name="text-embedding-3-small", role="context", normalization="l2_float32_v1", protocol_identity={})
    if source.qa_records != ordered_question_records(target_rows):
        raise ValueError("ordered question records differ")
    if len(source.qa_records) != 1427 or len(source.question_digests) != 1420:
        raise ValueError("question/vector coverage differs")
    vectors = np.array(source.vectors, copy=True)
    target = QueryEmbeddingArtifact(dataset_sha256=sha(args.target_data), model_name=source.model_name, role=source.role, qa_records=source.qa_records, question_digests=source.question_digests, vectors=vectors, normalization=source.normalization, protocol_identity=source.protocol_identity)
    target.validate_exact_dataset(target_rows, dataset_sha256=sha(args.target_data), model_name="text-embedding-3-small", role="context", normalization="l2_float32_v1", protocol_identity={})
    if not np.array_equal(source.vectors, target.vectors):
        raise RuntimeError("vector values changed")
    target.save(args.output)
    report = {"schema": "query_artifact_rebind_v1", "status": "pass", "source_artifact": source.identity(args.source_artifact), "target_artifact": target.identity(args.output), "ordered_question_records_equal": True, "vector_values_equal": True, "vector_array_sha256": hashlib.sha256(source.vectors.tobytes()).hexdigest(), "live_embedding_requests": 0}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
