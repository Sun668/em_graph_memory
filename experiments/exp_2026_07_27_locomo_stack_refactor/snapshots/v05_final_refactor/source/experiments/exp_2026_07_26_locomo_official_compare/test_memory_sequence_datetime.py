from __future__ import annotations

import unittest

from em_graph.builder import ensure_memory_sequence_edges, memory_sort_key
from em_graph.models import EMGraph, EdgeType, MemoryNode


def _memory(
    dia_id: str,
    session_num: int,
    date_time: str,
) -> MemoryNode:
    return MemoryNode(
        id=f"memory:{dia_id}",
        dia_id=dia_id,
        session_num=session_num,
        date_time=date_time,
        speaker="speaker",
        text=dia_id,
        text_normalized=dia_id,
    )


class MemorySequenceDatetimeTest(unittest.TestCase):
    def test_real_datetime_overrides_session_number(self) -> None:
        later_number_earlier_time = _memory(
            "D2:1", 2, "9:30 am on 1 April, 2023"
        )
        earlier_number_later_time = _memory(
            "D1:1", 1, "6:15 pm on 10 May, 2023"
        )

        ordered = sorted(
            [earlier_number_later_time, later_number_earlier_time],
            key=memory_sort_key,
        )

        self.assertEqual([m.dia_id for m in ordered], ["D2:1", "D1:1"])

    def test_time_of_day_is_not_discarded(self) -> None:
        evening = _memory("D1:1", 1, "6:15 pm on 10 May, 2023")
        morning = _memory("D2:1", 2, "9:30 am on 10 May, 2023")

        ordered = sorted([evening, morning], key=memory_sort_key)

        self.assertEqual([m.dia_id for m in ordered], ["D2:1", "D1:1"])

    def test_turn_order_breaks_same_session_timestamp_ties(self) -> None:
        timestamp = "9:30 am on 10 May, 2023"
        turns = [
            _memory("D1:10", 1, timestamp),
            _memory("D1:2", 1, timestamp),
            _memory("D1:1", 1, timestamp),
        ]

        ordered = sorted(turns, key=memory_sort_key)

        self.assertEqual([m.dia_id for m in ordered], ["D1:1", "D1:2", "D1:10"])

    def test_iso_datetime_and_utc_offset_are_supported(self) -> None:
        utc = _memory("D1:1", 1, "2024-06-30T08:00:00Z")
        offset = _memory("D2:1", 2, "2024-06-30T17:00:00+08:00")

        ordered = sorted([offset, utc], key=memory_sort_key)

        self.assertEqual([m.dia_id for m in ordered], ["D1:1", "D2:1"])

    def test_missing_timestamps_fall_back_to_session_and_turn(self) -> None:
        memories = [
            _memory("D3:2", 3, ""),
            _memory("D2:1", 2, "not a timestamp"),
            _memory("D3:1", 3, ""),
        ]

        ordered = sorted(memories, key=memory_sort_key)

        self.assertEqual([m.dia_id for m in ordered], ["D2:1", "D3:1", "D3:2"])

    def test_sequence_edges_follow_real_datetime_bidirectionally(self) -> None:
        graph = EMGraph(sample_id="datetime-order")
        for memory in (
            _memory("D1:1", 1, "6:15 pm on 10 May, 2023"),
            _memory("D2:1", 2, "9:30 am on 1 April, 2023"),
            _memory("D2:2", 2, "9:30 am on 1 April, 2023"),
        ):
            graph.add_memory(memory)

        edge_count = ensure_memory_sequence_edges(graph)
        edges = {
            (edge.src_memory_id, edge.dst_memory_id, edge.edge_type)
            for edge in graph.memory_edges
        }

        self.assertEqual(edge_count, 4)
        self.assertIn(("memory:D2:1", "memory:D2:2", EdgeType.NEXT), edges)
        self.assertIn(("memory:D2:2", "memory:D2:1", EdgeType.PREV), edges)
        self.assertIn(("memory:D2:2", "memory:D1:1", EdgeType.NEXT), edges)
        self.assertIn(("memory:D1:1", "memory:D2:2", EdgeType.PREV), edges)


if __name__ == "__main__":
    unittest.main()
