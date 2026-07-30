from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(EXP_DIR))

from cost_telemetry import CostTelemetry


def _provider(stage, operation, input_tokens, output_tokens, wall=0.1):
    return {
        "stage": stage,
        "operation": operation,
        "requested_model": "requested",
        "actual_model": "actual",
        "request_count": 1,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": (
            None
            if input_tokens is None
            else input_tokens + (output_tokens or 0)
        ),
        "wall_seconds": wall,
        "token_source": "provider response usage",
    }


class CostTelemetryTests(unittest.TestCase):
    def test_graph_stage_chat_usage_is_reported_as_entity_extraction(self):
        telemetry = CostTelemetry("cold")
        telemetry.provider_events = [
            _provider("graph_construction", "chat", 10, 2),
        ]
        telemetry.retrieval_latencies = [0.1]
        events = {event["stage"]: event for event in telemetry.events()}
        self.assertEqual(events["entity_extraction"]["request_count"], 1)
        self.assertEqual(events["entity_extraction"]["input_tokens"], 10)

    def test_stage_events_partition_provider_operations(self):
        telemetry = CostTelemetry("cold")
        telemetry.provider_events = [
            _provider("entity_extraction", "chat", 10, 2),
            _provider("query_entity", "chat", 5, 1),
            _provider("query_entity", "embedding", 7, None),
            _provider("answer_generation", "chat", 20, 3),
        ]
        telemetry.stage_walls["graph_construction"] = 1.5
        telemetry.retrieval_latencies = [0.2, 0.3]
        events = {event["stage"]: event for event in telemetry.events()}
        self.assertEqual(events["entity_extraction"]["input_tokens"], 10)
        self.assertEqual(events["query_entity"]["input_tokens"], 5)
        self.assertEqual(events["embedding"]["request_count"], 1)
        self.assertEqual(events["answer_generation"]["output_tokens"], 3)
        self.assertEqual(events["retrieval"]["qa_count"], 2)
        self.assertEqual(events["graph_construction"]["wall_seconds"], 1.5)

    def test_warm_zero_provider_requests_are_preserved(self):
        telemetry = CostTelemetry("warm")
        telemetry.retrieval_latencies = [0.01]
        events = {event["stage"]: event for event in telemetry.events()}
        self.assertEqual(events["entity_extraction"]["request_count"], 0)
        self.assertEqual(events["query_entity"]["input_tokens"], 0)
        self.assertEqual(events["embedding"]["request_count"], 0)
        self.assertEqual(events["answer_generation"]["output_tokens"], 0)

    def test_missing_provider_usage_fails(self):
        telemetry = CostTelemetry("cold")
        telemetry.provider_events = [
            _provider("query_entity", "chat", None, 1),
        ]
        telemetry.retrieval_latencies = [0.1]
        with self.assertRaisesRegex(ValueError, "token usage missing"):
            telemetry.events()


if __name__ == "__main__":
    unittest.main()
