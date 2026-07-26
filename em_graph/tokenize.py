"""Shared text helpers for entity keys, BM25, and embedding fields."""

from __future__ import annotations

import re
from typing import List, Optional, Set

from em_graph.models import MemoryNode

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def normalize_entity_key(value: str) -> str:
    """Lowercase key used for entity identity / soft-match queries."""
    key = str(value or "").lower().strip()
    key = re.sub(r"'s$", "", key)
    key = re.sub(r"\s+", " ", key)
    return key

_FALLBACK_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "do",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "what",
    "were",
    "with",
    "you",
    "your",
    "did",
    "does",
    "when",
    "where",
    "who",
    "why",
}

_NLTK_STOPWORDS: Optional[Set[str]] = None
_STEMMER = None


def memory_search_text(memory: MemoryNode) -> str:
    return " ".join(
        [
            memory.text_normalized,
            memory.text,
            memory.speaker,
            memory.blip_caption,
            memory.query,
        ]
    ).strip()


def _stopwords() -> Set[str]:
    global _NLTK_STOPWORDS
    if _NLTK_STOPWORDS is not None:
        return _NLTK_STOPWORDS
    try:
        from nltk.corpus import stopwords

        try:
            words = stopwords.words("english")
        except LookupError:
            import nltk

            nltk.download("stopwords", quiet=True)
            words = stopwords.words("english")
        _NLTK_STOPWORDS = {w.lower() for w in words}
    except Exception:
        _NLTK_STOPWORDS = set(_FALLBACK_STOPWORDS)
    return _NLTK_STOPWORDS


def _stemmer():
    global _STEMMER
    if _STEMMER is not None:
        return _STEMMER
    try:
        from nltk.stem import PorterStemmer

        _STEMMER = PorterStemmer()
    except Exception:
        _STEMMER = False
    return _STEMMER


def tokenize_for_bm25(text: str) -> List[str]:
    """Stopword-filtered Porter stems for BM25 (list, keeps duplicates for TF)."""
    stops = _stopwords()
    stemmer = _stemmer()
    out: List[str] = []
    for tok in _TOKEN_RE.findall(str(text or "").lower()):
        if len(tok) <= 1 or tok in stops:
            continue
        if stemmer and stemmer is not False:
            try:
                tok = stemmer.stem(tok)
            except Exception:
                pass
        out.append(tok)
    return out
