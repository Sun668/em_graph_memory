"""Regression tests for publish-stack cache identity."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from em_graph import (
    EMGraph,
    ExtractedEntity,
    MemoryEmbeddingIndex,
    MemoryNode,
    retrieve_dialog_ids,
    retrieve_dialog_ids_with_audit,
)
from experiments.exp_2026_07_26_locomo_official_compare.run_publish_stack import (
    answer_checkpoint_is_current,
    answer_response_cache_key,
    artifact_scope,
    emb_path,
    ensure_qkeys,
    official_row_round,
    qa_cache_key,
    select_samples,
    text_embedding_cache_path,
)


class PublishStackCacheIdentityTest(unittest.TestCase):
    def test_full_question_sha256_prevents_120_character_collision(self) -> None:
        prefix = "x" * 120
        first = prefix + " first suffix"
        second = prefix + " second suffix"

        first_key = qa_cache_key("conv-26", 1, first)
        second_key = qa_cache_key("conv-26", 1, second)

        self.assertNotEqual(first_key, second_key)
        self.assertTrue(
            first_key.endswith(hashlib.sha256(first.encode("utf-8")).hexdigest())
        )
        self.assertTrue(
            second_key.endswith(hashlib.sha256(second.encode("utf-8")).hexdigest())
        )

    def test_qa_index_keeps_duplicate_questions_distinct(self) -> None:
        first_key = qa_cache_key("conv-26", 1, "Same question?")
        second_key = qa_cache_key("conv-26", 2, "Same question?")
        self.assertNotEqual(first_key, second_key)

    def test_embedding_identity_validates_model_ids_and_text_digests(self) -> None:
        index = MemoryEmbeddingIndex(
            memory_ids=["memory:D1"],
            vectors=np.ones((1, 3), dtype=np.float32),
            model_name="text-embedding-3-small",
            text_digests=["digest-one"],
        )
        self.assertTrue(
            index.matches(
                model_name="text-embedding-3-small",
                memory_ids=["memory:D1"],
                text_digests=["digest-one"],
            )
        )
        self.assertFalse(
            index.matches(
                model_name="other-model",
                memory_ids=["memory:D1"],
                text_digests=["digest-one"],
            )
        )
        self.assertFalse(
            index.matches(
                model_name="text-embedding-3-small",
                memory_ids=["memory:D2"],
                text_digests=["digest-one"],
            )
        )
        self.assertFalse(
            index.matches(
                model_name="text-embedding-3-small",
                memory_ids=["memory:D1"],
                text_digests=["digest-two"],
            )
        )

    def test_embedding_scores_preserve_negative_cosine_values(self) -> None:
        index = MemoryEmbeddingIndex(
            memory_ids=["memory:D1", "memory:D2"],
            vectors=np.asarray(
                [
                    [-1.0, 0.0],
                    [-0.25, 0.0],
                ],
                dtype=np.float32,
            ),
            model_name="text-embedding-3-small",
        )

        with patch.object(
            index,
            "_embed_query",
            return_value=np.asarray([1.0, 0.0], dtype=np.float32),
        ):
            scores = index.scores("question")

        self.assertEqual(scores, {"memory:D1": -1.0, "memory:D2": -0.25})

    def test_full_pool_retrieval_returns_top_k_negative_scores(self) -> None:
        graph = EMGraph(sample_id="negative-top-k")
        for turn in range(1, 4):
            graph.add_memory(
                MemoryNode(
                    id=f"memory:D1:{turn}",
                    dia_id=f"D1:{turn}",
                    session_num=1,
                    date_time="1:56 pm on 8 May, 2023",
                    speaker="Caroline",
                    text=f"Dialog {turn}",
                    text_normalized=f"Dialog {turn}",
                )
            )

        class NegativeEmbeddingIndex:
            def scores(self, query, memory_ids=None):
                del query
                values = {
                    "memory:D1:1": -0.9,
                    "memory:D1:2": -0.1,
                    "memory:D1:3": -0.5,
                }
                if memory_ids is None:
                    return values
                allowed = set(memory_ids)
                return {
                    key: value
                    for key, value in values.items()
                    if key in allowed
                }

        ranked = retrieve_dialog_ids(
            graph,
            "question",
            top_k=2,
            embedding_index=NegativeEmbeddingIndex(),
            q_entity_keys=set(),
            entity_weight=0.0,
            semantic_weight=1.0,
        )

        self.assertEqual(ranked, [("D1:2", -0.1), ("D1:3", -0.5)])
        audited, audit = retrieve_dialog_ids_with_audit(
            graph,
            "question",
            top_k=2,
            embedding_index=NegativeEmbeddingIndex(),
            q_entity_keys=set(),
            entity_weight=0.0,
            semantic_weight=1.0,
        )
        self.assertEqual(audited, ranked)
        self.assertEqual(
            [row["embedding_score"] for row in audit["ranked"]],
            [-0.1, -0.5],
        )

    def test_a_and_b_use_one_canonical_embedding_path(self) -> None:
        expected = emb_path("conv-26", "text-embedding-3-small")
        self.assertEqual(
            expected.name,
            "conv-26_memory_emb_extract_v4_gpt35_tes_"
            "text-embedding-3-small.npz",
        )

    def test_conv26_scope_isolated_from_all10_artifacts(self) -> None:
        self.assertEqual(artifact_scope(None), "all10")
        self.assertEqual(artifact_scope(["conv-26"]), "conv-26")
        selected = select_samples(
            [{"sample_id": "conv-26"}, {"sample_id": "conv-30"}],
            ["conv-26"],
        )
        self.assertEqual(selected, [{"sample_id": "conv-26"}])
        with self.assertRaises(ValueError):
            select_samples([{"sample_id": "conv-26"}], ["missing"])

    def test_shared_query_embedding_cache_is_model_specific(self) -> None:
        path = text_embedding_cache_path("text-embedding-3-small")
        self.assertEqual(
            path.name,
            "text_embed_cache_gpt35_tes_text-embedding-3-small.npz",
        )

    def test_answer_cache_uses_full_prompt_identity(self) -> None:
        base = {
            "question": "Where did Caroline go?",
            "category": 4,
            "context": "Context one",
            "model": "gpt-3.5-turbo",
            "ground_truth": "Paris",
        }
        first = answer_response_cache_key(**base)
        same_non_cat5_prompt = answer_response_cache_key(
            **{**base, "ground_truth": "Different evaluation-only answer"}
        )
        different_context = answer_response_cache_key(
            **{**base, "context": "Context two"}
        )
        different_model = answer_response_cache_key(
            **{**base, "model": "another-model"}
        )
        cat5_first = answer_response_cache_key(
            **{**base, "category": 5, "ground_truth": "Paris"}
        )
        cat5_second = answer_response_cache_key(
            **{**base, "category": 5, "ground_truth": "Rome"}
        )

        self.assertEqual(first, same_non_cat5_prompt)
        self.assertNotEqual(first, different_context)
        self.assertNotEqual(first, different_model)
        self.assertNotEqual(cat5_first, cat5_second)

    def test_qkeys_cache_identity_includes_full_question_sha256(self) -> None:
        class FakeExtractor:
            def __init__(self) -> None:
                self.calls = []

            def extract(self, text):
                self.calls.append(text)
                return [ExtractedEntity(value=text.split()[0], type="Who")]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qkeys.json"
            first_sample = {
                "qa": [{"question": "Alice visited where?"}],
            }
            second_sample = {
                "qa": [{"question": "Bob visited where?"}],
            }
            extractor = FakeExtractor()
            with patch(
                "experiments.exp_2026_07_26_locomo_official_compare."
                "run_publish_stack.qkeys_path",
                return_value=path,
            ):
                first = ensure_qkeys("conv-test", first_sample, extractor)
                second = ensure_qkeys("conv-test", second_sample, extractor)

            self.assertEqual(first[1], {"alice"})
            self.assertEqual(second[1], {"bob"})
            self.assertEqual(extractor.calls, [
                "Alice visited where?",
                "Bob visited where?",
            ])
            payload = json.loads(path.read_text(encoding="utf-8"))
            second_key = qa_cache_key(
                "conv-test", 1, "Bob visited where?"
            )
            self.assertEqual(payload, {second_key: ["bob"]})

    def test_checkpoint_requires_complete_response_identity(self) -> None:
        current = {
            "prediction": "Paris",
            "context_ids": ["D1:1"],
            "token_f1": 1.0,
            "answer_response_cache_key": "new-protocol-key",
        }
        self.assertTrue(
            answer_checkpoint_is_current(
                current,
                context_ids=["D1:1"],
                expected_response_key="new-protocol-key",
            )
        )
        self.assertFalse(
            answer_checkpoint_is_current(
                current,
                context_ids=["D1:1"],
                expected_response_key="old-protocol-key",
            )
        )

    def test_official_row_rounds_before_aggregation(self) -> None:
        self.assertEqual(official_row_round(2.0 / 3.0), 0.667)


if __name__ == "__main__":
    unittest.main()
