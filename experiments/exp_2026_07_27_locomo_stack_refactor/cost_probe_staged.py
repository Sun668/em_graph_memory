#!/usr/bin/env python3
"""Resumable, fail-closed cold/warm cost measurement transactions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(EXP_DIR))

import run as graph_runner
from cost_probe import _answer_event, _validate_warm_identity
from cost_report import build_report
from cost_telemetry import CostTelemetry
from em_graph import QueryEmbeddingArtifact
from em_graph.recall.embedding_index import (
    L2_NORMALIZATION,
    embedding_query_role,
)
from formal_graph import DATASET_SHA256, _selected_samples
from official_dragon import assert_formal_source_clean

SCHEMA = "locomo_staged_cost_checkpoint_v2"
PROVIDER_RETRY_EXHAUSTED = re.compile(
    r"^Failed after [1-9][0-9]* retries for model=.+$"
)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _provider_event(
    telemetry: CostTelemetry,
    stage: str,
    *,
    operation: str,
    observed_stages: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    source_stages = set(observed_stages or [stage])
    selected = [
        event
        for event in telemetry.provider_events
        if event["stage"] in source_stages
        and event["operation"] == operation
    ]
    if any(
        event.get(key) is None
        for event in selected
        for key in ("input_tokens", "output_tokens")
    ):
        raise ValueError(f"provider token usage missing for {stage}")
    return {
        "stage": stage,
        "cache_state": telemetry.cache_state,
        "wall_seconds": float(
            sum(float(event["wall_seconds"]) for event in selected)
        ),
        "request_count": int(
            sum(int(event["request_count"]) for event in selected)
        ),
        "input_tokens": int(
            sum(int(event["input_tokens"]) for event in selected)
        ),
        "output_tokens": int(
            sum(int(event["output_tokens"] or 0) for event in selected)
        ),
    }


def _embedding_event(telemetry: CostTelemetry) -> Dict[str, Any]:
    selected = [
        event
        for event in telemetry.provider_events
        if event["operation"] == "embedding"
    ]
    if any(event.get("input_tokens") is None for event in selected):
        raise ValueError("provider token usage missing for embedding")
    event = {
        "stage": "embedding",
        "cache_state": telemetry.cache_state,
        "wall_seconds": float(
            telemetry.stage_walls.get(
                "embedding",
                sum(float(event["wall_seconds"]) for event in selected),
            )
        ),
        "request_count": int(
            sum(int(event["request_count"]) for event in selected)
        ),
        "input_tokens": int(
            sum(int(event["input_tokens"]) for event in selected)
        ),
        "output_tokens": 0,
    }
    return event


def _graph_events(telemetry: CostTelemetry) -> List[Dict[str, Any]]:
    return [
        {
            "stage": "graph_construction",
            "cache_state": telemetry.cache_state,
            "wall_seconds": float(
                telemetry.stage_walls.get("graph_construction", 0.0)
            ),
            "request_count": 0,
        },
        _provider_event(
            telemetry,
            "entity_extraction",
            operation="chat",
            observed_stages=[
                "entity_extraction",
                "graph_construction",
            ],
        ),
    ]


def _retrieval_events(
    telemetry: CostTelemetry,
    *,
    query_artifact: QueryEmbeddingArtifact,
) -> List[Dict[str, Any]]:
    if not telemetry.retrieval_latencies:
        raise ValueError("retrieval batch must contain at least one QA")
    embedding_requests = sum(
        int(event["request_count"])
        for event in telemetry.provider_events
        if event["operation"] == "embedding"
    )
    if embedding_requests:
        raise RuntimeError(
            "strict query artifact retrieval made live embedding requests"
        )
    if query_artifact.misses != 0:
        raise RuntimeError("strict query artifact retrieval recorded misses")
    if query_artifact.hits < len(telemetry.retrieval_latencies):
        raise RuntimeError(
            "query artifact lookup count is below retrieval QA count"
        )
    return [
        _provider_event(telemetry, "query_entity", operation="chat"),
        {
            "stage": "retrieval",
            "cache_state": telemetry.cache_state,
            "wall_seconds": float(sum(telemetry.retrieval_latencies)),
            "request_count": 0,
            "qa_count": len(telemetry.retrieval_latencies),
            "latency_seconds": list(telemetry.retrieval_latencies),
            "query_artifact_cache_hits": int(query_artifact.hits),
            "query_artifact_cache_misses": int(query_artifact.misses),
            "live_query_embedding_requests": embedding_requests,
            "provider_recovery": {
                "retry_count": len(telemetry.provider_recovery_events),
                "failure_wall_seconds_excluded": float(
                    sum(
                        event["failure_wall_seconds"]
                        for event in telemetry.provider_recovery_events
                    )
                ),
                "wait_seconds_excluded": float(
                    sum(
                        event["wait_seconds"]
                        for event in telemetry.provider_recovery_events
                    )
                ),
                "latency_policy": (
                    "latency_seconds records only the completed retrieval "
                    "attempt; exhausted-attempt and inter-attempt wait time "
                    "are disclosed here and excluded"
                ),
                "events": list(telemetry.provider_recovery_events),
            },
        },
    ]


def _state_path(args: argparse.Namespace) -> Path:
    return Path(args.checkpoint).resolve()


def _resolved_identity(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "measurement_id": args.measurement_id,
        "parameter_snapshot_sha256": args.parameter_snapshot_sha256,
        "data_file": str(Path(args.data_file).resolve()),
        "cache_dir": str(Path(args.cache_dir).resolve()),
        "warm_cost_file": str(Path(args.warm_cost_file).resolve()),
        "output_events": str(Path(args.output_events).resolve()),
        "output_report": str(Path(args.output_report).resolve()),
        "query_artifact": str(Path(args.query_artifact).resolve()),
        "formal_query_usage": str(
            Path(args.formal_query_usage).resolve()
        ),
        "scope": args.scope,
        "samples": list(args.samples or []),
        "variant": args.variant,
        "top_k": int(args.top_k),
        "batch_size": int(args.batch_size),
        "provider_recovery_attempts": int(
            args.provider_recovery_attempts
        ),
        "provider_recovery_wait_seconds": float(
            args.provider_recovery_wait_seconds
        ),
        "provider_recovery_max_wait_seconds": float(
            args.provider_recovery_max_wait_seconds
        ),
        "extract_model": args.extract_model,
        "embedding_model": args.embedding_model,
        "answer_model": args.answer_model,
        "entity_weight": args.entity_weight,
        "semantic_weight": args.semantic_weight,
        "sequence_scale": args.sequence_scale,
        "entity_min_rel_score": args.entity_min_rel_score,
        "entity_top_k_per_key": args.entity_top_k_per_key,
        "who_only_dampen": args.who_only_dampen,
        "no_degree_discount": bool(args.no_degree_discount),
    }


def _load_state(args: argparse.Namespace) -> Dict[str, Any]:
    state = _read_json(_state_path(args))
    if state.get("schema") != SCHEMA:
        raise ValueError("unsupported staged cost checkpoint schema")
    if (
        state.get("resolved_identity") is not None
        and state["resolved_identity"] != _resolved_identity(args)
    ):
        raise ValueError("staged cost arguments differ from frozen checkpoint")
    if state.get("in_progress") is not None:
        raise RuntimeError(
            "checkpoint has an interrupted in_progress operation; "
            "the run is invalid and must restart from a new run id"
        )
    return state


def _save_state(args: argparse.Namespace, state: Mapping[str, Any]) -> None:
    _atomic_json(_state_path(args), state)


def _sample_map(args: argparse.Namespace) -> Dict[str, Mapping[str, Any]]:
    return {
        str(sample["sample_id"]): sample
        for sample in _selected_samples(args)
    }


def _operation_plan(
    samples: Sequence[Mapping[str, Any]],
    batch_size: int,
) -> List[Dict[str, Any]]:
    operations: List[Dict[str, Any]] = []
    for cache_state in ("cold", "warm"):
        for sample in samples:
            operations.append(
                {
                    "key": f"{cache_state}:graph:{sample['sample_id']}",
                    "kind": "graph",
                    "cache_state": cache_state,
                    "sample_id": str(sample["sample_id"]),
                }
            )
        for sample in samples:
            operations.append(
                {
                    "key": f"{cache_state}:index:{sample['sample_id']}",
                    "kind": "index",
                    "cache_state": cache_state,
                    "sample_id": str(sample["sample_id"]),
                }
            )
        for sample in samples:
            qa_count = len(sample["qa"])
            for start in range(0, qa_count, batch_size):
                end = min(start + batch_size, qa_count)
                operations.append(
                    {
                        "key": (
                            f"{cache_state}:retrieve:{sample['sample_id']}:"
                            f"{start}:{end}"
                        ),
                        "kind": "retrieve",
                        "cache_state": cache_state,
                        "sample_id": str(sample["sample_id"]),
                        "qa_start": start,
                        "qa_end": end,
                    }
                )
    return operations


def command_init(args: argparse.Namespace) -> None:
    assert_formal_source_clean()
    checkpoint = _state_path(args)
    cache_root = Path(args.cache_dir).resolve()
    event_path = Path(args.output_events).resolve()
    report_path = Path(args.output_report).resolve()
    for path in (checkpoint, cache_root, event_path, report_path):
        if path.exists():
            raise FileExistsError(f"staged cost target already exists: {path}")
    warm_path = Path(args.warm_cost_file).resolve()
    warm_document = _read_json(warm_path)
    samples = list(_selected_samples(args))
    query_artifact, query_artifact_identity = _validated_query_artifact(args)
    config = _validate_warm_identity(
        warm_path,
        warm_document,
        args,
        samples,
    )
    formal_query_identity = (
        config.get("cache_identity", {})
        .get("query_embedding_artifact", {})
    )
    if (
        formal_query_identity.get("sha256")
        != query_artifact_identity.get("sha256")
    ):
        raise ValueError(
            "query artifact differs from the matched formal condition"
        )
    operations = _operation_plan(samples, int(args.batch_size))
    qa_count = sum(len(sample["qa"]) for sample in samples)
    formal_query_usage_identity = _validated_formal_query_usage(
        args,
        qa_count=qa_count,
    )
    state = {
        "schema": SCHEMA,
        "run_id": args.measurement_id,
        "formal_run_id": warm_document["run_id"],
        "condition_fingerprint": warm_document["condition_fingerprint"],
        "parameter_snapshot_sha256": args.parameter_snapshot_sha256,
        "resolved_identity": _resolved_identity(args),
        "cache_root": str(cache_root),
        "event_path": str(event_path),
        "report_path": str(report_path),
        "warm_cost_file": str(warm_path),
        "query_artifact_identity": query_artifact_identity,
        "formal_query_usage_identity": formal_query_usage_identity,
        "batch_size": int(args.batch_size),
        "sample_ids": [str(sample["sample_id"]) for sample in samples],
        "qa_count": qa_count,
        "operations": operations,
        "completed": [],
        "in_progress": None,
        "events": [],
        "formal_config_source_commit": config["source_commit"],
    }
    if query_artifact.hits or query_artifact.misses:
        raise RuntimeError("query artifact validation must not perform lookups")
    _save_state(args, state)
    print(json.dumps({"status": "initialized", "operations": len(operations)}))


def _validated_query_artifact(
    args: argparse.Namespace,
) -> tuple[QueryEmbeddingArtifact, Dict[str, Any]]:
    data_path = Path(args.data_file).resolve()
    all_samples = graph_runner._load_samples(data_path, None)
    path = Path(args.query_artifact).resolve()
    artifact = QueryEmbeddingArtifact.load(path)
    artifact.validate_exact_dataset(
        all_samples,
        dataset_sha256=DATASET_SHA256,
        model_name=args.embedding_model,
        role=embedding_query_role(args.embedding_model),
        normalization=L2_NORMALIZATION,
    )
    return artifact, artifact.identity(path)


def _validated_formal_query_usage(
    args: argparse.Namespace,
    *,
    qa_count: int,
) -> Dict[str, Any]:
    path = Path(args.formal_query_usage).resolve()
    usage = _read_json(path)
    expected = {
        "schema": "query_embedding_usage_v1",
        "qa_count": int(qa_count),
        "required_lookup_count": int(qa_count),
        "cache_misses": 0,
        "live_embedding_requests": 0,
        "status": "pass",
    }
    mismatches = [
        key for key, value in expected.items() if usage.get(key) != value
    ]
    lookup_count = int(usage.get("lookup_count", -1))
    cache_hits = int(usage.get("cache_hits", -1))
    if lookup_count != cache_hits or lookup_count < int(qa_count):
        mismatches.append("lookup_count/cache_hits")
    if mismatches:
        raise ValueError(
            "formal query usage identity mismatch: "
            + ", ".join(sorted(set(mismatches)))
        )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "schema": usage["schema"],
        "qa_count": int(usage["qa_count"]),
        "required_lookup_count": int(usage["required_lookup_count"]),
        "lookup_count": lookup_count,
        "cache_hits": cache_hits,
        "cache_misses": 0,
        "live_embedding_requests": 0,
        "status": "pass",
    }


def _shared_recall_inputs(
    args: argparse.Namespace,
    store: Any,
    recall_parameters: Mapping[str, Any],
) -> tuple[Any, Any]:
    full_pool = bool(recall_parameters["force_full_pool"])
    extractor = (
        None
        if full_pool
        else graph_runner._question_extractor(args.extract_model, store)
    )
    question_cache = (
        None
        if full_pool
        else graph_runner.QuestionEntityCache(
            cache_file=str(store.question_entity_cache_path()),
            namespace=(
                f"{graph_runner.ENTITY_EXTRACT_VERSION}::{args.extract_model}"
            ),
        )
    )
    return extractor, question_cache


def _validate_provider_recovery(args: argparse.Namespace) -> None:
    attempts = int(args.provider_recovery_attempts)
    wait_seconds = float(args.provider_recovery_wait_seconds)
    max_wait_seconds = float(args.provider_recovery_max_wait_seconds)
    if attempts < 0:
        raise ValueError("provider recovery attempts must be nonnegative")
    if wait_seconds < 0:
        raise ValueError("provider recovery wait must be nonnegative")
    if max_wait_seconds < wait_seconds:
        raise ValueError(
            "provider recovery max wait must be at least the initial wait"
        )


def _recall_with_provider_recovery(
    args: argparse.Namespace,
    telemetry: CostTelemetry,
    recall: Any,
    sample: Mapping[str, Any],
    qa_index: int,
    question: str,
) -> None:
    """Retry only an exhausted provider call within one open transaction."""
    max_recoveries = int(args.provider_recovery_attempts)
    for attempt in range(max_recoveries + 1):
        started = time.perf_counter()
        try:
            with telemetry.retrieval():
                recall.recall(
                    sample,
                    qa_index,
                    question,
                    args.top_k,
                )
            return
        except RuntimeError as exc:
            failure_wall_seconds = time.perf_counter() - started
            is_provider_exhaustion = bool(
                PROVIDER_RETRY_EXHAUSTED.fullmatch(str(exc))
            )
            if not is_provider_exhaustion or attempt >= max_recoveries:
                raise
            wait_seconds = min(
                float(args.provider_recovery_wait_seconds) * (2 ** attempt),
                float(args.provider_recovery_max_wait_seconds),
            )
            telemetry.record_provider_recovery(
                failure_wall_seconds=failure_wall_seconds,
                wait_seconds=wait_seconds,
                error=exc,
            )
            print(
                json.dumps(
                    {
                        "status": "provider_recovery_wait",
                        "qa_index": int(qa_index),
                        "recovery": attempt + 1,
                        "max_recoveries": max_recoveries,
                        "wait_seconds": wait_seconds,
                    }
                ),
                flush=True,
            )
            time.sleep(wait_seconds)


def _execute_operation(
    args: argparse.Namespace,
    operation: Mapping[str, Any],
    sample: Mapping[str, Any],
    *,
    query_artifact: QueryEmbeddingArtifact,
) -> List[Dict[str, Any]]:
    cache_state = str(operation["cache_state"])
    telemetry = CostTelemetry(cache_state)
    store = graph_runner.EMGraphArtifactStore.from_env(args.cache_dir)
    if operation["kind"] == "graph":
        with telemetry.stage("graph_construction"):
            graph_runner.build_graph(
                dict(sample),
                extract_model=args.extract_model,
                store=store,
                memory_only=bool(
                    graph_runner.VARIANTS[args.variant]["graph"]["memory_only"]
                ),
                graph_profile=graph_runner.VARIANTS[args.variant]["graph"],
            )
        return _graph_events(telemetry)

    recall_parameters = graph_runner._recall_parameters_from_args(args)
    extractor, question_cache = _shared_recall_inputs(
        args, store, recall_parameters
    )
    if operation["kind"] == "index":
        with telemetry.stage("embedding"):
            recall = graph_runner._load_recall(
                dict(sample),
                variant=args.variant,
                extract_model=args.extract_model,
                embedding_model=args.embedding_model,
                store=store,
                recall_parameters=recall_parameters,
                query_cache=query_artifact,
                strict_query_cache=True,
                use_text_cache=False,
                question_extractor=extractor,
                question_cache=question_cache,
            )
        event = _embedding_event(telemetry)
        native_usage = recall.embedding_index.embedding_usage()
        if event["request_count"] != int(native_usage["request_count"]):
            raise RuntimeError("embedding observer/native request counts differ")
        if event["input_tokens"] != int(native_usage["input_tokens"]):
            raise RuntimeError("embedding observer/native token counts differ")
        return [event]

    if operation["kind"] != "retrieve":
        raise ValueError(f"unsupported operation kind {operation['kind']}")
    recall = graph_runner._load_recall(
        dict(sample),
        variant=args.variant,
        extract_model=args.extract_model,
        embedding_model=args.embedding_model,
        store=store,
        recall_parameters=recall_parameters,
        query_cache=query_artifact,
        strict_query_cache=True,
        use_text_cache=False,
        question_extractor=extractor,
        question_cache=question_cache,
    )
    start = int(operation["qa_start"])
    end = int(operation["qa_end"])
    for qa_index in range(start, end):
        qa = sample["qa"][qa_index]
        _recall_with_provider_recovery(
            args,
            telemetry,
            recall,
            sample,
            qa_index,
            str(qa["question"]),
        )
    native_embedding_usage = recall.embedding_index.embedding_usage()
    if int(native_embedding_usage["request_count"]) != 0:
        raise RuntimeError(
            "strict query artifact retrieval changed native embedding usage"
        )
    if question_cache is not None:
        question_cache.flush()
    return _retrieval_events(
        telemetry,
        query_artifact=query_artifact,
    )


def command_step(args: argparse.Namespace) -> None:
    assert_formal_source_clean()
    state = _load_state(args)
    if str(Path(args.cache_dir).resolve()) != state["cache_root"]:
        raise ValueError("cache root differs from checkpoint")
    completed = set(state["completed"])
    operation = next(
        (item for item in state["operations"] if item["key"] not in completed),
        None,
    )
    if operation is None:
        print(json.dumps({"status": "all_operations_complete"}))
        return
    state["in_progress"] = operation["key"]
    _save_state(args, state)
    formal_query_usage_identity = _validated_formal_query_usage(
        args,
        qa_count=int(state["qa_count"]),
    )
    if (
        formal_query_usage_identity
        != state.get("formal_query_usage_identity")
    ):
        raise ValueError("formal query usage identity differs from checkpoint")
    query_artifact, query_identity = _validated_query_artifact(args)
    if query_identity != state.get("query_artifact_identity"):
        raise ValueError("query artifact identity differs from checkpoint")
    samples = _sample_map(args)
    events = _execute_operation(
        args,
        operation,
        samples[str(operation["sample_id"])],
        query_artifact=query_artifact,
    )
    state = _read_json(_state_path(args))
    if state.get("in_progress") != operation["key"]:
        raise RuntimeError("checkpoint in_progress identity changed")
    state["events"].extend(events)
    state["completed"].append(operation["key"])
    state["in_progress"] = None
    _save_state(args, state)
    print(
        json.dumps(
            {
                "status": "completed",
                "operation": operation["key"],
                "completed": len(state["completed"]),
                "total": len(state["operations"]),
            }
        )
    )


def command_status(args: argparse.Namespace) -> None:
    state = _read_json(_state_path(args))
    completed = set(state["completed"])
    next_operation = next(
        (item["key"] for item in state["operations"] if item["key"] not in completed),
        None,
    )
    print(
        json.dumps(
            {
                "schema": state["schema"],
                "completed": len(completed),
                "total": len(state["operations"]),
                "in_progress": state.get("in_progress"),
                "next": next_operation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _validate_matched_query_usage(
    events: Sequence[Mapping[str, Any]],
    *,
    qa_count: int,
    formal_lookup_count: int,
) -> Dict[str, Any]:
    summaries: Dict[str, Dict[str, Any]] = {}
    signatures: Dict[str, List[Dict[str, int]]] = {}
    for cache_state in ("cold", "warm"):
        retrieval_events = [
            event
            for event in events
            if event.get("cache_state") == cache_state
            and event.get("stage") == "retrieval"
        ]
        signatures[cache_state] = [
            {
                "qa_count": int(event["qa_count"]),
                "query_artifact_cache_hits": int(
                    event["query_artifact_cache_hits"]
                ),
                "query_artifact_cache_misses": int(
                    event["query_artifact_cache_misses"]
                ),
                "live_query_embedding_requests": int(
                    event["live_query_embedding_requests"]
                ),
            }
            for event in retrieval_events
        ]
        state_qa_count = sum(
            batch["qa_count"] for batch in signatures[cache_state]
        )
        query_hits = sum(
            batch["query_artifact_cache_hits"]
            for batch in signatures[cache_state]
        )
        query_misses = sum(
            batch["query_artifact_cache_misses"]
            for batch in signatures[cache_state]
        )
        live_query_requests = sum(
            batch["live_query_embedding_requests"]
            for batch in signatures[cache_state]
        )
        if (
            state_qa_count != qa_count
            or query_hits < qa_count
            or query_misses != 0
            or live_query_requests != 0
        ):
            raise RuntimeError(
                f"{cache_state} query artifact coverage/usage is invalid"
            )
        summaries[cache_state] = {
            "batch_count": len(retrieval_events),
            "qa_count": state_qa_count,
            "query_artifact_cache_hits": query_hits,
            "query_artifact_cache_misses": query_misses,
            "live_query_embedding_requests": live_query_requests,
            "hit_delta_from_formal_reference": (
                query_hits - formal_lookup_count
            ),
        }
    if signatures["cold"] != signatures["warm"]:
        raise RuntimeError("cold/warm query artifact batch usage differs")
    return {
        "validation": "matched_cold_warm_batch_usage_v1",
        "formal_reference_lookup_count": formal_lookup_count,
        "cold": summaries["cold"],
        "warm": summaries["warm"],
    }


def command_finalize(args: argparse.Namespace) -> None:
    assert_formal_source_clean()
    state = _load_state(args)
    formal_query_usage_identity = _validated_formal_query_usage(
        args,
        qa_count=int(state["qa_count"]),
    )
    if (
        formal_query_usage_identity
        != state.get("formal_query_usage_identity")
    ):
        raise ValueError("formal query usage identity differs from checkpoint")
    if len(state["completed"]) != len(state["operations"]):
        raise ValueError("cannot finalize incomplete staged cost checkpoint")
    warm_document = _read_json(Path(state["warm_cost_file"]))
    events = list(state["events"])
    events.extend(
        [
            _answer_event(warm_document, "cold"),
            _answer_event(warm_document, "warm"),
        ]
    )
    store = graph_runner.EMGraphArtifactStore.from_env(args.cache_dir)
    graph_paths = sorted((store.root / "graphs").glob("*.json"))
    index_paths = sorted((store.root / "embedding_indexes").glob("*.npz"))
    if len(graph_paths) != len(state["sample_ids"]):
        raise RuntimeError("complete graph artifact count is invalid")
    if len(index_paths) != len(state["sample_ids"]):
        raise RuntimeError("complete embedding-index artifact count is invalid")
    question_cache_path = store.question_entity_cache_path()
    raw_question_path = store.question_extraction_cache_path()
    question_cache = _read_json(question_cache_path)
    raw_questions = _read_json(raw_question_path)
    if len(question_cache) != state["qa_count"]:
        raise RuntimeError("ordered question-entity cache coverage is invalid")
    expected_unique_questions = len(
        {
            str(qa.get("question") or "")
            for sample in _selected_samples(args)
            for qa in sample["qa"]
        }
    )
    if len(raw_questions) != expected_unique_questions:
        raise RuntimeError("raw question extraction cache coverage is invalid")
    observed_query_usage = _validate_matched_query_usage(
        events,
        qa_count=int(state["qa_count"]),
        formal_lookup_count=int(
            state["formal_query_usage_identity"]["lookup_count"]
        ),
    )
    provider_stages = {
        "entity_extraction",
        "embedding",
        "query_entity",
    }
    cold_provider_events = [
        event
        for event in events
        if event.get("cache_state") == "cold"
        and event.get("stage") in provider_stages
    ]
    warm_provider_events = [
        event
        for event in events
        if event.get("cache_state") == "warm"
        and event.get("stage") in provider_stages
    ]
    cold_by_stage = {
        stage: sum(
            int(event["request_count"])
            for event in cold_provider_events
            if event["stage"] == stage
        )
        for stage in provider_stages
    }
    if any(cold_by_stage[stage] <= 0 for stage in provider_stages):
        raise RuntimeError("cold provider usage is missing a required stage")
    if any(int(event["request_count"]) != 0 for event in warm_provider_events):
        raise RuntimeError("warm cache made new provider requests")
    manifest = {
        "schema": "locomo_cost_events_v1",
        "run_id": state["formal_run_id"],
        "condition_fingerprint": state["condition_fingerprint"],
        "latency_clock": "time.perf_counter",
        "token_source": "provider response usage",
        "measurement_scope": {
            "sample_ids": state["sample_ids"],
            "qa_count": state["qa_count"],
            "variant": args.variant,
            "top_k": args.top_k,
            "cold_cache_root_created_fresh": True,
            "warm_reuses_same_complete_cache": True,
            "answer_measurement_reused_across_cache_states": True,
            "staged_transactions": True,
            "batch_size": state["batch_size"],
            "provider_recovery": {
                "additional_attempts": int(
                    args.provider_recovery_attempts
                ),
                "initial_wait_seconds": float(
                    args.provider_recovery_wait_seconds
                ),
                "maximum_wait_seconds": float(
                    args.provider_recovery_max_wait_seconds
                ),
                "backoff": "exponential, capped",
                "retry_scope": (
                    "same QA and same process after the shared chat client "
                    "exhausts its internal retries"
                ),
                "latency_policy": (
                    "failed-attempt and inter-attempt wait time are excluded "
                    "from completed retrieval latency and disclosed per batch"
                ),
            },
            "checkpoint": str(_state_path(args)),
            "parameter_snapshot_sha256": state["parameter_snapshot_sha256"],
            "query_artifact": state["query_artifact_identity"],
            "formal_query_usage": state[
                "formal_query_usage_identity"
            ],
            "observed_query_usage": observed_query_usage,
        },
        "events": events,
        "disk_artifacts": [
            {"kind": "graph", "path": str(store.root / "graphs")},
            {
                "kind": "embedding_index",
                "path": str(store.root / "embedding_indexes"),
            },
            {"kind": "cache", "path": str(store.root / "entities")},
            {
                "kind": "cache",
                "path": state["query_artifact_identity"]["path"],
            },
        ],
    }
    event_path = Path(state["event_path"])
    report_path = Path(state["report_path"])
    if event_path.exists() or report_path.exists():
        raise FileExistsError("final staged cost output already exists")
    _atomic_json(event_path, manifest)
    _atomic_json(report_path, build_report(manifest, manifest_path=event_path))
    print(json.dumps({"status": "finalized", "report": str(report_path)}))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "step", "status", "finalize"])
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--measurement-id", required=True)
    parser.add_argument("--parameter-snapshot-sha256", required=True)
    parser.add_argument("--data-file", default=str(ROOT / "data/locomo10.json"))
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--warm-cost-file", required=True)
    parser.add_argument("--output-events", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--query-artifact", required=True)
    parser.add_argument("--formal-query-usage", required=True)
    parser.add_argument("--scope", choices=["all10", "preflight"], required=True)
    parser.add_argument("--samples", nargs="*")
    parser.add_argument("--variant", choices=sorted(graph_runner.VARIANTS), required=True)
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--provider-recovery-attempts", type=int, default=6)
    parser.add_argument(
        "--provider-recovery-wait-seconds",
        type=float,
        default=30.0,
    )
    parser.add_argument(
        "--provider-recovery-max-wait-seconds",
        type=float,
        default=120.0,
    )
    parser.add_argument("--extract-model", default="gpt-3.5-turbo")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--answer-model", default="gpt-3.5-turbo")
    parser.add_argument("--entity-weight", type=float)
    parser.add_argument("--semantic-weight", type=float)
    parser.add_argument("--sequence-scale", type=float)
    parser.add_argument("--entity-min-rel-score", type=float)
    parser.add_argument("--entity-top-k-per-key", type=int)
    parser.add_argument("--who-only-dampen", type=float)
    parser.add_argument("--no-degree-discount", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    _validate_provider_recovery(args)
    {
        "init": command_init,
        "step": command_step,
        "status": command_status,
        "finalize": command_finalize,
    }[args.command](args)


if __name__ == "__main__":
    main()
