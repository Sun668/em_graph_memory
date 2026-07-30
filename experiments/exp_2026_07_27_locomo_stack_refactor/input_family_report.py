#!/usr/bin/env python3
"""Predeclared raw-text input-family inference with Holm correction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

import significance_report

SCHEMA = "locomo_input_family_significance_v1"
ALPHA = 0.05
COMPARISONS: Mapping[str, Tuple[str, str]] = {
    "time_annotation_inside_b": ("B", "B_raw_text"),
    "b_over_a_under_raw_text": ("A_raw_text", "B_raw_text"),
}


def _fingerprint(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def holm_families(
    comparisons: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Adjust the two input hypotheses per metric and estimator."""
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
    required = {
        variant for pair in COMPARISONS.values() for variant in pair
    }
    missing = sorted(required - set(directories))
    if missing:
        raise ValueError(f"missing input-family directories: {missing}")

    loaded: Dict[str, Any] = {}
    for variant in sorted(required):
        directory = directories[variant]
        config, rows, identity = significance_report._metric_rows(
            directory.resolve(), data_file=data_file.resolve()
        )
        actual = (config.get("retrieval") or {}).get("variant")
        if actual != variant:
            raise ValueError(
                f"variant/directory mismatch: expected {variant}, got {actual}"
            )
        loaded[variant] = (config, rows, identity)

    comparisons: Dict[str, Any] = {}
    for name, (a_variant, b_variant) in COMPARISONS.items():
        a_config, a_rows, a_identity = loaded[a_variant]
        b_config, b_rows, b_identity = loaded[b_variant]
        significance_report._assert_matched(
            a_config, b_config, a_rows, b_rows
        )
        comparisons[name] = {
            "hypothesis": f"{b_variant} minus {a_variant}",
            "condition_a_variant": a_variant,
            "condition_b_variant": b_variant,
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
            "correction": "Holm step-down",
            "strata": (
                "two raw-text input hypotheses adjusted separately within "
                "each outcome metric and bootstrap estimator; estimators are "
                "robustness estimators, not separate hypotheses"
            ),
        },
        "comparisons": comparisons,
        "holm": holm_families(comparisons),
        "metric_recalculation": False,
    }
    report["report_fingerprint"] = _fingerprint(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b-dir", required=True)
    parser.add_argument("--a-raw-text-dir", required=True)
    parser.add_argument("--b-raw-text-dir", required=True)
    parser.add_argument("--data-file", default="data/locomo10.json")
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260727)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.resamples != significance_report.DEFAULT_RESAMPLES:
        raise ValueError("formal input-family analysis requires 10000 resamples")
    if args.seed != significance_report.SEED:
        raise ValueError("formal input-family analysis seed must be 20260727")
    report = build_report(
        directories={
            "B": Path(args.b_dir),
            "A_raw_text": Path(args.a_raw_text_dir),
            "B_raw_text": Path(args.b_raw_text_dir),
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
