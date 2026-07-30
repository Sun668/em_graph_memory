#!/usr/bin/env python3
"""Build one immutable, dataset-bound query embedding artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = ROOT / "code"
sys.path.insert(0, str(CODE_DIR))

import numpy as np

from common.llm import set_api_key_from_env
from em_graph import MemoryEmbeddingIndex, QueryEmbeddingArtifact
from em_graph.cache import ordered_question_records, text_digest
from em_graph.recall.embedding_index import (
    L2_NORMALIZATION,
    SUPPORTED_NORMALIZATIONS,
    dragon_encoder_ids,
    embedding_protocol_identity,
    embedding_runtime_identity,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"query artifact report already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _requires_api_key(model_name: str) -> bool:
    return dragon_encoder_ids(model_name) is None


def command_build(args: argparse.Namespace) -> None:
    data_path = Path(args.data_file).resolve()
    output_path = Path(args.output).resolve()
    report_path = Path(args.report).resolve()
    if output_path.exists():
        raise FileExistsError(
            f"query embedding artifact already exists: {output_path}"
        )
    if report_path.exists():
        raise FileExistsError(
            f"query embedding report already exists: {report_path}"
        )
    samples = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(samples, list):
        raise ValueError("dataset root must be a list")
    dataset_sha256 = _sha256_file(data_path)
    records = ordered_question_records(samples)
    questions_by_digest = {}
    for sample in samples:
        for qa in sample.get("qa") or []:
            question = str(qa.get("question") or "")
            digest = text_digest(question)
            questions_by_digest.setdefault(digest, question)
    digests = list(questions_by_digest)
    questions = [questions_by_digest[digest] for digest in digests]

    if _requires_api_key(args.embedding_model):
        set_api_key_from_env()
    embedder = MemoryEmbeddingIndex(
        memory_ids=[],
        vectors=np.zeros((0, 0), dtype=np.float32),
        model_name=args.embedding_model,
        normalization=args.normalization,
        use_text_cache=False,
    )
    vectors = embedder._embed_texts(
        questions,
        role=args.role,
        show_progress=True,
        text_cache=None,
    )
    runtime_identity = (
        None
        if args.normalization == L2_NORMALIZATION
        else embedding_runtime_identity(args.embedding_model)
    )
    protocol_identity = (
        {}
        if args.normalization == L2_NORMALIZATION
        else embedding_protocol_identity(
            args.embedding_model,
            args.normalization,
            runtime_identity=runtime_identity,
        )
    )
    artifact = QueryEmbeddingArtifact(
        dataset_sha256=dataset_sha256,
        model_name=args.embedding_model,
        role=args.role,
        qa_records=records,
        question_digests=digests,
        vectors=vectors,
        normalization=args.normalization,
        protocol_identity=protocol_identity,
    )
    artifact.validate_exact_dataset(
        samples,
        dataset_sha256=dataset_sha256,
        model_name=args.embedding_model,
        role=args.role,
        normalization=args.normalization,
        protocol_identity=protocol_identity,
    )
    artifact.save(output_path)
    identity = artifact.identity(output_path)
    usage = embedder.embedding_usage()
    report = {
        "schema": "query_embedding_build_report_v1",
        "created_at": datetime.now().astimezone().isoformat(),
        "command": " ".join(sys.argv),
        "dataset_path": str(data_path),
        "artifact": identity,
        "embedding_requests": usage["request_count"],
        "embedding_input_tokens": usage["input_tokens"],
        "status": "pass",
    }
    _write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-file",
        default=str(ROOT / "data" / "locomo10.json"),
    )
    parser.add_argument(
        "--embedding-model",
        default="text-embedding-3-small",
    )
    parser.add_argument("--role", default="context")
    parser.add_argument(
        "--normalization",
        choices=sorted(SUPPORTED_NORMALIZATIONS),
        default="l2_float32_v1",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.set_defaults(function=command_build)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
