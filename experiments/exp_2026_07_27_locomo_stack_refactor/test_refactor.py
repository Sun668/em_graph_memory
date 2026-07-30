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
    QueryEmbeddingArtifact,
    TextEmbeddingCache,
    build_em_graph,
    build_memory_graph,
    retrieve_dialog_ids,
)
from em_graph.recall.tokenize import memory_search_text
from em_graph.recall.embedding_index import (
    L2_NORMALIZATION,
    NO_NORMALIZATION,
    dragon_encoder_revisions,
    embedding_protocol_identity,
)
from em_graph.recall.retrieval import normalize_semantic_scores
from em_graph.cache import (
    QuestionEntityCache,
    ordered_question_records,
)
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
from experiments.exp_2026_07_27_locomo_stack_refactor.prepare_query_embeddings import (
    _requires_api_key,
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
    def test_local_dragon_query_build_skips_remote_api_guard(self):
        self.assertFalse(_requires_api_key("dragon"))
        self.assertFalse(
            _requires_api_key("facebook/dragon-plus-query-encoder")
        )
        self.assertTrue(_requires_api_key("text-embedding-3-small"))

    def test_em_graph_has_no_legacy_root_modules(self):
        package_root = ROOT / "code" / "em_graph"
        legacy_modules = {
            "builder",
            "config",
            "embedding_index",
            "entity_bm25_index",
            "entity_extractor",
            "models",
            "replace_pronouns",
            "retrieval",
            "retrieval_audit",
            "tokenize",
        }
        found = {
            path.stem
            for path in package_root.glob("*.py")
            if path.name != "__init__.py"
        }
        self.assertTrue(legacy_modules.isdisjoint(found), found)

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

    def test_text_embedding_cache_merges_interleaved_stale_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "text.npz"
            first = TextEmbeddingCache(str(path), flush_every=100)
            second = TextEmbeddingCache(str(path), flush_every=100)
            first.set("first", "model", "context", np.asarray([1.0, 0.0]))
            first.flush()
            second.set(
                "second", "model", "context", np.asarray([0.0, 1.0])
            )
            second.flush()
            merged = TextEmbeddingCache(str(path))
            np.testing.assert_array_equal(
                merged.get("first", "model", "context"),
                np.asarray([1.0, 0.0], dtype=np.float32),
            )
            np.testing.assert_array_equal(
                merged.get("second", "model", "context"),
                np.asarray([0.0, 1.0], dtype=np.float32),
            )

    def test_text_embedding_cache_rejects_conflicting_existing_vector(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "text.npz"
            first = TextEmbeddingCache(str(path), flush_every=100)
            second = TextEmbeddingCache(str(path), flush_every=100)
            first.set("same", "model", "context", np.asarray([1.0, 0.0]))
            first.flush()
            second.set("same", "model", "context", np.asarray([0.0, 1.0]))
            with self.assertRaisesRegex(ValueError, "conflicting vectors"):
                second.flush()

    def test_query_embedding_artifact_is_exact_and_strict(self):
        samples = [
            {
                "sample_id": "sample",
                "qa": [
                    {"question": "First?"},
                    {"question": "Second?"},
                ],
            }
        ]
        records = ordered_question_records(samples)
        digests = [record["question_sha256"] for record in records]
        vectors = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queries.npz"
            artifact = QueryEmbeddingArtifact(
                dataset_sha256="a" * 64,
                model_name="model",
                role="context",
                qa_records=records,
                question_digests=digests,
                vectors=vectors,
            )
            artifact.save(path)
            loaded = QueryEmbeddingArtifact.load(path)
            loaded.validate_exact_dataset(
                samples,
                dataset_sha256="a" * 64,
                model_name="model",
                role="context",
            )
            np.testing.assert_array_equal(
                loaded.get("First?", "model", "context"),
                vectors[0],
            )
            with self.assertRaisesRegex(RuntimeError, "artifact miss"):
                loaded.get("Missing?", "model", "context")
            usage = loaded.usage(qa_count=2, required_lookup_count=1)
            self.assertEqual(usage["cache_hits"], 1)
            self.assertEqual(usage["cache_misses"], 1)
            self.assertEqual(usage["status"], "fail")

    def test_raw_query_artifact_round_trip_binds_v2_protocol(self):
        samples = [{"sample_id": "sample", "qa": [{"question": "Raw?"}]}]
        records = ordered_question_records(samples)
        vectors = np.asarray([[3.0, 4.0]], dtype=np.float32)
        protocol = embedding_protocol_identity(
            "dragon", NO_NORMALIZATION
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw_queries.npz"
            artifact = QueryEmbeddingArtifact(
                dataset_sha256="b" * 64,
                model_name="dragon",
                role="query",
                qa_records=records,
                question_digests=[records[0]["question_sha256"]],
                vectors=vectors,
                normalization=NO_NORMALIZATION,
                protocol_identity=protocol,
            )
            artifact.save(path)
            loaded = QueryEmbeddingArtifact.load(path)
            loaded.validate_exact_dataset(
                samples,
                dataset_sha256="b" * 64,
                model_name="dragon",
                role="query",
                normalization=NO_NORMALIZATION,
                protocol_identity=protocol,
            )
            self.assertEqual(
                loaded.identity(path)["schema"],
                "query_embedding_artifact_v2",
            )
            np.testing.assert_array_equal(loaded.vectors, vectors)
            with self.assertRaisesRegex(ValueError, "normalization"):
                loaded.validate_exact_dataset(
                    samples,
                    dataset_sha256="b" * 64,
                    model_name="dragon",
                    role="query",
                    normalization=L2_NORMALIZATION,
                )

    def test_strict_query_artifact_prevents_live_embedding(self):
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
        index = MemoryEmbeddingIndex(
            memory_ids=["memory:D1:1"],
            vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
            model_name="model",
            text_digests=["digest"],
            _query_cache=artifact,
            strict_query_cache=True,
        )
        with patch.object(
            index,
            "_embed_batch_api",
            side_effect=AssertionError("must not call embedding API"),
        ):
            self.assertEqual(index.scores("Q?"), {"memory:D1:1": 1.0})

    def test_loaded_index_can_disable_context_cache_seeding(self):
        graph = EMGraph(sample_id="sample")
        graph.add_memory(
            MemoryNode(
                id="memory:D1:1",
                dia_id="D1:1",
                session_num=1,
                date_time="date",
                speaker="A",
                text="text",
                text_normalized="text",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.npz"
            built = MemoryEmbeddingIndex(
                memory_ids=["memory:D1:1"],
                vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
                model_name="model",
                text_digests=[
                    hashlib.sha256(
                        memory_search_text(
                            graph.memories["memory:D1:1"]
                        ).encode("utf-8")
                    ).hexdigest()
                ],
            )
            built.save(path)
            loaded = MemoryEmbeddingIndex.build(
                graph,
                model_name="model",
                cache_path=str(path),
                text_cache=None,
                use_text_cache=False,
            )
            self.assertFalse(loaded.use_text_cache)
            self.assertIsNone(loaded._text_cache)

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
                normalization=NO_NORMALIZATION,
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

    def test_legacy_v2_index_loads_as_l2_and_raw_cache_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.npz"
            np.savez_compressed(
                path,
                format_version=np.asarray("v2"),
                memory_ids=np.asarray(["memory:D1:1"], dtype=object),
                vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
                model_name=np.asarray("model"),
                text_digests=np.asarray(["digest"], dtype=object),
            )
            loaded = MemoryEmbeddingIndex.load(str(path))
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.normalization, L2_NORMALIZATION)
            graph = EMGraph(sample_id="sample")
            graph.add_memory(
                MemoryNode(
                    id="memory:D1:1",
                    dia_id="D1:1",
                    session_num=1,
                    date_time="date",
                    speaker="A",
                    text="text",
                    text_normalized="text",
                )
            )
            with self.assertRaisesRegex(
                ValueError, "refusing to overwrite"
            ):
                MemoryEmbeddingIndex.build(
                    graph,
                    model_name="model",
                    normalization=NO_NORMALIZATION,
                    cache_path=str(path),
                    text_cache=None,
                    use_text_cache=False,
                )

    def test_dragon_revisions_and_query_local_minmax_are_locked(self):
        self.assertEqual(
            dragon_encoder_revisions("dragon"),
            (
                "2d3808c087119b953f8494b7638c216c71712cee",
                "68074e7406bb0061b0d049b58592acafae00e9d4",
            ),
        )
        self.assertEqual(
            normalize_semantic_scores(
                {"a": -2.0, "b": 1.0, "c": 4.0},
                "query_local_minmax_v1",
            ),
            {"a": 0.0, "b": 0.5, "c": 1.0},
        )
        self.assertEqual(
            normalize_semantic_scores(
                {"a": 7.0, "b": 7.0},
                "query_local_minmax_v1",
            ),
            {"a": 0.0, "b": 0.0},
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

    def test_gated_retrieval_fills_the_official_exact_top_k_budget(self):
        graph = EMGraph(sample_id="sample")
        for index in range(1, 4):
            graph.add_memory(
                MemoryNode(
                    id=f"memory:D1:{index}",
                    dia_id=f"D1:{index}",
                    session_num=1,
                    date_time="date",
                    speaker="A",
                    text=f"text {index}",
                    text_normalized=f"text {index}",
                )
            )

        class _ThreeScores:
            def scores(self, _question, memory_ids=None):
                values = {
                    "memory:D1:1": 0.1,
                    "memory:D1:2": 0.5,
                    "memory:D1:3": 0.9,
                }
                if memory_ids is None:
                    return values
                return {key: values[key] for key in memory_ids}

        with patch(
            "em_graph.recall.retrieval._entity_memory_scores",
            return_value={"memory:D1:1": 1.0},
        ):
            ranked = retrieve_dialog_ids(
                graph,
                "question",
                top_k=3,
                embedding_index=_ThreeScores(),
                entity_bm25_index=MagicMock(),
                q_entity_keys={"entity"},
                entity_weight=0.3,
                semantic_weight=0.7,
                expand_sequence=False,
            )
        self.assertEqual(
            [dialog_id for dialog_id, _score in ranked],
            ["D1:1", "D1:3", "D1:2"],
        )
        self.assertEqual(len(ranked), 3)

    def test_retrieval_fuses_query_local_minmax_semantic_scores(self):
        graph = EMGraph(sample_id="sample")
        for index in range(1, 4):
            graph.add_memory(
                MemoryNode(
                    id=f"memory:D1:{index}",
                    dia_id=f"D1:{index}",
                    session_num=1,
                    date_time="date",
                    speaker="A",
                    text=f"text {index}",
                    text_normalized=f"text {index}",
                )
            )

        class _RawScores:
            def scores(self, _question, memory_ids=None):
                values = {
                    "memory:D1:1": -2.0,
                    "memory:D1:2": 1.0,
                    "memory:D1:3": 4.0,
                }
                if memory_ids is None:
                    return values
                return {key: values[key] for key in memory_ids}

        ranked = retrieve_dialog_ids(
            graph,
            "question",
            top_k=3,
            embedding_index=_RawScores(),
            q_entity_keys=set(),
            entity_weight=0.3,
            semantic_weight=0.7,
            semantic_score_normalization="query_local_minmax_v1",
            expand_sequence=False,
        )
        self.assertEqual(
            ranked,
            [("D1:3", 0.7), ("D1:2", 0.35), ("D1:1", 0.0)],
        )

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
