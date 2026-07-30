"""Exact LoCoMo QA F1 logic plus experiment-level aggregation.

The per-question functions mirror ``snap-research/locomo``:
``task_eval/evaluation.py``.  The only addition is ``summarize_f1``, which
averages those official per-question scores overall, by category, and over the
non-adversarial subset.
"""

from __future__ import annotations

import string
from collections import Counter
from typing import Any, Dict, Iterable, List

import numpy as np
import regex
from nltk.stem import PorterStemmer

_STEMMER = PorterStemmer()


def normalize_answer(text: str) -> str:
    text = str(text or "").replace(",", "")

    def remove_articles(value: str) -> str:
        return regex.sub(r"\b(a|an|the|and)\b", " ", value)

    def white_space_fix(value: str) -> str:
        return " ".join(value.split())

    def remove_punc(value: str) -> str:
        exclude = set(string.punctuation)
        return "".join(ch for ch in value if ch not in exclude)

    return white_space_fix(remove_articles(remove_punc(text.lower())))


def f1_score(prediction: str, ground_truth: str) -> float:
    prediction_tokens = [
        _STEMMER.stem(word) for word in normalize_answer(prediction).split()
    ]
    ground_truth_tokens = [
        _STEMMER.stem(word) for word in normalize_answer(ground_truth).split()
    ]
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = float(num_same) / len(prediction_tokens)
    recall = float(num_same) / len(ground_truth_tokens)
    return (2 * precision * recall) / (precision + recall)


def multi_answer_f1(prediction: str, ground_truth: str) -> float:
    predictions = [part.strip() for part in str(prediction).split(",")]
    ground_truths = [part.strip() for part in str(ground_truth).split(",")]
    return float(
        np.mean(
            [
                max(f1_score(pred, gold) for pred in predictions)
                for gold in ground_truths
            ]
        )
    )


def official_qa_f1(prediction: str, ground_truth: str, category: int) -> float:
    """Return the official LoCoMo score for one QA row."""
    output = str(prediction or "")
    answer = str(ground_truth or "")
    category = int(category)
    if category == 3:
        answer = answer.split(";")[0].strip()
    if category in (2, 3, 4):
        return f1_score(output, answer)
    if category == 1:
        return multi_answer_f1(output, answer)
    if category == 5:
        lowered = output.lower()
        return float(
            "no information available" in lowered or "not mentioned" in lowered
        )
    raise ValueError(f"unsupported LoCoMo QA category: {category}")


def summarize_f1(
    rows: Iterable[Dict[str, Any]], category_names: Dict[int, str]
) -> Dict[str, Any]:
    materialized: List[Dict[str, Any]] = list(rows)
    scored = [row for row in materialized if row.get("token_f1") is not None]
    by_category: Dict[str, Dict[str, Any]] = {}
    for category in sorted({int(row["category"]) for row in scored}):
        bucket = [row for row in scored if int(row["category"]) == category]
        by_category[str(category)] = {
            "n": len(bucket),
            "token_f1_pct": round(
                100.0 * sum(float(row["token_f1"]) for row in bucket) / len(bucket),
                2,
            ),
            "name": category_names.get(category, str(category)),
        }
    non_adversarial = [row for row in scored if int(row["category"]) != 5]
    return {
        "official_token_f1_25_overall_pct": round(
            100.0 * sum(float(row["token_f1"]) for row in scored) / len(scored), 2
        )
        if scored
        else None,
        "official_token_f1_25_ex_cat5_pct": round(
            100.0
            * sum(float(row["token_f1"]) for row in non_adversarial)
            / len(non_adversarial),
            2,
        )
        if non_adversarial
        else None,
        "f1_by_category": by_category,
    }
