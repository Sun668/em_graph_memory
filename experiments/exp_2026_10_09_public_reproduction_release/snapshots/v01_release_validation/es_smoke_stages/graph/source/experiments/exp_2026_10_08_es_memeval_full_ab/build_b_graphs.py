#!/usr/bin/env python3
"""Build versioned candidate B graphs with an instruction-guard fallback."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping

ROOT = Path(__file__).resolve().parents[2]
BASE_RUNNER = ROOT / "experiments/exp_2026_07_27_locomo_stack_refactor/run.py"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import (
    EMGraph,
    EMGraphArtifactStore,
    EMGraphConfig,
    assert_bipartite,
    build_em_graph,
)
from common.llm import observe_model_usage

from entity_compat import (
    COMPAT_PROTOCOL,
    FALLBACK_SCAFFOLD_CHARS,
    OVERLAY_CACHE_FILENAME,
    PRIMARY_SCAFFOLD_CHARS,
    CompatibleEntityCache,
    InstructionGuardEntityExtractor,
    UsageBudget,
    audit_compatible_cache_coverage,
    compatible_graph_identity,
    sha256_file,
)


def load_base_runner() -> Any:
    spec = importlib.util.spec_from_file_location("compat_base_runner", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner: {BASE_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def select_samples(
    payload: Any,
    sample_ids: List[str],
) -> List[Dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("dataset root must be a list")
    samples = [dict(item) for item in payload if isinstance(item, Mapping)]
    if not sample_ids:
        return samples
    requested = set(sample_ids)
    selected = [
        item
        for item in samples
        if str(item.get("sample_id") or "") in requested
    ]
    found = {str(item.get("sample_id") or "") for item in selected}
    if found != requested:
        raise ValueError(f"unknown sample ids: {sorted(requested - found)}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--parameter-snapshot", type=Path, required=True)
    parser.add_argument("--data-file", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--extract-model", required=True)
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--samples", nargs="*", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    parameter_path = args.parameter_snapshot.resolve()
    data_path = args.data_file.resolve()
    cache_dir = args.cache_dir.resolve()
    output_dir = args.output_dir.resolve()
    parameters = json.loads(parameter_path.read_text(encoding="utf-8"))
    errors: List[str] = []
    if parameters.get("schema") != "research-experiment-parameters-v1":
        errors.append("unexpected parameter schema")
    if parameters.get("status") != "frozen":
        errors.append("parameter snapshot is not frozen")
    if parameters.get("run_id") != args.run_id:
        errors.append("run id mismatch")
    if os.environ.get("RESEARCH_RUN_CLASS") != "diagnostic":
        errors.append("RESEARCH_RUN_CLASS must be diagnostic")
    if Path(os.environ.get("RESEARCH_PARAMETER_SNAPSHOT", "")).resolve() != parameter_path:
        errors.append("RESEARCH_PARAMETER_SNAPSHOT mismatch")
    if Path(os.environ.get("RESEARCH_CONDITION_DIR", "")).resolve() != output_dir:
        errors.append("RESEARCH_CONDITION_DIR mismatch")
    if output_dir.exists():
        errors.append("condition output directory already exists")
    if not cache_dir.is_dir():
        errors.append("cache directory is missing")
    if sha256_file(data_path) != parameters["dataset"]["sha256"]:
        errors.append("dataset SHA mismatch")
    if args.extract_model != parameters["models"]["extraction"]:
        errors.append("extract model mismatch")
    if args.workers != int(parameters["resources"]["entity_workers"]):
        errors.append("worker count mismatch")
    if FALLBACK_SCAFFOLD_CHARS > 5000:
        errors.append("fallback prompt scaffold exceeds 5000 characters")
    if errors:
        raise SystemExit("preflight failed:\n- " + "\n- ".join(errors))

    output_dir.mkdir(parents=True)
    base = load_base_runner()
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    samples = select_samples(payload, list(args.samples))
    store = EMGraphArtifactStore.from_env(str(cache_dir))
    profile = dict(base.VARIANTS["B"]["graph"])
    base_cache_path = store.entity_cache_path()
    overlay_cache_path = base_cache_path.parent / OVERLAY_CACHE_FILENAME
    cache = CompatibleEntityCache(
        base_cache_file=base_cache_path,
        overlay_cache_file=overlay_cache_path,
    )
    cost_limits = dict(parameters.get("cost_limits") or {})
    budget = UsageBudget(
        ledger_file=output_dir / "provider_usage.json",
        cap_usd=float(cost_limits["candidate_stage_cumulative_budget_stop_usd"]),
        prior_estimated_spend_usd=float(
            cost_limits["prior_estimated_spend_usd"]
        ),
        input_usd_per_million=float(cost_limits["input_usd_per_million"]),
        output_usd_per_million=float(cost_limits["output_usd_per_million"]),
        max_output_tokens=int(cost_limits["max_output_tokens_per_request"]),
    )
    extractor = InstructionGuardEntityExtractor(
        model=args.extract_model,
        cache=cache,
        budget=budget,
    )

    records: List[Dict[str, Any]] = []
    status = "complete"
    failure: Dict[str, Any] | None = None
    usage_context = observe_model_usage(
        budget.observe,
        stage="longmemeval_m_conversation_entity_extraction",
    )
    usage_context.__enter__()
    try:
        for raw_sample in samples:
            sample_id = str(raw_sample.get("sample_id") or "")
            conversation_sample = {
                "sample_id": sample_id,
                "conversation": raw_sample.get("conversation") or {},
            }
            profiled = base._profiled_sample(conversation_sample, profile)
            identity = compatible_graph_identity(
                base,
                profiled,
                args.extract_model,
                profile,
            )
            graph_path = store.graph_path(sample_id, identity=identity)
            reused = False
            before_failures = len(extractor.failures)
            if graph_path.exists():
                graph = EMGraph.load_from_file(str(graph_path))
                assert_bipartite(graph)
                if not bool((graph.stats or {}).get("partial")):
                    reused = True
                else:
                    graph = build_em_graph(
                        profiled,
                        config=EMGraphConfig(
                            model=args.extract_model,
                            add_speaker_as_entity=bool(
                                profile["add_speaker_as_entity"]
                            ),
                            auto_time_words=bool(
                                profile["use_time_annotations"]
                            ),
                        ),
                        extractor=extractor,
                        checkpoint_path=str(graph_path),
                        checkpoint_every=40,
                        max_workers=args.workers,
                    )
            else:
                graph = build_em_graph(
                    profiled,
                    config=EMGraphConfig(
                        model=args.extract_model,
                        add_speaker_as_entity=bool(
                            profile["add_speaker_as_entity"]
                        ),
                        auto_time_words=bool(profile["use_time_annotations"]),
                    ),
                    extractor=extractor,
                    checkpoint_path=str(graph_path),
                    checkpoint_every=40,
                    max_workers=args.workers,
                )
            cache.flush()
            new_failures = extractor.failures[before_failures:]
            if new_failures:
                raise RuntimeError(
                    f"terminal entity extraction failures for {sample_id}: "
                    f"{new_failures}"
                )
            graph.stats = {
                **dict(graph.stats or {}),
                "cache_identity": identity,
                "entity_parser_protocol": COMPAT_PROTOCOL,
                "primary_prompt_scaffold_chars": PRIMARY_SCAFFOLD_CHARS,
                "fallback_prompt_scaffold_chars": FALLBACK_SCAFFOLD_CHARS,
                "graph_constraint": {
                    "construction_inputs": [
                        "session date_time",
                        "dia_id",
                        "speaker",
                        "dialog text",
                        "blip_caption",
                    ],
                    "qa_question_used": False,
                    "qa_answer_used": False,
                    "qa_evidence_used": False,
                    "qa_category_used": False,
                    "judge_output_used": False,
                    "previous_prediction_used": False,
                },
            }
            graph.save_to_file(str(graph_path))
            assert_bipartite(graph)
            coverage = audit_compatible_cache_coverage(
                profiled,
                graph,
                profile,
                cache,
                args.extract_model,
            )
            if coverage["status"] != "pass":
                raise RuntimeError(
                    f"compatibility cache/graph coverage failed for {sample_id}"
                )
            records.append(
                {
                    "sample_id": sample_id,
                    "conversation_sha256": sha256_json(
                        profiled.get("conversation") or {}
                    ),
                    "graph_path": str(graph_path),
                    "graph_sha256": sha256_file(graph_path),
                    "graph_identity": identity,
                    "reused_complete_graph": reused,
                    "memory_count": len(graph.memories),
                    "entity_count": len(graph.entities),
                    "entity_edge_count": len(graph.edges),
                    "coverage": coverage,
                }
            )
            write_json_atomic(
                output_dir / "progress.json",
                {
                    "schema": "candidate-b-compat-progress-v1",
                    "status": "in-progress",
                    "run_id": args.run_id,
                    "records": records,
                    "extractor": extractor.stats(),
                },
            )
    except Exception as exc:
        status = "failed"
        failure = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        cache.flush()
        budget.persist()
        usage_context.__exit__(None, None, None)

    result = {
        "schema": "candidate-b-compat-graph-build-result-v1",
        "status": status,
        "run_id": args.run_id,
        "protocol": COMPAT_PROTOCOL,
        "dataset": {
            "path": str(data_path),
            "sha256": sha256_file(data_path),
            "selected_sample_count": len(samples),
            "selected_sample_ids": [
                str(sample.get("sample_id") or "") for sample in samples
            ],
        },
        "models": {"extraction": args.extract_model},
        "workers": args.workers,
        "primary_prompt_scaffold_chars": PRIMARY_SCAFFOLD_CHARS,
        "fallback_prompt_scaffold_chars": FALLBACK_SCAFFOLD_CHARS,
        "records": records,
        "extractor": extractor.stats(),
        "failure": failure,
        "graph_constraint": {
            "status": "pass",
            "construction_input": "sample.conversation only",
            "qa_question_used": False,
            "qa_answer_used": False,
            "qa_evidence_used": False,
            "qa_category_used": False,
            "judge_output_used": False,
            "previous_prediction_used": False,
        },
        "source": {
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                text=True,
            ).strip(),
            "base_runner": str(BASE_RUNNER),
            "base_runner_sha256": sha256_file(BASE_RUNNER),
            "parameter_snapshot": str(parameter_path),
            "parameter_snapshot_sha256": sha256_file(parameter_path),
        },
    }
    write_json_atomic(output_dir / "result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if status != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
