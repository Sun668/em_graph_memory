from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR))
sys.path.insert(0, str(ROOT / "code"))

import formal_graph
from cost_telemetry import CostTelemetry
from validate_formal_result import condition_fingerprint


def _args(**overrides):
    values = {
        "run_id": "tes_A_top25_run01",
        "scope": "preflight",
        "variant": "A",
        "top_k": 25,
        "extract_model": "gpt-3.5-turbo",
        "embedding_model": "text-embedding-3-small",
        "embedding_normalization": "l2_float32_v1",
        "answer_model": "gpt-3.5-turbo",
        "cache_dir": "outputs/em_graph",
        "entity_weight": None,
        "semantic_weight": None,
        "semantic_score_normalization": None,
        "sequence_scale": None,
        "entity_min_rel_score": None,
        "entity_top_k_per_key": None,
        "who_only_dampen": None,
        "no_degree_discount": False,
        "o2_local_dragon_diagnostic": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FormalGraphTests(unittest.TestCase):
    def test_o2_protocol_is_exact_and_fail_closed(self):
        args = _args(
            run_id="formal_all10_O2_B_dragon_raw_minmax_top25",
            scope="all10",
            variant="B",
            embedding_model="dragon",
            embedding_normalization="none_float32_v1",
            semantic_score_normalization="query_local_minmax_v1",
            o2_local_dragon_diagnostic=True,
        )
        formal_graph._validate_o2_protocol(args)
        args.semantic_weight = 0.8
        with self.assertRaisesRegex(ValueError, "protocol mismatch"):
            formal_graph._validate_o2_protocol(args)

    def test_formal_config_is_fingerprinted_and_no_resume(self):
        args = _args()
        recall = formal_graph.graph_runner._recall_parameters_from_args(args)
        with tempfile.TemporaryDirectory() as directory:
            config = formal_graph._formal_config(
                args=args,
                samples=[{"sample_id": "conv-26"}],
                condition_dir=Path(directory) / args.run_id,
                source_audit={
                    "source_commit": "a" * 40,
                    "source_tree": "b" * 40,
                },
                cache_records=[{"sample_id": "conv-26"}],
                recall_parameters=recall,
                query_artifact_identity={
                    "schema": "query_embedding_artifact_v1",
                    "sha256": "c" * 64,
                },
                command=".venv/bin/python formal_graph.py",
            )
        self.assertFalse(config["resume"])
        self.assertFalse(config["overwrite"])
        self.assertEqual(config["retrieval"]["variant"], "A")
        self.assertEqual(config["condition_fingerprint"], condition_fingerprint(config))
        self.assertIsNone(config["models"]["extraction"])
        self.assertEqual(
            config["cache_identity"]["query_embedding_artifact"]["sha256"],
            "c" * 64,
        )

    def test_graph_audit_excludes_all_test_annotations(self):
        args = _args(variant="B")
        recall = formal_graph.graph_runner._recall_parameters_from_args(args)
        audit = formal_graph._audit(
            args, [{"sample_id": "conv-26"}], recall
        )
        self.assertEqual(audit["mandatory_graph_constraint"], "pass")
        self.assertEqual(audit["answer_recall"][:18], "EM graph retrieval")
        self.assertIn("QA answers", audit["excluded_from_graph_construction"])
        self.assertTrue(audit["prompt_budget"]["pass"])

    def test_preflight_requires_samples(self):
        args = _args()
        args.data_file = str(ROOT / "data" / "locomo10.json")
        args.samples = None
        with self.assertRaisesRegex(ValueError, "requires --samples"):
            formal_graph._selected_samples(args)

    def test_timed_router_records_each_recall(self):
        class Router:
            def recall(self, sample, qa_index, question, top_k):
                return (sample["sample_id"], qa_index, question, top_k)

        telemetry = CostTelemetry("warm")
        router = formal_graph._TimedRecallRouter(Router(), telemetry)
        result = router.recall({"sample_id": "conv-26"}, 3, "q", 25)
        self.assertEqual(result, ("conv-26", 3, "q", 25))
        self.assertEqual(len(telemetry.retrieval_latencies), 1)
        self.assertGreaterEqual(telemetry.retrieval_latencies[0], 0)


if __name__ == "__main__":
    unittest.main()
