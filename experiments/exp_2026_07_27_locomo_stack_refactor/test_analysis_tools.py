from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
import copy
import json

import numpy as np

EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR))

import cost_report
import significance_report
import component_family_report
import fusion_family_report
import input_family_report
import sequence_family_report
from test_validate_formal_result import (
    FormalResultFixture,
    _sha256_file,
    write_relocation_manifest,
)


def _rows(offset: float = 0.0):
    rows = []
    categories = [1, 2, 3, 4, 5] * 2
    for index, category in enumerate(categories):
        base = 0.1 + 0.01 * index
        rows.append(
            {
                "sample_id": "conv-a" if index < 5 else "conv-b",
                "qa_index": index % 5,
                "question": f"q{index}",
                "answer": f"a{index}",
                "evidence": [f"D{index}"],
                "category": category,
                "f1": base + offset,
                "recall": 0.2 + offset,
                "recall_serialized": 0.2 + offset,
                "context_ids": [f"D{index}", f"D{index + 1}"],
            }
        )
    return rows


class SignificanceTests(unittest.TestCase):
    def test_sequence_family_holm_is_stratified_by_metric_and_estimator(self):
        reports = {}
        for index, name in enumerate(sequence_family_report.COMPARISONS):
            paired = 0.01 * (index + 1)
            cluster = 0.02 * (index + 1)
            reports[name] = {
                "analysis": {
                    "overall": {
                        "metrics": {
                            metric: {
                                "paired_qa_bootstrap": {
                                    "two_sided_zero_p": paired
                                },
                                "conversation_cluster_bootstrap": {
                                    "two_sided_zero_p": cluster
                                },
                            }
                            for metric in ("f1", "recall")
                        }
                    }
                }
            }
        adjusted = sequence_family_report.holm_families(reports)
        self.assertEqual(set(adjusted), {"f1", "recall"})
        self.assertAlmostEqual(
            adjusted["f1"]["paired_qa"][
                "sequence_scale_0_25_vs_primary"
            ]["holm_adjusted_p"],
            0.02,
        )

    def test_sequence_family_condition_scale_is_fail_closed(self):
        config = {
            "retrieval": {
                "variant": "B",
                "sequence_secondary_scale": 0.5,
            }
        }
        sequence_family_report._assert_sequence_condition(
            "primary_scale_0_50", config
        )
        with self.assertRaisesRegex(ValueError, "sequence-scale mismatch"):
            sequence_family_report._assert_sequence_condition(
                "sequence_scale_0_25", config
            )

    def test_sequence_family_rejects_query_artifact_mismatch(self):
        control = {
            "dataset_sha256": "data",
            "scope": "all10",
            "sample_ids": ["conv-a"],
            "models": {"answer": "reader"},
            "graph_profile": {"memory_only": False},
            "answer_protocol": {"temperature": 0},
            "retrieval": {
                "variant": "B",
                "top_k": 25,
                "sequence_secondary_scale": 0.5,
            },
            "cache_identity": {
                "records": [{"sample_id": "conv-a"}],
                "query_embedding_artifact": {"sha256": "query-a"},
            },
        }
        candidate = copy.deepcopy(control)
        candidate["retrieval"]["sequence_secondary_scale"] = 1.0
        candidate["cache_identity"]["query_embedding_artifact"][
            "sha256"
        ] = "query-b"
        with self.assertRaisesRegex(
            ValueError, "differs from primary outside sequence scale"
        ):
            sequence_family_report._assert_same_scientific_identity(
                control, "sequence_scale_1_00", candidate
            )

    def test_fusion_family_holm_is_stratified_by_metric_and_estimator(self):
        reports = {}
        for index, name in enumerate(fusion_family_report.COMPARISONS):
            paired = 0.01 * (index + 1)
            cluster = 0.02 * (index + 1)
            reports[name] = {
                "analysis": {
                    "overall": {
                        "metrics": {
                            metric: {
                                "paired_qa_bootstrap": {
                                    "two_sided_zero_p": paired
                                },
                                "conversation_cluster_bootstrap": {
                                    "two_sided_zero_p": cluster
                                },
                            }
                            for metric in ("f1", "recall")
                        }
                    }
                }
            }
        adjusted = fusion_family_report.holm_families(reports)
        self.assertEqual(set(adjusted), {"f1", "recall"})
        self.assertEqual(
            set(adjusted["f1"]),
            {"paired_qa", "conversation_cluster"},
        )
        self.assertAlmostEqual(
            adjusted["f1"]["paired_qa"][
                "fusion_0_10_0_90_vs_primary"
            ]["holm_adjusted_p"],
            0.02,
        )
        self.assertTrue(
            adjusted["recall"]["paired_qa"][
                "fusion_0_10_0_90_vs_primary"
            ]["reject_at_0_05"]
        )

    def test_fusion_family_condition_weights_are_fail_closed(self):
        config = {
            "retrieval": {
                "variant": "B",
                "entity_weight": 0.3,
                "semantic_weight": 0.7,
            }
        }
        fusion_family_report._assert_fusion_condition(
            "primary_0_30_0_70", config
        )
        with self.assertRaisesRegex(ValueError, "fusion mismatch"):
            fusion_family_report._assert_fusion_condition(
                "fusion_0_10_0_90", config
            )

    def test_fusion_family_rejects_query_artifact_mismatch(self):
        control = {
            "dataset_sha256": "data",
            "scope": "all10",
            "sample_ids": ["conv-a"],
            "models": {"answer": "reader"},
            "graph_profile": {"memory_only": False},
            "answer_protocol": {"temperature": 0},
            "retrieval": {
                "variant": "B",
                "top_k": 25,
                "entity_weight": 0.3,
                "semantic_weight": 0.7,
            },
            "cache_identity": {
                "records": [{"sample_id": "conv-a"}],
                "query_embedding_artifact": {"sha256": "query-a"},
            },
        }
        candidate = copy.deepcopy(control)
        candidate["retrieval"]["entity_weight"] = 0.1
        candidate["retrieval"]["semantic_weight"] = 0.9
        candidate["cache_identity"]["query_embedding_artifact"][
            "sha256"
        ] = "query-b"
        with self.assertRaisesRegex(
            ValueError, "differs from primary outside fusion weights"
        ):
            fusion_family_report._assert_same_scientific_identity(
                control, "fusion_0_10_0_90", candidate
            )

    def test_input_family_holm_is_stratified_by_metric_and_estimator(self):
        reports = {}
        for index, name in enumerate(input_family_report.COMPARISONS):
            paired = 0.01 * (index + 1)
            cluster = 0.02 * (index + 1)
            reports[name] = {
                "analysis": {
                    "overall": {
                        "metrics": {
                            metric: {
                                "paired_qa_bootstrap": {
                                    "two_sided_zero_p": paired
                                },
                                "conversation_cluster_bootstrap": {
                                    "two_sided_zero_p": cluster
                                },
                            }
                            for metric in ("f1", "recall")
                        }
                    }
                }
            }
        adjusted = input_family_report.holm_families(reports)
        self.assertEqual(set(adjusted), {"f1", "recall"})
        self.assertEqual(
            set(adjusted["f1"]),
            {"paired_qa", "conversation_cluster"},
        )
        self.assertAlmostEqual(
            adjusted["f1"]["paired_qa"]["time_annotation_inside_b"][
                "holm_adjusted_p"
            ],
            0.02,
        )
        self.assertTrue(
            adjusted["recall"]["paired_qa"][
                "time_annotation_inside_b"
            ]["reject_at_0_05"]
        )

    def test_component_family_holm_is_stratified_by_metric_and_estimator(self):
        reports = {}
        for index, name in enumerate(component_family_report.COMPARISONS):
            paired = 0.01 * (index + 1)
            cluster = 0.02 * (index + 1)
            reports[name] = {
                "analysis": {
                    "overall": {
                        "metrics": {
                            metric: {
                                "paired_qa_bootstrap": {
                                    "two_sided_zero_p": paired
                                },
                                "conversation_cluster_bootstrap": {
                                    "two_sided_zero_p": cluster
                                },
                            }
                            for metric in ("f1", "recall")
                        }
                    }
                }
            }
        adjusted = component_family_report.holm_families(reports)
        self.assertEqual(set(adjusted), {"f1", "recall"})
        self.assertEqual(
            set(adjusted["f1"]),
            {"paired_qa", "conversation_cluster"},
        )
        self.assertAlmostEqual(
            adjusted["f1"]["paired_qa"]["sequence_inside_b"][
                "holm_adjusted_p"
            ],
            0.04,
        )
        self.assertTrue(
            adjusted["recall"]["paired_qa"]["sequence_inside_b"][
                "reject_at_0_05"
            ]
        )

    def test_constant_paired_gain_has_exact_ci_and_breakdowns(self):
        report = significance_report.compare_rows(
            _rows(),
            _rows(0.1),
            resamples=200,
            seed=significance_report.SEED,
        )
        for metric in ("f1", "recall"):
            block = report["overall"]["metrics"][metric]
            self.assertAlmostEqual(block["mean_difference"], 0.1)
            np.testing.assert_allclose(
                block["paired_qa_bootstrap"]["confidence_interval_95"],
                [0.1, 0.1],
            )
            np.testing.assert_allclose(
                block["conversation_cluster_bootstrap"][
                    "confidence_interval_95"
                ],
                [0.1, 0.1],
            )
        self.assertEqual(set(report["categories"]), {"1", "2", "3", "4", "5"})
        self.assertEqual(
            report["categories_1_4"]["status"],
            "local non-official diagnostic",
        )
        self.assertEqual(len(report["per_conversation"]), 2)
        self.assertFalse(report["metric_recalculation"])

    def test_fixed_seed_is_reproducible(self):
        first = significance_report.compare_rows(
            _rows(), _rows(0.03), resamples=100
        )
        second = significance_report.compare_rows(
            _rows(), _rows(0.03), resamples=100
        )
        self.assertEqual(first, second)

    def test_holm_step_down(self):
        adjusted = significance_report.holm_adjust(
            {"x": 0.01, "y": 0.04, "z": 0.03}
        )
        self.assertAlmostEqual(adjusted["x"], 0.03)
        self.assertAlmostEqual(adjusted["z"], 0.06)
        self.assertAlmostEqual(adjusted["y"], 0.06)

    def test_empty_evidence_recall_contributes_zero_with_full_denominator(self):
        rows = [
            {
                "category": 1,
                "evidence": [],
                "recall": 1.0,
                "recall_serialized": 1.0,
            },
            {
                "category": 1,
                "evidence": ["D1"],
                "recall": 0.5,
                "recall_serialized": 0.5,
            },
        ]
        self.assertEqual(
            significance_report.official_recall_contribution(rows[0]),
            0.0,
        )
        means = significance_report.recall_means_by_category(rows)
        self.assertEqual(means, {1: 0.25})
        audit = significance_report._recall_aggregation_audit(
            rows,
            {"recall_by_category": {"1": 0.25}},
        )
        self.assertEqual(audit["raw_serialized_recall_means"], {1: 0.75})
        self.assertEqual(audit["official_contribution_means"], {1: 0.25})
        self.assertTrue(audit["matches_official_stats"])

        a_rows = _rows()
        b_rows = copy.deepcopy(a_rows)
        a_rows[0]["evidence"] = []
        b_rows[0]["evidence"] = []
        a_rows[0]["recall"] = 0.0
        a_rows[0]["recall_serialized"] = 0.0
        b_rows[0]["recall"] = 1.0
        b_rows[0]["recall_serialized"] = 1.0
        report = significance_report.compare_rows(
            a_rows, b_rows, resamples=100
        )
        self.assertEqual(
            report["overall"]["metrics"]["recall"]["mean_difference"], 0.0
        )
        self.assertEqual(
            report["categories"]["1"]["metrics"]["recall"][
                "mean_difference"
            ],
            0.0,
        )
        self.assertEqual(
            report["per_conversation"][0]["recall"]["difference"], 0.0
        )
        self.assertEqual(
            report["overall"]["metrics"]["recall"][
                "paired_qa_bootstrap"
            ]["confidence_interval_95"],
            [0.0, 0.0],
        )

    def test_dense_control_exact_ordered_contexts_pass(self):
        a_rows = _rows()
        significance_report.assert_ordered_context_equality(
            a_rows, copy.deepcopy(a_rows)
        )

    def test_dense_control_context_id_difference_fails(self):
        a_rows = _rows()
        b_rows = copy.deepcopy(a_rows)
        b_rows[0]["context_ids"][1] = "different"
        with self.assertRaisesRegex(ValueError, "context id mismatch"):
            significance_report.assert_ordered_context_equality(
                a_rows, b_rows
            )

    def test_dense_control_context_order_difference_fails(self):
        a_rows = _rows()
        b_rows = copy.deepcopy(a_rows)
        b_rows[0]["context_ids"].reverse()
        with self.assertRaisesRegex(ValueError, "context order mismatch"):
            significance_report.assert_ordered_context_equality(
                a_rows, b_rows
            )

    def test_dense_control_reads_two_formal_conditions_and_passes(self):
        dataset = json.loads(
            (EXP_DIR.parents[1] / "data" / "locomo10.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").mkdir()
            (root / "b").mkdir()
            a_fixture = FormalResultFixture(
                root / "a",
                dataset,
                scope="preflight",
                sample_ids=["conv-26"],
                top_k=2,
            )
            b_fixture = FormalResultFixture(
                root / "b",
                dataset,
                scope="preflight",
                sample_ids=["conv-26"],
                top_k=2,
            )
            b_fixture.config["retrieval"]["variant"] = "B_embed"
            b_fixture.config["graph_profile"]["memory_only"] = False
            b_fixture.config["cache_identity"][
                "query_embedding_artifact"
            ] = copy.deepcopy(
                a_fixture.config["cache_identity"][
                    "query_embedding_artifact"
                ]
            )
            b_fixture.write()
            report = significance_report.build_dense_control_report(
                a_fixture.condition_dir,
                b_fixture.condition_dir,
                data_file=a_fixture.data_file,
            )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["qa_count"], 199)
        self.assertEqual(report["mismatches"], 0)

    def test_dense_control_rejects_query_artifact_difference(self):
        a_config = {
            "cache_identity": {
                "query_embedding_artifact": {"sha256": "a" * 64}
            }
        }
        b_config = {
            "cache_identity": {
                "query_embedding_artifact": {"sha256": "b" * 64}
            }
        }
        with self.assertRaisesRegex(
            ValueError,
            "query embedding artifact mismatch",
        ):
            significance_report.assert_same_query_embedding_artifact(
                a_config,
                b_config,
            )

    def test_significance_accepts_only_explicitly_verified_relocation(self):
        dataset = json.loads(
            (EXP_DIR.parents[1] / "data" / "locomo10.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").mkdir()
            (root / "b").mkdir()
            a_fixture = FormalResultFixture(
                root / "a",
                dataset,
                scope="preflight",
                sample_ids=["conv-26"],
                top_k=2,
            )
            b_fixture = FormalResultFixture(
                root / "b",
                dataset,
                scope="preflight",
                sample_ids=["conv-26"],
                top_k=2,
            )
            b_fixture.config["retrieval"]["variant"] = "B"
            b_fixture.config["graph_profile"]["memory_only"] = False
            b_fixture.write()
            manifest_path = write_relocation_manifest(a_fixture)
            manifest_sha256 = _sha256_file(manifest_path)
            with self.assertRaisesRegex(
                ValueError,
                "formal validation failed",
            ):
                significance_report.build_report(
                    a_fixture.condition_dir,
                    b_fixture.condition_dir,
                    data_file=a_fixture.data_file,
                    resamples=100,
                    seed=significance_report.SEED,
                )
            report = significance_report.build_report(
                a_fixture.condition_dir,
                b_fixture.condition_dir,
                data_file=a_fixture.data_file,
                resamples=100,
                seed=significance_report.SEED,
                a_relocation_manifest=manifest_path,
            )
        self.assertTrue(report["condition_a"]["relocation"]["used"])
        self.assertFalse(report["condition_b"]["relocation"]["used"])
        self.assertEqual(
            report["condition_a"]["relocation"]["manifest_sha256"],
            manifest_sha256,
        )


class CostTests(unittest.TestCase):
    def _manifest(self, directory: Path):
        graph = directory / "graph.json"
        index = directory / "index.npy"
        cache = directory / "cache.json"
        graph.write_bytes(b"g" * 3)
        index.write_bytes(b"i" * 5)
        cache.write_bytes(b"c" * 7)
        events = []
        for state, scale in (("cold", 1.0), ("warm", 0.5)):
            events.extend(
                [
                    {
                        "stage": "graph_construction",
                        "cache_state": state,
                        "wall_seconds": 2.0 * scale,
                        "request_count": 0,
                    },
                    {
                        "stage": "entity_extraction",
                        "cache_state": state,
                        "wall_seconds": 1.0 * scale,
                        "request_count": 2,
                        "input_tokens": 20,
                        "output_tokens": 4,
                    },
                    {
                        "stage": "embedding",
                        "cache_state": state,
                        "wall_seconds": 0.4 * scale,
                        "request_count": 1,
                        "input_tokens": 8,
                        "output_tokens": 0,
                    },
                    {
                        "stage": "query_entity",
                        "cache_state": state,
                        "wall_seconds": 0.2 * scale,
                        "request_count": 2,
                        "input_tokens": 10,
                        "output_tokens": 2,
                    },
                    {
                        "stage": "retrieval",
                        "cache_state": state,
                        "wall_seconds": 0.3 * scale,
                        "request_count": 0,
                        "qa_count": 3,
                        "latency_seconds": [
                            0.05 * scale,
                            0.10 * scale,
                            0.15 * scale,
                        ],
                        "provider_recovery": {
                            "retry_count": 1 if state == "cold" else 0,
                            "failure_wall_seconds_excluded": (
                                4.0 if state == "cold" else 0.0
                            ),
                            "wait_seconds_excluded": (
                                3.0 if state == "cold" else 0.0
                            ),
                            "events": (
                                [
                                    {
                                        "failure_wall_seconds": 4.0,
                                        "wait_seconds": 3.0,
                                        "error_type": "RuntimeError",
                                        "error_message": (
                                            "Failed after 10 retries for "
                                            "model=test"
                                        ),
                                    }
                                ]
                                if state == "cold"
                                else []
                            ),
                        },
                    },
                    {
                        "stage": "answer_generation",
                        "cache_state": state,
                        "wall_seconds": 1.5 * scale,
                        "request_count": 3,
                        "input_tokens": 30,
                        "output_tokens": 6,
                    },
                ]
            )
        return {
            "schema": cost_report.EVENT_SCHEMA,
            "run_id": "run01",
            "condition_fingerprint": "a" * 64,
            "latency_clock": "time.perf_counter",
            "token_source": "provider response usage",
            "events": events,
            "disk_artifacts": [
                {"kind": "graph", "path": str(graph)},
                {"kind": "embedding_index", "path": str(index)},
                {"kind": "cache", "path": str(cache)},
            ],
        }

    def test_cost_report_has_required_cold_warm_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            report = cost_report.build_report(
                self._manifest(Path(directory))
            )
        self.assertEqual(
            set(report["cache_measurements"]), {"cold", "warm"}
        )
        cold = report["cache_measurements"]["cold"]["stages"]
        self.assertEqual(cold["entity_extraction"]["request_count"], 2)
        self.assertEqual(cold["entity_extraction"]["input_tokens"], 20)
        self.assertEqual(cold["embedding"]["request_count"], 1)
        self.assertEqual(cold["embedding"]["input_tokens"], 8)
        self.assertEqual(cold["query_entity"]["output_tokens"], 2)
        self.assertEqual(cold["retrieval"]["qa_count"], 3)
        self.assertAlmostEqual(
            cold["retrieval"]["latency"]["p50_seconds"], 0.1
        )
        self.assertEqual(
            cold["retrieval"]["provider_recovery"]["retry_count"],
            1,
        )
        self.assertEqual(
            cold["retrieval"]["provider_recovery"][
                "failure_wall_seconds_excluded"
            ],
            4.0,
        )
        self.assertTrue(
            report["measurement_policy"]["provider_recovery_disclosed"]
        )
        self.assertEqual(cold["answer_generation"]["request_count"], 3)
        self.assertEqual(
            report["disk_usage"]["totals_bytes"],
            {"cache": 7, "embedding_index": 5, "graph": 3},
        )
        self.assertFalse(
            report["measurement_policy"]["missing_values_estimated"]
        )

    def test_missing_warm_measurement_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            manifest["events"] = [
                event
                for event in manifest["events"]
                if event["cache_state"] == "cold"
            ]
            with self.assertRaisesRegex(ValueError, "cold and warm"):
                cost_report.build_report(manifest)

    def test_missing_token_usage_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            del manifest["events"][1]["input_tokens"]
            with self.assertRaisesRegex(ValueError, "input_tokens"):
                cost_report.build_report(manifest)

    def test_missing_embedding_token_usage_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            embedding_event = next(
                event
                for event in manifest["events"]
                if event["cache_state"] == "cold"
                and event["stage"] == "embedding"
            )
            del embedding_event["input_tokens"]
            with self.assertRaisesRegex(ValueError, "input_tokens"):
                cost_report.build_report(manifest)

    def test_missing_required_stage_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            manifest["events"] = [
                event
                for event in manifest["events"]
                if not (
                    event["cache_state"] == "warm"
                    and event["stage"] == "embedding"
                )
            ]
            with self.assertRaisesRegex(ValueError, "missing stages"):
                cost_report.build_report(manifest)

    def test_zero_request_warm_cache_is_reported_without_division(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            for event in manifest["events"]:
                if (
                    event["cache_state"] == "warm"
                    and event["stage"] in cost_report.REQUEST_TOKEN_STAGES
                ):
                    event["request_count"] = 0
                    event["input_tokens"] = 0
                    event["output_tokens"] = 0
                    event["wall_seconds"] = 0
            report = cost_report.build_report(manifest)
        warm = report["cache_measurements"]["warm"]["stages"]
        self.assertIsNone(
            warm["query_entity"]["mean_request_latency_seconds"]
        )
        self.assertEqual(warm["query_entity"]["request_count"], 0)

    def test_invalid_provider_recovery_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            retrieval = next(
                event
                for event in manifest["events"]
                if event["cache_state"] == "cold"
                and event["stage"] == "retrieval"
            )
            retrieval["provider_recovery"]["retry_count"] = 2
            with self.assertRaisesRegex(
                ValueError,
                "provider recovery is invalid",
            ):
                cost_report.build_report(manifest)


if __name__ == "__main__":
    unittest.main()
