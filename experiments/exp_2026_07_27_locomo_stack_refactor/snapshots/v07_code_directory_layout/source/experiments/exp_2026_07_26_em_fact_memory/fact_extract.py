"""Conversation-only fact-sentence extraction (Mem0-style distillation probe)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "code"))

from common.llm import run_chat, set_api_key_from_env

FACT_EXTRACT_VERSION = "v1"

# Non-data scaffold only (inserted dialog text is not counted toward budget).
FACT_EXTRACTION_PROMPT = """Extract atomic factual memory sentences from one conversation turn.

Rules:
1. Output ONLY facts explicitly supported by the turn (and optional image caption).
2. Each fact is one short declarative sentence (about 5-25 words).
3. Prefer concrete people, places, times, events, states, preferences, relationships.
4. Resolve pronouns using the speaker name when obvious (e.g. "Caroline likes ...").
5. Keep temporal cues that appear in the turn or the provided Date field.
6. Do NOT invent, infer beyond the text, or copy whole chatty paragraphs.
7. Skip greetings, acknowledgements, and empty turns: return [].
8. Deduplicate near-identical facts in this turn.
9. Return a JSON array of strings only.

Example:

Date: 1 May 2023
Speaker: Caroline
Text: "I adopted a labrador puppy last weekend and named him Rigby."

Output:
["Caroline adopted a labrador puppy last weekend.", "Caroline named the puppy Rigby."]

Date: {date_time}
Speaker: {speaker}
Text: {text}

Return only the JSON array:"""


_WHITESPACE_RE = re.compile(r"\s+")


def prompt_scaffold_len() -> int:
    return len(
        FACT_EXTRACTION_PROMPT.format(date_time="", speaker="", text="")
    )


def normalize_fact(text: str) -> str:
    t = _WHITESPACE_RE.sub(" ", str(text or "").strip())
    t = t.strip(" `\"'")
    if t.endswith("."):
        return t
    if t and t[-1] not in ".!?":
        return t + "."
    return t


def postprocess_facts(facts: List[str]) -> List[str]:
    best: Dict[str, str] = {}
    for raw in facts:
        fact = normalize_fact(raw)
        if len(fact) < 8:
            continue
        key = fact.lower()
        prev = best.get(key)
        if prev is None or len(fact) > len(prev):
            best[key] = fact
    return list(best.values())


class FactCache:
    def __init__(self, cache_file: Optional[str] = None, flush_every: int = 20):
        if cache_file is None:
            cache_file = os.path.join(
                os.path.dirname(__file__), "cache", "fact_cache.json"
            )
        self.cache_file = os.path.abspath(cache_file)
        self.flush_every = max(int(flush_every), 1)
        self._dirty = 0
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.cache_file):
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to load fact cache: {exc}")
            self._cache = {}

    def flush(self) -> None:
        with self._lock:
            if self._dirty <= 0:
                return
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            self._dirty = 0

    @staticmethod
    def _key(text: str, model: str, version: str = FACT_EXTRACT_VERSION) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        return f"{version}::{model}::{digest}"

    def get(self, text: str, model: str) -> Optional[List[str]]:
        with self._lock:
            cached = self._cache.get(self._key(text, model))
        if isinstance(cached, list):
            return [str(x) for x in cached]
        return None

    def set(self, text: str, model: str, facts: List[str]) -> None:
        with self._lock:
            self._cache[self._key(text, model)] = list(facts)
            self._dirty += 1
            should_flush = self._dirty >= self.flush_every
        if should_flush:
            self.flush()


@dataclass
class FactExtractor:
    model: str = ""
    use_cache: bool = True
    cache: Optional[FactCache] = None
    wait_time: float = 0.15

    def __post_init__(self) -> None:
        self.model = self.model or os.environ.get("OPENAI_MODEL", "deepseek-v4-flash")
        if self.cache is None:
            self.cache = FactCache()

    def extract_turn(
        self,
        *,
        date_time: str,
        speaker: str,
        text: str,
    ) -> List[str]:
        payload = (
            f"Date: {date_time}\nSpeaker: {speaker}\nText: {text}"
        ).strip()
        if not str(text or "").strip():
            return []

        if self.use_cache and self.cache is not None:
            cached = self.cache.get(payload, self.model)
            if cached is not None:
                return postprocess_facts(cached)

        facts = self._call_llm(date_time=date_time, speaker=speaker, text=text)
        cleaned = postprocess_facts(facts)
        if self.use_cache and self.cache is not None:
            self.cache.set(payload, self.model, cleaned)
        return cleaned

    def _call_llm(
        self,
        *,
        date_time: str,
        speaker: str,
        text: str,
        max_retries: int = 3,
    ) -> List[str]:
        set_api_key_from_env()
        prompt = FACT_EXTRACTION_PROMPT.format(
            date_time=date_time or "",
            speaker=speaker or "",
            text=text or "",
        )
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                response = run_chat(
                    query=prompt,
                    model=self.model,
                    num_tokens_request=1200,
                    temperature=0.2,
                    wait_time=self.wait_time,
                )
                return self._parse_response(response)
            except ValueError as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(1)
        assert last_error is not None
        raise last_error

    def _parse_response(self, response: str) -> List[str]:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:].strip()
        elif response.startswith("```"):
            response = response[3:].strip()
        if response.endswith("```"):
            response = response[:-3].strip()
        response = re.sub(r"```(?:json)?", "", response).strip()
        cleaned = re.sub(r",\s*([}\]])", r"\1", response)

        parsed = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(cleaned.lstrip())
            except json.JSONDecodeError:
                start = cleaned.find("[")
                end = cleaned.rfind("]")
                if start != -1 and end > start:
                    parsed = json.loads(cleaned[start : end + 1])

        if parsed is None:
            raise ValueError(f"Failed to parse facts JSON: {response[:400]}")
        if isinstance(parsed, dict) and "facts" in parsed:
            parsed = parsed["facts"]
        if not isinstance(parsed, list):
            raise ValueError(f"Expected list of facts, got {type(parsed)}")
        out: List[str] = []
        for item in parsed:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and "fact" in item:
                out.append(str(item["fact"]))
            elif isinstance(item, dict) and "text" in item:
                out.append(str(item["text"]))
        return out
