"""The only retrieval boundary visible to LoCoMo QA evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class RecalledQAContext:
    context: str
    context_ids: Sequence[str]


class QARecall(Protocol):
    def recall(
        self,
        sample: Mapping[str, Any],
        qa_index: int,
        question: str,
        top_k: int,
    ) -> RecalledQAContext:
        """Return reader context and retrieved evidence ids for one QA."""

