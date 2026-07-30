from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR))
sys.path.insert(0, str(ROOT / "code"))

import official_dragon
from locomo_eval.vendor_runtime import load_official_modules
from validate_formal_result import condition_fingerprint


def _sample():
    return {
        "sample_id": "conv-test",
        "conversation": {
            "session_1_date_time": "1 January 2024",
            "session_1": [
                {
                    "dia_id": "D1",
                    "speaker": "Alice",
                    "text": "Hello",
                },
                {
                    "dia_id": "D2,D3",
                    "speaker": "Bob",
                    "text": "Look",
                    "blip_caption": "a blue bird",
                },
            ],
        },
        "qa": [
            {
                "question": "Who said hello?",
                "answer": "Alice",
                "category": 1,
                "evidence": ["D1"],
            }
        ],
    }


class _FakeBatch(dict):
    def to(self, _device):
        return self


class _FakeTokenizer:
    def __init__(self):
        self.calls = []

    def __call__(self, texts, **kwargs):
        self.calls.append((list(texts), kwargs))
        return _FakeBatch(input_ids=np.asarray([[1], [2]]))


class _FakeEncoder:
    def __init__(self):
        self.eval_called = False

    def eval(self):
        self.eval_called = True

    def __call__(self, **_kwargs):
        import torch

        return SimpleNamespace(
            last_hidden_state=torch.tensor(
                [
                    [[3.0, 4.0], [99.0, 99.0]],
                    [[5.0, 12.0], [88.0, 88.0]],
                ]
            )
        )


class OfficialDragonTests(unittest.TestCase):
    def test_dialog_and_query_inputs_match_upstream_prepare_for_rag(self):
        sample = _sample()
        captured = []

        def fake_embeddings(_retriever, texts, mode):
            captured.append((mode, list(texts)))
            return np.arange(len(texts) * 3, dtype=np.float32).reshape(
                len(texts), 3
            )

        _evaluation, _stats, gpt_utils = load_official_modules()
        with tempfile.TemporaryDirectory() as temp_dir:
            args = SimpleNamespace(
                data_file="locomo10.json",
                rag_mode="dialog",
                emb_dir=temp_dir,
                retriever="dragon",
            )
            with patch.object(gpt_utils, "get_embeddings", fake_embeddings):
                official_db, official_questions = gpt_utils.prepare_for_rag(
                    args, sample
                )
        contexts, dates, ids = official_dragon.official_dialog_rows(sample)
        self.assertEqual(contexts, official_db["context"])
        self.assertEqual(dates, official_db["date_time"])
        self.assertEqual(ids, official_db["dia_id"])
        self.assertEqual(captured[0], ("context", contexts))
        self.assertEqual(captured[1], ("query", ["Who said hello?"]))
        np.testing.assert_array_equal(official_questions, [[0.0, 1.0, 2.0]])

    def test_embedding_uses_cls_without_l2_normalization(self):
        tokenizer = _FakeTokenizer()
        encoder = _FakeEncoder()
        vectors = official_dragon.embed_texts(
            ["one", "two"],
            tokenizer=tokenizer,
            encoder=encoder,
            device="cpu",
        )
        np.testing.assert_array_equal(vectors, [[3.0, 4.0], [5.0, 12.0]])
        np.testing.assert_array_equal(
            np.linalg.norm(vectors, axis=1),
            [5.0, 13.0],
        )
        self.assertTrue(encoder.eval_called)
        self.assertEqual(
            tokenizer.calls[0][1],
            {
                "padding": True,
                "truncation": True,
                "return_tensors": "pt",
            },
        )

    def test_raw_dot_ranking_and_reader_context_match_upstream(self):
        sample = _sample()
        contexts, dates, ids = official_dragon.official_dialog_rows(sample)
        context_vectors = np.asarray(
            [[2.0, 0.0], [0.0, 3.0]], dtype=np.float32
        )
        query_vectors = np.asarray([[0.25, 1.0]], dtype=np.float32)
        recall = official_dragon.OfficialDialogDragonRecall(
            sample_id="conv-test",
            contexts=np.asarray(contexts),
            date_times=np.asarray(dates),
            context_ids=np.asarray(ids),
            questions=np.asarray(["Who said hello?"]),
            context_vectors=context_vectors,
            query_vectors=query_vectors,
            metadata={},
            cache_file=Path("unused"),
        )
        actual = recall.recall(sample, 0, "Who said hello?", 2)

        _evaluation, _stats, gpt_utils = load_official_modules()
        expected_context, expected_ids = gpt_utils.get_rag_context(
            {
                "context": contexts,
                "date_time": dates,
                "dia_id": ids,
                "embeddings": context_vectors,
            },
            query_vectors[0],
            SimpleNamespace(top_k=2, rag_mode="dialog"),
        )
        self.assertEqual(actual.context, expected_context)
        self.assertEqual(actual.context_ids, expected_ids)
        self.assertEqual(actual.context_ids, ["D2", "D3", "D1"])

    def test_model_ids_match_pinned_upstream_dragon_source(self):
        source = (
            ROOT
            / "code"
            / "locomo_eval"
            / "vendor"
            / "locomo"
            / "task_eval"
            / "rag_utils.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "'facebook/dragon-plus-query-encoder'",
            source,
        )
        self.assertIn(
            "'facebook/dragon-plus-context-encoder'",
            source,
        )
        self.assertEqual(
            official_dragon.QUERY_MODEL,
            "facebook/dragon-plus-query-encoder",
        )
        self.assertEqual(
            official_dragon.CONTEXT_MODEL,
            "facebook/dragon-plus-context-encoder",
        )
        self.assertEqual(official_dragon.EMBED_BATCH_SIZE, 24)

    def test_o1_requirements_match_upstream_runtime_versions(self):
        requirements = (
            EXP_DIR / "requirements_o1_official.txt"
        ).read_text(encoding="utf-8").splitlines()
        self.assertIn("numpy==1.26.0", requirements)
        self.assertIn("torch==2.0.1", requirements)
        self.assertIn("transformers==4.35.0", requirements)
        self.assertIn("tokenizers==0.14.1", requirements)
        self.assertIn("nltk==3.8.1", requirements)
        self.assertIn("regex==2022.10.31", requirements)
        self.assertIn("tqdm==4.64.1", requirements)

    def test_formal_config_is_official_reference_and_cache_bound(self):
        args = SimpleNamespace(
            answer_model="gpt-3.5-turbo",
            top_k=25,
            run_id="o1_dragon_top25_run01",
            scope="all10",
        )
        with tempfile.TemporaryDirectory() as directory:
            condition_dir = Path(directory) / args.run_id
            config = official_dragon._formal_run_config(
                args=args,
                samples=[_sample()],
                condition_dir=condition_dir,
                source_audit={
                    "source_commit": "a" * 40,
                    "source_tree": "b" * 40,
                    "vendor": {"checked_files": 16},
                },
                cache_records=[
                    {
                        "sample_id": "conv-test",
                        "sha256": "c" * 64,
                    }
                ],
                runtime={
                    **official_dragon.OFFICIAL_DEPENDENCY_VERSIONS,
                    "platform": "test",
                    "device": "cpu",
                },
                command=".venv/bin/python official_dragon.py evaluate",
            )
        self.assertEqual(
            config["condition_kind"],
            "official_dialog_reference",
        )
        self.assertEqual(config["retrieval"]["normalization"], "none")
        self.assertEqual(
            config["retrieval"]["similarity"],
            "raw_dot_product",
        )
        self.assertIsNone(config["models"]["extraction"])
        self.assertIsNone(config["models"]["answer_actual"])
        self.assertEqual(
            config["models"]["query_revision"],
            official_dragon.QUERY_REVISION,
        )
        self.assertEqual(
            config["artifacts"]["provider_usage"],
            "provider_usage.json",
        )
        self.assertEqual(
            config["condition_fingerprint"],
            condition_fingerprint(config),
        )

    def _write_cache(
        self,
        cache_dir,
        *,
        runtime,
        metadata_override=None,
    ):
        sample = _sample()
        contexts, date_times, context_ids = (
            official_dragon.official_dialog_rows(sample)
        )
        questions = [sample["qa"][0]["question"]]
        metadata = official_dragon._stable_cache_metadata(
            sample,
            contexts=contexts,
            questions=questions,
            runtime=runtime,
        )
        metadata.update(metadata_override or {})
        np.savez_compressed(
            official_dragon.cache_path(Path(cache_dir), "conv-test"),
            metadata=np.asarray(json.dumps(metadata, sort_keys=True)),
            contexts=np.asarray(contexts),
            date_times=np.asarray(date_times),
            context_ids=np.asarray(context_ids),
            questions=np.asarray(questions),
            context_vectors=np.asarray(
                [[1.0, 0.0], [0.0, 1.0]], dtype=np.float32
            ),
            query_vectors=np.asarray([[1.0, 0.0]], dtype=np.float32),
        )

    def test_cache_rejects_dependency_version_mismatch(self):
        runtime = {
            **official_dragon.OFFICIAL_DEPENDENCY_VERSIONS,
            "platform": "test",
            "device": "cpu",
            "torch_build": "2.0.1",
            "torch_cuda": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            self._write_cache(directory, runtime=runtime)
            different = {**runtime, "numpy": "2.2.6"}
            with patch.object(
                official_dragon,
                "retrieval_runtime_identity",
                return_value=different,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "official DRAGON dependency mismatch"
                ):
                    official_dragon.OfficialDialogDragonRecall.load(
                        _sample(),
                        cache_dir=Path(directory),
                    )

    def test_cache_rejects_revision_and_device_mismatch(self):
        runtime = {
            **official_dragon.OFFICIAL_DEPENDENCY_VERSIONS,
            "platform": "test",
            "device": "cpu",
            "torch_build": "2.0.1",
            "torch_cuda": None,
        }
        cases = (
            ({"query_revision": "f" * 40}, runtime),
            ({}, {**runtime, "device": "cuda:0"}),
        )
        for metadata_override, current_runtime in cases:
            with self.subTest(
                metadata_override=metadata_override,
                device=current_runtime["device"],
            ):
                with tempfile.TemporaryDirectory() as directory:
                    self._write_cache(
                        directory,
                        runtime=runtime,
                        metadata_override=metadata_override,
                    )
                    with patch.object(
                        official_dragon,
                        "retrieval_runtime_identity",
                        return_value=current_runtime,
                    ):
                        with self.assertRaisesRegex(
                            RuntimeError, "cache identity mismatch"
                        ):
                            official_dragon.OfficialDialogDragonRecall.load(
                                _sample(),
                                cache_dir=Path(directory),
                            )

    def test_reader_usage_requires_complete_single_actual_model(self):
        event = {
            "stage": "official_reader",
            "operation": "chat",
            "requested_model": "gpt-3.5-turbo",
            "actual_model": "gpt-3.5-turbo-0125",
            "request_count": 1,
            "input_tokens": 10,
            "output_tokens": 2,
            "total_tokens": 12,
            "wall_seconds": 0.1,
        }
        summary = official_dragon._reader_usage_summary(
            [event, event],
            requested_model="gpt-3.5-turbo",
            expected_requests=2,
            status="complete",
        )
        self.assertEqual(summary["actual_model"], "gpt-3.5-turbo-0125")
        self.assertEqual(summary["request_count"], 2)
        with self.assertRaisesRegex(RuntimeError, "request count mismatch"):
            official_dragon._reader_usage_summary(
                [event],
                requested_model="gpt-3.5-turbo",
                expected_requests=2,
                status="complete",
            )
        with self.assertRaisesRegex(RuntimeError, "multiple model identities"):
            official_dragon._reader_usage_summary(
                [event, {**event, "actual_model": "other"}],
                requested_model="gpt-3.5-turbo",
                expected_requests=2,
                status="complete",
            )
        with self.assertRaisesRegex(
            RuntimeError, "not the requested official model family"
        ):
            official_dragon._reader_usage_summary(
                [{**event, "actual_model": "different-model"}],
                requested_model="gpt-3.5-turbo",
                expected_requests=1,
                status="complete",
            )

    def test_vendor_manifest_and_dependency_boundary(self):
        result = official_dragon.verify_vendor_manifest()
        self.assertEqual(result["checked_files"], 16)
        self.assertEqual(result["failures"], [])
        source = Path(official_dragon.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from em_graph", source)
        self.assertNotIn("import em_graph", source)


if __name__ == "__main__":
    unittest.main()
