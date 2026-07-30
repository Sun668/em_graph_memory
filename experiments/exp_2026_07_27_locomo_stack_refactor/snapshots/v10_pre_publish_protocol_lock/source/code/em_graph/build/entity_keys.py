"""Canonical keys shared by graph construction and recall."""

from __future__ import annotations

import re


def normalize_entity_key(value: str) -> str:
    """Lowercase key used for Entity identity and recall matching."""
    key = str(value or "").lower().strip()
    key = re.sub(r"'s$", "", key)
    return re.sub(r"\s+", " ", key)
