#!/usr/bin/env python3
"""Validate LoCoMo formal outputs without recalculating official metrics.

The frozen evaluator remains the sole owner of LoCoMo F1 and recall_acc.  This
tool verifies dataset/output identity, serialized-field completeness, official
stats aggregation, graph/prompt audits, and formal output isolation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shlex
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
)

ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = ROOT / "code"
sys.path.insert(0, str(CODE_DIR))

from em_graph import QueryEmbeddingArtifact

SCHEMA = "locomo_formal_run_v1"
REPORT_SCHEMA = "locomo_formal_validation_v1"
RELOCATION_SCHEMA = "locomo_formal_relocation_v1"
ALL10_QA_COUNT = 1986
ALL10_CATEGORY5_COUNT = 446
REQUIRED_CATEGORIES = {1, 2, 3, 4, 5}
CONDITION_KINDS = {"graph_method", "official_dialog_reference"}
SCOPES = {"all10", "preflight"}
FORBIDDEN_GRAPH_INPUTS = {
    "QA questions",
    "QA answers",
    "QA evidence",
    "QA categories",
    "judge outputs",
    "previous predictions",
    "question-driven ledgers",
}
REQUIRED_MODEL_KEYS = {
    "extraction",
    "embedding",
    "answer",
    "query_encoder",
    "context_encoder",
}
REQUIRED_RETRIEVAL_KEYS = {
    "variant",
    "rag_mode",
    "top_k",
    "entity_weight",
    "semantic_weight",
    "sequence_secondary_scale",
    "entity_min_rel_score",
    "entity_top_k_per_key",
    "who_only_dampen",
    "degree_discount",
}
REQUIRED_GRAPH_PROFILE_KEYS = {
    "memory_only",
    "use_caption",
    "use_time_annotations",
    "add_speaker_as_entity",
}
REQUIRED_ANSWER_PROTOCOL_KEYS = {
    "message_role",
    "temperature",
    "max_tokens",
    "batch_size",
    "category5_option_order",
}
REQUIRED_ARTIFACT_KEYS = {
    "prediction",
    "stats",
    "audit",
    "validation",
}
RELOCATION_REQUIRED_ARTIFACT_KEYS = {
    "run_config",
    "prediction",
    "stats",
    "audit",
}


class ValidationFailure(ValueError):
    """Raised only by callers that request exception-on-failure behavior."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def condition_identity(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Return every field that distinguishes one formal condition."""
    return {
        "schema": config.get("schema"),
        "run_id": config.get("run_id"),
        "condition_kind": config.get("condition_kind"),
        "scope": config.get("scope"),
        "dataset_sha256": config.get("dataset_sha256"),
        "sample_ids": config.get("sample_ids"),
        "models": config.get("models"),
        "retrieval": config.get("retrieval"),
        "graph_profile": config.get("graph_profile"),
        "answer_protocol": config.get("answer_protocol"),
        "cache_identity": config.get("cache_identity"),
        "official_upstream_commit": config.get("official_upstream_commit"),
        "source_commit": config.get("source_commit"),
    }


def condition_fingerprint(config: Mapping[str, Any]) -> str:
    return _canonical_sha256(condition_identity(config))


def _load_json(path: Path, errors: List[str], label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError, OSError) as exc:
        errors.append(f"cannot read {label} {path.name}: {exc}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {label} {path.name}: {exc}")
    return None


def _resolve_manifest_reference(value: Any, manifest_path: Path) -> Path:
    path = Path(str(value or ""))
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def _validate_relocation_manifest(
    config: Mapping[str, Any],
    *,
    condition_dir: Path,
    manifest_path: Path,
    errors: List[str],
    checks: MutableMapping[str, Any],
) -> Dict[str, Any]:
    """Verify a relocated result against an immutable pre-migration snapshot.

    Relocation never changes the historical run config.  It is accepted only
    when an explicit external manifest binds the original/current locations
    and every metric-critical artifact to a pre-existing snapshot.
    """
    manifest_path = manifest_path.resolve()
    local_errors: List[str] = []
    manifest = _load_json(
        manifest_path,
        local_errors,
        "relocation manifest",
    )
    if not isinstance(manifest, Mapping):
        detail = {
            "manifest": str(manifest_path),
            "errors": local_errors or ["manifest root must be an object"],
        }
        _record_check(
            checks,
            errors,
            "relocation_identity",
            False,
            detail,
        )
        return {"pass": False, **detail}

    configured_dir_text = str(config.get("output_directory") or "")
    configured_dir = Path(configured_dir_text).resolve()
    current_dir = condition_dir.resolve()
    if manifest.get("schema") != RELOCATION_SCHEMA:
        local_errors.append(
            "relocation manifest schema must be "
            f"{RELOCATION_SCHEMA!r}"
        )
    if manifest.get("reason") != "repository_root_changed":
        local_errors.append(
            "relocation reason must be 'repository_root_changed'"
        )
    if str(manifest.get("run_id") or "") != str(config.get("run_id") or ""):
        local_errors.append("relocation run_id does not match run config")
    if str(manifest.get("condition_fingerprint") or "") != str(
        config.get("condition_fingerprint") or ""
    ):
        local_errors.append(
            "relocation condition_fingerprint does not match run config"
        )
    if str(manifest.get("original_output_directory") or "") != (
        configured_dir_text
    ):
        local_errors.append(
            "relocation original_output_directory does not exactly match "
            "run config"
        )
    manifest_current = _resolve_manifest_reference(
        manifest.get("relocated_condition_directory"),
        manifest_path,
    )
    if manifest_current != current_dir:
        local_errors.append(
            "relocation current directory does not match condition directory"
        )
    if configured_dir == current_dir:
        local_errors.append(
            "relocation manifest is not valid when configured and actual "
            "directories already match"
        )

    snapshot_path = _resolve_manifest_reference(
        manifest.get("source_snapshot_result"),
        manifest_path,
    )
    snapshot = _load_json(
        snapshot_path,
        local_errors,
        "source snapshot result",
    )
    snapshot_sha = None
    if snapshot_path.is_file():
        snapshot_sha = sha256_file(snapshot_path)
        if snapshot_sha != str(
            manifest.get("source_snapshot_result_sha256") or ""
        ):
            local_errors.append(
                "source snapshot result SHA-256 does not match manifest"
            )
    if isinstance(snapshot, Mapping):
        snapshot_matches = {
            "schema": snapshot.get("schema")
            == "locomo_experiment_snapshot_v1",
            "run_id": snapshot.get("run_id") == config.get("run_id"),
            "condition_fingerprint": snapshot.get("condition_fingerprint")
            == config.get("condition_fingerprint"),
            "source_commit": snapshot.get("source_commit")
            == config.get("source_commit"),
            "dataset_sha256": snapshot.get("dataset_sha256")
            == config.get("dataset_sha256"),
        }
        for name, matched in snapshot_matches.items():
            if not matched:
                local_errors.append(
                    f"source snapshot {name} does not match run config"
                )
        snapshot_hashes = snapshot.get("artifact_hashes")
        if not isinstance(snapshot_hashes, Mapping):
            local_errors.append(
                "source snapshot artifact_hashes must be an object"
            )
            snapshot_hashes = {}
    else:
        snapshot_hashes = {}

    required_artifacts = set(RELOCATION_REQUIRED_ARTIFACT_KEYS)
    if config.get("condition_kind") == "graph_method":
        required_artifacts.add("query_cache_usage")
    else:
        required_artifacts.add("provider_usage")
    immutable = manifest.get("immutable_artifacts")
    if not isinstance(immutable, Mapping):
        local_errors.append(
            "relocation immutable_artifacts must be an object"
        )
        immutable = {}
    missing = sorted(required_artifacts - set(immutable))
    if missing:
        local_errors.append(
            f"relocation immutable_artifacts missing required keys: {missing}"
        )

    configured_artifacts = config.get("artifacts") or {}
    artifact_results: Dict[str, Any] = {}
    for key in sorted(required_artifacts):
        entry = immutable.get(key)
        if not isinstance(entry, Mapping):
            continue
        if key == "run_config":
            expected_name = "run_config.json"
        else:
            expected_name = str(configured_artifacts.get(key) or "")
        actual_name = str(entry.get("path") or "")
        expected_sha = str(entry.get("sha256") or "")
        if (
            not expected_name
            or actual_name != expected_name
            or Path(actual_name).name != actual_name
        ):
            local_errors.append(
                f"relocation artifact {key} path does not match run config"
            )
            continue
        source_sha = str(snapshot_hashes.get(key) or "")
        artifact_path = current_dir / actual_name
        actual_sha = (
            sha256_file(artifact_path) if artifact_path.is_file() else None
        )
        matched = (
            len(expected_sha) == 64
            and expected_sha == source_sha
            and expected_sha == actual_sha
        )
        artifact_results[key] = {
            "path": actual_name,
            "manifest_sha256": expected_sha,
            "source_snapshot_sha256": source_sha,
            "actual_sha256": actual_sha,
            "pass": matched,
        }
        if not matched:
            local_errors.append(
                f"relocation artifact {key} does not match source snapshot"
            )

    external_results: Dict[str, Any] = {}
    external = manifest.get("external_artifacts")
    if config.get("condition_kind") == "graph_method":
        query_identity = (
            (config.get("cache_identity") or {}).get(
                "query_embedding_artifact"
            )
            if isinstance(config.get("cache_identity"), Mapping)
            else None
        )
        query_entry = (
            external.get("query_embedding_artifact")
            if isinstance(external, Mapping)
            else None
        )
        if not isinstance(query_identity, Mapping):
            local_errors.append(
                "run config is missing query embedding artifact identity"
            )
        elif not isinstance(query_entry, Mapping):
            local_errors.append(
                "relocation external_artifacts must bind "
                "query_embedding_artifact"
            )
        else:
            original_path = str(query_entry.get("original_path") or "")
            configured_path = str(query_identity.get("path") or "")
            relocated_path = _resolve_manifest_reference(
                query_entry.get("relocated_path"),
                manifest_path,
            )
            entry_sha = str(query_entry.get("sha256") or "")
            configured_sha = str(query_identity.get("sha256") or "")
            actual_sha = (
                sha256_file(relocated_path)
                if relocated_path.is_file()
                else None
            )
            matched = (
                original_path == configured_path
                and len(entry_sha) == 64
                and entry_sha == configured_sha
                and entry_sha == actual_sha
            )
            external_results["query_embedding_artifact"] = {
                "original_path": original_path,
                "configured_path": configured_path,
                "relocated_path": str(relocated_path),
                "manifest_sha256": entry_sha,
                "configured_sha256": configured_sha,
                "actual_sha256": actual_sha,
                "pass": matched,
            }
            if not matched:
                local_errors.append(
                    "relocated query embedding artifact does not match "
                    "run config"
                )

    passed = not local_errors
    detail = {
        "manifest": str(manifest_path),
        "manifest_sha256": (
            sha256_file(manifest_path) if manifest_path.is_file() else None
        ),
        "source_snapshot_result": str(snapshot_path),
        "source_snapshot_result_sha256": snapshot_sha,
        "configured_original_directory": configured_dir_text,
        "relocated_condition_directory": str(current_dir),
        "artifacts": artifact_results,
        "external_artifacts": external_results,
        "errors": local_errors,
    }
    _record_check(
        checks,
        errors,
        "relocation_identity",
        passed,
        detail,
    )
    return {"pass": passed, **detail}


def _dialog_ids(sample: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    for key, dialogs in (sample.get("conversation") or {}).items():
        if (
            str(key).startswith("session_")
            and not str(key).endswith("_date_time")
            and isinstance(dialogs, list)
        ):
            ids.extend(
                str(dialog["dia_id"])
                for dialog in dialogs
                if isinstance(dialog, Mapping) and "dia_id" in dialog
            )
    return ids


def _record_check(
    checks: MutableMapping[str, Any],
    errors: List[str],
    name: str,
    passed: bool,
    detail: Any,
) -> None:
    checks[name] = {"pass": bool(passed), "detail": detail}
    if not passed:
        errors.append(f"{name}: {detail}")


def _validate_run_config(
    config: Mapping[str, Any],
    *,
    condition_dir: Path,
    data_path: Path,
    errors: List[str],
    checks: MutableMapping[str, Any],
    relocation: Optional[Mapping[str, Any]] = None,
) -> None:
    _record_check(
        checks,
        errors,
        "run_config_schema",
        config.get("schema") == SCHEMA,
        {"expected": SCHEMA, "actual": config.get("schema")},
    )
    run_id = str(config.get("run_id") or "")
    _record_check(
        checks,
        errors,
        "run_id_matches_directory",
        bool(run_id) and run_id == condition_dir.name,
        {"run_id": run_id, "directory": condition_dir.name},
    )
    _record_check(
        checks,
        errors,
        "condition_kind",
        config.get("condition_kind") in CONDITION_KINDS,
        config.get("condition_kind"),
    )
    _record_check(
        checks,
        errors,
        "scope",
        config.get("scope") in SCOPES,
        config.get("scope"),
    )
    source_commit = str(config.get("source_commit") or "")
    _record_check(
        checks,
        errors,
        "source_commit",
        len(source_commit) == 40
        and all(char in "0123456789abcdef" for char in source_commit),
        source_commit,
    )
    _record_check(
        checks,
        errors,
        "exact_command",
        bool(str(config.get("command") or "").strip()),
        config.get("command"),
    )
    _record_check(
        checks,
        errors,
        "start_time_recorded",
        bool(str(config.get("started_at") or "").strip()),
        config.get("started_at"),
    )
    resolved_dir = Path(str(config.get("output_directory") or "")).resolve()
    direct_directory_match = resolved_dir == condition_dir
    relocation_match = bool(relocation and relocation.get("pass"))
    _record_check(
        checks,
        errors,
        "output_directory_identity",
        direct_directory_match or relocation_match,
        {
            "mode": (
                "direct"
                if direct_directory_match
                else (
                    "verified_relocation"
                    if relocation_match
                    else "mismatch"
                )
            ),
            "configured": str(resolved_dir),
            "actual": str(condition_dir),
            "relocation_manifest_sha256": (
                relocation.get("manifest_sha256")
                if relocation_match
                else None
            ),
        },
    )
    start_state = config.get("start_state")
    valid_start = (
        isinstance(start_state, Mapping)
        and start_state.get("output_directory_empty") is True
        and start_state.get("existing_entries") == []
        and start_state.get("prediction_file_existed") is False
    )
    _record_check(
        checks,
        errors,
        "empty_output_at_start",
        valid_start,
        start_state,
    )
    no_resume = (
        config.get("resume") is False
        and config.get("overwrite") is False
        and "--overwrite"
        not in shlex.split(str(config.get("command") or ""))
    )
    _record_check(
        checks,
        errors,
        "no_resume_or_overwrite",
        no_resume,
        {
            "resume": config.get("resume"),
            "overwrite": config.get("overwrite"),
        },
    )
    actual_dataset_sha = sha256_file(data_path)
    _record_check(
        checks,
        errors,
        "dataset_sha256",
        config.get("dataset_sha256") == actual_dataset_sha,
        {
            "configured": config.get("dataset_sha256"),
            "actual": actual_dataset_sha,
        },
    )
    for name, required in (
        ("models", REQUIRED_MODEL_KEYS),
        ("retrieval", REQUIRED_RETRIEVAL_KEYS),
        ("graph_profile", REQUIRED_GRAPH_PROFILE_KEYS),
        ("answer_protocol", REQUIRED_ANSWER_PROTOCOL_KEYS),
    ):
        value = config.get(name)
        missing = sorted(required - set(value or {}))
        _record_check(
            checks,
            errors,
            f"resolved_{name}",
            isinstance(value, Mapping) and not missing,
            {"missing": missing, "value": value},
        )
    artifacts = config.get("artifacts")
    artifact_names = list((artifacts or {}).values())
    simple_names = all(
        isinstance(name, str)
        and name
        and Path(name).name == name
        for name in artifact_names
    )
    unique_names = len(set(artifact_names)) == len(artifact_names)
    required_artifacts = set(REQUIRED_ARTIFACT_KEYS)
    if config.get("condition_kind") == "graph_method":
        required_artifacts.add("query_cache_usage")
    missing_artifacts = sorted(required_artifacts - set(artifacts or {}))
    _record_check(
        checks,
        errors,
        "resolved_artifacts",
        isinstance(artifacts, Mapping)
        and not missing_artifacts
        and simple_names
        and unique_names,
        {
            "missing": missing_artifacts,
            "simple_names": simple_names,
            "unique_names": unique_names,
            "artifacts": artifacts,
        },
    )
    expected_fingerprint = condition_fingerprint(config)
    _record_check(
        checks,
        errors,
        "condition_fingerprint",
        config.get("condition_fingerprint") == expected_fingerprint,
        {
            "configured": config.get("condition_fingerprint"),
            "expected": expected_fingerprint,
        },
    )


def _validate_directory_contents(
    condition_dir: Path,
    config: Mapping[str, Any],
    *,
    errors: List[str],
    checks: MutableMapping[str, Any],
) -> None:
    artifacts = config.get("artifacts") or {}
    allowed = {"run_config.json", *artifacts.values()}
    actual = {path.name for path in condition_dir.iterdir()}
    validation_name = artifacts.get("validation")
    allowed_before_report = allowed - ({validation_name} if validation_name else set())
    valid = actual == allowed or actual == allowed_before_report
    _record_check(
        checks,
        errors,
        "single_condition_directory",
        valid,
        {
            "actual": sorted(actual),
            "allowed_before_or_after_validation": sorted(allowed),
        },
    )


def _validate_official_provider_usage(
    condition_dir: Path,
    config: Mapping[str, Any],
    expected_samples: Sequence[Mapping[str, Any]],
    *,
    errors: List[str],
    checks: MutableMapping[str, Any],
) -> None:
    if config.get("condition_kind") != "official_dialog_reference":
        return
    artifacts = config.get("artifacts") or {}
    name = artifacts.get("provider_usage")
    usage = (
        _load_json(
            condition_dir / str(name or ""),
            errors,
            "provider_usage",
        )
        if name
        else None
    )
    expected_requests = sum(
        len(sample.get("qa") or []) for sample in expected_samples
    )
    models = config.get("models") or {}
    actual_counts = (
        usage.get("actual_model_counts")
        if isinstance(usage, Mapping)
        else None
    )
    requested_model = (
        usage.get("requested_model")
        if isinstance(usage, Mapping)
        else None
    )
    actual_model = (
        usage.get("actual_model")
        if isinstance(usage, Mapping)
        else None
    )
    model_family_matches = (
        isinstance(requested_model, str)
        and isinstance(actual_model, str)
        and (
            actual_model == requested_model
            or actual_model.startswith(f"{requested_model}-")
        )
    )
    valid = (
        bool(name)
        and isinstance(usage, Mapping)
        and usage.get("schema") == "locomo_reader_provider_usage_v1"
        and usage.get("status") == "complete"
        and requested_model == models.get("answer")
        and usage.get("expected_request_count") == expected_requests
        and usage.get("request_count") == expected_requests
        and isinstance(actual_counts, Mapping)
        and len(actual_counts) == 1
        and actual_model == models.get("answer_actual")
        and actual_counts.get(actual_model) == expected_requests
        and model_family_matches
    )
    _record_check(
        checks,
        errors,
        "official_reader_provider_identity",
        valid,
        {
            "artifact": name,
            "expected_requests": expected_requests,
            "requested_model": requested_model,
            "configured_answer": models.get("answer"),
            "actual_model": actual_model,
            "configured_actual_model": models.get("answer_actual"),
            "actual_model_counts": actual_counts,
            "model_family_matches": model_family_matches,
        },
    )


def _validate_query_embedding_artifact(
    condition_dir: Path,
    config: Mapping[str, Any],
    dataset: Sequence[Mapping[str, Any]],
    expected_samples: Sequence[Mapping[str, Any]],
    *,
    errors: List[str],
    checks: MutableMapping[str, Any],
    relocation: Optional[Mapping[str, Any]] = None,
) -> None:
    if config.get("condition_kind") != "graph_method":
        return
    cache_identity = config.get("cache_identity")
    identity = (
        cache_identity.get("query_embedding_artifact")
        if isinstance(cache_identity, Mapping)
        else None
    )
    models = config.get("models") or {}
    valid = False
    detail: Dict[str, Any] = {"configured": identity}
    try:
        if not isinstance(identity, Mapping):
            raise ValueError("missing query embedding artifact identity")
        configured_path = Path(
            str(identity.get("path") or "")
        ).resolve()
        relocated_query = (
            (relocation.get("external_artifacts") or {}).get(
                "query_embedding_artifact"
            )
            if relocation and relocation.get("pass")
            else None
        )
        path = (
            Path(str(relocated_query.get("relocated_path"))).resolve()
            if isinstance(relocated_query, Mapping)
            and relocated_query.get("pass")
            else configured_path
        )
        artifact = QueryEmbeddingArtifact.load(path)
        artifact.validate_exact_dataset(
            dataset,
            dataset_sha256=str(config.get("dataset_sha256") or ""),
            model_name=str(models.get("embedding") or ""),
            role=str(identity.get("role") or ""),
            normalization=str(identity.get("normalization") or ""),
        )
        actual_identity = artifact.identity(path)
        expected_runtime_identity = dict(identity)
        expected_runtime_identity["path"] = str(path)
        valid = expected_runtime_identity == actual_identity
        detail["configured_path"] = str(configured_path)
        detail["effective_path"] = str(path)
        detail["actual"] = actual_identity
        if not valid:
            raise ValueError("query artifact configured identity mismatch")
    except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
        detail["error"] = str(exc)
    _record_check(
        checks,
        errors,
        "query_embedding_artifact_identity_and_coverage",
        valid,
        detail,
    )

    artifacts = config.get("artifacts") or {}
    usage_name = artifacts.get("query_cache_usage")
    usage = (
        _load_json(
            condition_dir / str(usage_name or ""),
            errors,
            "query_cache_usage",
        )
        if usage_name
        else None
    )
    qa_count = sum(len(sample.get("qa") or []) for sample in expected_samples)
    semantic_enabled = float(
        (config.get("retrieval") or {}).get("semantic_weight") or 0.0
    ) != 0.0
    required_lookups = qa_count if semantic_enabled else 0
    usage_valid = (
        isinstance(usage, Mapping)
        and usage.get("schema") == "query_embedding_usage_v1"
        and usage.get("status") == "pass"
        and usage.get("qa_count") == qa_count
        and usage.get("required_lookup_count") == required_lookups
        and int(usage.get("lookup_count") or 0) >= required_lookups
        and int(usage.get("cache_hits") or 0) >= required_lookups
        and usage.get("cache_misses") == 0
        and usage.get("live_embedding_requests") == 0
    )
    _record_check(
        checks,
        errors,
        "query_embedding_runtime_usage",
        usage_valid,
        {
            "artifact": usage_name,
            "expected_qa": qa_count,
            "required_lookups": required_lookups,
            "usage": usage,
        },
    )


def _select_dataset(
    dataset: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    *,
    errors: List[str],
    checks: MutableMapping[str, Any],
) -> List[Mapping[str, Any]]:
    by_id = {str(sample.get("sample_id") or ""): sample for sample in dataset}
    sample_ids = config.get("sample_ids")
    if not isinstance(sample_ids, list) or not sample_ids:
        _record_check(
            checks,
            errors,
            "sample_scope",
            False,
            "sample_ids must be a non-empty ordered list",
        )
        return []
    missing = [sample_id for sample_id in sample_ids if sample_id not in by_id]
    selected = [by_id[sample_id] for sample_id in sample_ids if sample_id in by_id]
    scope = config.get("scope")
    all10_ids = [str(sample.get("sample_id") or "") for sample in dataset]
    scope_valid = (
        (
            scope == "all10"
            and sample_ids == all10_ids
            and len(sample_ids) == 10
        )
        or (scope == "preflight" and not missing)
    )
    _record_check(
        checks,
        errors,
        "sample_scope",
        scope_valid and not missing,
        {
            "scope": scope,
            "sample_ids": sample_ids,
            "missing": missing,
            "dataset_ids": all10_ids,
        },
    )
    return selected


def _validate_predictions(
    outputs: Any,
    expected_samples: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    *,
    errors: List[str],
    checks: MutableMapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(outputs, list):
        _record_check(
            checks,
            errors,
            "prediction_shape",
            False,
            "prediction root must be a list",
        )
        return {}
    expected_ids = [str(sample["sample_id"]) for sample in expected_samples]
    actual_ids = [
        str(sample.get("sample_id") or "")
        for sample in outputs
        if isinstance(sample, Mapping)
    ]
    _record_check(
        checks,
        errors,
        "sample_order",
        len(outputs) == len(expected_samples) and actual_ids == expected_ids,
        {"expected": expected_ids, "actual": actual_ids},
    )
    retrieval = config.get("retrieval") or {}
    top_k = int(retrieval.get("top_k") or 0)
    model_key = str(config.get("model_key") or "")
    prediction_key = str(config.get("prediction_key") or "")
    f1_key = f"{model_key}_f1"
    recall_key = f"{model_key}_recall"
    context_key = f"{prediction_key}_context"
    required_keys_valid = (
        bool(model_key)
        and prediction_key == f"{model_key}_prediction"
        and top_k > 0
    )
    _record_check(
        checks,
        errors,
        "metric_key_identity",
        required_keys_valid,
        {
            "model_key": model_key,
            "prediction_key": prediction_key,
            "top_k": top_k,
        },
    )

    qa_count = 0
    category5_count = 0
    missing_fields: List[str] = []
    qa_mismatches: List[str] = []
    context_errors: List[str] = []
    category_counts: Counter[int] = Counter()
    f1_sums: MutableMapping[int, float] = defaultdict(float)
    recall_sums: MutableMapping[int, float] = defaultdict(float)
    row_records: List[Dict[str, Any]] = []

    for sample_index, expected_sample in enumerate(expected_samples):
        if sample_index >= len(outputs) or not isinstance(
            outputs[sample_index], Mapping
        ):
            continue
        output_sample = outputs[sample_index]
        output_qas = output_sample.get("qa")
        expected_qas = expected_sample.get("qa") or []
        if not isinstance(output_qas, list):
            qa_mismatches.append(f"{expected_sample['sample_id']}: qa is not a list")
            continue
        if len(output_qas) != len(expected_qas):
            qa_mismatches.append(
                f"{expected_sample['sample_id']}: expected {len(expected_qas)} "
                f"QA, got {len(output_qas)}"
            )
        valid_ids = set(_dialog_ids(expected_sample))
        expected_context_count = min(top_k, len(valid_ids))
        for qa_index, expected_qa in enumerate(expected_qas):
            if qa_index >= len(output_qas) or not isinstance(
                output_qas[qa_index], Mapping
            ):
                continue
            row = output_qas[qa_index]
            qa_count += 1
            category = int(expected_qa["category"])
            category_counts[category] += 1
            category5_count += int(category == 5)
            for source_key in ("question", "answer", "category", "evidence"):
                if row.get(source_key) != expected_qa.get(source_key):
                    qa_mismatches.append(
                        f"{expected_sample['sample_id']}[{qa_index}] "
                        f"{source_key} mismatch"
                    )
            for required_key in (
                prediction_key,
                f1_key,
                recall_key,
                context_key,
            ):
                if required_key not in row:
                    missing_fields.append(
                        f"{expected_sample['sample_id']}[{qa_index}] "
                        f"missing {required_key}"
                    )
            contexts = row.get(context_key)
            if isinstance(contexts, list):
                normalized_contexts = [str(value) for value in contexts]
                duplicates = [
                    value
                    for value, count in Counter(normalized_contexts).items()
                    if count > 1
                ]
                unknown = sorted(set(normalized_contexts) - valid_ids)
                if len(contexts) != expected_context_count:
                    context_errors.append(
                        f"{expected_sample['sample_id']}[{qa_index}] "
                        f"expected {expected_context_count} contexts, "
                        f"got {len(contexts)}"
                    )
                if duplicates:
                    context_errors.append(
                        f"{expected_sample['sample_id']}[{qa_index}] "
                        f"duplicate contexts {duplicates}"
                    )
                if unknown:
                    context_errors.append(
                        f"{expected_sample['sample_id']}[{qa_index}] "
                        f"unknown contexts {unknown}"
                    )
            else:
                context_errors.append(
                    f"{expected_sample['sample_id']}[{qa_index}] "
                    f"{context_key} is not a list"
                )
            try:
                f1_value = float(row[f1_key])
                recall_value = float(row[recall_key])
                if not math.isfinite(f1_value) or not 0.0 <= f1_value <= 1.0:
                    raise ValueError
                if (
                    not math.isfinite(recall_value)
                    or not 0.0 <= recall_value <= 1.0
                ):
                    raise ValueError
                f1_sums[category] += f1_value
                if expected_qa.get("evidence"):
                    recall_sums[category] += recall_value
                row_records.append(
                    {
                        "sample_id": str(expected_sample["sample_id"]),
                        "qa_index": qa_index,
                        "category": category,
                        "f1": f1_value,
                        "recall": recall_value,
                        "has_evidence": bool(expected_qa.get("evidence")),
                    }
                )
            except (KeyError, TypeError, ValueError):
                missing_fields.append(
                    f"{expected_sample['sample_id']}[{qa_index}] "
                    "invalid F1/recall value"
                )

    expected_qa_count = sum(
        len(sample.get("qa") or []) for sample in expected_samples
    )
    expected_category5 = sum(
        int(int(qa["category"]) == 5)
        for sample in expected_samples
        for qa in sample.get("qa") or []
    )
    scope = config.get("scope")
    formal_counts_valid = (
        scope != "all10"
        or expected_qa_count == ALL10_QA_COUNT
        and expected_category5 == ALL10_CATEGORY5_COUNT
        and len(expected_samples) == 10
    )
    _record_check(
        checks,
        errors,
        "formal_all10_counts",
        formal_counts_valid
        and qa_count == expected_qa_count
        and category5_count == expected_category5,
        {
            "scope": scope,
            "samples": len(expected_samples),
            "qa": qa_count,
            "expected_qa": expected_qa_count,
            "category5": category5_count,
            "expected_category5": expected_category5,
        },
    )
    _record_check(
        checks,
        errors,
        "qa_order_and_source_fields",
        not qa_mismatches,
        qa_mismatches[:20],
    )
    _record_check(
        checks,
        errors,
        "prediction_metric_context_completeness",
        not missing_fields,
        missing_fields[:20],
    )
    _record_check(
        checks,
        errors,
        "context_ids",
        not context_errors,
        context_errors[:20],
    )
    _record_check(
        checks,
        errors,
        "categories_present",
        set(category_counts) == REQUIRED_CATEGORIES,
        dict(category_counts),
    )
    return {
        "qa_count": qa_count,
        "category5_count": category5_count,
        "category_counts": dict(category_counts),
        "f1_sums": dict(f1_sums),
        "recall_sums": dict(recall_sums),
        "row_records": row_records,
    }


def _mapping_with_int_keys(value: Mapping[str, Any]) -> Dict[int, Any]:
    return {int(key): item for key, item in value.items()}


def _close_mapping(
    actual: Mapping[int, Any],
    expected: Mapping[int, Any],
    *,
    tolerance: float = 1e-12,
) -> bool:
    if set(actual) != set(expected):
        return False
    return all(
        math.isclose(
            float(actual[key]),
            float(expected[key]),
            rel_tol=0.0,
            abs_tol=tolerance,
        )
        for key in expected
    )


def _validate_stats(
    stats: Any,
    aggregates: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    errors: List[str],
    checks: MutableMapping[str, Any],
) -> None:
    model_key = str(config.get("model_key") or "")
    block = stats.get(model_key) if isinstance(stats, Mapping) else None
    if not isinstance(block, Mapping):
        available = sorted(stats.keys()) if isinstance(stats, Mapping) else []
        _record_check(
            checks,
            errors,
            "official_stats_key",
            False,
            {"expected": model_key, "available": available},
        )
        return
    _record_check(
        checks,
        errors,
        "official_stats_key",
        True,
        model_key,
    )
    try:
        actual_counts = _mapping_with_int_keys(block["category_counts"])
        actual_f1 = _mapping_with_int_keys(block["cum_accuracy_by_category"])
        actual_recall_means = _mapping_with_int_keys(block["recall_by_category"])
    except (KeyError, TypeError, ValueError):
        _record_check(
            checks,
            errors,
            "official_stats_aggregation",
            False,
            "missing or invalid official stats mappings",
        )
        return
    expected_counts = {
        int(key): int(value)
        for key, value in aggregates.get("category_counts", {}).items()
    }
    expected_f1 = {
        int(key): float(value)
        for key, value in aggregates.get("f1_sums", {}).items()
    }
    expected_recall_means = {
        category: float(aggregates.get("recall_sums", {}).get(category, 0.0))
        / count
        for category, count in expected_counts.items()
    }
    stats_valid = (
        actual_counts == expected_counts
        and _close_mapping(actual_f1, expected_f1)
        and _close_mapping(actual_recall_means, expected_recall_means)
    )
    _record_check(
        checks,
        errors,
        "official_stats_aggregation",
        stats_valid,
        {
            "counts": actual_counts,
            "expected_counts": expected_counts,
            "f1_sums": actual_f1,
            "expected_f1_sums": expected_f1,
            "recall_means": actual_recall_means,
            "expected_recall_means": expected_recall_means,
        },
    )


def _validate_audit(
    audit: Any,
    config: Mapping[str, Any],
    *,
    errors: List[str],
    checks: MutableMapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(audit, Mapping):
        _record_check(
            checks,
            errors,
            "graph_and_prompt_audit",
            False,
            "audit root must be an object",
        )
        return {"graph_claim_eligible": False}
    prompt = audit.get("prompt_budget")
    prompt_pass = (
        isinstance(prompt, Mapping)
        and prompt.get("pass") is True
        and int(prompt.get("limit_chars") or 0) <= 5000
        and int(
            prompt.get(
                "entity_scaffold_chars",
                prompt.get("added_experiment_scaffold_chars", 0),
            )
            or 0
        )
        <= int(prompt.get("limit_chars") or 0)
    )
    kind = config.get("condition_kind")
    if kind == "graph_method":
        excluded = set(audit.get("excluded_from_graph_construction") or [])
        graph_pass = (
            audit.get("mandatory_graph_constraint") == "pass"
            and FORBIDDEN_GRAPH_INPUTS.issubset(excluded)
            and "graph" in str(audit.get("answer_recall") or "").lower()
        )
        graph_claim_eligible = graph_pass
    else:
        graph_pass = (
            audit.get("mandatory_graph_constraint") == "fail"
            and "non-compliant"
            in str(audit.get("reporting_status") or "").lower()
            and audit.get("qa_or_judge_inputs_used_for_graph_construction")
            is False
        )
        graph_claim_eligible = False
    _record_check(
        checks,
        errors,
        "graph_and_prompt_audit",
        graph_pass and prompt_pass,
        {
            "condition_kind": kind,
            "mandatory_graph_constraint": audit.get(
                "mandatory_graph_constraint"
            ),
            "prompt_budget": prompt,
            "graph_claim_eligible": graph_claim_eligible,
        },
    )
    return {"graph_claim_eligible": graph_claim_eligible}


def validate_formal_result(
    condition_dir: Path,
    *,
    data_file: Path,
    relocation_manifest: Optional[Path] = None,
) -> Dict[str, Any]:
    condition_dir = condition_dir.resolve()
    data_file = data_file.resolve()
    errors: List[str] = []
    checks: Dict[str, Any] = {}
    if not condition_dir.is_dir():
        return {
            "schema": REPORT_SCHEMA,
            "status": "fail",
            "condition_directory": str(condition_dir),
            "errors": ["condition directory does not exist"],
            "checks": {},
        }
    config_path = condition_dir / "run_config.json"
    config = _load_json(config_path, errors, "run_config")
    if not isinstance(config, Mapping):
        return {
            "schema": REPORT_SCHEMA,
            "status": "fail",
            "condition_directory": str(condition_dir),
            "errors": errors or ["run_config root must be an object"],
            "checks": checks,
        }
    configured_dir = Path(
        str(config.get("output_directory") or "")
    ).resolve()
    relocation: Optional[Dict[str, Any]] = None
    if relocation_manifest is not None:
        relocation = _validate_relocation_manifest(
            config,
            condition_dir=condition_dir,
            manifest_path=relocation_manifest,
            errors=errors,
            checks=checks,
        )
    elif configured_dir != condition_dir:
        relocation = {
            "pass": False,
            "manifest_sha256": None,
        }
    _validate_run_config(
        config,
        condition_dir=condition_dir,
        data_path=data_file,
        errors=errors,
        checks=checks,
        relocation=relocation,
    )
    _validate_directory_contents(
        condition_dir,
        config,
        errors=errors,
        checks=checks,
    )
    dataset = _load_json(data_file, errors, "dataset")
    if not isinstance(dataset, list):
        errors.append("dataset root must be a list")
        dataset = []
    expected_samples = _select_dataset(
        dataset,
        config,
        errors=errors,
        checks=checks,
    )
    _validate_query_embedding_artifact(
        condition_dir,
        config,
        dataset,
        expected_samples,
        errors=errors,
        checks=checks,
        relocation=relocation,
    )
    _validate_official_provider_usage(
        condition_dir,
        config,
        expected_samples,
        errors=errors,
        checks=checks,
    )
    artifacts = config.get("artifacts") or {}
    predictions = _load_json(
        condition_dir / str(artifacts.get("prediction") or ""),
        errors,
        "prediction",
    )
    stats = _load_json(
        condition_dir / str(artifacts.get("stats") or ""),
        errors,
        "stats",
    )
    audit = _load_json(
        condition_dir / str(artifacts.get("audit") or ""),
        errors,
        "audit",
    )
    aggregates = _validate_predictions(
        predictions,
        expected_samples,
        config,
        errors=errors,
        checks=checks,
    )
    _validate_stats(
        stats,
        aggregates,
        config,
        errors=errors,
        checks=checks,
    )
    audit_result = _validate_audit(
        audit,
        config,
        errors=errors,
        checks=checks,
    )
    scope = config.get("scope")
    status = "pass" if not errors else "fail"
    artifact_hashes = {}
    for key in ("prediction", "stats", "audit", "provider_usage"):
        name = artifacts.get(key)
        path = condition_dir / str(name or "")
        if name and path.is_file():
            artifact_hashes[key] = {
                "path": name,
                "sha256": sha256_file(path),
            }
    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "run_id": config.get("run_id"),
        "condition_fingerprint": config.get("condition_fingerprint"),
        "condition_directory": str(condition_dir),
        "relocation": (
            {
                "used": bool(relocation and relocation.get("pass")),
                "manifest": (
                    relocation.get("manifest") if relocation else None
                ),
                "manifest_sha256": (
                    relocation.get("manifest_sha256")
                    if relocation
                    else None
                ),
                "source_snapshot_result": (
                    relocation.get("source_snapshot_result")
                    if relocation
                    else None
                ),
                "source_snapshot_result_sha256": (
                    relocation.get("source_snapshot_result_sha256")
                    if relocation
                    else None
                ),
            }
            if relocation_manifest is not None
            else {"used": False}
        ),
        "scope": scope,
        "formal_all10": scope == "all10",
        "paper_metric_eligible": (
            status == "pass"
            and scope == "all10"
            and bool(audit_result.get("graph_claim_eligible"))
        ),
        "official_reference_eligible": (
            status == "pass"
            and scope == "all10"
            and config.get("condition_kind") == "official_dialog_reference"
        ),
        "graph_claim_eligible": bool(
            audit_result.get("graph_claim_eligible")
        ),
        "counts": {
            "samples": len(expected_samples),
            "qa": aggregates.get("qa_count", 0),
            "category5": aggregates.get("category5_count", 0),
        },
        "artifact_hashes": artifact_hashes,
        "checks": checks,
        "errors": errors,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition-dir", type=Path, required=True)
    parser.add_argument(
        "--data-file",
        type=Path,
        default=ROOT / "data" / "locomo10.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help=(
            "write report here; defaults to the validation artifact named "
            "by run_config.json"
        ),
    )
    parser.add_argument(
        "--relocation-manifest",
        type=Path,
        help=(
            "explicit external proof for a result copied from the immutable "
            "output directory recorded in run_config.json"
        ),
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    condition_dir = args.condition_dir.resolve()
    report = validate_formal_result(
        condition_dir,
        data_file=args.data_file,
        relocation_manifest=args.relocation_manifest,
    )
    report_path = args.report
    if args.relocation_manifest is not None and report_path is None:
        raise ValueError(
            "--report outside the condition directory is required when "
            "--relocation-manifest is used"
        )
    if report_path is None:
        config = json.loads(
            (condition_dir / "run_config.json").read_text(encoding="utf-8")
        )
        report_path = condition_dir / config["artifacts"]["validation"]
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
