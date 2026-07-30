#!/usr/bin/env python3
"""Measure matched cold/warm graph+retrieval cost around a formal answer run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(EXP_DIR))

import run as graph_runner
from cost_report import build_report
from cost_telemetry import CostTelemetry
from formal_graph import _selected_samples
from official_dragon import assert_formal_source_clean
from validate_formal_result import validate_formal_result


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _answer_event(
    warm_document: Mapping[str, Any],
    cache_state: str,
) -> Dict[str, Any]:
    matches = [
        event
        for event in warm_document["events"]
        if event["stage"] == "answer_generation"
    ]
    if len(matches) != 1:
        raise ValueError("warm formal telemetry must have one answer event")
    event = dict(matches[0])
    event["cache_state"] = cache_state
    event["measurement_reuse"] = (
        "same formal answer measurement reused because answer generation "
        "is independent of graph cache state"
    )
    return event


def _replace_answer(
    events: Sequence[Mapping[str, Any]],
    answer: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    return [
        dict(answer) if event["stage"] == "answer_generation" else dict(event)
        for event in events
    ]


def _validate_warm_identity(
    warm_path: Path,
    warm_document: Mapping[str, Any],
    args: argparse.Namespace,
    samples: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    condition_dir = warm_path.parent
    validation = validate_formal_result(
        condition_dir, data_file=Path(args.data_file)
    )
    if validation["status"] != "pass":
        raise ValueError(
            f"warm formal condition validation failed: {validation['errors']}"
        )
    config = json.loads(
        (condition_dir / "run_config.json").read_text(encoding="utf-8")
    )
    expected = {
        "condition_fingerprint": config["condition_fingerprint"],
        "sample_ids": [str(sample["sample_id"]) for sample in samples],
        "variant": args.variant,
        "top_k": int(args.top_k),
        "extraction_model": (
            None
            if graph_runner.VARIANTS[args.variant]["graph"]["memory_only"]
            else args.extract_model
        ),
        "embedding_model": args.embedding_model,
        "answer_model": args.answer_model,
    }
    actual = {
        "condition_fingerprint": warm_document.get("condition_fingerprint"),
        "sample_ids": config.get("sample_ids"),
        "variant": config.get("retrieval", {}).get("variant"),
        "top_k": config.get("retrieval", {}).get("top_k"),
        "extraction_model": config.get("models", {}).get("extraction"),
        "embedding_model": config.get("models", {}).get("embedding"),
        "answer_model": config.get("models", {}).get("answer"),
    }
    if actual != expected:
        raise ValueError(
            f"warm formal condition identity mismatch: "
            f"expected={expected}, actual={actual}"
        )
    configured_cost_name = config["artifacts"].get("cost_events")
    if warm_path.name != configured_cost_name:
        raise ValueError("warm cost file is not the configured formal artifact")
    return config


def _measure_state(
    args: argparse.Namespace,
    samples: Sequence[Mapping[str, Any]],
    *,
    cache_state: str,
) -> tuple[List[Dict[str, Any]], Any]:
    telemetry = CostTelemetry(cache_state)
    store = graph_runner.EMGraphArtifactStore.from_env(args.cache_dir)
    with telemetry.stage("graph_construction"):
        for sample in samples:
            graph_runner.build_graph(
                dict(sample),
                extract_model=args.extract_model,
                store=store,
                memory_only=bool(
                    graph_runner.VARIANTS[args.variant]["graph"]["memory_only"]
                ),
                graph_profile=graph_runner.VARIANTS[args.variant]["graph"],
            )
    recall_parameters = graph_runner._recall_parameters_from_args(args)
    shared_text_cache = graph_runner.TextEmbeddingCache(
        cache_file=str(store.text_embedding_cache_path(args.embedding_model))
    )
    full_pool = bool(recall_parameters["force_full_pool"])
    shared_question_extractor = (
        None
        if full_pool
        else graph_runner._question_extractor(args.extract_model, store)
    )
    shared_question_cache = (
        None
        if full_pool
        else graph_runner.QuestionEntityCache(
            cache_file=str(store.question_entity_cache_path()),
            namespace=(
                f"{graph_runner.ENTITY_EXTRACT_VERSION}::"
                f"{args.extract_model}"
            ),
        )
    )
    with telemetry.stage("embedding"):
        recalls = {
            str(sample["sample_id"]): graph_runner._load_recall(
                dict(sample),
                variant=args.variant,
                extract_model=args.extract_model,
                embedding_model=args.embedding_model,
                store=store,
                recall_parameters=recall_parameters,
                text_cache=shared_text_cache,
                question_extractor=shared_question_extractor,
                question_cache=shared_question_cache,
            )
            for sample in samples
        }
    router = graph_runner.EMGraphRecallRouter(recalls)
    for sample in samples:
        for qa_index, qa in enumerate(sample["qa"]):
            with telemetry.retrieval():
                router.recall(
                    sample,
                    qa_index,
                    str(qa["question"]),
                    args.top_k,
                )
    return telemetry.events(), store


def command_measure(args: argparse.Namespace) -> None:
    assert_formal_source_clean()
    cache_dir = Path(args.cache_dir).resolve()
    if cache_dir.exists():
        raise FileExistsError(
            f"cold cost cache directory already exists: {cache_dir}"
        )
    warm_path = Path(args.warm_cost_file).resolve()
    warm_document = json.loads(warm_path.read_text(encoding="utf-8"))
    samples = _selected_samples(args)
    _validate_warm_identity(warm_path, warm_document, args, samples)
    output_events = Path(args.output_events).resolve()
    output_report = Path(args.output_report).resolve()
    for output in (output_events, output_report):
        if output.exists():
            raise FileExistsError(f"cost output already exists: {output}")
    cold_events, store = _measure_state(
        args, samples, cache_state="cold"
    )
    warm_events, _store = _measure_state(
        args, samples, cache_state="warm"
    )
    cold_events = _replace_answer(
        cold_events, _answer_event(warm_document, "cold")
    )
    warm_events = _replace_answer(
        warm_events, _answer_event(warm_document, "warm")
    )
    manifest = {
        "schema": "locomo_cost_events_v1",
        "run_id": warm_document["run_id"],
        "condition_fingerprint": warm_document["condition_fingerprint"],
        "latency_clock": "time.perf_counter",
        "token_source": "provider response usage",
        "measurement_scope": {
            "sample_ids": [str(sample["sample_id"]) for sample in samples],
            "qa_count": sum(len(sample["qa"]) for sample in samples),
            "variant": args.variant,
            "top_k": args.top_k,
            "cold_cache_root_created_fresh": True,
            "warm_reuses_same_complete_cache": True,
            "answer_measurement_reused_across_cache_states": True,
            "warm_formal_cost_file": str(warm_path),
        },
        "events": [*cold_events, *warm_events],
        "disk_artifacts": [
            {"kind": "graph", "path": str(store.root / "graphs")},
            {
                "kind": "embedding_index",
                "path": str(store.root / "embedding_indexes"),
            },
            {"kind": "cache", "path": str(store.root / "entities")},
            {"kind": "cache", "path": str(store.root / "text_embeddings")},
        ],
    }
    manifest_path = output_events
    _write_json(manifest_path, manifest)
    report = build_report(manifest, manifest_path=manifest_path)
    _write_json(output_report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", default=str(ROOT / "data/locomo10.json"))
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--warm-cost-file", required=True)
    parser.add_argument("--output-events", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--scope", choices=["all10", "preflight"], required=True)
    parser.add_argument("--samples", nargs="*")
    parser.add_argument("--variant", choices=sorted(graph_runner.VARIANTS), required=True)
    parser.add_argument("--top-k", type=int, required=True)
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
    parser.set_defaults(function=command_measure)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
