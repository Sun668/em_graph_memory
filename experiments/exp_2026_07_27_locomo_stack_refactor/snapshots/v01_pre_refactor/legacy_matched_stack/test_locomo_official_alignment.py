"""Parity tests for the extracted LoCoMo QA and metric modules."""

from __future__ import annotations

import random
import string
import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import regex
from nltk.stem import PorterStemmer
from experiments.shared.llm_client import run_chatgpt as run_shared_chatgpt

from experiments.exp_2026_07_26_locomo_official_compare.locomo_official_metrics import (
    official_qa_f1,
    summarize_f1,
)
from experiments.exp_2026_07_26_locomo_official_compare.locomo_official_qa import (
    QA_MAX_TOKENS,
    QA_PROMPT,
    QA_PROMPT_CAT_5,
    QA_TEMPERATURE,
    build_prompt,
    generate_answer,
    get_category_5_answer,
    prepare_question,
    qa_message_role,
)

_PS = PorterStemmer()


def _official_normalize_answer(text: str) -> str:
    text = text.replace(",", "")
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = regex.sub(r"\b(a|an|the|and)\b", " ", text.lower())
    return " ".join(text.lower().split())


def _official_f1_score(prediction: str, ground_truth: str) -> float:
    prediction_tokens = [
        _PS.stem(word) for word in _official_normalize_answer(prediction).split()
    ]
    ground_truth_tokens = [
        _PS.stem(word) for word in _official_normalize_answer(ground_truth).split()
    ]
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = float(num_same) / len(prediction_tokens)
    recall = float(num_same) / len(ground_truth_tokens)
    return (2 * precision * recall) / (precision + recall)


def _official_row_score(prediction: str, answer: str, category: int) -> float:
    if category == 3:
        answer = answer.split(";")[0].strip()
    if category in (2, 3, 4):
        return _official_f1_score(prediction, answer)
    if category == 1:
        predictions = [part.strip() for part in prediction.split(",")]
        answers = [part.strip() for part in answer.split(",")]
        return float(
            np.mean(
                [
                    max(_official_f1_score(pred, gold) for pred in predictions)
                    for gold in answers
                ]
            )
        )
    if category == 5:
        lowered = prediction.lower()
        return float(
            "no information available" in lowered or "not mentioned" in lowered
        )
    raise ValueError(category)


class OfficialMetricParityTest(unittest.TestCase):
    def test_all_categories_match_reference(self) -> None:
        cases = [
            ("Paris, running", "the Paris and runs", 4),
            ("May 2023", "in May, 2023", 2),
            ("blue", "blue; azure; navy", 3),
            ("Paris, Rome", "Paris, Rome", 1),
            ("Not mentioned in the conversation", "secret answer", 5),
            ("secret answer", "secret answer", 5),
        ]
        for prediction, answer, category in cases:
            with self.subTest(category=category, prediction=prediction):
                self.assertEqual(
                    official_qa_f1(prediction, answer, category),
                    _official_row_score(prediction, answer, category),
                )

    def test_category_5_prompt_and_decode_match_protocol(self) -> None:
        prepared_a = prepare_question(
            "Who won?", "Alice", 5, rng=random.Random(1)
        )
        self.assertEqual(
            prepared_a.text,
            "Who won? Select the correct answer: "
            "(a) Not mentioned in the conversation (b) Alice. ",
        )
        self.assertEqual(
            get_category_5_answer("(a)", prepared_a.category_5_answer_key or {}),
            "Not mentioned in the conversation",
        )
        prepared_b = prepare_question(
            "Who won?", "Alice", 5, rng=random.Random(2)
        )
        self.assertEqual(
            prepared_b.text,
            "Who won? Select the correct answer: "
            "(a) Alice (b) Not mentioned in the conversation. ",
        )
        self.assertEqual(
            get_category_5_answer("b", prepared_b.category_5_answer_key or {}),
            "Not mentioned in the conversation",
        )
        self.assertEqual(
            build_prompt("context", prepared_a),
            "context\n\n" + QA_PROMPT_CAT_5.format(prepared_a.text),
        )

    def test_regular_and_temporal_prompts_match_protocol(self) -> None:
        regular = prepare_question("Where?", "Paris", 4)
        temporal = prepare_question("When?", "May 2023", 2)
        self.assertEqual(build_prompt("ctx", regular), "ctx\n\n" + QA_PROMPT.format("Where?"))
        self.assertEqual(
            temporal.text,
            "When? Use DATE of CONVERSATION to answer with an approximate date.",
        )

    def test_gpt35_generation_uses_official_system_role_and_limits(self) -> None:
        with patch(
            "experiments.exp_2026_07_26_locomo_official_compare."
            "locomo_official_qa.run_chatgpt",
            return_value="Paris",
        ) as mocked:
            answer = generate_answer(
                context='1 May 2023: Alice said, "I visited Paris."',
                question="Where did Alice visit?",
                ground_truth="Paris",
                category=4,
                model="gpt-3.5-turbo",
            )

        self.assertEqual(answer, "Paris")
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["message_role"], "system")
        self.assertEqual(kwargs["num_tokens_request"], QA_MAX_TOKENS)
        self.assertEqual(kwargs["temperature"], QA_TEMPERATURE)
        self.assertEqual(qa_message_role("gpt-4"), "user")

    def test_shared_client_forwards_explicit_message_role(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Paris")
                )
            ]
        )
        with patch(
            "common.llm._get_openai_client",
            return_value=client,
        ):
            answer = run_shared_chatgpt(
                "prompt",
                model="gpt-3.5-turbo",
                temperature=0,
                num_tokens_request=32,
                message_role="system",
            )

        self.assertEqual(answer, "Paris")
        messages = client.chat.completions.create.call_args.kwargs["messages"]
        self.assertEqual(messages, [{"role": "system", "content": "prompt"}])

    def test_summary_names_separate_overall_and_compliant_ex_cat5(self) -> None:
        summary = summarize_f1(
            [
                {"category": 4, "token_f1": 0.5},
                {"category": 5, "token_f1": 1.0},
            ],
            {4: "Single-hop", 5: "Adversarial"},
        )
        self.assertEqual(summary["official_token_f1_25_overall_pct"], 75.0)
        self.assertEqual(summary["official_token_f1_25_ex_cat5_pct"], 50.0)
        self.assertNotIn("f1_25_overall_pct", summary)


if __name__ == "__main__":
    unittest.main()
