"""Standalone configuration for the EM heterogeneous graph package."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Set


# Bump when extraction prompt/postprocess changes (cache key namespace).
ENTITY_EXTRACT_VERSION = "v4"

# Retrieval-oriented type set.
ENTITY_TYPES: Set[str] = {
    "Who",
    "What",
    "When",
    "Where",
    "Why",
    "How",
    "How much",
}


ENTITY_EXTRACTION_PROMPT = """Extract high-signal entities for memory-graph retrieval from the text below.

Use ONLY these types: Who, What, When, Where, Why, How, How much.

Rules (same for dialog text and questions):
1. Prefer people, places, times, objects, events, states, and attributes useful for retrieval.
2. Default to short noun phrases (about 1-3 words) so the same concept can reuse one entity key across sentences.
3. Use a longer multi-word value only when needed for a meaningful state or proper concept
   (e.g. a fixed status phrase or named group). Do not copy whole clauses or sentences.
4. Whenever possible, extract one subject-predicate-object structure that captures the core meaning of each sentence:
   - Usually label the subject as Who.
   - Label the core predicate or action as What.
   - Label the object with the entity type appropriate to its meaning.
   - Omit a component if it is absent, not explicitly stated, or would violate rule 9.
5. Do NOT extract low-information wrappers around another entity
   (prepositional shells or filler phrases whose head is already the real entity).
6. Deduplicate near-identical values; keep the clearest short form.
7. Only extract what is actually present; do not invent facts.
8. Do not extract as many as possible — skip weak or redundant mentions.
9. Do NOT extract:
   - Interrogative or function words
     (what, which, who, whom, whose, where, when, why, how, a, an, the, it, they, we, you, i, me, my, your, their).
   - Auxiliary verbs, copular verbs, or generic function verbs without independent retrieval value
     (do, does, did, be, am, is, are, was, were, have, has, had, can, could, will, would, shall, should, may, might, must).
   Keep core actions or content predicates with real retrieval value, such as research, adopt, travel, paint, study, or recommend.

Return a JSON array of objects with "value" (string) and "type" (string).

Example 1:

Text: "The technician will repair the machine in the workshop tomorrow."
Output:
[{{"value": "technician", "type": "Who"}}, {{"value": "repair", "type": "What"}}, {{"value": "machine", "type": "What"}}, {{"value": "workshop", "type": "Where"}}, {{"value": "tomorrow", "type": "When"}}]

Example 2:

Text: "What will the technician repair?"
Output:
[{{"value": "technician", "type": "Who"}}, {{"value": "repair", "type": "What"}}]

Text to extract from:
{text}

Return only the JSON array, no additional text or explanation:"""


@dataclass
class EMGraphConfig:
    """Build-time knobs for layer-1 EM graph construction."""

    model: str = field(
        default_factory=lambda: os.environ.get("OPENAI_MODEL", "deepseek-v4-pro")
    )
    use_cache: bool = True
    add_speaker_as_entity: bool = True
    # When True, auto-scan known relative time phrases if time_words is omitted.
    auto_time_words: bool = True
