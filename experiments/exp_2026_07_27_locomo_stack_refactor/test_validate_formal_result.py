from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import QueryEmbeddingArtifact
from em_graph.cache import ordered_question_records
from validate_formal_result import (
    condition_fingerprint,
    validate_formal_result,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dialog_ids(sample: Mapping[str, Any]) -> list[str]:
    ids = []
    for key, dialogs in sample["conversation"].items():
        if (
            key.startswith("session_")
            and not key.endswith("_date_time")
            and isinstance(dialogs, list)
        ):
            ids.extend(str(dialog["dia_id"]) for dialog in dialogs)
    return ids


def write_relocation_manifest(
    fixture: "FormalResultFixture",
) -> Path:
    """Make a pre-migration snapshot and proof for one relocated fixture."""
    original_dir = (
        fixture.root
        / "original_machine"
        / "outputs"
        / "locomo_formal"
        / fixture.condition_dir.name
    )
    query_identity = fixture.config["cache_identity"][
        "query_embedding_artifact"
    ]
    relocated_query_path = Path(query_identity["path"]).resolve()
    original_query_path = (
        fixture.root
        / "original_machine"
        / "outputs"
        / "em_graph"
        / "query_embeddings.npz"
    )
    fixture.config["output_directory"] = str(original_dir)
    query_identity["path"] = str(original_query_path)
    fixture.write()
    artifact_names = {
        "run_config": "run_config.json",
        "prediction": fixture.config["artifacts"]["prediction"],
        "stats": fixture.config["artifacts"]["stats"],
        "audit": fixture.config["artifacts"]["audit"],
        "query_cache_usage": fixture.config["artifacts"][
            "query_cache_usage"
        ],
    }
    artifact_hashes = {
        key: _sha256_file(fixture.condition_dir / name)
        for key, name in artifact_names.items()
    }
    snapshot = {
        "schema": "locomo_experiment_snapshot_v1",
        "snapshot": "fixture_pre_migration",
        "run_id": fixture.config["run_id"],
        "condition_fingerprint": fixture.config["condition_fingerprint"],
        "source_commit": fixture.config["source_commit"],
        "dataset_sha256": fixture.config["dataset_sha256"],
        "artifact_hashes": artifact_hashes,
    }
    snapshot_path = fixture.root / "source_snapshot_result.json"
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = {
        "schema": "locomo_formal_relocation_v1",
        "reason": "repository_root_changed",
        "run_id": fixture.config["run_id"],
        "condition_fingerprint": fixture.config["condition_fingerprint"],
        "original_output_directory": str(original_dir),
        "relocated_condition_directory": str(
            fixture.condition_dir.resolve()
        ),
        "source_snapshot_result": str(snapshot_path),
        "source_snapshot_result_sha256": _sha256_file(snapshot_path),
        "immutable_artifacts": {
            key: {
                "path": name,
                "sha256": artifact_hashes[key],
            }
            for key, name in artifact_names.items()
        },
        "external_artifacts": {
            "query_embedding_artifact": {
                "original_path": str(original_query_path),
                "relocated_path": str(relocated_query_path),
                "sha256": query_identity["sha256"],
            }
        },
    }
    manifest_path = fixture.root / "relocation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path


class FormalResultFixture:
    def __init__(
        self,
        root: Path,
        dataset: Sequence[Mapping[str, Any]],
        *,
        scope: str,
        sample_ids: Iterable[str],
        condition_kind: str = "graph_method",
        top_k: int = 1,
    ):
        self.root = root
        self.dataset = list(dataset)
        self.sample_ids = list(sample_ids)
        self.condition_dir = root / (
            "all10_A_top1_run01"
            if scope == "all10"
            else "conv26_A_top1_preflight01"
        )
        self.condition_dir.mkdir()
        self.data_file = root / "locomo10.json"
        self.data_file.write_text(
            json.dumps(self.dataset, ensure_ascii=False),
            encoding="utf-8",
        )
        self.model_key = "gpt-3.5-turbo_dialog_top_1"
        self.prediction_key = f"{self.model_key}_prediction"
        self.config: Dict[str, Any] = {
            "schema": "locomo_formal_run_v1",
            "run_id": self.condition_dir.name,
            "condition_kind": condition_kind,
            "scope": scope,
            "sample_ids": self.sample_ids,
            "dataset_sha256": _sha256_file(self.data_file),
            "source_commit": "a" * 40,
            "started_at": "2026-07-27T17:30:00+08:00",
            "command": (
                ".venv/bin/python run.py evaluate --variant A --top-k 1 "
                f"--output-dir {self.condition_dir}"
            ),
            "output_directory": str(self.condition_dir),
            "start_state": {
                "output_directory_empty": True,
                "existing_entries": [],
                "prediction_file_existed": False,
            },
            "resume": False,
            "overwrite": False,
            "models": {
                "extraction": "gpt-3.5-turbo",
                "embedding": "text-embedding-3-small",
                "answer": "gpt-3.5-turbo",
                "answer_actual": (
                    "gpt-3.5-turbo-0125"
                    if condition_kind == "official_dialog_reference"
                    else None
                ),
                "query_encoder": None,
                "context_encoder": None,
            },
            "retrieval": {
                "variant": "A",
                "rag_mode": "dialog",
                "top_k": top_k,
                "entity_weight": 0.0,
                "semantic_weight": 1.0,
                "sequence_secondary_scale": 0.5,
                "entity_min_rel_score": 0.5,
                "entity_top_k_per_key": 20,
                "who_only_dampen": 0.25,
                "degree_discount": True,
            },
            "graph_profile": {
                "memory_only": True,
                "use_caption": True,
                "use_time_annotations": True,
                "add_speaker_as_entity": True,
            },
            "answer_protocol": {
                "message_role": "system",
                "temperature": 0,
                "max_tokens": 32,
                "batch_size": 1,
                "category5_option_order": (
                    "unchanged unseeded upstream random.random()"
                ),
            },
            "model_key": self.model_key,
            "prediction_key": self.prediction_key,
            "artifacts": {
                "prediction": "predictions.json",
                "stats": "stats.json",
                "audit": "graph_audit.json",
                "validation": "validation.json",
            },
        }
        if condition_kind == "graph_method":
            records = ordered_question_records(self.dataset)
            digests = list(
                dict.fromkeys(
                    record["question_sha256"] for record in records
                )
            )
            vectors = np.full(
                (len(digests), 2),
                1.0 / np.sqrt(2.0),
                dtype=np.float32,
            )
            query_artifact = QueryEmbeddingArtifact(
                dataset_sha256=self.config["dataset_sha256"],
                model_name="text-embedding-3-small",
                role="context",
                qa_records=records,
                question_digests=digests,
                vectors=vectors,
            )
            self.query_artifact_path = root / "query_embeddings.npz"
            query_artifact.save(self.query_artifact_path)
            self.config["cache_identity"] = {
                "artifact_root": str(root),
                "records": [],
                "query_embedding_artifact": query_artifact.identity(
                    self.query_artifact_path
                ),
            }
            self.config["artifacts"]["query_cache_usage"] = (
                "query_cache_usage.json"
            )
        if condition_kind == "official_dialog_reference":
            self.config["artifacts"]["provider_usage"] = (
                "provider_usage.json"
            )
        self.config["condition_fingerprint"] = condition_fingerprint(
            self.config
        )
        self.outputs = self._outputs()
        self.stats = self._stats()
        self.audit = self._audit(condition_kind)
        self.write()

    @property
    def selected(self):
        by_id = {sample["sample_id"]: sample for sample in self.dataset}
        return [by_id[sample_id] for sample_id in self.sample_ids]

    def _outputs(self):
        outputs = []
        top_k = self.config["retrieval"]["top_k"]
        for sample in self.selected:
            contexts = _dialog_ids(sample)[:top_k]
            qas = []
            for qa in sample["qa"]:
                qas.append(
                    {
                        **copy.deepcopy(qa),
                        self.prediction_key: "fixture prediction",
                        f"{self.prediction_key}_context": list(contexts),
                        f"{self.model_key}_f1": 0.5,
                        f"{self.model_key}_recall": (
                            0.25 if qa["evidence"] else 1.0
                        ),
                    }
                )
            outputs.append({"sample_id": sample["sample_id"], "qa": qas})
        return outputs

    def _stats(self):
        counts = Counter()
        f1_sums = defaultdict(float)
        recall_sums = defaultdict(float)
        for sample in self.outputs:
            for qa in sample["qa"]:
                category = int(qa["category"])
                counts[category] += 1
                f1_sums[category] += qa[f"{self.model_key}_f1"]
                if qa["evidence"]:
                    recall_sums[category] += qa[f"{self.model_key}_recall"]
        return {
            self.model_key: {
                "category_counts": dict(counts),
                "cum_accuracy_by_category": dict(f1_sums),
                "recall_by_category": {
                    category: recall_sums[category] / count
                    for category, count in counts.items()
                },
            }
        }

    @staticmethod
    def _audit(condition_kind: str):
        if condition_kind == "official_dialog_reference":
            return {
                "mandatory_graph_constraint": "fail",
                "reporting_status": (
                    "non-compliant diagnostic/reference baseline"
                ),
                "qa_or_judge_inputs_used_for_graph_construction": False,
                "prompt_budget": {
                    "added_experiment_scaffold_chars": 0,
                    "limit_chars": 5000,
                    "pass": True,
                },
            }
        return {
            "mandatory_graph_constraint": "pass",
            "graph_construction": "conversation fields only",
            "excluded_from_graph_construction": [
                "QA questions",
                "QA answers",
                "QA evidence",
                "QA categories",
                "judge outputs",
                "previous predictions",
                "question-driven ledgers",
            ],
            "answer_recall": "EM graph retrieval",
            "prompt_budget": {
                "entity_scaffold_chars": 2410,
                "limit_chars": 5000,
                "pass": True,
            },
        }

    def write(self):
        self.config["condition_fingerprint"] = condition_fingerprint(
            self.config
        )
        values = {
            "run_config.json": self.config,
            "predictions.json": self.outputs,
            "stats.json": self.stats,
            "graph_audit.json": self.audit,
        }
        if self.config["condition_kind"] == "official_dialog_reference":
            expected = sum(len(sample["qa"]) for sample in self.selected)
            values["provider_usage.json"] = {
                "schema": "locomo_reader_provider_usage_v1",
                "status": "complete",
                "requested_model": "gpt-3.5-turbo",
                "actual_model": "gpt-3.5-turbo-0125",
                "expected_request_count": expected,
                "request_count": expected,
                "requested_model_counts": {
                    "gpt-3.5-turbo": expected,
                },
                "actual_model_counts": {
                    "gpt-3.5-turbo-0125": expected,
                },
                "input_tokens": expected * 10,
                "output_tokens": expected * 2,
                "total_tokens": expected * 12,
                "wall_seconds": float(expected),
                "token_source": "provider response usage",
            }
        else:
            expected = sum(len(sample["qa"]) for sample in self.selected)
            values["query_cache_usage.json"] = {
                "schema": "query_embedding_usage_v1",
                "qa_count": expected,
                "required_lookup_count": expected,
                "lookup_count": expected,
                "cache_hits": expected,
                "cache_misses": 0,
                "live_embedding_requests": 0,
                "status": "pass",
            }
        for name, value in values.items():
            (self.condition_dir / name).write_text(
                json.dumps(value, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def validate(self):
        return validate_formal_result(
            self.condition_dir,
            data_file=self.data_file,
        )


class FormalResultValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(
            (ROOT / "data" / "locomo10.json").read_text(encoding="utf-8")
        )

    def test_valid_all10_graph_result_passes_strict_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="all10",
                sample_ids=[sample["sample_id"] for sample in self.dataset],
            )
            report = fixture.validate()
            self.assertEqual(report["status"], "pass", report["errors"])
            self.assertEqual(
                report["counts"],
                {"samples": 10, "qa": 1986, "category5": 446},
            )
            self.assertTrue(report["paper_metric_eligible"])
            self.assertTrue(report["graph_claim_eligible"])

    def test_valid_preflight_is_not_paper_metric(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            report = fixture.validate()
            self.assertEqual(report["status"], "pass", report["errors"])
            self.assertEqual(
                report["counts"],
                {"samples": 1, "qa": 199, "category5": 47},
            )
            self.assertFalse(report["formal_all10"])
            self.assertFalse(report["paper_metric_eligible"])

    def test_relocated_result_fails_closed_without_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            write_relocation_manifest(fixture)
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(
                report["checks"]["output_directory_identity"]["pass"]
            )
            self.assertNotIn("relocation_identity", report["checks"])

    def test_relocated_result_passes_with_snapshot_bound_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            manifest_path = write_relocation_manifest(fixture)
            report = validate_formal_result(
                fixture.condition_dir,
                data_file=fixture.data_file,
                relocation_manifest=manifest_path,
            )
            self.assertEqual(report["status"], "pass", report["errors"])
            self.assertTrue(
                report["checks"]["relocation_identity"]["pass"]
            )
            self.assertEqual(
                report["checks"]["output_directory_identity"]["detail"][
                    "mode"
                ],
                "verified_relocation",
            )
            self.assertTrue(report["relocation"]["used"])
            self.assertEqual(
                report["relocation"]["manifest_sha256"],
                _sha256_file(manifest_path),
            )

    def test_relocation_manifest_rejects_artifact_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            manifest_path = write_relocation_manifest(fixture)
            prediction_path = fixture.condition_dir / "predictions.json"
            prediction_path.write_bytes(prediction_path.read_bytes() + b"\n")
            report = validate_formal_result(
                fixture.condition_dir,
                data_file=fixture.data_file,
                relocation_manifest=manifest_path,
            )
            self.assertEqual(report["status"], "fail")
            self.assertFalse(
                report["checks"]["relocation_identity"]["pass"]
            )
            self.assertFalse(
                report["checks"]["relocation_identity"]["detail"][
                    "artifacts"
                ]["prediction"]["pass"]
            )

    def test_relocation_manifest_rejects_snapshot_or_path_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            manifest_path = write_relocation_manifest(fixture)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_snapshot_result_sha256"] = "0" * 64
            manifest["relocated_condition_directory"] = str(
                fixture.root / "wrong"
            )
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            report = validate_formal_result(
                fixture.condition_dir,
                data_file=fixture.data_file,
                relocation_manifest=manifest_path,
            )
            self.assertEqual(report["status"], "fail")
            errors = report["checks"]["relocation_identity"]["detail"][
                "errors"
            ]
            self.assertTrue(
                any("SHA-256" in error for error in errors),
                errors,
            )
            self.assertTrue(
                any("current directory" in error for error in errors),
                errors,
            )

    def test_relocation_manifest_rejects_query_artifact_remap_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            manifest_path = write_relocation_manifest(fixture)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["external_artifacts"]["query_embedding_artifact"][
                "sha256"
            ] = "0" * 64
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            report = validate_formal_result(
                fixture.condition_dir,
                data_file=fixture.data_file,
                relocation_manifest=manifest_path,
            )
            self.assertEqual(report["status"], "fail")
            query_check = report["checks"]["relocation_identity"]["detail"][
                "external_artifacts"
            ]["query_embedding_artifact"]
            self.assertFalse(query_check["pass"])
            self.assertEqual(query_check["actual_sha256"], query_check[
                "configured_sha256"
            ])

    def test_official_reference_passes_but_is_not_graph_claim_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="all10",
                sample_ids=[sample["sample_id"] for sample in self.dataset],
                condition_kind="official_dialog_reference",
            )
            report = fixture.validate()
            self.assertEqual(report["status"], "pass", report["errors"])
            self.assertTrue(report["official_reference_eligible"])
            self.assertFalse(report["graph_claim_eligible"])
            self.assertFalse(report["paper_metric_eligible"])
            self.assertTrue(
                report["checks"][
                    "official_reader_provider_identity"
                ]["pass"]
            )

    def test_official_reference_rejects_reader_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="all10",
                sample_ids=[sample["sample_id"] for sample in self.dataset],
                condition_kind="official_dialog_reference",
            )
            usage_path = fixture.condition_dir / "provider_usage.json"
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
            usage["actual_model_counts"] = {"different-model": 1986}
            usage_path.write_text(json.dumps(usage), encoding="utf-8")
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(
                report["checks"][
                    "official_reader_provider_identity"
                ]["pass"]
            )

    def test_rejects_resume_overwrite_and_unproven_empty_start(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            fixture.config["resume"] = True
            fixture.config["overwrite"] = True
            fixture.config["command"] += " --overwrite"
            fixture.config["start_state"]["output_directory_empty"] = False
            fixture.write()
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(report["checks"]["empty_output_at_start"]["pass"])
            self.assertFalse(report["checks"]["no_resume_or_overwrite"]["pass"])

    def test_rejects_qa_reorder_missing_field_and_stats_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            fixture.outputs[0]["qa"][0], fixture.outputs[0]["qa"][1] = (
                fixture.outputs[0]["qa"][1],
                fixture.outputs[0]["qa"][0],
            )
            fixture.outputs[0]["qa"][2].pop(f"{fixture.model_key}_f1")
            fixture.stats[fixture.model_key]["category_counts"][1] += 1
            fixture.write()
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(
                report["checks"]["qa_order_and_source_fields"]["pass"]
            )
            self.assertFalse(
                report["checks"][
                    "prediction_metric_context_completeness"
                ]["pass"]
            )
            self.assertFalse(
                report["checks"]["official_stats_aggregation"]["pass"]
            )

    def test_rejects_short_duplicate_and_unknown_context_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
                top_k=3,
            )
            key = f"{fixture.prediction_key}_context"
            fixture.outputs[0]["qa"][0][key] = ["unknown"]
            valid = _dialog_ids(fixture.selected[0])[0]
            fixture.outputs[0]["qa"][1][key] = [valid, valid, valid]
            fixture.write()
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(report["checks"]["context_ids"]["pass"])

    def test_rejects_unexpected_file_and_fingerprint_change(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            fixture.config["retrieval"]["entity_weight"] = 0.1
            # Deliberately retain the old fingerprint.
            old_fingerprint = json.loads(
                (fixture.condition_dir / "run_config.json").read_text()
            )["condition_fingerprint"]
            (fixture.condition_dir / "run_config.json").write_text(
                json.dumps(
                    {**fixture.config, "condition_fingerprint": old_fingerprint},
                    indent=2,
                ),
                encoding="utf-8",
            )
            (fixture.condition_dir / "unrelated.json").write_text(
                "{}",
                encoding="utf-8",
            )
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(
                report["checks"]["condition_fingerprint"]["pass"]
            )
            self.assertFalse(
                report["checks"]["single_condition_directory"]["pass"]
            )

    def test_missing_artifact_and_unexpected_directory_return_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            (fixture.condition_dir / "predictions.json").unlink()
            (fixture.condition_dir / "unexpected").mkdir()
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertTrue(
                any("cannot read prediction" in error for error in report["errors"])
            )
            self.assertFalse(
                report["checks"]["single_condition_directory"]["pass"]
            )

    def test_rejects_graph_constraint_or_prompt_budget_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            fixture.audit["mandatory_graph_constraint"] = "fail"
            fixture.audit["prompt_budget"]["entity_scaffold_chars"] = 5001
            fixture.write()
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(
                report["checks"]["graph_and_prompt_audit"]["pass"]
            )

    def test_rejects_query_artifact_hash_and_runtime_miss(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = FormalResultFixture(
                Path(directory),
                self.dataset,
                scope="preflight",
                sample_ids=["conv-26"],
            )
            with fixture.query_artifact_path.open("ab") as handle:
                handle.write(b"tamper")
            usage_path = fixture.condition_dir / "query_cache_usage.json"
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
            usage["cache_misses"] = 1
            usage["status"] = "fail"
            usage_path.write_text(json.dumps(usage), encoding="utf-8")
            report = fixture.validate()
            self.assertEqual(report["status"], "fail")
            self.assertFalse(
                report["checks"][
                    "query_embedding_artifact_identity_and_coverage"
                ]["pass"]
            )
            self.assertFalse(
                report["checks"]["query_embedding_runtime_usage"]["pass"]
            )


if __name__ == "__main__":
    unittest.main()
