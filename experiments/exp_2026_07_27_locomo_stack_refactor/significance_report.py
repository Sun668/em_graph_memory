#!/usr/bin/env python3
"""Paired significance analysis over immutable official LoCoMo row metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from validate_formal_result import sha256_file, validate_formal_result

SEED = 20260727
DEFAULT_RESAMPLES = 10_000
REPORT_SCHEMA = "locomo_significance_v1"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _metric_rows(
    condition_dir: Path,
    *,
    data_file: Path,
    relocation_manifest: Optional[Path] = None,
) -> Tuple[Mapping[str, Any], List[Dict[str, Any]], Mapping[str, Any]]:
    validation = validate_formal_result(
        condition_dir,
        data_file=data_file,
        relocation_manifest=relocation_manifest,
    )
    if validation["status"] != "pass":
        raise ValueError(
            f"formal validation failed for {condition_dir}: "
            f"{validation['errors']}"
        )
    config_path = condition_dir / "run_config.json"
    config = _read_json(config_path)
    artifacts = config["artifacts"]
    prediction_path = condition_dir / artifacts["prediction"]
    stats_path = condition_dir / artifacts["stats"]
    outputs = _read_json(prediction_path)
    stats = _read_json(stats_path)
    model_key = str(config["model_key"])
    prediction_key = str(config["prediction_key"])
    f1_key = f"{model_key}_f1"
    recall_key = f"{model_key}_recall"
    context_key = f"{prediction_key}_context"
    rows: List[Dict[str, Any]] = []
    for sample in outputs:
        sample_id = str(sample["sample_id"])
        for qa_index, qa in enumerate(sample["qa"]):
            serialized_recall = float(qa[recall_key])
            rows.append(
                {
                    "sample_id": sample_id,
                    "qa_index": qa_index,
                    "question": qa["question"],
                    "answer": qa["answer"],
                    "evidence": qa["evidence"],
                    "category": int(qa["category"]),
                    "f1": float(qa[f1_key]),
                    "recall_serialized": serialized_recall,
                    "recall": (
                        serialized_recall if bool(qa["evidence"]) else 0.0
                    ),
                    "context_ids": list(qa[context_key]),
                }
            )
    recall_audit = _recall_aggregation_audit(rows, stats[model_key])
    identity = {
        "directory": str(condition_dir.resolve()),
        "run_id": config["run_id"],
        "condition_fingerprint": config["condition_fingerprint"],
        "prediction_sha256": sha256_file(prediction_path),
        "stats_sha256": sha256_file(stats_path),
        "validation_status": validation["status"],
        "relocation": validation.get("relocation", {"used": False}),
        "recall_aggregation_audit": recall_audit,
    }
    return config, rows, identity


def official_recall_contribution(row: Mapping[str, Any]) -> float:
    """Return the contribution used by official aggregate recall_acc.

    Empty-evidence QA rows remain in the denominator but contribute zero,
    regardless of the serialized row-level recall value.
    """
    serialized = float(row.get("recall_serialized", row["recall"]))
    return serialized if bool(row.get("evidence")) else 0.0


def recall_means_by_category(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[int, float]:
    counts: Dict[int, int] = {}
    sums: Dict[int, float] = {}
    for row in rows:
        category = int(row["category"])
        counts[category] = counts.get(category, 0) + 1
        sums[category] = sums.get(category, 0.0) + (
            official_recall_contribution(row)
        )
    return {
        category: sums.get(category, 0.0) / count
        for category, count in counts.items()
    }


def _recall_aggregation_audit(
    rows: Sequence[Mapping[str, Any]],
    stats_block: Mapping[str, Any],
) -> Dict[str, Any]:
    official_means = {
        int(category): float(value)
        for category, value in stats_block["recall_by_category"].items()
    }
    contribution_means = recall_means_by_category(rows)
    raw_sums: Dict[int, float] = {}
    counts: Dict[int, int] = {}
    empty_evidence_counts: Dict[int, int] = {}
    for row in rows:
        category = int(row["category"])
        counts[category] = counts.get(category, 0) + 1
        raw_sums[category] = raw_sums.get(category, 0.0) + float(
            row["recall_serialized"]
        )
        if not row["evidence"]:
            empty_evidence_counts[category] = (
                empty_evidence_counts.get(category, 0) + 1
            )
    raw_means = {
        category: raw_sums[category] / counts[category]
        for category in counts
    }
    matches = set(official_means) == set(contribution_means) and all(
        math.isclose(
            official_means[category],
            contribution_means[category],
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        for category in official_means
    )
    if not matches:
        raise ValueError(
            "official recall contribution does not match official stats: "
            f"computed={contribution_means}, stats={official_means}"
        )
    return {
        "policy": (
            "serialized recall when evidence is non-empty; otherwise 0; "
            "all QA rows remain in the denominator"
        ),
        "raw_serialized_recall_means": raw_means,
        "official_contribution_means": contribution_means,
        "official_stats_recall_means": official_means,
        "empty_evidence_counts": empty_evidence_counts,
        "matches_official_stats": True,
    }


def _assert_matched(
    a_config: Mapping[str, Any],
    b_config: Mapping[str, Any],
    a_rows: Sequence[Mapping[str, Any]],
    b_rows: Sequence[Mapping[str, Any]],
) -> None:
    if (
        a_config.get("condition_kind") != "graph_method"
        or b_config.get("condition_kind") != "graph_method"
    ):
        raise ValueError("paired method significance requires graph_method runs")
    matched_fields = {
        "dataset_sha256": (
            a_config.get("dataset_sha256"),
            b_config.get("dataset_sha256"),
        ),
        "scope": (a_config.get("scope"), b_config.get("scope")),
        "sample_ids": (a_config.get("sample_ids"), b_config.get("sample_ids")),
        "top_k": (
            (a_config.get("retrieval") or {}).get("top_k"),
            (b_config.get("retrieval") or {}).get("top_k"),
        ),
        "embedding_model": (
            (a_config.get("models") or {}).get("embedding"),
            (b_config.get("models") or {}).get("embedding"),
        ),
        "answer_model": (
            (a_config.get("models") or {}).get("answer"),
            (b_config.get("models") or {}).get("answer"),
        ),
        "answer_protocol": (
            a_config.get("answer_protocol"),
            b_config.get("answer_protocol"),
        ),
    }
    mismatches = {
        key: values
        for key, values in matched_fields.items()
        if values[0] != values[1]
    }
    if mismatches:
        raise ValueError(f"conditions are not matched: {mismatches}")
    if len(a_rows) != len(b_rows):
        raise ValueError("paired conditions have different row counts")
    source_fields = (
        "sample_id",
        "qa_index",
        "question",
        "answer",
        "evidence",
        "category",
    )
    for index, (a_row, b_row) in enumerate(zip(a_rows, b_rows)):
        if any(a_row[key] != b_row[key] for key in source_fields):
            raise ValueError(f"paired row identity mismatch at index {index}")


def assert_ordered_context_equality(
    a_rows: Sequence[Mapping[str, Any]],
    b_embed_rows: Sequence[Mapping[str, Any]],
) -> None:
    """Require exact A/B_embed retrieval equality for every paired QA."""
    if len(a_rows) != len(b_embed_rows):
        raise ValueError("dense-control row count mismatch")
    source_fields = (
        "sample_id",
        "qa_index",
        "question",
        "answer",
        "evidence",
        "category",
    )
    for index, (a_row, b_row) in enumerate(zip(a_rows, b_embed_rows)):
        if any(a_row[key] != b_row[key] for key in source_fields):
            raise ValueError(
                f"dense-control sample/QA order mismatch at index {index}"
            )
        a_contexts = list(a_row["context_ids"])
        b_contexts = list(b_row["context_ids"])
        if a_contexts == b_contexts:
            continue
        if sorted(a_contexts) == sorted(b_contexts):
            reason = "context order mismatch"
        else:
            reason = "context id mismatch"
        raise ValueError(
            f"dense-control {reason} at "
            f"{a_row['sample_id']}[{a_row['qa_index']}]: "
            f"A={a_contexts}, B_embed={b_contexts}"
        )


def assert_same_query_embedding_artifact(
    a_config: Mapping[str, Any],
    b_embed_config: Mapping[str, Any],
) -> str:
    """Require one immutable query-vector artifact for both conditions."""
    a_cache = a_config.get("cache_identity") or {}
    b_cache = b_embed_config.get("cache_identity") or {}
    a_identity = a_cache.get("query_embedding_artifact") or {}
    b_identity = b_cache.get("query_embedding_artifact") or {}
    a_sha = str(a_identity.get("sha256") or "")
    b_sha = str(b_identity.get("sha256") or "")
    if len(a_sha) != 64 or a_sha != b_sha:
        raise ValueError(
            "dense-control query embedding artifact mismatch: "
            f"A={a_sha!r}, B_embed={b_sha!r}"
        )
    return a_sha


def build_dense_control_report(
    a_dir: Path,
    b_embed_dir: Path,
    *,
    data_file: Path,
    a_relocation_manifest: Optional[Path] = None,
    b_embed_relocation_manifest: Optional[Path] = None,
) -> Dict[str, Any]:
    a_config, a_rows, a_identity = _metric_rows(
        a_dir.resolve(),
        data_file=data_file.resolve(),
        relocation_manifest=a_relocation_manifest,
    )
    b_config, b_rows, b_identity = _metric_rows(
        b_embed_dir.resolve(),
        data_file=data_file.resolve(),
        relocation_manifest=b_embed_relocation_manifest,
    )
    _assert_matched(a_config, b_config, a_rows, b_rows)
    a_variant = (a_config.get("retrieval") or {}).get("variant")
    b_variant = (b_config.get("retrieval") or {}).get("variant")
    if a_variant != "A" or b_variant != "B_embed":
        raise ValueError(
            "dense-control requires retrieval variants A and B_embed; "
            f"got {a_variant!r} and {b_variant!r}"
        )
    query_artifact_sha256 = assert_same_query_embedding_artifact(
        a_config,
        b_config,
    )
    assert_ordered_context_equality(a_rows, b_rows)
    report = {
        "schema": "locomo_dense_control_v1",
        "status": "pass",
        "gate": "ordered context ids exact equality for every QA",
        "condition_a": a_identity,
        "condition_b_embed": b_identity,
        "qa_count": len(a_rows),
        "mismatches": 0,
        "query_embedding_artifact_sha256": query_artifact_sha256,
    }
    report["report_fingerprint"] = _canonical_hash(report)
    return report


def _percentile_interval(values: np.ndarray) -> List[float]:
    lower, upper = np.quantile(values, [0.025, 0.975])
    return [float(lower), float(upper)]


def _two_sided_zero_p(values: np.ndarray) -> float:
    count = len(values)
    lower = (int(np.count_nonzero(values <= 0.0)) + 1) / (count + 1)
    upper = (int(np.count_nonzero(values >= 0.0)) + 1) / (count + 1)
    return float(min(1.0, 2.0 * min(lower, upper)))


def _bootstrap(
    differences: np.ndarray,
    sample_ids: np.ndarray,
    *,
    resamples: int,
    rng: np.random.Generator,
) -> Dict[str, Any]:
    if len(differences) == 0:
        raise ValueError("cannot bootstrap an empty row selection")
    qa_values = np.empty(resamples, dtype=np.float64)
    chunk_size = 256
    for start in range(0, resamples, chunk_size):
        stop = min(start + chunk_size, resamples)
        qa_draws = rng.integers(
            0,
            len(differences),
            size=(stop - start, len(differences)),
        )
        qa_values[start:stop] = differences[qa_draws].mean(axis=1)

    clusters = np.asarray(list(dict.fromkeys(sample_ids.tolist())))
    cluster_rows = {
        cluster: differences[sample_ids == cluster] for cluster in clusters
    }
    cluster_values = np.empty(resamples, dtype=np.float64)
    for index in range(resamples):
        selected = rng.choice(clusters, size=len(clusters), replace=True)
        cluster_values[index] = np.concatenate(
            [cluster_rows[cluster] for cluster in selected]
        ).mean()

    return {
        "mean_difference": float(differences.mean()),
        "paired_qa_bootstrap": {
            "resamples": resamples,
            "confidence_interval_95": _percentile_interval(qa_values),
            "two_sided_zero_p": _two_sided_zero_p(qa_values),
        },
        "conversation_cluster_bootstrap": {
            "resamples": resamples,
            "clusters": int(len(clusters)),
            "estimator": (
                "mean over all QA rows after resampling whole conversations"
            ),
            "confidence_interval_95": _percentile_interval(cluster_values),
            "two_sided_zero_p": _two_sided_zero_p(cluster_values),
        },
    }


def _selection_report(
    a_rows: Sequence[Mapping[str, Any]],
    b_rows: Sequence[Mapping[str, Any]],
    indices: np.ndarray,
    *,
    resamples: int,
    rng: np.random.Generator,
) -> Dict[str, Any]:
    selected_a = [a_rows[int(index)] for index in indices]
    selected_b = [b_rows[int(index)] for index in indices]
    sample_ids = np.asarray([row["sample_id"] for row in selected_a])
    report: Dict[str, Any] = {"qa_count": int(len(indices)), "metrics": {}}
    for metric in ("f1", "recall"):
        if metric == "recall":
            a_values = np.asarray(
                [official_recall_contribution(row) for row in selected_a],
                dtype=np.float64,
            )
            b_values = np.asarray(
                [official_recall_contribution(row) for row in selected_b],
                dtype=np.float64,
            )
        else:
            a_values = np.asarray(
                [float(row[metric]) for row in selected_a], dtype=np.float64
            )
            b_values = np.asarray(
                [float(row[metric]) for row in selected_b], dtype=np.float64
            )
        analysis = _bootstrap(
            b_values - a_values,
            sample_ids,
            resamples=resamples,
            rng=rng,
        )
        analysis.update(
            {
                "a_mean": float(a_values.mean()),
                "b_mean": float(b_values.mean()),
            }
        )
        report["metrics"][metric] = analysis
    return report


def compare_rows(
    a_rows: Sequence[Mapping[str, Any]],
    b_rows: Sequence[Mapping[str, Any]],
    *,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = SEED,
) -> Dict[str, Any]:
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if len(a_rows) != len(b_rows):
        raise ValueError("paired conditions have different row counts")
    rng = np.random.default_rng(seed)
    all_indices = np.arange(len(a_rows))
    overall = _selection_report(
        a_rows, b_rows, all_indices, resamples=resamples, rng=rng
    )
    categories = {}
    for category in range(1, 6):
        indices = np.asarray(
            [
                index
                for index, row in enumerate(a_rows)
                if int(row["category"]) == category
            ],
            dtype=np.int64,
        )
        categories[str(category)] = _selection_report(
            a_rows,
            b_rows,
            indices,
            resamples=resamples,
            rng=rng,
        )
    categories_1_4 = np.asarray(
        [
            index
            for index, row in enumerate(a_rows)
            if int(row["category"]) in {1, 2, 3, 4}
        ],
        dtype=np.int64,
    )
    subset = _selection_report(
        a_rows,
        b_rows,
        categories_1_4,
        resamples=resamples,
        rng=rng,
    )
    subset["status"] = "local non-official diagnostic"

    per_conversation = []
    for sample_id in dict.fromkeys(str(row["sample_id"]) for row in a_rows):
        indices = [
            index
            for index, row in enumerate(a_rows)
            if str(row["sample_id"]) == sample_id
        ]
        row = {"sample_id": sample_id, "qa_count": len(indices)}
        for metric in ("f1", "recall"):
            if metric == "recall":
                a_values = np.asarray(
                    [
                        official_recall_contribution(a_rows[index])
                        for index in indices
                    ]
                )
                b_values = np.asarray(
                    [
                        official_recall_contribution(b_rows[index])
                        for index in indices
                    ]
                )
            else:
                a_values = np.asarray(
                    [float(a_rows[index][metric]) for index in indices]
                )
                b_values = np.asarray(
                    [float(b_rows[index][metric]) for index in indices]
                )
            row[metric] = {
                "a_mean": float(a_values.mean()),
                "b_mean": float(b_values.mean()),
                "difference": float((b_values - a_values).mean()),
            }
        per_conversation.append(row)
    return {
        "seed": seed,
        "resamples": resamples,
        "metric_source": (
            "immutable official per-row serialized F1 and recall values; "
            "recall contribution is forced to zero for empty evidence"
        ),
        "metric_recalculation": False,
        "recall_contribution_policy": (
            "serialized per-row recall when evidence is non-empty; otherwise "
            "0; denominator includes every selected QA"
        ),
        "difference_direction": "B_minus_A",
        "overall": overall,
        "categories": categories,
        "categories_1_4": subset,
        "per_conversation": per_conversation,
    }


def holm_adjust(p_values: Mapping[str, float]) -> Dict[str, float]:
    """Holm step-down adjusted p-values for simultaneous component claims."""
    ordered = sorted(
        ((name, float(value)) for name, value in p_values.items()),
        key=lambda item: item[1],
    )
    adjusted: Dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for rank, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * value))
        adjusted[name] = running
    return {name: adjusted[name] for name in p_values}


def build_report(
    a_dir: Path,
    b_dir: Path,
    *,
    data_file: Path,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = SEED,
    a_relocation_manifest: Optional[Path] = None,
    b_relocation_manifest: Optional[Path] = None,
) -> Dict[str, Any]:
    a_config, a_rows, a_identity = _metric_rows(
        a_dir.resolve(),
        data_file=data_file.resolve(),
        relocation_manifest=a_relocation_manifest,
    )
    b_config, b_rows, b_identity = _metric_rows(
        b_dir.resolve(),
        data_file=data_file.resolve(),
        relocation_manifest=b_relocation_manifest,
    )
    _assert_matched(a_config, b_config, a_rows, b_rows)
    analysis = compare_rows(
        a_rows,
        b_rows,
        resamples=resamples,
        seed=seed,
    )
    report = {
        "schema": REPORT_SCHEMA,
        "hypothesis": "predeclared primary B versus A",
        "condition_a": a_identity,
        "condition_b": b_identity,
        "analysis": analysis,
        "multiple_comparison": {
            "primary_test": "no correction; single predeclared comparison",
            "component_claims": (
                "use holm_adjust across component-test p-values"
            ),
        },
    }
    report["report_fingerprint"] = _canonical_hash(report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    compare = subcommands.add_parser("compare")
    compare.add_argument("--a-dir", required=True)
    compare.add_argument("--b-dir", required=True)
    compare.add_argument("--data-file", default="data/locomo10.json")
    compare.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    compare.add_argument("--seed", type=int, default=SEED)
    compare.add_argument("--output", required=True)
    compare.add_argument("--a-relocation-manifest")
    compare.add_argument("--b-relocation-manifest")
    dense = subcommands.add_parser("dense-control")
    dense.add_argument("--a-dir", required=True)
    dense.add_argument("--b-embed-dir", required=True)
    dense.add_argument("--data-file", default="data/locomo10.json")
    dense.add_argument("--output", required=True)
    dense.add_argument("--a-relocation-manifest")
    dense.add_argument("--b-embed-relocation-manifest")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "compare":
        if args.seed != SEED:
            raise ValueError(f"formal analysis seed must be {SEED}")
        if args.resamples != DEFAULT_RESAMPLES:
            raise ValueError(
                f"formal analysis requires {DEFAULT_RESAMPLES} resamples"
            )
        report = build_report(
            Path(args.a_dir),
            Path(args.b_dir),
            data_file=Path(args.data_file),
            resamples=args.resamples,
            seed=args.seed,
            a_relocation_manifest=(
                Path(args.a_relocation_manifest)
                if args.a_relocation_manifest
                else None
            ),
            b_relocation_manifest=(
                Path(args.b_relocation_manifest)
                if args.b_relocation_manifest
                else None
            ),
        )
    else:
        report = build_dense_control_report(
            Path(args.a_dir),
            Path(args.b_embed_dir),
            data_file=Path(args.data_file),
            a_relocation_manifest=(
                Path(args.a_relocation_manifest)
                if args.a_relocation_manifest
                else None
            ),
            b_embed_relocation_manifest=(
                Path(args.b_embed_relocation_manifest)
                if args.b_embed_relocation_manifest
                else None
            ),
        )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
