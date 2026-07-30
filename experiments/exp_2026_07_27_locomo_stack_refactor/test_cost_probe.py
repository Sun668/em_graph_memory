from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(EXP_DIR))

from cost_probe import (
    _answer_event,
    _measure_state,
    _replace_answer,
    _validate_warm_identity,
)
from em_graph import QuestionEntityCache


class CostProbeTests(unittest.TestCase):
    def test_measurement_shares_writable_caches_across_samples(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = SimpleNamespace(
                cache_dir=tmp_dir,
                variant="B",
                top_k=25,
                extract_model="gpt-3.5-turbo",
                embedding_model="text-embedding-3-small",
                entity_weight=0.3,
                semantic_weight=0.7,
                sequence_scale=0.5,
                entity_min_rel_score=0.5,
                entity_top_k_per_key=20,
                who_only_dampen=0.25,
                no_degree_discount=False,
            )
            samples = [
                {"sample_id": "conv-a", "qa": [{"question": "one"}]},
                {"sample_id": "conv-b", "qa": [{"question": "two"}]},
            ]
            question_path = Path(tmp_dir, "question_entities.json")
            store = SimpleNamespace(
                root=Path(tmp_dir),
                text_embedding_cache_path=lambda _model: Path(
                    tmp_dir, "text_embeddings.npz"
                ),
                question_entity_cache_path=lambda: question_path,
            )
            text_cache = object()
            question_extractor = object()
            shared_caches = []

            def fake_load_recall(sample, **kwargs):
                question_cache = kwargs["question_cache"]
                shared_caches.append(question_cache)

                def recall(
                    routed_sample,
                    qa_index,
                    question,
                    _top_k,
                ):
                    question_cache.set(
                        routed_sample["sample_id"],
                        qa_index,
                        question,
                        {routed_sample["sample_id"]},
                    )

                return SimpleNamespace(recall=recall)

            with patch(
                "cost_probe.graph_runner.EMGraphArtifactStore.from_env",
                return_value=store,
            ), patch(
                "cost_probe.graph_runner.build_graph",
            ), patch(
                "cost_probe.graph_runner.TextEmbeddingCache",
                return_value=text_cache,
            ) as text_cache_type, patch(
                "cost_probe.graph_runner._question_extractor",
                return_value=question_extractor,
            ) as extractor_factory, patch(
                "cost_probe.graph_runner.QuestionEntityCache",
                wraps=QuestionEntityCache,
            ) as question_cache_type, patch(
                "cost_probe.graph_runner._load_recall",
                side_effect=fake_load_recall,
            ) as load_recall:
                events, returned_store = _measure_state(
                    args,
                    samples,
                    cache_state="cold",
                )

            self.assertIs(returned_store, store)
            self.assertEqual(len(events), 6)
            self.assertEqual(load_recall.call_count, 2)
            self.assertIs(shared_caches[0], shared_caches[1])
            shared_caches[0].flush()
            retained = __import__("json").loads(
                question_path.read_text(encoding="utf-8")
            )
            self.assertEqual(len(retained), 2)
            for call in load_recall.call_args_list:
                self.assertIs(call.kwargs["text_cache"], text_cache)
                self.assertIs(
                    call.kwargs["question_extractor"],
                    question_extractor,
                )
                self.assertIs(
                    call.kwargs["question_cache"],
                    shared_caches[0],
                )
            text_cache_type.assert_called_once()
            extractor_factory.assert_called_once_with(args.extract_model, store)
            question_cache_type.assert_called_once()

    def test_answer_measurement_is_reused_with_explicit_disclosure(self):
        warm = {
            "events": [
                {
                    "stage": "answer_generation",
                    "cache_state": "warm",
                    "wall_seconds": 2,
                    "request_count": 3,
                    "input_tokens": 30,
                    "output_tokens": 6,
                }
            ]
        }
        cold_answer = _answer_event(warm, "cold")
        self.assertEqual(cold_answer["cache_state"], "cold")
        self.assertEqual(cold_answer["request_count"], 3)
        self.assertIn("independent", cold_answer["measurement_reuse"])
        events = _replace_answer(
            [
                {"stage": "retrieval"},
                {"stage": "answer_generation", "request_count": 0},
            ],
            cold_answer,
        )
        self.assertEqual(events[1], cold_answer)
        self.assertEqual(events[0]["stage"], "retrieval")

    def test_warm_document_must_have_exactly_one_answer_event(self):
        with self.assertRaisesRegex(ValueError, "one answer"):
            _answer_event({"events": []}, "cold")

    def test_warm_identity_mismatch_fails(self):
        args = SimpleNamespace(
            data_file=str(ROOT / "data/locomo10.json"),
            variant="B",
            top_k=25,
            extract_model="gpt-3.5-turbo",
            embedding_model="text-embedding-3-small",
            answer_model="gpt-3.5-turbo",
        )
        config = {
            "condition_fingerprint": "a" * 64,
            "sample_ids": ["conv-26"],
            "retrieval": {"variant": "B", "top_k": 10},
            "models": {
                "extraction": "gpt-3.5-turbo",
                "embedding": "text-embedding-3-small",
                "answer": "gpt-3.5-turbo",
            },
            "artifacts": {"cost_events": "cost_events_warm.json"},
        }
        with patch(
            "cost_probe.validate_formal_result",
            return_value={"status": "pass"},
        ), patch(
            "pathlib.Path.read_text",
            return_value=__import__("json").dumps(config),
        ):
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                _validate_warm_identity(
                    Path("/tmp/condition/cost_events_warm.json"),
                    {"condition_fingerprint": "a" * 64},
                    args,
                    [{"sample_id": "conv-26"}],
                )


if __name__ == "__main__":
    unittest.main()
