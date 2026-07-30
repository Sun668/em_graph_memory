from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from common import llm


class _EmbeddingResource:
    def create(self, **_kwargs):
        return SimpleNamespace(
            model="actual-embed",
            data=[SimpleNamespace(embedding=[1.0, 2.0])],
            usage=SimpleNamespace(prompt_tokens=7, total_tokens=7),
        )


class _ChatResource:
    def create(self, **_kwargs):
        return SimpleNamespace(
            model="actual-chat",
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(
                prompt_tokens=11,
                completion_tokens=3,
                total_tokens=14,
            ),
        )


class UsageTelemetryTests(unittest.TestCase):
    def test_embedding_provider_usage_is_observed_without_vector_change(self):
        events = []
        client = SimpleNamespace(embeddings=_EmbeddingResource())
        with patch.object(llm, "_get_openai_client", return_value=client):
            with llm.observe_model_usage(events.append, stage="embedding"):
                vector = llm.get_openai_embedding(["hello"], model="requested")
        self.assertEqual(vector.tolist(), [[1.0, 2.0]])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage"], "embedding")
        self.assertEqual(events[0]["operation"], "embedding")
        self.assertEqual(events[0]["requested_model"], "requested")
        self.assertEqual(events[0]["actual_model"], "actual-embed")
        self.assertEqual(events[0]["input_tokens"], 7)
        self.assertIsNone(events[0]["output_tokens"])

    def test_chat_provider_usage_is_observed_without_text_change(self):
        events = []
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=_ChatResource())
        )
        with patch.object(llm, "_get_openai_client", return_value=client):
            with llm.observe_model_usage(
                events.append, stage="answer_generation"
            ):
                answer = llm.run_chatgpt(
                    "question",
                    model="requested-chat",
                    max_retries=1,
                    wait_time=0,
                )
        self.assertEqual(answer, "ok")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage"], "answer_generation")
        self.assertEqual(events[0]["actual_model"], "actual-chat")
        self.assertEqual(events[0]["input_tokens"], 11)
        self.assertEqual(events[0]["output_tokens"], 3)
        self.assertEqual(events[0]["total_tokens"], 14)

    def test_observer_restores_after_context(self):
        events = []
        with llm.observe_model_usage(events.append, stage="outer"):
            self.assertEqual(llm._usage_stage, "outer")
            with llm.observe_model_usage(events.append, stage="inner"):
                self.assertEqual(llm._usage_stage, "inner")
            self.assertEqual(llm._usage_stage, "outer")
        self.assertEqual(llm._usage_stage, "unspecified")
        self.assertIsNone(llm._usage_observer)


if __name__ == "__main__":
    unittest.main()
