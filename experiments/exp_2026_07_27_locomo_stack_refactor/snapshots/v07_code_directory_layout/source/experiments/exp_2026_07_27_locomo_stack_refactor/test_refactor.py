from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from common.llm import run_chatgpt
from em_graph import (
    EMGraph,
    EMGraphArtifactStore,
    EMGraphRecall,
    MemoryEmbeddingIndex,
    MemoryNode,
    build_em_graph,
    build_memory_graph,
)
from em_graph.recall.tokenize import memory_search_text
from em_graph.cache import QuestionEntityCache
from locomo_eval import (
    LoCoMoEvaluationConfig,
    OfficialLoCoMoEvaluator,
    RecalledQAContext,
)
from locomo_eval.vendor_runtime import VENDOR_ROOT, load_official_modules
from experiments.exp_2026_07_27_locomo_stack_refactor.run import (
    _embedding_identity,
    _graph_identity,
)


EXPECTED_VENDOR_HASHES = {
    "LICENSE.txt": "41003d4a74749c0220e33dd415042164b5a1093ed401f36277234f772d22d3d0",
    "global_methods.py": "d377f85e090b9fcea13b74bbd4016bb551371f2b98aa9cee43ddab301fcf2a3d",
    "task_eval/evaluate_qa.py": "dde7c1c6b5501486f96ce31398d6e49de76abbfa656e980b137e54fc69e9f6ee",
    "task_eval/evaluation.py": "8e3be5d57ff2ff9ec5cd05939592f468c5f3f1fd95d13e431932bdf6bf0fd6fd",
    "task_eval/evaluation_stats.py": "d36bf596de05ea6f1c355e433167a8cd704bea3a3745277c650ac0c464bba139",
    "task_eval/gpt_utils.py": "5fc977375878199735acd28fba5ae6f4d657fa0e000c0d2918a90c07b6035793",
    "task_eval/rag_utils.py": "136a30a444a1b3a2533e71a5aa94f8b4f30f06f784b66528a8efcb6dbe50f6c7",
}


class _EmbeddingIndex:
    def scores(self, _question, memory_ids=None):
        scores = {"memory:D1:1": -0.2, "memory:D1:2": -0.8}
        if memory_ids is None:
            return scores
        return {key: scores[key] for key in memory_ids}


class _Recall:
    def __init__(self):
        self.calls = []

    def recall(self, sample, qa_index, question, top_k):
        self.calls.append((sample["sample_id"], qa_index, question, top_k))
        return RecalledQAContext(
            context='1:00 PM on 1 January, 2020: A said, "Paris"',
            context_ids=["D1:1"],
        )


class RefactorTests(unittest.TestCase):
    def test_vendored_official_sources_are_byte_identical(self):
        for relative, expected in EXPECTED_VENDOR_HASHES.items():
            digest = hashlib.sha256(
                (VENDOR_ROOT / relative).read_bytes()
            ).hexdigest()
            self.assertEqual(digest, expected, relative)

    def test_em_graph_recall_preserves_signed_topk_and_reader_format(self):
        graph = EMGraph(sample_id="sample")
        graph.add_memory(
            MemoryNode(
                id="memory:D1:1",
                dia_id="D1:1",
                session_num=1,
                date_time="date one",
                speaker="Alice",
                text="raw wording",
                text_normalized="normalized wording",
                blip_caption="a blue boat",
            )
        )
        graph.add_memory(
            MemoryNode(
                id="memory:D1:2",
                dia_id="D1:2",
                session_num=1,
                date_time="date one",
                speaker="Bob",
                text="other text",
                text_normalized="other text",
            )
        )
        recall = EMGraphRecall(
            graph,
            _EmbeddingIndex(),
            entity_weight=0.0,
            semantic_weight=1.0,
            expand_sequence=False,
            force_full_pool=True,
        )
        result = recall.recall(
            {"sample_id": "sample"},
            0,
            "question",
            2,
        )
        self.assertEqual(result.context_ids, ["D1:1", "D1:2"])
        self.assertEqual(
            result.context.splitlines()[0],
            'date one: Alice said, "raw wording" and shared a blue boat',
        )
        self.assertNotIn("normalized wording", result.context)

    def test_question_cache_key_uses_full_question_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = QuestionEntityCache(
                str(Path(directory) / "questions.json"),
                namespace="v4::model-a",
                flush_every=1,
            )
            first = "x" * 120 + "A"
            second = "x" * 120 + "B"
            cache.set("sample", 0, first, {"first"})
            self.assertEqual(cache.get("sample", 0, first), {"first"})
            self.assertIsNone(cache.get("sample", 0, second))
            self.assertIn(
                hashlib.sha256(first.encode("utf-8")).hexdigest(),
                cache.cache_key("sample", 0, first, "v4::model-a"),
            )

    def test_duplicate_questions_are_isolated_by_qa_index(self):
        first = QuestionEntityCache.cache_key("sample", 0, "Same?")
        second = QuestionEntityCache.cache_key("sample", 1, "Same?")
        self.assertNotEqual(first, second)

    def test_question_cache_namespace_isolates_model_and_protocol(self):
        first = QuestionEntityCache.cache_key(
            "sample",
            0,
            "Same?",
            "v4::model-a",
        )
        second = QuestionEntityCache.cache_key(
            "sample",
            0,
            "Same?",
            "v5::model-a",
        )
        third = QuestionEntityCache.cache_key(
            "sample",
            0,
            "Same?",
            "v4::model-b",
        )
        self.assertEqual(len({first, second, third}), 3)

    def test_embedding_identity_checks_model_ids_and_full_text_digests(self):
        index = MemoryEmbeddingIndex(
            memory_ids=["memory:D1:1"],
            vectors=np.ones((1, 2), dtype=np.float32),
            model_name="embedding-model",
            text_digests=["full-digest"],
        )
        self.assertTrue(
            index.matches(
                model_name="embedding-model",
                memory_ids=["memory:D1:1"],
                text_digests=["full-digest"],
            )
        )
        self.assertFalse(
            index.matches(
                model_name="other-model",
                memory_ids=["memory:D1:1"],
                text_digests=["full-digest"],
            )
        )
        self.assertFalse(
            index.matches(
                model_name="embedding-model",
                memory_ids=["memory:D1:1"],
                text_digests=["other-digest"],
            )
        )

    def test_artifact_paths_change_with_complete_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EMGraphArtifactStore.from_env(directory)
            first = store.graph_path(
                "sample",
                identity={"model": "one", "conversation_sha256": "a"},
            )
            second = store.graph_path(
                "sample",
                identity={"model": "two", "conversation_sha256": "a"},
            )
            changed_data = store.graph_path(
                "sample",
                identity={"model": "one", "conversation_sha256": "b"},
            )
            self.assertNotEqual(first, second)
            self.assertNotEqual(first, changed_data)

    def test_a_memory_graph_and_b_em_graph_share_embedding_identity(self):
        sample = {
            "sample_id": "sample",
            "conversation": {
                "session_1_date_time": "1:00 PM on 1 January, 2020",
                "session_1": [
                    {
                        "dia_id": "D1:1",
                        "speaker": "A",
                        "text": "I went yesterday.",
                        "query": "private image search text",
                        "blip_caption": "a bridge",
                    }
                ],
            },
        }
        memory_graph = build_memory_graph(sample)
        self.assertEqual(len(memory_graph.memories), 1)
        self.assertEqual(len(memory_graph.entities), 0)
        self.assertTrue(memory_graph.stats["memory_only"])
        self.assertNotIn(
            "query",
            memory_graph.memories["memory:D1:1"].to_dict(),
        )
        a_identity = _graph_identity(
            sample,
            "extract-model",
            memory_only=True,
        )
        b_identity = _graph_identity(
            sample,
            "extract-model",
            memory_only=False,
        )
        self.assertNotEqual(a_identity, b_identity)
        em_graph = build_em_graph(
            sample,
            extractor=SimpleNamespace(extract=lambda _text: []),
            max_workers=1,
        )
        self.assertEqual(
            [
                memory_search_text(memory)
                for memory in memory_graph.memories.values()
            ],
            [
                memory_search_text(memory)
                for memory in em_graph.memories.values()
            ],
        )
        embedding_identity = _embedding_identity(sample, "embedding-model")
        self.assertNotIn("graph_kind", embedding_identity)
        self.assertNotIn("extract_model", embedding_identity)

    def test_shared_client_preserves_explicit_official_message_role(self):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Paris"))]
        )
        with patch("common.llm._get_openai_client", return_value=client):
            answer = run_chatgpt(
                "prompt",
                model="gpt-3.5-turbo",
                temperature=0,
                num_tokens_request=32,
                message_role="system",
            )
        self.assertEqual(answer, "Paris")
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(
            kwargs["messages"],
            [{"role": "system", "content": "prompt"}],
        )
        self.assertEqual(kwargs["max_tokens"], 32)
        self.assertEqual(kwargs["temperature"], 0)

    def test_official_answer_prompt_and_metrics_use_injected_recall(self):
        recall = _Recall()
        sample = {
            "sample_id": "sample",
            "conversation": {
                "session_1_date_time": "1:00 PM on 1 January, 2020",
                "session_1": [
                    {"dia_id": "D1:1", "speaker": "A", "text": "Paris"},
                    {"dia_id": "D1:2", "speaker": "B", "text": "Okay"},
                ],
            },
            "qa": [
                {
                    "question": "Where?",
                    "answer": "Paris",
                    "category": 4,
                    "evidence": ["D1:1"],
                }
            ],
        }
        with patch(
            "locomo_eval.vendor_runtime.run_chatgpt",
            return_value="Paris",
        ) as model_call:
            output = OfficialLoCoMoEvaluator(
                recall,
                LoCoMoEvaluationConfig(top_k=1),
            ).evaluate_sample(sample)
        row = output["qa"][0]
        key = "gpt-3.5-turbo_dialog_top_1"
        self.assertEqual(row[f"{key}_prediction"], "Paris")
        self.assertEqual(row[f"{key}_f1"], 1.0)
        self.assertEqual(row[f"{key}_recall"], 1.0)
        self.assertEqual(recall.calls, [("sample", 0, "Where?", 1)])
        kwargs = model_call.call_args.kwargs
        self.assertEqual(kwargs["num_tokens_request"], 32)
        self.assertEqual(kwargs["temperature"], 0)
        self.assertEqual(kwargs["message_role"], "system")

    def test_official_category_scoring_is_loaded_from_vendor(self):
        evaluation, _stats, _gpt = load_official_modules()
        qas = [
            {
                "answer": "Paris",
                "prediction": "Paris",
                "category": 4,
                "evidence": [],
            },
            {
                "answer": "unused",
                "prediction": "No information available",
                "category": 5,
                "evidence": [],
            },
        ]
        f1_values, _lengths, recalls = evaluation.eval_question_answering(qas)
        self.assertEqual(f1_values, [1.0, 1])
        self.assertEqual(recalls, [1, 1])

    def test_official_output_resume_and_overwrite_semantics(self):
        sample = {
            "sample_id": "sample",
            "conversation": {
                "session_1_date_time": "date",
                "session_1": [
                    {"dia_id": "D1:1", "speaker": "A", "text": "Paris"},
                    {"dia_id": "D1:2", "speaker": "B", "text": "Okay"},
                ],
            },
            "qa": [
                {
                    "question": "Where?",
                    "answer": "Paris",
                    "category": 4,
                    "evidence": ["D1:1"],
                }
            ],
        }
        key = "gpt-3.5-turbo_dialog_top_1"
        previous = {
            "sample_id": "sample",
            "qa": [
                {
                    **sample["qa"][0],
                    f"{key}_prediction": "Paris",
                    f"{key}_prediction_context": ["D1:1"],
                    f"{key}_f1": 1.0,
                    f"{key}_recall": 1.0,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "output.json"
            output_path.write_text(
                json.dumps([previous]),
                encoding="utf-8",
            )
            recall = _Recall()
            with patch(
                "locomo_eval.vendor_runtime.run_chatgpt",
                side_effect=AssertionError("resume should not call model"),
            ):
                outputs = OfficialLoCoMoEvaluator(
                    recall,
                    LoCoMoEvaluationConfig(top_k=1, overwrite=False),
                ).evaluate_dataset([sample], output_file=output_path)
            self.assertEqual(
                outputs[0]["qa"][0][f"{key}_prediction"],
                "Paris",
            )
            self.assertEqual(recall.calls, [])

            overwrite_recall = _Recall()
            with patch(
                "locomo_eval.vendor_runtime.run_chatgpt",
                return_value="Paris",
            ):
                OfficialLoCoMoEvaluator(
                    overwrite_recall,
                    LoCoMoEvaluationConfig(top_k=1, overwrite=True),
                ).evaluate_dataset([sample], output_file=output_path)
            self.assertEqual(
                overwrite_recall.calls,
                [("sample", 0, "Where?", 1)],
            )

    def test_all_official_qa_categories_run_through_vendor(self):
        evaluation, _stats, _gpt = load_official_modules()
        rows = [
            {
                "answer": "Paris, Rome",
                "prediction": "Paris, Rome",
                "category": 1,
                "evidence": [],
            },
            {
                "answer": "May 2023",
                "prediction": "May 2023",
                "category": 2,
                "evidence": [],
            },
            {
                "answer": "blue; azure",
                "prediction": "blue",
                "category": 3,
                "evidence": [],
            },
            {
                "answer": "Paris",
                "prediction": "Paris",
                "category": 4,
                "evidence": [],
            },
            {
                "answer": "secret",
                "prediction": "not mentioned",
                "category": 5,
                "evidence": [],
            },
        ]
        values, _lengths, recalls = evaluation.eval_question_answering(rows)
        self.assertEqual(values, [1.0, 1.0, 1.0, 1.0, 1])
        self.assertEqual(recalls, [1, 1, 1, 1, 1])

    def test_package_dependency_boundary(self):
        root = Path(__file__).resolve().parents[2]
        em_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (root / "code" / "em_graph").rglob("*.py")
        )
        eval_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (root / "code" / "locomo_eval").glob("*.py")
        )
        self.assertNotIn("locomo_eval", em_source)
        self.assertNotIn("em_graph", eval_source)


if __name__ == "__main__":
    unittest.main()
