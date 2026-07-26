"""Pronoun and relative-time normalization for dialog text."""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple

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


def _previous_weekday(anchor: date, weekday: int) -> date:
    delta = (anchor.weekday() - weekday) % 7
    if delta == 0:
        delta = 7
    return anchor - timedelta(days=delta)


def resolve_time_word(time_word: str, dialog_time: str) -> Optional[str]:
    """
    Map one relative time phrase to a concrete date string.

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
    elif phrase in ("last week", "last weekend"):
        resolved = anchor - timedelta(days=7)
    elif phrase == "last month":
        resolved = anchor - timedelta(days=30)
    elif phrase == "next month":
        month = anchor.month + 1
        year = anchor.year
        if month == 13:
            month = 1
            year += 1
        resolved = date(year, month, min(anchor.day, 28))
    elif phrase in ("a year ago", "one year ago"):
        resolved = date(anchor.year - 1, anchor.month, min(anchor.day, 28))
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


def _replace_speaker_pronouns(
    text: str,
    speaker: str,
    previous_speaker: Optional[str],
) -> str:
    if speaker:
        text = re.sub(r"\bI\b", speaker, text, flags=re.IGNORECASE)
        text = re.sub(r"\bme\b", speaker, text, flags=re.IGNORECASE)
        text = re.sub(r"\bmy\b", f"{speaker}'s", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmine\b", f"{speaker}'s", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmyself\b", speaker, text, flags=re.IGNORECASE)
    if previous_speaker:
        text = re.sub(r"\byou\b", previous_speaker, text, flags=re.IGNORECASE)
        text = re.sub(
            r"\byour\b", f"{previous_speaker}'s", text, flags=re.IGNORECASE
        )
        text = re.sub(
            r"\byours\b", f"{previous_speaker}'s", text, flags=re.IGNORECASE
        )
        text = re.sub(r"\byourself\b", previous_speaker, text, flags=re.IGNORECASE)
    return text


def _replace_time_words(
    text: str,
    dialog_time: str,
    time_words: Sequence[str],
) -> str:
    # Longer phrases first to avoid partial overlaps.
    ordered = sorted({str(w).strip() for w in time_words if str(w).strip()}, key=len, reverse=True)
    for word in ordered:
        concrete = resolve_time_word(word, dialog_time)
        if not concrete:
            continue
        text = re.sub(rf"\b{re.escape(word)}\b", concrete, text, flags=re.IGNORECASE)
    return text


def replace_pronouns(
    text: str,
    *,
    speaker: str,
    previous_speaker: Optional[str] = None,
    dialog_time: str = "",
    time_words: Optional[Iterable[str]] = None,
    auto_time_words: bool = True,
) -> str:
    """
    Normalize person pronouns and relative time words in one dialog turn.

    Person:
      - I / me / my / mine / myself → ``speaker``
      - you / your / yours / yourself → ``previous_speaker`` (when provided)

    Time:
      - Inputs are ``dialog_time`` (when the conversation happened) and the
        surface phrases to rewrite (e.g. ``yesterday``).
      - If ``time_words`` is omitted and ``auto_time_words`` is True, known
        relative phrases in the text are detected automatically.
    """
    result = str(text or "")
    if not result:
        return result

    result = _replace_speaker_pronouns(result, speaker, previous_speaker)

    words: List[str]
    if time_words is not None:
        words = [str(w) for w in time_words]
    elif auto_time_words and dialog_time:
        words = _detect_time_words(result)
    else:
        words = []

    if words and dialog_time:
        result = _replace_time_words(result, dialog_time, words)
    return result
