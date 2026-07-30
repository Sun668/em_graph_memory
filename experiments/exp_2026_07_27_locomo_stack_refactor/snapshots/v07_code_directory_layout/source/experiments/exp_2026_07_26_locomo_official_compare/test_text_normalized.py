from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from em_graph.builder import build_em_graph
from em_graph.config import EMGraphConfig
from em_graph.models import MemoryNode
from em_graph.replace_pronouns import (
    normalize_dialog_text,
    replace_pronouns,
    resolve_time_word,
)
from em_graph.tokenize import memory_search_text


class TextNormalizedTest(unittest.TestCase):
    def test_preserves_pronouns_contractions_and_wording(self) -> None:
        raw = "  I'm happy.  You've helped me, and I'd help you too.  "

        normalized = normalize_dialog_text(raw)

        self.assertEqual(
            normalized,
            "I'm happy. You've helped me, and I'd help you too.",
        )
        self.assertNotIn("Caroline'm", normalized)
        self.assertNotIn("Melanie've", normalized)

    def test_adds_time_annotations_without_removing_surface_phrases(self) -> None:
        normalized = normalize_dialog_text(
            "I went yesterday and will return tomorrow.",
            dialog_time="1:56 pm on 8 May, 2023",
        )

        self.assertEqual(
            normalized,
            "I went yesterday [7 May 2023] and will return "
            "tomorrow [9 May 2023].",
        )

    def test_normalization_is_idempotent(self) -> None:
        first = normalize_dialog_text(
            "Last week was busy, but today is calm.",
            dialog_time="1:56 pm on 10 May, 2023",
        )
        second = normalize_dialog_text(
            first,
            dialog_time="1:56 pm on 10 May, 2023",
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first,
            "Last week [1 May 2023 to 7 May 2023] was busy, "
            "but today [10 May 2023] is calm.",
        )

    def test_calendar_periods_do_not_use_fixed_day_approximations(self) -> None:
        anchor = "9:30 am on 10 January, 2024"

        self.assertEqual(resolve_time_word("last month", anchor), "December 2023")
        self.assertEqual(resolve_time_word("next month", anchor), "February 2024")
        self.assertEqual(
            resolve_time_word("last weekend", anchor),
            "6 January 2024 to 7 January 2024",
        )

    def test_year_ago_preserves_day_except_for_leap_day(self) -> None:
        self.assertEqual(
            resolve_time_word("a year ago", "9:30 am on 31 March, 2024"),
            "31 March 2023",
        )
        self.assertEqual(
            resolve_time_word("one year ago", "9:30 am on 29 February, 2024"),
            "28 February 2023",
        )

    def test_previous_weekday_is_strictly_before_anchor(self) -> None:
        self.assertEqual(
            resolve_time_word("last monday", "9:30 am on 8 May, 2023"),
            "1 May 2023",
        )

    def test_compatibility_wrapper_no_longer_substitutes_speakers(self) -> None:
        normalized = replace_pronouns(
            "I'm glad you came yesterday.",
            speaker="Caroline",
            previous_speaker="Melanie",
            dialog_time="1:56 pm on 8 May, 2023",
        )

        self.assertEqual(
            normalized,
            "I'm glad you came yesterday [7 May 2023].",
        )

    def test_graph_builder_stores_and_extracts_the_new_normalized_text(self) -> None:
        class RecordingExtractor:
            def __init__(self) -> None:
                self.inputs = []

            def extract(self, text):
                self.inputs.append(text)
                return []

        extractor = RecordingExtractor()
        sample = {
            "sample_id": "normalization-test",
            "conversation": {
                "session_1_date_time": "1:56 pm on 8 May, 2023",
                "session_1": [
                    {
                        "dia_id": "D1:1",
                        "speaker": "Caroline",
                        "text": "I'm glad you came yesterday.",
                        "query": "private crawler search phrase",
                        "img_url": "https://example.invalid/private.jpg",
                        "blip_caption": "a photo of a hiking trail",
                    }
                ],
            },
        }

        graph = build_em_graph(
            sample,
            config=EMGraphConfig(add_speaker_as_entity=False),
            extractor=extractor,
            max_workers=1,
        )
        memory = graph.memories["memory:D1:1"]

        self.assertEqual(memory.text, "I'm glad you came yesterday.")
        self.assertEqual(
            memory.text_normalized,
            "I'm glad you came yesterday [7 May 2023].",
        )
        self.assertEqual(
            extractor.inputs,
            [
                memory.text_normalized
                + " [Image: a photo of a hiking trail]"
            ],
        )
        self.assertNotIn("private crawler search phrase", extractor.inputs[0])
        self.assertFalse(hasattr(memory, "query"))
        self.assertFalse(hasattr(memory, "img_url"))
        self.assertNotIn("query", memory.to_dict())
        self.assertNotIn("img_url", memory.to_dict())

    def test_graph_builder_does_not_use_img_caption_fallback(self) -> None:
        class RecordingExtractor:
            def __init__(self) -> None:
                self.inputs = []

            def extract(self, text):
                self.inputs.append(text)
                return []

        extractor = RecordingExtractor()
        graph = build_em_graph(
            {
                "sample_id": "no-img-caption-fallback",
                "conversation": {
                    "session_1_date_time": "1:56 pm on 8 May, 2023",
                    "session_1": [
                        {
                            "dia_id": "D1:1",
                            "speaker": "Caroline",
                            "text": "Official dialog text.",
                            "img_caption": "non-official fallback caption",
                        }
                    ],
                },
            },
            config=EMGraphConfig(add_speaker_as_entity=False),
            extractor=extractor,
            max_workers=1,
        )

        self.assertEqual(extractor.inputs, ["Official dialog text."])
        self.assertEqual(graph.memories["memory:D1:1"].blip_caption, "")

    def test_memory_search_text_is_canonical_and_excludes_image_query(self) -> None:
        memory = MemoryNode(
            id="memory:D1:1",
            dia_id="D1:1",
            session_num=1,
            date_time="1:56 pm on 8 May, 2023",
            speaker="Caroline",
            text="Raw dialog text.",
            text_normalized="Normalized dialog text.",
            blip_caption="a photo of a hiking trail",
        )

        search_text = memory_search_text(memory)

        self.assertEqual(
            search_text,
            'Caroline said, "Normalized dialog text." '
            "and shared a photo of a hiking trail",
        )
        self.assertNotIn("private crawler search phrase", search_text)
        self.assertNotIn(memory.text, search_text)

    def test_memory_search_text_does_not_fall_back_to_raw_text(self) -> None:
        memory = MemoryNode(
            id="memory:D1:1",
            dia_id="D1:1",
            session_num=1,
            date_time="1:56 pm on 8 May, 2023",
            speaker="Caroline",
            text="Raw dialog text must not be embedded.",
            text_normalized="",
            blip_caption="",
        )

        self.assertEqual(memory_search_text(memory), 'Caroline said, ""')


if __name__ == "__main__":
    unittest.main()
