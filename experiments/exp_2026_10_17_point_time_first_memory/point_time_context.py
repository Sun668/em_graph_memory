"""Fixed point-time-only Reader context at the existing QARecall boundary.

The relative-time conversion matches the Conv26 diagnostic rule. Retrieval,
graph construction, context IDs, and all but the first Reader line stay B.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Mapping

from em_graph.build.replace_pronouns import (
    _DEFAULT_TIME_PATTERNS,
    format_concrete_date,
    parse_dialog_time,
    resolve_time_word,
)
from em_graph.recall.service import format_recalled_context
from locomo_eval.recall import RecalledQAContext

ROUTE_PATTERN = r"^(?:when\b|how\s+long\b)"
ROUTE_RE = re.compile(ROUTE_PATTERN, re.I)
PHRASE_PATTERN = "|".join(sorted(_DEFAULT_TIME_PATTERNS, key=len, reverse=True))
ANNOTATION_RE = re.compile(
    rf"\b(?P<relative>{PHRASE_PATTERN})\b\s+\[(?P<absolute>[^\]\n]+)\]",
    re.I,
)
NEW_RELATIVE_RE = re.compile(r"\b(last year|last summer|two days ago)\b", re.I)


def replace_relative_time(memory: Any) -> tuple[str, int]:
    raw = str(memory.text or "")
    normalized = str(memory.text_normalized or "")
    if not normalized:
        normalized = raw
    changed = 0

    def substitution(match: re.Match[str]) -> str:
        nonlocal changed
        relative, absolute = match.group("relative"), match.group("absolute")
        if resolve_time_word(relative, str(memory.date_time or "")) != absolute:
            raise ValueError(f"time annotation mismatch in {memory.dia_id}")
        if relative.lower() in {"last week", "last weekend"}:
            return relative
        changed += 1
        return absolute

    rendered = ANNOTATION_RE.sub(substitution, normalized)
    if changed == 0 and rendered != " ".join(raw.split()):
        raise ValueError(f"unexpected normalized text in {memory.dia_id}")
    anchor = parse_dialog_time(str(memory.date_time or ""))

    def new_substitution(match: re.Match[str]) -> str:
        nonlocal changed
        if anchor is None:
            return match.group(0)
        phrase = match.group(0).lower()
        changed += 1
        if phrase == "last year":
            return str(anchor.year - 1)
        if phrase == "last summer":
            return f"summer {anchor.year - 1}"
        return format_concrete_date(anchor - timedelta(days=2))

    rendered = NEW_RELATIVE_RE.sub(new_substitution, rendered)
    return rendered if changed else raw, changed


def treatment_context(graph: Any, ids: list[str]) -> tuple[str, int]:
    by_dialog = {m.dia_id: m for m in graph.memories.values()}
    lines, substitutions = [], 0
    for position, did in enumerate(ids):
        m = by_dialog[did]
        text, n = replace_relative_time(m) if position == 0 else (str(m.text or ""), 0)
        substitutions += n
        line = f'{m.date_time}: {m.speaker} said, "{text}"'
        if str(m.blip_caption or "").strip():
            line += f" and shared {str(m.blip_caption).strip()}"
        lines.append(line)
    return "\n".join(lines), substitutions


class PointTimeFirstEvidenceRecall:
    """Wrap B graph recall, changing only a routed first Memory's Reader text."""

    def __init__(self, base: Any, recalls: Mapping[str, Any]):
        self.base = base
        self.recalls = dict(recalls)

    def recall(
        self,
        sample: Mapping[str, Any],
        qa_index: int,
        question: str,
        top_k: int,
    ) -> RecalledQAContext:
        original = self.base.recall(sample, qa_index, question, top_k)
        if not ROUTE_RE.search(question):
            return original
        ids = list(original.context_ids)
        if not ids:
            return original
        sample_id = str(sample.get("sample_id") or "")
        graph = self.recalls[sample_id].graph
        changed_context, substitutions = treatment_context(graph, ids)
        if substitutions == 0:
            return original
        if original.context != format_recalled_context(graph, ids):
            raise ValueError(f"B Reader context mismatch in {sample_id}:{qa_index}")
        suffix = (
            "\n" + format_recalled_context(graph, ids[1:])
            if len(ids) > 1 else ""
        )
        if not changed_context.endswith(suffix) or original.context == changed_context:
            raise ValueError(f"first-Memory-only change failed in {sample_id}:{qa_index}")
        return RecalledQAContext(context=changed_context, context_ids=ids)
