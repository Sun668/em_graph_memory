"""LLM entity extraction for EM graph Memory text (standalone)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from em_graph.config import (
    ENTITY_EXTRACT_VERSION,
    ENTITY_EXTRACTION_PROMPT,
    ENTITY_TYPES,
)
from em_graph.llm import run_chat, set_api_key_from_env


_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class ExtractedEntity:
    value: str
    type: str

    def to_dict(self) -> Dict[str, str]:
        return {"value": self.value, "type": self.type}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedEntity":
        return cls(value=str(data["value"]), type=str(data["type"]))


def normalize_entity_value(value: str) -> str:
    text = _WHITESPACE_RE.sub(" ", str(value or "").strip())
    text = re.sub(r"'s$", "", text, flags=re.I)
    return text.strip(" .,;:!?\"'")


def canonicalize_entity_type(entity_type: str) -> Optional[str]:
    t = str(entity_type or "").strip()
    return t if t in ENTITY_TYPES else None


def postprocess_entities(
    entities: List[ExtractedEntity],
) -> List[ExtractedEntity]:
    """Normalize values, canonicalize types, dedupe. Same for all texts."""
    best: Dict[str, ExtractedEntity] = {}
    for ent in entities:
        etype = canonicalize_entity_type(ent.type)
        if etype is None:
            continue
        value = normalize_entity_value(ent.value)
        if not value:
            continue
        key = value.lower()
        prev = best.get(key)
        if prev is None or len(value) > len(prev.value):
            best[key] = ExtractedEntity(value=value, type=etype)
    out = list(best.values())
    out.sort(key=lambda e: (0 if e.type == "Who" else 1, -len(e.value), e.value.lower()))
    return out


class EntityCache:
    """JSON cache keyed by extract-version + model + text hash."""

    def __init__(self, cache_file: Optional[str] = None, flush_every: int = 20):
        if cache_file is None:
            cache_file = os.path.join(
                os.path.dirname(__file__), "cache", "entity_cache.json"
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
        except Exception as exc:
            print(f"Warning: failed to load EM entity cache: {exc}")
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
    def _key(text: str, model: str, version: str = ENTITY_EXTRACT_VERSION) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        return f"{version}::{model}::{digest}"

    def get(self, text: str, model: str) -> Optional[List[Dict[str, str]]]:
        with self._lock:
            cached = self._cache.get(self._key(text, model))
        if isinstance(cached, list):
            return cached
        return None

    def set(self, text: str, model: str, entities: List[Dict[str, str]]) -> None:
        with self._lock:
            self._cache[self._key(text, model)] = entities
            self._dirty += 1
            should_flush = self._dirty >= self.flush_every
        if should_flush:
            self.flush()


class EntityExtractor:
    """LLM entity extractor with shared postprocess for all texts."""

    def __init__(
        self,
        model: str = "",
        use_cache: bool = True,
        cache: Optional[EntityCache] = None,
        wait_time: float = 0.2,
    ):
        self.model = model or os.environ.get("OPENAI_MODEL", "deepseek-v4-pro")
        self.use_cache = use_cache
        self.cache = cache if cache is not None else EntityCache()
        self.wait_time = float(wait_time)

    def extract(self, text: str) -> List[ExtractedEntity]:
        text = str(text or "").strip()
        if not text:
            return []

        if self.use_cache:
            cached = self.cache.get(text, self.model)
            if cached is not None:
                return postprocess_entities(
                    [ExtractedEntity.from_dict(item) for item in cached]
                )

        entities_data = self._call_llm(text)
        if self.use_cache:
            self.cache.set(text, self.model, entities_data)
        return postprocess_entities(
            [ExtractedEntity.from_dict(item) for item in entities_data]
        )

    def _call_llm(self, text: str, max_retries: int = 3) -> List[Dict[str, str]]:
        set_api_key_from_env()
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                token_budget = (
                    4000 if str(self.model).lower().startswith("gpt-5") else 2500
                )
                response = run_chat(
                    query=prompt,
                    model=self.model,
                    num_tokens_request=token_budget,
                    temperature=0.3,
                    wait_time=self.wait_time,
                )
                return self._parse_response(response)
            except ValueError as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(1)
        assert last_error is not None
        raise last_error

    def _parse_response(self, response: str) -> List[Dict[str, str]]:
        response = response.strip()
        # Strip one leading fence and any trailing fence.
        if response.startswith("```json"):
            response = response[7:].strip()
        elif response.startswith("```"):
            response = response[3:].strip()
        if response.endswith("```"):
            response = response[:-3].strip()
        # Models sometimes emit "[]```json\n[]" — drop leftover fences mid-text.
        response = re.sub(r"```(?:json)?", "", response).strip()

        cleaned = re.sub(r",\s*([}\]])", r"\1", response)
        cleaned = re.sub(r"//.*?$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

        entities = None
        parse_errors: List[str] = []

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "entities" in parsed:
                entities = parsed["entities"]
            elif isinstance(parsed, list):
                entities = parsed
        except json.JSONDecodeError as exc:
            parse_errors.append(f"Direct parse failed: {exc}")

        # Prefer the first JSON value when trailing junk remains.
        if entities is None:
            try:
                parsed, _end = json.JSONDecoder().raw_decode(cleaned.lstrip())
                if isinstance(parsed, dict) and "entities" in parsed:
                    entities = parsed["entities"]
                elif isinstance(parsed, list):
                    entities = parsed
            except json.JSONDecodeError as exc:
                parse_errors.append(f"raw_decode failed: {exc}")

        if entities is None:
            try:
                start_idx = cleaned.find("[")
                end_idx = cleaned.rfind("]")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    arr_str = cleaned[start_idx : end_idx + 1]
                    arr_str = re.sub(r",\s*([}\]])", r"\1", arr_str)
                    entities = json.loads(arr_str)
            except (json.JSONDecodeError, ValueError) as exc:
                parse_errors.append(f"Array extraction failed: {exc}")

        if entities is None:
            try:
                entity_pattern = (
                    r'\{\s*"value"\s*:\s*"([^"]*)"\s*,\s*"type"\s*:\s*"([^"]*)"\s*\}'
                )
                matches = re.findall(entity_pattern, response)
                if matches:
                    entities = [{"value": m[0], "type": m[1]} for m in matches]
            except Exception as exc:
                parse_errors.append(f"Regex extraction failed: {exc}")

        if entities is None:
            raise ValueError(
                "Failed to parse entity JSON:\n"
                + "\n".join(parse_errors)
                + f"\n\nResponse was:\n{response[:500]}..."
            )
        if not isinstance(entities, list):
            raise ValueError(f"Expected list, got {type(entities)}")

        cleaned_entities: List[Dict[str, str]] = []
        for entity in entities:
            if not isinstance(entity, dict):
                raise ValueError(f"Expected dict, got {type(entity)}")
            if "value" not in entity or "type" not in entity:
                raise ValueError(f"Entity missing value/type: {entity}")
            etype = canonicalize_entity_type(str(entity["type"]))
            if etype is None:
                etype = "What"
            value = normalize_entity_value(str(entity["value"]))
            if value:
                cleaned_entities.append({"value": value, "type": etype})
        return cleaned_entities
