"""Evidence-preserving normalization for dialog text.

The original implementation replaced first/second-person pronouns with speaker
names. That corrupted contractions and verb agreement (for example ``I'm`` →
``Caroline'm``). The active normalizer therefore keeps the dialog wording
intact and only adds deterministic annotations to supported relative-time
phrases.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple

DIALOG_NORMALIZATION_VERSION = "evidence_time_annotations_v1"

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_WEEKDAY = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_ANCHOR_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*,?\s*(\d{4})\b",
    re.I,
)

# Longer phrases first so "last week" wins over bare "week" if both ever appear.
_DEFAULT_TIME_PATTERNS: Tuple[str, ...] = (
    r"a year ago",
    r"one year ago",
    r"last weekend",
    r"last week",
    r"last month",
    r"next month",
    r"this morning",
    r"this afternoon",
    r"this evening",
    r"last monday",
    r"last tuesday",
    r"last wednesday",
    r"last thursday",
    r"last friday",
    r"last saturday",
    r"last sunday",
    r"yesterday",
    r"tomorrow",
    r"today",
)


def parse_dialog_time(dialog_time: str) -> Optional[date]:
    """Parse LoCoMo-style anchors like ``1:56 pm on 8 May, 2023``."""
    if not dialog_time:
        return None
    match = _ANCHOR_DATE_RE.search(dialog_time)
    if not match:
        return None
    day = int(match.group(1))
    month = _MONTHS[match.group(2).lower()[:3]]
    year = int(match.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def format_concrete_date(value: date) -> str:
    return f"{value.day} {calendar.month_name[value.month]} {value.year}"


def format_date_range(start: date, end: date) -> str:
    return f"{format_concrete_date(start)} to {format_concrete_date(end)}"


def _previous_weekday(anchor: date, weekday: int) -> date:
    delta = (anchor.weekday() - weekday) % 7
    if delta == 0:
        delta = 7
    return anchor - timedelta(days=delta)


def resolve_time_word(time_word: str, dialog_time: str) -> Optional[str]:
    """
    Map one relative time phrase to a concrete date or calendar-period string.

    Inputs are the dialog occurrence time and the surface phrase (e.g. ``yesterday``).
    """
    anchor = parse_dialog_time(dialog_time)
    if anchor is None:
        return None
    phrase = str(time_word or "").lower().strip()
    if not phrase:
        return None

    resolved: Optional[date] = None
    if phrase == "yesterday":
        resolved = anchor - timedelta(days=1)
    elif phrase in ("today", "this morning", "this afternoon", "this evening"):
        resolved = anchor
    elif phrase == "tomorrow":
        resolved = anchor + timedelta(days=1)
    elif phrase == "last week":
        current_week_start = anchor - timedelta(days=anchor.weekday())
        return format_date_range(
            current_week_start - timedelta(days=7),
            current_week_start - timedelta(days=1),
        )
    elif phrase == "last weekend":
        current_week_start = anchor - timedelta(days=anchor.weekday())
        return format_date_range(
            current_week_start - timedelta(days=2),
            current_week_start - timedelta(days=1),
        )
    elif phrase == "last month":
        month = anchor.month - 1
        year = anchor.year
        if month == 0:
            month = 12
            year -= 1
        return f"{calendar.month_name[month]} {year}"
    elif phrase == "next month":
        month = anchor.month + 1
        year = anchor.year
        if month == 13:
            month = 1
            year += 1
        return f"{calendar.month_name[month]} {year}"
    elif phrase in ("a year ago", "one year ago"):
        try:
            resolved = anchor.replace(year=anchor.year - 1)
        except ValueError:
            # The only valid-date failure here is 29 February in a non-leap year.
            resolved = date(anchor.year - 1, 2, 28)
    else:
        match = re.fullmatch(
            r"last\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            phrase,
        )
        if match:
            resolved = _previous_weekday(anchor, _WEEKDAY[match.group(1)])

    if resolved is None:
        return None
    return format_concrete_date(resolved)


def _detect_time_words(text: str) -> List[str]:
    found: List[str] = []
    seen = set()
    for pattern in _DEFAULT_TIME_PATTERNS:
        for match in re.finditer(rf"\b{pattern}\b", text, flags=re.IGNORECASE):
            surface = match.group(0)
            key = surface.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(surface)
    return found


def _annotate_time_words(
    text: str,
    dialog_time: str,
    time_words: Sequence[str],
) -> str:
    """Append a resolved annotation while retaining each original phrase."""
    ordered = sorted(
        {str(w).strip() for w in time_words if str(w).strip()},
        key=len,
        reverse=True,
    )
    for word in ordered:
        concrete = resolve_time_word(word, dialog_time)
        if not concrete:
            continue
        # The negative lookahead makes normalization idempotent: a phrase
        # immediately followed by an annotation is not annotated again.
        pattern = re.compile(
            rf"\b{re.escape(word)}\b(?!\s*\[[^\]\n]+\])",
            flags=re.IGNORECASE,
        )
        text = pattern.sub(
            lambda match: f"{match.group(0)} [{concrete}]",
            text,
        )
    return text


def normalize_dialog_text(
    text: str,
    *,
    dialog_time: str = "",
    time_words: Optional[Iterable[str]] = None,
    auto_time_words: bool = True,
) -> str:
    """
    Preserve dialog evidence and annotate supported relative-time phrases.

    Time:
      - Inputs are ``dialog_time`` (when the conversation happened) and the
        surface phrases to annotate (e.g. ``yesterday``).
      - If ``time_words`` is omitted and ``auto_time_words`` is True, known
        relative phrases in the text are detected automatically.
      - The surface phrase is retained and the resolved date/period is appended
        in square brackets.

    The operation is deterministic and idempotent. Speaker/addressee identity
    belongs in the retrieval formatter rather than being substituted into the
    quoted dialog text.
    """
    result = " ".join(str(text or "").split())
    if not result:
        return result

    words: List[str]
    if time_words is not None:
        words = [str(w) for w in time_words]
    elif auto_time_words and dialog_time:
        words = _detect_time_words(result)
    else:
        words = []

    if words and dialog_time:
        result = _annotate_time_words(result, dialog_time, words)
    return result


def replace_pronouns(
    text: str,
    *,
    speaker: str,
    previous_speaker: Optional[str] = None,
    dialog_time: str = "",
    time_words: Optional[Iterable[str]] = None,
    auto_time_words: bool = True,
) -> str:
    """Backward-compatible wrapper for the evidence-preserving normalizer.

    ``speaker`` and ``previous_speaker`` are accepted for API compatibility but
    are intentionally not substituted into the original dialog text.
    """
    del speaker, previous_speaker
    return normalize_dialog_text(
        text,
        dialog_time=dialog_time,
        time_words=time_words,
        auto_time_words=auto_time_words,
    )
