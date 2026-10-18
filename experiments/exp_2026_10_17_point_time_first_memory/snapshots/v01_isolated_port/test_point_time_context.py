"""No-provider checks for the isolated Reader-context change."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from em_graph.build.models import MemoryNode
from em_graph.recall.service import format_recalled_context
from locomo_eval.recall import RecalledQAContext
from point_time_context import PointTimeFirstEvidenceRecall


class PointTimeContextTests(unittest.TestCase):
    def test_only_first_memory_text_changes_and_ids_stay_ordered(self):
        date_time = "1:56 pm on 8 May, 2023"
        memories = [
            MemoryNode(
                id=f"m{i}", dia_id=f"d{i}", session_num=1,
                date_time=date_time, speaker="A",
                text="I visited yesterday.",
                text_normalized="I visited yesterday [7 May 2023].",
            )
            for i in (1, 2)
        ]
        graph = SimpleNamespace(memories={m.id: m for m in memories})
        ids = ["d1", "d2"]

        class Base:
            def recall(self, sample, qa_index, question, top_k):
                return RecalledQAContext(format_recalled_context(graph, ids), ids)

        recall = PointTimeFirstEvidenceRecall(Base(), {"conv-test": SimpleNamespace(graph=graph)})
        result = recall.recall({"sample_id": "conv-test"}, 0, "When did A visit?", 25)
        self.assertEqual(result.context_ids, ids)
        self.assertIn('"I visited 7 May 2023."', result.context.splitlines()[0])
        self.assertEqual(result.context.splitlines()[1], format_recalled_context(graph, ["d2"]))
        unchanged = recall.recall({"sample_id": "conv-test"}, 1, "Where did A visit?", 25)
        self.assertEqual(unchanged.context, format_recalled_context(graph, ids))


if __name__ == "__main__":
    unittest.main()
