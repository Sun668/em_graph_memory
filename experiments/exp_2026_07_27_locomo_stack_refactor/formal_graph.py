#!/usr/bin/env python3
"""Isolated formal-condition orchestration for the EM-Graph LoCoMo runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
CODE_DIR = ROOT / "code"
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(EXP_DIR))

import run as graph_runner
from common.llm import set_api_key_from_env
from cost_telemetry import CostTelemetry
from em_graph import QueryEmbeddingArtifact
from em_graph.build.config import ENTITY_EXTRACT_VERSION
from em_graph.cache import QuestionEntityCache
from em_graph.recall.embedding_index import (
    L2_NORMALIZATION,
    NO_NORMALIZATION,
    SUPPORTED_NORMALIZATIONS,
    dragon_encoder_ids,
    dragon_encoder_revisions,
    embedding_query_role,
    embedding_protocol_identity,
    embedding_runtime_identity,
)
from em_graph.recall.retrieval import SEMANTIC_SCORE_NORMALIZATIONS
from locomo_eval import LoCoMoEvaluationConfig, OfficialLoCoMoEvaluator
from locomo_eval.vendor_runtime import load_official_modules
from official_dragon import assert_formal_source_clean
from validate_formal_result import condition_fingerprint, validate_formal_result

DATASET_SHA256 = (
    "047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74"
)
SCOPES = {"all10", "preflight"}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _selected_samples(args: argparse.Namespace) -> List[Dict[str, Any]]:
    path = Path(args.data_file).resolve()
    actual = _sha256_file(path)
    if actual != DATASET_SHA256:
        raise RuntimeError(
            f"dataset SHA-256 mismatch: expected {DATASET_SHA256}, got {actual}"
        )
    if args.scope == "all10":
        if args.samples:
            raise ValueError("all10 scope cannot use --samples")
        sample_ids = None
    else:
        if not args.samples:
            raise ValueError("preflight scope requires --samples")
        sample_ids = args.samples
    return graph_runner._load_samples(path, sample_ids)


def _cache_record(
    sample: Mapping[str, Any],
    *,
    args: argparse.Namespace,
    store: Any,
) -> Dict[str, Any]:
    variant_spec = graph_runner.VARIANTS[args.variant]
    profile = dict(variant_spec["graph"])
    profiled = graph_runner._profiled_sample(sample, profile)
    graph_identity = graph_runner._graph_identity(
        profiled,
        args.extract_model,
        memory_only=bool(profile["memory_only"]),
        graph_profile=profile,
    )
    embedding_identity = graph_runner._embedding_identity(
        profiled,
        args.embedding_model,
        graph_profile=profile,
        normalization=args.embedding_normalization,
        runtime_identity=getattr(
            args, "embedding_runtime_identity", None
        ),
    )
    sample_id = str(sample["sample_id"])
    graph_path = store.graph_path(sample_id, identity=graph_identity)
    index_path = store.embedding_index_path(
        sample_id, identity=embedding_identity
    )
    if not graph_path.exists() or not index_path.exists():
        raise FileNotFoundError(
            f"resolved graph/index cache missing for {sample_id}"
        )
    return {
        "sample_id": sample_id,
        "graph": {
            "path": str(graph_path.resolve()),
            "sha256": _sha256_file(graph_path),
            "identity": graph_identity,
        },
        "embedding_index": {
            "path": str(index_path.resolve()),
            "sha256": _sha256_file(index_path),
            "identity": embedding_identity,
        },
    }


def _formal_config(
    *,
    args: argparse.Namespace,
    samples: Sequence[Mapping[str, Any]],
    condition_dir: Path,
    source_audit: Mapping[str, Any],
    cache_records: Sequence[Mapping[str, Any]],
    recall_parameters: Mapping[str, Any],
    query_artifact_identity: Mapping[str, Any],
    command: str,
) -> Dict[str, Any]:
    model_key = f"{args.answer_model}_dialog_top_{args.top_k}"
    profile = dict(graph_runner.VARIANTS[args.variant]["graph"])
    embedding_normalization = getattr(
        args, "embedding_normalization", L2_NORMALIZATION
    )
    encoders = dragon_encoder_ids(args.embedding_model)
    revisions = dragon_encoder_revisions(args.embedding_model)
    config: Dict[str, Any] = {
        "schema": "locomo_formal_run_v1",
        "run_id": args.run_id,
        "condition_kind": "graph_method",
        "scope": args.scope,
        "sample_ids": [str(sample["sample_id"]) for sample in samples],
        "dataset_sha256": DATASET_SHA256,
        "source_commit": source_audit["source_commit"],
        "source_tree": source_audit["source_tree"],
        "started_at": datetime.now().astimezone().isoformat(),
        "command": command,
        "output_directory": str(condition_dir.resolve()),
        "start_state": {
            "output_directory_empty": True,
            "existing_entries": [],
            "prediction_file_existed": False,
            "directory_existed": False,
        },
        "resume": False,
        "overwrite": False,
        "models": {
            "extraction": (
                None if profile["memory_only"] else args.extract_model
            ),
            "embedding": args.embedding_model,
            "answer": args.answer_model,
            "query_encoder": encoders[0] if encoders else None,
            "context_encoder": encoders[1] if encoders else None,
            "query_encoder_revision": (
                revisions[0] if revisions else None
            ),
            "context_encoder_revision": (
                revisions[1] if revisions else None
            ),
            "embedding_normalization": embedding_normalization,
            "embedding_runtime": getattr(
                args, "embedding_runtime_identity", None
            ),
        },
        "retrieval": {
            "variant": args.variant,
            "rag_mode": "dialog",
            "top_k": int(args.top_k),
            **dict(recall_parameters),
        },
        "graph_profile": profile,
        "answer_protocol": {
            "message_role": "system",
            "temperature": 0,
            "max_tokens": 32,
            "batch_size": 1,
            "category5_option_order": (
                "unchanged unseeded upstream random.random()"
            ),
        },
        "cache_identity": {
            "artifact_root": str(Path(args.cache_dir).resolve()),
            "records": list(cache_records),
            "query_embedding_artifact": dict(query_artifact_identity),
        },
        "model_key": model_key,
        "prediction_key": f"{model_key}_prediction",
        "artifacts": {
            "prediction": "predictions.json",
            "stats": "stats.json",
            "audit": "audit.json",
            "validation": "validation.json",
            "progress": "progress.json",
            "cost_events": "cost_events_warm.json",
            "query_cache_usage": "query_cache_usage.json",
        },
        "source_audit": dict(source_audit),
    }
    if getattr(args, "o2_local_dragon_diagnostic", False):
        config["comparison_scope"] = "local_dragon_stack_diagnostic"
        config["official_comparison_eligible"] = False
        config["diagnostic_reason"] = (
            "O1 official DRAGON reproduction exceeded the preregistered "
            "Recall@25 tolerance"
        )
    config["condition_fingerprint"] = condition_fingerprint(config)
    return config


def _audit(
    args: argparse.Namespace,
    samples: Sequence[Mapping[str, Any]],
    recall_parameters: Mapping[str, Any],
) -> Dict[str, Any]:
    profile = dict(graph_runner.VARIANTS[args.variant]["graph"])
    scaffold = (
        0
        if profile["memory_only"]
        else len(graph_runner.ENTITY_EXTRACTION_PROMPT.format(text=""))
    )
    return {
        "mandatory_graph_constraint": "pass",
        "graph_construction": "conversation fields only",
        "construction_inputs": [
            "session date_time",
            "dia_id",
            "speaker",
            "dialog text",
            "blip_caption",
        ],
        "excluded_from_graph_construction": [
            "QA questions",
            "QA answers",
            "QA evidence",
            "QA categories",
            "judge outputs",
            "previous predictions",
            "question-driven ledgers",
        ],
        "answer_recall": "EM graph retrieval over conversation-built nodes/edges",
        "qa_usage": (
            "question entities and the immutable query embedding artifact are "
            "retrieval-time query data in physically separate caches and are "
            "never graph-construction inputs"
        ),
        "variant": args.variant,
        "sample_ids": [str(sample["sample_id"]) for sample in samples],
        "graph_profile": profile,
        "recall_parameters": dict(recall_parameters),
        "retrieval_score_version": graph_runner.RETRIEVAL_SCORE_VERSION,
        "prompt_budget": {
            "entity_scaffold_chars": scaffold,
            "limit_chars": 5000,
            "pass": scaffold <= 5000,
        },
    }


def command_evaluate(args: argparse.Namespace) -> None:
    _validate_o2_protocol(args)
    source_audit = assert_formal_source_clean()
    args.embedding_runtime_identity = (
        None
        if args.embedding_normalization == L2_NORMALIZATION
        else embedding_runtime_identity(args.embedding_model)
    )
    samples = _selected_samples(args)
    condition_dir = Path(args.output_root).resolve() / args.run_id
    if condition_dir.exists():
        raise FileExistsError(
            f"formal condition directory already exists: {condition_dir}; "
            "delete that exact directory before rerun"
        )
    set_api_key_from_env()
    recall_parameters = graph_runner._recall_parameters_from_args(args)
    store = graph_runner.EMGraphArtifactStore.from_env(args.cache_dir)
    data_path = Path(args.data_file).resolve()
    all_samples = graph_runner._load_samples(data_path, None)
    query_artifact_path = Path(args.query_artifact).resolve()
    query_artifact = QueryEmbeddingArtifact.load(query_artifact_path)
    query_role = embedding_query_role(args.embedding_model)
    query_artifact.validate_exact_dataset(
        all_samples,
        dataset_sha256=DATASET_SHA256,
        model_name=args.embedding_model,
        role=query_role,
        normalization=args.embedding_normalization,
        protocol_identity=(
            None
            if args.embedding_normalization == L2_NORMALIZATION
            else embedding_protocol_identity(
                args.embedding_model,
                args.embedding_normalization,
                runtime_identity=args.embedding_runtime_identity,
            )
        ),
    )
    query_artifact_identity = query_artifact.identity(query_artifact_path)
    full_pool = bool(recall_parameters["force_full_pool"])
    shared_question_extractor = (
        None
        if full_pool
        else graph_runner._question_extractor(args.extract_model, store)
    )
    shared_question_cache = (
        None
        if full_pool
        else QuestionEntityCache(
            cache_file=str(store.question_entity_cache_path()),
            namespace=f"{ENTITY_EXTRACT_VERSION}::{args.extract_model}",
        )
    )
    recalls = {
        str(sample["sample_id"]): graph_runner._load_recall(
            sample,
            variant=args.variant,
            extract_model=args.extract_model,
            embedding_model=args.embedding_model,
            embedding_normalization=args.embedding_normalization,
            embedding_runtime=args.embedding_runtime_identity,
            store=store,
            recall_parameters=recall_parameters,
            query_cache=query_artifact,
            strict_query_cache=True,
            use_text_cache=False,
            question_extractor=shared_question_extractor,
            question_cache=shared_question_cache,
        )
        for sample in samples
    }
    cache_records = [
        _cache_record(sample, args=args, store=store) for sample in samples
    ]
    command = " ".join(
        shlex.quote(value)
        for value in [str(Path(sys.executable).resolve()), *sys.argv]
    )
    condition_dir.mkdir(parents=True)
    config = _formal_config(
        args=args,
        samples=samples,
        condition_dir=condition_dir,
        source_audit=source_audit,
        cache_records=cache_records,
        recall_parameters=recall_parameters,
        query_artifact_identity=query_artifact_identity,
        command=command,
    )
    artifacts = config["artifacts"]
    _write_json(condition_dir / "run_config.json", config)
    _write_json(
        condition_dir / artifacts["audit"],
        _audit(args, samples, recall_parameters),
    )
    telemetry = CostTelemetry("warm")
    recall_router = _TimedRecallRouter(
        graph_runner.EMGraphRecallRouter(recalls),
        telemetry,
    )
    evaluator = OfficialLoCoMoEvaluator(
        recall_router,
        LoCoMoEvaluationConfig(
            model=args.answer_model,
            top_k=args.top_k,
            rag_mode="dialog",
            batch_size=1,
            overwrite=False,
        ),
    )
    outputs = []
    prediction_path = condition_dir / artifacts["prediction"]
    for index, sample in enumerate(samples, start=1):
        with telemetry.stage("answer_generation"):
            outputs.append(evaluator.evaluate_sample(sample))
        _write_json(prediction_path, outputs)
        _write_json(
            condition_dir / artifacts["progress"],
            {
                "status": "complete" if index == len(samples) else "in_progress",
                "completed_samples": index,
                "total_samples": len(samples),
                "completed_qa": sum(len(row["qa"]) for row in outputs),
            },
        )
    _evaluation, evaluation_stats, _gpt_utils = load_official_modules()
    evaluation_stats.analyze_aggr_acc(
        str(Path(args.data_file).resolve()),
        str(prediction_path),
        str(condition_dir / artifacts["stats"]),
        config["model_key"],
        f"{config['model_key']}_f1",
        rag=True,
    )
    _write_json(
        condition_dir / artifacts["query_cache_usage"],
        query_artifact.usage(
            qa_count=sum(len(sample.get("qa") or []) for sample in samples),
            required_lookup_count=(
                sum(len(sample.get("qa") or []) for sample in samples)
                if float(recall_parameters["semantic_weight"]) != 0.0
                else 0
            ),
        ),
    )
    _write_json(
        condition_dir / artifacts["cost_events"],
        {
            "schema": "locomo_cost_events_partial_v1",
            "run_id": config["run_id"],
            "condition_fingerprint": config["condition_fingerprint"],
            "cache_state": "warm",
            "events": telemetry.events(),
            "note": (
                "warm formal-answer measurement; combine with the matched "
                "cold probe before cost_report.py"
            ),
        },
    )
    report = validate_formal_result(
        condition_dir, data_file=Path(args.data_file)
    )
    _write_json(condition_dir / artifacts["validation"], report)
    if report["status"] != "pass":
        raise RuntimeError(f"formal validation failed: {report['errors']}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


class _TimedRecallRouter:
    def __init__(self, router: Any, telemetry: CostTelemetry):
        self.router = router
        self.telemetry = telemetry

    def recall(
        self,
        sample: Mapping[str, Any],
        qa_index: int,
        question: str,
        top_k: int,
    ) -> Any:
        with self.telemetry.retrieval():
            return self.router.recall(sample, qa_index, question, top_k)


def _validate_o2_protocol(args: argparse.Namespace) -> None:
    if not args.o2_local_dragon_diagnostic:
        return
    recall = graph_runner._recall_parameters_from_args(args)
    expected = {
        "scope": "all10",
        "variant": "B",
        "top_k": 25,
        "embedding_model": "dragon",
        "embedding_normalization": NO_NORMALIZATION,
        "entity_weight": 0.3,
        "semantic_weight": 0.7,
        "semantic_score_normalization": "query_local_minmax_v1",
        "sequence_secondary_scale": 0.5,
        "entity_min_rel_score": 0.5,
        "entity_top_k_per_key": 20,
        "who_only_dampen": 0.25,
        "degree_discount": True,
    }
    actual = {
        "scope": args.scope,
        "variant": args.variant,
        "top_k": int(args.top_k),
        "embedding_model": args.embedding_model,
        "embedding_normalization": args.embedding_normalization,
        **{
            key: recall[key]
            for key in (
                "entity_weight",
                "semantic_weight",
                "semantic_score_normalization",
                "sequence_secondary_scale",
                "entity_min_rel_score",
                "entity_top_k_per_key",
                "who_only_dampen",
                "degree_discount",
            )
        },
    }
    if actual != expected:
        raise ValueError(
            "O2 local DRAGON protocol mismatch: "
            f"expected {expected}, got {actual}"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", default=str(ROOT / "data/locomo10.json"))
    parser.add_argument("--cache-dir", default=str(ROOT / "outputs/em_graph"))
    parser.add_argument(
        "--output-root", default=str(ROOT / "outputs/locomo_formal")
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scope", choices=sorted(SCOPES), required=True)
    parser.add_argument("--samples", nargs="*")
    parser.add_argument("--variant", choices=sorted(graph_runner.VARIANTS), required=True)
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--extract-model", default="gpt-3.5-turbo")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument(
        "--embedding-normalization",
        choices=sorted(SUPPORTED_NORMALIZATIONS),
        default=L2_NORMALIZATION,
    )
    parser.add_argument("--answer-model", default="gpt-3.5-turbo")
    parser.add_argument("--query-artifact", required=True)
    parser.add_argument("--entity-weight", type=float)
    parser.add_argument("--semantic-weight", type=float)
    parser.add_argument(
        "--semantic-score-normalization",
        choices=sorted(SEMANTIC_SCORE_NORMALIZATIONS),
    )
    parser.add_argument("--sequence-scale", type=float)
    parser.add_argument("--entity-min-rel-score", type=float)
    parser.add_argument("--entity-top-k-per-key", type=int)
    parser.add_argument("--who-only-dampen", type=float)
    parser.add_argument("--no-degree-discount", action="store_true")
    parser.add_argument(
        "--o2-local-dragon-diagnostic",
        action="store_true",
    )
    parser.set_defaults(function=command_evaluate)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
