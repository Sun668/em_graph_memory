"""Stage-aware collection of provider usage and pipeline wall times."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

from common.llm import observe_model_usage


class CostTelemetry:
    """Collect raw measurements and emit strict cost-report stage events."""

    def __init__(self, cache_state: str):
        if cache_state not in {"cold", "warm"}:
            raise ValueError("cache_state must be cold or warm")
        self.cache_state = cache_state
        self.provider_events: List[Dict[str, Any]] = []
        self.provider_recovery_events: List[Dict[str, Any]] = []
        self.stage_walls: Dict[str, float] = {}
        self.retrieval_latencies: List[float] = []

    def _observe(self, event: Mapping[str, Any]) -> None:
        self.provider_events.append(dict(event))

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        with observe_model_usage(self._observe, stage=name):
            yield
        self.stage_walls[name] = self.stage_walls.get(name, 0.0) + (
            time.perf_counter() - started
        )

    @contextmanager
    def retrieval(self) -> Iterator[None]:
        started = time.perf_counter()
        with observe_model_usage(self._observe, stage="query_entity"):
            yield
        self.retrieval_latencies.append(time.perf_counter() - started)

    def record_provider_recovery(
        self,
        *,
        failure_wall_seconds: float,
        wait_seconds: float,
        error: BaseException,
    ) -> None:
        """Record excluded outage time before retrying the same retrieval."""
        self.provider_recovery_events.append(
            {
                "failure_wall_seconds": float(failure_wall_seconds),
                "wait_seconds": float(wait_seconds),
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )

    def _provider_stage(
        self,
        stage: str,
        *,
        operation: Optional[str] = None,
        observed_stages: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        source_stages = set(observed_stages or [stage])
        selected = [
            event
            for event in self.provider_events
            if event["stage"] in source_stages
            and (operation is None or event["operation"] == operation)
        ]
        token_values = [
            event.get(key)
            for event in selected
            for key in ("input_tokens", "output_tokens")
        ]
        if any(value is None for value in token_values):
            raise ValueError(
                f"provider token usage missing for {stage}/{operation}"
            )
        return {
            "stage": stage,
            "cache_state": self.cache_state,
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

    def events(self) -> List[Dict[str, Any]]:
        embedding = [
            event
            for event in self.provider_events
            if event["operation"] == "embedding"
        ]
        if any(event.get("input_tokens") is None for event in embedding):
            raise ValueError("provider token usage missing for embedding")
        embedding_event = {
            "stage": "embedding",
            "cache_state": self.cache_state,
            "wall_seconds": float(
                self.stage_walls.get(
                    "embedding",
                    sum(float(event["wall_seconds"]) for event in embedding),
                )
            ),
            "request_count": int(
                sum(int(event["request_count"]) for event in embedding)
            ),
            "input_tokens": int(
                sum(int(event["input_tokens"]) for event in embedding)
            ),
            "output_tokens": 0,
        }
        retrieval_event = {
            "stage": "retrieval",
            "cache_state": self.cache_state,
            "wall_seconds": float(sum(self.retrieval_latencies)),
            "request_count": 0,
            "qa_count": len(self.retrieval_latencies),
            "latency_seconds": list(self.retrieval_latencies),
        }
        if not self.retrieval_latencies:
            raise ValueError("at least one retrieval measurement is required")
        return [
            {
                "stage": "graph_construction",
                "cache_state": self.cache_state,
                "wall_seconds": float(
                    self.stage_walls.get("graph_construction", 0.0)
                ),
                "request_count": 0,
            },
            self._provider_stage(
                "entity_extraction",
                operation="chat",
                observed_stages=[
                    "entity_extraction",
                    "graph_construction",
                ],
            ),
            embedding_event,
            self._provider_stage("query_entity", operation="chat"),
            retrieval_event,
            self._provider_stage("answer_generation", operation="chat"),
        ]
