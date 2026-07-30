from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(EXP_DIR))

from cost_probe_staged import (
    SCHEMA,
    _atomic_json,
    _embedding_event,
    _execute_operation,
    _graph_events,
    _load_state,
    _operation_plan,
    _recall_with_provider_recovery,
    _retrieval_events,
    _validate_matched_query_usage,
    _validated_formal_query_usage,
    command_step,
)
from cost_telemetry import CostTelemetry
from em_graph import (
    EntityExtractor,
    MemoryEmbeddingIndex,
    QueryEmbeddingArtifact,
    build_em_graph,
)
from em_graph.cache import ordered_question_records


class StagedCostProbeTests(unittest.TestCase):
    @staticmethod
    def _query_usage_events(
        cache_state: str,
        batches: list[tuple[int, int, int, int]],
    ) -> list[dict[str, object]]:
        return [
            {
                "stage": "retrieval",
                "cache_state": cache_state,
                "qa_count": batch_qa,
                "query_artifact_cache_hits": hits,
                "query_artifact_cache_misses": misses,
                "live_query_embedding_requests": live,
            }
            for batch_qa, hits, misses, live in batches
        ]

    def test_all10_plan_is_ordered_and_complete(self):
        samples = json.loads(
            (ROOT / "data" / "locomo10.json").read_text(encoding="utf-8")
        )
        operations = _operation_plan(samples, 50)
        self.assertEqual(len(operations), 128)
        self.assertEqual(operations[0]["key"], "cold:graph:conv-26")
        self.assertEqual(operations[9]["key"], "cold:graph:conv-50")
        self.assertEqual(operations[10]["key"], "cold:index:conv-26")
        self.assertEqual(operations[-1]["key"], "warm:retrieve:conv-50:200:204")
        self.assertEqual(len({item["key"] for item in operations}), 128)

    def test_atomic_json_replaces_complete_document(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir, "state.json")
            _atomic_json(path, {"version": 1})
            _atomic_json(path, {"version": 2, "complete": True})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"version": 2, "complete": True},
            )
            self.assertEqual(list(Path(tmp_dir).iterdir()), [path])

    def test_interrupted_operation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            checkpoint = Path(tmp_dir, "state.json")
            _atomic_json(
                checkpoint,
                {
                    "schema": SCHEMA,
                    "in_progress": "cold:graph:conv-26",
                },
            )
            args = SimpleNamespace(checkpoint=str(checkpoint))
            with self.assertRaisesRegex(RuntimeError, "run is invalid"):
                _load_state(args)

    def test_changed_arguments_fail_checkpoint_identity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            checkpoint = Path(tmp_dir, "state.json")
            state = {
                "schema": SCHEMA,
                "in_progress": None,
                "resolved_identity": {"measurement_id": "frozen"},
            }
            _atomic_json(checkpoint, state)
            args = SimpleNamespace(
                checkpoint=str(checkpoint),
                measurement_id="changed",
                parameter_snapshot_sha256="a" * 64,
                data_file=str(ROOT / "data" / "locomo10.json"),
                cache_dir=str(Path(tmp_dir, "cache")),
                warm_cost_file=str(Path(tmp_dir, "warm.json")),
                output_events=str(Path(tmp_dir, "events.json")),
                output_report=str(Path(tmp_dir, "report.json")),
                query_artifact=str(Path(tmp_dir, "query.npz")),
                formal_query_usage=str(Path(tmp_dir, "query_usage.json")),
                scope="all10",
                samples=None,
                variant="B",
                top_k=25,
                batch_size=50,
                provider_recovery_attempts=6,
                provider_recovery_wait_seconds=30.0,
                provider_recovery_max_wait_seconds=120.0,
                extract_model="gpt-3.5-turbo",
                embedding_model="text-embedding-3-small",
                answer_model="gpt-3.5-turbo",
                entity_weight=0.3,
                semantic_weight=0.7,
                sequence_scale=0.5,
                entity_min_rel_score=0.5,
                entity_top_k_per_key=20,
                who_only_dampen=0.25,
                no_degree_discount=False,
            )
            with self.assertRaisesRegex(ValueError, "arguments differ"):
                _load_state(args)

    def test_step_commits_events_after_operation_completes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            checkpoint = Path(tmp_dir, "state.json")
            cache_root = Path(tmp_dir, "cache")
            operation = {
                "key": "cold:graph:conv-26",
                "kind": "graph",
                "cache_state": "cold",
                "sample_id": "conv-26",
            }
            _atomic_json(
                checkpoint,
                {
                    "schema": SCHEMA,
                    "cache_root": str(cache_root.resolve()),
                    "operations": [operation],
                    "completed": [],
                    "in_progress": None,
                    "events": [],
                    "query_artifact_identity": {"sha256": "query"},
                    "formal_query_usage_identity": {
                        "sha256": "query-usage"
                    },
                    "qa_count": 1,
                },
            )
            args = SimpleNamespace(
                checkpoint=str(checkpoint),
                cache_dir=str(cache_root),
            )
            event = {
                "stage": "graph_construction",
                "cache_state": "cold",
                "wall_seconds": 1.0,
                "request_count": 0,
            }
            with patch(
                "cost_probe_staged.assert_formal_source_clean",
            ), patch(
                "cost_probe_staged._validated_query_artifact",
                return_value=(object(), {"sha256": "query"}),
            ), patch(
                "cost_probe_staged._validated_formal_query_usage",
                return_value={"sha256": "query-usage"},
            ), patch(
                "cost_probe_staged._sample_map",
                return_value={"conv-26": {"sample_id": "conv-26"}},
            ), patch(
                "cost_probe_staged._execute_operation",
                return_value=[event],
            ):
                command_step(args)
            state = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertIsNone(state["in_progress"])
            self.assertEqual(state["completed"], [operation["key"]])
            self.assertEqual(state["events"], [event])

    def test_threaded_graph_calls_are_reduced_to_entity_usage(self):
        sample = {
            "sample_id": "sample",
            "conversation": {
                "session_1_date_time": "1:00 PM on 1 January, 2020",
                "session_1": [
                    {
                        "dia_id": "D1:1",
                        "speaker": "A",
                        "text": "Alice visited Paris.",
                    },
                    {
                        "dia_id": "D1:2",
                        "speaker": "B",
                        "text": "Bob visited Rome.",
                    },
                ],
            },
        }
        response = SimpleNamespace(
            model="provider-model",
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=2,
                total_tokens=12,
            ),
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="[]", model_extra={})
                )
            ],
        )
        client = MagicMock()
        client.chat.completions.create.return_value = response
        extractor = EntityExtractor(
            model="requested-model",
            use_cache=False,
            wait_time=0,
        )
        telemetry = CostTelemetry("cold")
        with patch(
            "em_graph.build.entity_extractor.set_api_key_from_env",
        ), patch(
            "common.llm.set_api_key_from_env",
        ), patch(
            "common.llm._get_openai_client",
            return_value=client,
        ):
            with telemetry.stage("graph_construction"):
                build_em_graph(sample, extractor=extractor, max_workers=2)
        events = {event["stage"]: event for event in _graph_events(telemetry)}
        self.assertEqual(events["entity_extraction"]["request_count"], 2)
        self.assertEqual(events["entity_extraction"]["input_tokens"], 20)
        self.assertEqual(events["entity_extraction"]["output_tokens"], 4)

    def test_real_embedding_client_usage_reaches_cost_event(self):
        response = SimpleNamespace(
            model="provider-embedding",
            usage=SimpleNamespace(
                prompt_tokens=5,
                total_tokens=5,
            ),
            data=[
                SimpleNamespace(index=0, embedding=[1.0, 0.0]),
                SimpleNamespace(index=1, embedding=[0.0, 1.0]),
            ],
        )
        client = MagicMock()
        client.embeddings.create.return_value = response
        index = MemoryEmbeddingIndex(
            memory_ids=[],
            vectors=np.zeros((0, 0), dtype=np.float32),
            model_name="requested-embedding",
            _client=client,
        )
        telemetry = CostTelemetry("cold")
        with telemetry.stage("embedding"):
            vectors = index._embed_batch_api(["one", "two"])
        event = _embedding_event(telemetry)
        self.assertEqual(vectors.shape, (2, 2))
        self.assertEqual(event["request_count"], 1)
        self.assertEqual(event["input_tokens"], 5)
        self.assertEqual(event["output_tokens"], 0)
        self.assertEqual(index.embedding_usage()["request_count"], 1)
        self.assertEqual(index.embedding_usage()["input_tokens"], 5)

    def test_retrieval_requires_at_least_one_query_artifact_hit_per_qa(self):
        samples = [{"sample_id": "sample", "qa": [{"question": "Q?"}]}]
        records = ordered_question_records(samples)
        artifact = QueryEmbeddingArtifact(
            dataset_sha256="a" * 64,
            model_name="model",
            role="context",
            qa_records=records,
            question_digests=[records[0]["question_sha256"]],
            vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
        )
        artifact.get("Q?", "model", "context")
        telemetry = CostTelemetry("cold")
        telemetry.retrieval_latencies = [0.1]
        events = _retrieval_events(
            telemetry,
            query_artifact=artifact,
        )
        retrieval = next(
            event for event in events if event["stage"] == "retrieval"
        )
        self.assertEqual(retrieval["query_artifact_cache_hits"], 1)
        self.assertEqual(retrieval["query_artifact_cache_misses"], 0)
        self.assertEqual(retrieval["live_query_embedding_requests"], 0)

    def test_retrieval_allows_fallback_to_read_query_artifact_twice(self):
        samples = [{"sample_id": "sample", "qa": [{"question": "Q?"}]}]
        records = ordered_question_records(samples)
        artifact = QueryEmbeddingArtifact(
            dataset_sha256="a" * 64,
            model_name="model",
            role="context",
            qa_records=records,
            question_digests=[records[0]["question_sha256"]],
            vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
        )
        artifact.get("Q?", "model", "context")
        artifact.get("Q?", "model", "context")
        telemetry = CostTelemetry("cold")
        telemetry.retrieval_latencies = [0.1]
        events = _retrieval_events(
            telemetry,
            query_artifact=artifact,
        )
        retrieval = next(
            event for event in events if event["stage"] == "retrieval"
        )
        self.assertEqual(retrieval["query_artifact_cache_hits"], 2)

    def test_retrieval_rejects_fewer_query_hits_than_qa(self):
        samples = [{"sample_id": "sample", "qa": [{"question": "Q?"}]}]
        records = ordered_question_records(samples)
        artifact = QueryEmbeddingArtifact(
            dataset_sha256="a" * 64,
            model_name="model",
            role="context",
            qa_records=records,
            question_digests=[records[0]["question_sha256"]],
            vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
        )
        telemetry = CostTelemetry("cold")
        telemetry.retrieval_latencies = [0.1]
        with self.assertRaisesRegex(
            RuntimeError,
            "below retrieval QA count",
        ):
            _retrieval_events(telemetry, query_artifact=artifact)

    def test_formal_query_usage_binds_exact_lookup_count(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir, "query_usage.json")
            path.write_text(
                json.dumps(
                    {
                        "schema": "query_embedding_usage_v1",
                        "qa_count": 2,
                        "required_lookup_count": 2,
                        "lookup_count": 3,
                        "cache_hits": 3,
                        "cache_misses": 0,
                        "live_embedding_requests": 0,
                        "status": "pass",
                    }
                ),
                encoding="utf-8",
            )
            identity = _validated_formal_query_usage(
                SimpleNamespace(formal_query_usage=str(path)),
                qa_count=2,
            )
            self.assertEqual(identity["lookup_count"], 3)
            self.assertEqual(identity["cache_hits"], 3)

    def test_matched_query_usage_allows_disclosed_formal_delta(self):
        batches = [(1, 1, 0, 0), (1, 2, 0, 0)]
        events = self._query_usage_events("cold", batches)
        events.extend(self._query_usage_events("warm", batches))
        result = _validate_matched_query_usage(
            events,
            qa_count=2,
            formal_lookup_count=2,
        )
        self.assertEqual(result["cold"]["query_artifact_cache_hits"], 3)
        self.assertEqual(result["warm"]["query_artifact_cache_hits"], 3)
        self.assertEqual(result["cold"]["hit_delta_from_formal_reference"], 1)

    def test_matched_query_usage_rejects_paired_batch_difference(self):
        events = self._query_usage_events(
            "cold",
            [(1, 1, 0, 0), (1, 2, 0, 0)],
        )
        events.extend(
            self._query_usage_events(
                "warm",
                [(1, 2, 0, 0), (1, 1, 0, 0)],
            )
        )
        with self.assertRaisesRegex(RuntimeError, "batch usage differs"):
            _validate_matched_query_usage(
                events,
                qa_count=2,
                formal_lookup_count=2,
            )

    def test_matched_query_usage_rejects_miss_or_live_request(self):
        for batches in (
            [(1, 1, 1, 0)],
            [(1, 1, 0, 1)],
        ):
            events = self._query_usage_events("cold", batches)
            events.extend(self._query_usage_events("warm", batches))
            with self.assertRaisesRegex(RuntimeError, "usage is invalid"):
                _validate_matched_query_usage(
                    events,
                    qa_count=1,
                    formal_lookup_count=1,
                )

    def test_matched_query_usage_rejects_fewer_hits_than_qa(self):
        batches = [(2, 1, 0, 0)]
        events = self._query_usage_events("cold", batches)
        events.extend(self._query_usage_events("warm", batches))
        with self.assertRaisesRegex(RuntimeError, "usage is invalid"):
            _validate_matched_query_usage(
                events,
                qa_count=2,
                formal_lookup_count=2,
            )

    def test_retrieval_operation_uses_strict_read_only_query_artifact(self):
        samples = [{"sample_id": "sample", "qa": [{"question": "Q?"}]}]
        records = ordered_question_records(samples)
        artifact = QueryEmbeddingArtifact(
            dataset_sha256="a" * 64,
            model_name="model",
            role="context",
            qa_records=records,
            question_digests=[records[0]["question_sha256"]],
            vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
        )
        args = SimpleNamespace(
            cache_dir="/tmp/unused",
            variant="B",
            extract_model="extract",
            embedding_model="model",
            top_k=25,
            provider_recovery_attempts=0,
            provider_recovery_wait_seconds=0.0,
            provider_recovery_max_wait_seconds=0.0,
        )
        operation = {
            "kind": "retrieve",
            "cache_state": "cold",
            "sample_id": "sample",
            "qa_start": 0,
            "qa_end": 1,
        }
        observed = {}

        def fake_load_recall(_sample, **kwargs):
            observed.update(kwargs)

            def recall(_sample, _qa_index, question, _top_k):
                kwargs["query_cache"].get(question, "model", "context")

            return SimpleNamespace(
                recall=recall,
                embedding_index=SimpleNamespace(
                    embedding_usage=lambda: {
                        "request_count": 0,
                        "input_tokens": 0,
                    }
                ),
            )

        with patch(
            "cost_probe_staged.graph_runner.EMGraphArtifactStore.from_env",
            return_value=object(),
        ), patch(
            "cost_probe_staged.graph_runner._recall_parameters_from_args",
            return_value={"force_full_pool": False},
        ), patch(
            "cost_probe_staged._shared_recall_inputs",
            return_value=(None, None),
        ), patch(
            "cost_probe_staged.graph_runner._load_recall",
            side_effect=fake_load_recall,
        ):
            events = _execute_operation(
                args,
                operation,
                samples[0],
                query_artifact=artifact,
            )
        self.assertTrue(observed["strict_query_cache"])
        self.assertFalse(observed["use_text_cache"])
        self.assertIs(observed["query_cache"], artifact)
        retrieval = next(
            event for event in events if event["stage"] == "retrieval"
        )
        self.assertEqual(retrieval["query_artifact_cache_hits"], 1)

    def test_provider_exhaustion_retries_same_qa_and_discloses_outage(self):
        recall = MagicMock()
        recall.recall.side_effect = [
            RuntimeError("Failed after 10 retries for model=gpt-3.5-turbo"),
            None,
        ]
        telemetry = CostTelemetry("cold")
        args = SimpleNamespace(
            top_k=25,
            provider_recovery_attempts=2,
            provider_recovery_wait_seconds=3.0,
            provider_recovery_max_wait_seconds=5.0,
        )
        with patch("cost_probe_staged.time.sleep") as sleep:
            _recall_with_provider_recovery(
                args,
                telemetry,
                recall,
                {"sample_id": "sample"},
                7,
                "Question?",
            )
        self.assertEqual(recall.recall.call_count, 2)
        sleep.assert_called_once_with(3.0)
        self.assertEqual(len(telemetry.retrieval_latencies), 1)
        self.assertEqual(len(telemetry.provider_recovery_events), 1)
        recovery = telemetry.provider_recovery_events[0]
        self.assertEqual(recovery["wait_seconds"], 3.0)
        self.assertEqual(recovery["error_type"], "RuntimeError")

    def test_non_provider_runtime_error_is_not_retried(self):
        recall = MagicMock()
        recall.recall.side_effect = RuntimeError("graph identity mismatch")
        telemetry = CostTelemetry("cold")
        args = SimpleNamespace(
            top_k=25,
            provider_recovery_attempts=6,
            provider_recovery_wait_seconds=30.0,
            provider_recovery_max_wait_seconds=120.0,
        )
        with patch("cost_probe_staged.time.sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "graph identity"):
                _recall_with_provider_recovery(
                    args,
                    telemetry,
                    recall,
                    {"sample_id": "sample"},
                    0,
                    "Question?",
                )
        sleep.assert_not_called()
        self.assertEqual(recall.recall.call_count, 1)
        self.assertEqual(telemetry.retrieval_latencies, [])
        self.assertEqual(telemetry.provider_recovery_events, [])

    def test_provider_recovery_is_bounded_and_uses_capped_backoff(self):
        recall = MagicMock()
        recall.recall.side_effect = RuntimeError(
            "Failed after 10 retries for model=gpt-3.5-turbo"
        )
        telemetry = CostTelemetry("cold")
        args = SimpleNamespace(
            top_k=25,
            provider_recovery_attempts=2,
            provider_recovery_wait_seconds=3.0,
            provider_recovery_max_wait_seconds=5.0,
        )
        with patch("cost_probe_staged.time.sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "Failed after 10"):
                _recall_with_provider_recovery(
                    args,
                    telemetry,
                    recall,
                    {"sample_id": "sample"},
                    0,
                    "Question?",
                )
        self.assertEqual(recall.recall.call_count, 3)
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [3.0, 5.0],
        )
        self.assertEqual(len(telemetry.provider_recovery_events), 2)
        self.assertEqual(telemetry.retrieval_latencies, [])


if __name__ == "__main__":
    unittest.main()
