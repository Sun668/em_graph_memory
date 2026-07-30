#!/usr/bin/env python3
"""Predeclared fusion-weight family inference with Holm correction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

import significance_report

SCHEMA = "locomo_fusion_family_significance_v1"
ALPHA = 0.05
CONDITIONS: Mapping[str, Tuple[float, float]] = {
    "primary_0_30_0_70": (0.30, 0.70),
    "fusion_0_10_0_90": (0.10, 0.90),
    "fusion_0_50_0_50": (0.50, 0.50),
}
COMPARISONS: Mapping[str, Tuple[str, str]] = {
    "fusion_0_10_0_90_vs_primary": (
        "primary_0_30_0_70",
        "fusion_0_10_0_90",
    ),
    "fusion_0_50_0_50_vs_primary": (
        "primary_0_30_0_70",
        "fusion_0_50_0_50",
    ),
}


def _fingerprint(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scientific_identity(config: Mapping[str, Any]) -> Dict[str, Any]:
    retrieval = dict(config.get("retrieval") or {})
    retrieval.pop("entity_weight", None)
    retrieval.pop("semantic_weight", None)
    return {
        "dataset_sha256": config.get("dataset_sha256"),
        "scope": config.get("scope"),
        "sample_ids": config.get("sample_ids"),
        "models": config.get("models"),
        "graph_profile": config.get("graph_profile"),
        "answer_protocol": config.get("answer_protocol"),
        "cache_identity": config.get("cache_identity"),
        "retrieval_except_fusion_weights": retrieval,
    }


def _assert_same_scientific_identity(
    control: Mapping[str, Any],
    label: str,
    candidate: Mapping[str, Any],
) -> None:
    expected = _scientific_identity(control)
    actual = _scientific_identity(candidate)
    if actual != expected:
        raise ValueError(
            f"{label} differs from primary outside fusion weights"
        )


def _assert_fusion_condition(
    label: str,
    config: Mapping[str, Any],
) -> None:
    retrieval = config.get("retrieval") or {}
    actual_variant = retrieval.get("variant")
    if actual_variant != "B":
        raise ValueError(
            f"{label} must use complete variant B, got {actual_variant}"
        )
    actual = (
        float(retrieval.get("entity_weight")),
        float(retrieval.get("semantic_weight")),
    )
    expected = CONDITIONS[label]
    if actual != expected:
        raise ValueError(
            f"{label} fusion mismatch: expected {expected}, got {actual}"
        )


def holm_families(
    comparisons: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Adjust the two fusion hypotheses per metric and estimator."""
    output: Dict[str, Any] = {}
    estimators = {
        "paired_qa": "paired_qa_bootstrap",
        "conversation_cluster": "conversation_cluster_bootstrap",
    }
    for metric in ("f1", "recall"):
        output[metric] = {}
        for estimator_name, block_name in estimators.items():
            raw = {
                name: float(
                    report["analysis"]["overall"]["metrics"][metric][
                        block_name
                    ]["two_sided_zero_p"]
                )
                for name, report in comparisons.items()
            }
            adjusted = significance_report.holm_adjust(raw)
            output[metric][estimator_name] = {
                name: {
                    "raw_p": raw[name],
                    "holm_adjusted_p": adjusted[name],
                    "reject_at_0_05": adjusted[name] <= ALPHA,
                }
                for name in raw
            }
    return output


def build_report(
    *,
    directories: Mapping[str, Path],
    data_file: Path,
    resamples: int = significance_report.DEFAULT_RESAMPLES,
    seed: int = significance_report.SEED,
) -> Dict[str, Any]:
    missing = sorted(set(CONDITIONS) - set(directories))
    extra = sorted(set(directories) - set(CONDITIONS))
    if missing or extra:
        raise ValueError(
            f"fusion-family directory mismatch: missing={missing}, extra={extra}"
        )

    loaded: Dict[str, Any] = {}
    for label in CONDITIONS:
        config, rows, identity = significance_report._metric_rows(
            directories[label].resolve(), data_file=data_file.resolve()
        )
        _assert_fusion_condition(label, config)
        loaded[label] = (config, rows, identity)

    primary_config = loaded["primary_0_30_0_70"][0]
    primary_identity = _scientific_identity(primary_config)
    for label in ("fusion_0_10_0_90", "fusion_0_50_0_50"):
        _assert_same_scientific_identity(
            primary_config, label, loaded[label][0]
        )

    comparisons: Dict[str, Any] = {}
    for name, (a_label, b_label) in COMPARISONS.items():
        a_config, a_rows, a_identity = loaded[a_label]
        b_config, b_rows, b_identity = loaded[b_label]
        significance_report._assert_matched(
            a_config, b_config, a_rows, b_rows
        )
        comparisons[name] = {
            "hypothesis": f"{b_label} minus {a_label}",
            "condition_a_label": a_label,
            "condition_b_label": b_label,
            "condition_a": a_identity,
            "condition_b": b_identity,
            "analysis": significance_report.compare_rows(
                a_rows, b_rows, resamples=resamples, seed=seed
            ),
        }

    report: Dict[str, Any] = {
        "schema": SCHEMA,
        "status": "pass",
        "seed": seed,
        "resamples": resamples,
        "alpha": ALPHA,
        "family_definition": {
            "hypotheses": list(COMPARISONS),
            "count": len(COMPARISONS),
            "control": "complete B at Entity/Semantic 0.30/0.70",
            "treatments": [
                "complete B at Entity/Semantic 0.10/0.90",
                "complete B at Entity/Semantic 0.50/0.50",
            ],
            "correction": "Holm step-down",
            "strata": (
                "two preregistered fusion contrasts adjusted separately "
                "within each outcome metric and bootstrap estimator; the "
                "estimators are robustness estimators, not extra hypotheses"
            ),
        },
        "scientific_identity_except_fusion_weights": primary_identity,
        "comparisons": comparisons,
        "holm": holm_families(comparisons),
        "metric_recalculation": False,
    }
    report["report_fingerprint"] = _fingerprint(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-dir", required=True)
    parser.add_argument("--fusion-e10-s90-dir", required=True)
    parser.add_argument("--fusion-e50-s50-dir", required=True)
    parser.add_argument("--data-file", default="data/locomo10.json")
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260727)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.resamples != significance_report.DEFAULT_RESAMPLES:
        raise ValueError("formal fusion-family analysis requires 10000 resamples")
    if args.seed != significance_report.SEED:
        raise ValueError("formal fusion-family analysis seed must be 20260727")
    report = build_report(
        directories={
            "primary_0_30_0_70": Path(args.primary_dir),
            "fusion_0_10_0_90": Path(args.fusion_e10_s90_dir),
            "fusion_0_50_0_50": Path(args.fusion_e50_s50_dir),
        },
        data_file=Path(args.data_file),
        resamples=args.resamples,
        seed=args.seed,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
