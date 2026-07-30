"""Exact LoCoMo RAG QA prompt and Category-5 generation protocol.

This mirrors ``snap-research/locomo/task_eval/gpt_utils.py`` for batch size 1.
Category 5 intentionally includes the gold answer as one randomized option,
because that is part of the official LoCoMo protocol.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Optional

from experiments.shared.llm_client import run_chatgpt

QA_PROMPT = """
Based on the above context, write an answer in the form of a short phrase for the following question. Answer with exact words from the context whenever possible.
Question: {} Short answer:
"""

QA_PROMPT_CAT_5 = """
Based on the above context, answer the following question.

Question: {} Short answer:
"""

TEMPORAL_SUFFIX = " Use DATE of CONVERSATION to answer with an approximate date."
QA_MAX_TOKENS = 32
QA_TEMPERATURE = 0
QA_PROTOCOL_VERSION = "locomo_official_v2_system_role"


@dataclass(frozen=True)
class PreparedQuestion:
    text: str
    category_5_answer_key: Optional[Dict[str, str]] = None


def qa_message_role(model: str) -> str:
    """Match the official client: GPT-3.5 prompt is one system message."""
    return "system" if "gpt-3.5" in str(model).lower() else "user"


def prepare_question(
    question: str,
    ground_truth: str,
    category: int,
    *,
    rng: Optional[random.Random] = None,
) -> PreparedQuestion:
    text = str(question or "")
    category = int(category)
    if category == 2:
        return PreparedQuestion(text + TEMPORAL_SUFFIX)
    if category != 5:
        return PreparedQuestion(text)

    chooser = rng.random if rng is not None else random.random
    template = text + " Select the correct answer: (a) {} (b) {}. "
    if chooser() < 0.5:
        answer_key = {
            "a": "Not mentioned in the conversation",
            "b": str(ground_truth),
        }
        text = template.format(answer_key["a"], answer_key["b"])
    else:
        answer_key = {
            "b": "Not mentioned in the conversation",
            "a": str(ground_truth),
        }
        text = template.format(answer_key["a"], answer_key["b"])
    return PreparedQuestion(text, answer_key)


def get_category_5_answer(
    model_prediction: str, answer_key: Dict[str, str]
) -> str:
    prediction = str(model_prediction or "").strip().lower()
    if len(prediction) == 1:
        return answer_key["a"] if "a" in prediction else answer_key["b"]
    if len(prediction) == 3:
        return answer_key["a"] if "(a)" in prediction else answer_key["b"]
    return prediction


def build_prompt(context: str, prepared: PreparedQuestion) -> str:
    tail = (
        QA_PROMPT_CAT_5.format(prepared.text)
        if prepared.category_5_answer_key is not None
        else QA_PROMPT.format(prepared.text)
    )
    return str(context or "") + "\n\n" + tail


def generate_answer(
    context: str,
    question: str,
    ground_truth: str,
    category: int,
    model: str,
    *,
    rng: Optional[random.Random] = None,
) -> str:
    prepared = prepare_question(question, ground_truth, category, rng=rng)
    raw = run_chatgpt(
        build_prompt(context, prepared),
        num_gen=1,
        num_tokens_request=QA_MAX_TOKENS,
        model="chatgpt" if "gpt-3.5" in str(model) else model,
        use_16k=False,
        temperature=QA_TEMPERATURE,
        wait_time=2,
        message_role=qa_message_role(model),
    ).strip()
    if prepared.category_5_answer_key is not None:
        return get_category_5_answer(raw, prepared.category_5_answer_key)
    return raw
