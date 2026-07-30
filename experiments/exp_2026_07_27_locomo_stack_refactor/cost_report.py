#!/usr/bin/env python3
"""Aggregate explicit formal-run cost events without estimating missing data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

EVENT_SCHEMA = "locomo_cost_events_v1"
REPORT_SCHEMA = "locomo_cost_report_v1"
CACHE_STATES = {"cold", "warm"}
STAGES = {
    "graph_construction",
    "entity_extraction",
    "embedding",
    "query_entity",
    "retrieval",
    "answer_generation",
}
REQUEST_TOKEN_STAGES = {
    "entity_extraction",
    "embedding",
    "query_entity",
    "answer_generation",
}
DISK_KINDS = {"graph", "embedding_index", "cache"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _path_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(
            item.stat().st_size
            for item in path.rglob("*")
            if item.is_file()
        )
    raise FileNotFoundError(path)


def validate_events(document: Mapping[str, Any]) -> None:
    errors = []
    if document.get("schema") != EVENT_SCHEMA:
        errors.append(f"schema must be {EVENT_SCHEMA}")
    if not str(document.get("run_id") or ""):
        errors.append("run_id is required")
    if not str(document.get("condition_fingerprint") or ""):
        errors.append("condition_fingerprint is required")
    events = document.get("events")
    if not isinstance(events, list) or not events:
        errors.append("events must be a non-empty list")
        events = []
    seen_states = set()
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            errors.append(f"event {index} is not an object")
            continue
        stage = event.get("stage")
        cache_state = event.get("cache_state")
        if stage not in STAGES:
            errors.append(f"event {index} has invalid stage {stage!r}")
        if cache_state not in CACHE_STATES:
            errors.append(
                f"event {index} has invalid cache_state {cache_state!r}"
            )
        else:
            seen_states.add(cache_state)
        try:
            wall_seconds = float(event["wall_seconds"])
            if not math.isfinite(wall_seconds) or wall_seconds < 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            errors.append(f"event {index} has invalid wall_seconds")
        try:
            requests = int(event.get("request_count", 0))
            if requests < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"event {index} has invalid request_count")
            requests = 0
        if stage in REQUEST_TOKEN_STAGES:
            for key in ("input_tokens", "output_tokens"):
                try:
                    value = int(event[key])
                    if value < 0:
                        raise ValueError
                except (KeyError, TypeError, ValueError):
                    errors.append(f"event {index} has invalid {key}")
        if stage == "retrieval":
            try:
                qa_count = int(event["qa_count"])
                if qa_count <= 0:
                    raise ValueError
                latencies = event["latency_seconds"]
                if (
                    not isinstance(latencies, list)
                    or len(latencies) != qa_count
                    or any(
                        not math.isfinite(float(value))
                        or float(value) < 0
                        for value in latencies
                    )
                ):
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                errors.append(
                    f"event {index} retrieval latency/count is invalid"
                )
            recovery = event.get("provider_recovery")
            if recovery is not None:
                try:
                    retry_count = int(recovery["retry_count"])
                    failure_wall = float(
                        recovery["failure_wall_seconds_excluded"]
                    )
                    wait_seconds = float(
                        recovery["wait_seconds_excluded"]
                    )
                    recovery_events = recovery["events"]
                    if (
                        retry_count < 0
                        or not math.isfinite(failure_wall)
                        or failure_wall < 0
                        or not math.isfinite(wait_seconds)
                        or wait_seconds < 0
                        or not isinstance(recovery_events, list)
                        or len(recovery_events) != retry_count
                    ):
                        raise ValueError
                except (KeyError, TypeError, ValueError):
                    errors.append(
                        f"event {index} provider recovery is invalid"
                    )
    if seen_states != CACHE_STATES:
        errors.append(
            f"cold and warm measurements required; got {sorted(seen_states)}"
        )
    for cache_state in sorted(CACHE_STATES):
        seen_stages = {
            event.get("stage")
            for event in events
            if isinstance(event, Mapping)
            and event.get("cache_state") == cache_state
        }
        missing_stages = sorted(STAGES - seen_stages)
        if missing_stages:
            errors.append(
                f"{cache_state} measurement missing stages {missing_stages}"
            )

    artifacts = document.get("disk_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("disk_artifacts must be a non-empty list")
        artifacts = []
    seen_kinds = set()
    for index, artifact in enumerate(artifacts):
        kind = artifact.get("kind") if isinstance(artifact, Mapping) else None
        path = artifact.get("path") if isinstance(artifact, Mapping) else None
        if kind not in DISK_KINDS:
            errors.append(f"disk artifact {index} has invalid kind {kind!r}")
        else:
            seen_kinds.add(kind)
        if not path or not Path(str(path)).resolve().exists():
            errors.append(f"disk artifact {index} path does not exist: {path}")
    if seen_kinds != DISK_KINDS:
        errors.append(
            f"graph/index/cache disk artifacts required; got {sorted(seen_kinds)}"
        )
    if errors:
        raise ValueError("; ".join(errors))


def _latency_summary(values: Sequence[float]) -> Dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean_seconds": float(array.mean()),
        "p50_seconds": float(np.quantile(array, 0.50)),
        "p90_seconds": float(np.quantile(array, 0.90)),
        "p95_seconds": float(np.quantile(array, 0.95)),
        "p99_seconds": float(np.quantile(array, 0.99)),
        "max_seconds": float(array.max()),
    }


def build_report(
    document: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> Dict[str, Any]:
    validate_events(document)
    by_state: Dict[str, Any] = {}
    events = list(document["events"])
    for cache_state in ("cold", "warm"):
        selected = [
            event
            for event in events
            if event["cache_state"] == cache_state
        ]
        stages: Dict[str, Any] = {}
        for stage in sorted(STAGES):
            stage_events = [
                event for event in selected if event["stage"] == stage
            ]
            if not stage_events:
                continue
            block: Dict[str, Any] = {
                "event_count": len(stage_events),
                "wall_seconds": float(
                    sum(float(event["wall_seconds"]) for event in stage_events)
                ),
                "request_count": int(
                    sum(int(event.get("request_count", 0)) for event in stage_events)
                ),
            }
            if stage in REQUEST_TOKEN_STAGES:
                block["input_tokens"] = int(
                    sum(int(event["input_tokens"]) for event in stage_events)
                )
                block["output_tokens"] = int(
                    sum(int(event["output_tokens"]) for event in stage_events)
                )
                block["mean_request_latency_seconds"] = (
                    block["wall_seconds"] / block["request_count"]
                    if block["request_count"] > 0
                    else None
                )
            if stage == "retrieval":
                latencies = [
                    float(value)
                    for event in stage_events
                    for value in event["latency_seconds"]
                ]
                recoveries = [
                    event.get("provider_recovery") or {}
                    for event in stage_events
                ]
                block["qa_count"] = len(latencies)
                block["latency"] = _latency_summary(latencies)
                block["provider_recovery"] = {
                    "retry_count": int(
                        sum(
                            int(recovery.get("retry_count", 0))
                            for recovery in recoveries
                        )
                    ),
                    "failure_wall_seconds_excluded": float(
                        sum(
                            float(
                                recovery.get(
                                    "failure_wall_seconds_excluded",
                                    0.0,
                                )
                            )
                            for recovery in recoveries
                        )
                    ),
                    "wait_seconds_excluded": float(
                        sum(
                            float(
                                recovery.get(
                                    "wait_seconds_excluded",
                                    0.0,
                                )
                            )
                            for recovery in recoveries
                        )
                    ),
                    "latency_policy": (
                        "completed-attempt latency only; exhausted-attempt "
                        "and inter-attempt wait time are disclosed separately"
                    ),
                }
            stages[stage] = block
        by_state[cache_state] = {
            "nonexclusive_stage_wall_sum_seconds": float(
                sum(float(event["wall_seconds"]) for event in selected)
            ),
            "wall_sum_warning": (
                "stage timings overlap; do not interpret this sum as "
                "end-to-end latency"
            ),
            "stages": stages,
        }

    disk_totals = defaultdict(int)
    disk_records = []
    for artifact in document["disk_artifacts"]:
        path = Path(str(artifact["path"])).resolve()
        size = _path_bytes(path)
        disk_totals[str(artifact["kind"])] += size
        disk_records.append(
            {
                "kind": artifact["kind"],
                "path": str(path),
                "bytes": size,
            }
        )
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "run_id": document["run_id"],
        "condition_fingerprint": document["condition_fingerprint"],
        "measurement_policy": {
            "missing_values_estimated": False,
            "latency_clock": document.get("latency_clock", "perf_counter"),
            "token_source": document.get(
                "token_source", "provider response usage"
            ),
            "cache_states": ["cold", "warm"],
            "stage_wall_times_overlap": True,
            "provider_recovery_disclosed": True,
        },
        "cache_measurements": by_state,
        "disk_usage": {
            "totals_bytes": dict(sorted(disk_totals.items())),
            "artifacts": disk_records,
        },
    }
    if manifest_path is not None:
        report["source_event_manifest"] = {
            "path": str(manifest_path.resolve()),
            "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        }
    report["report_fingerprint"] = _canonical_hash(report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    event_path = Path(args.events).resolve()
    document = _read_json(event_path)
    report = build_report(document, manifest_path=event_path)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
