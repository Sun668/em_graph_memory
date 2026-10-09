#!/usr/bin/env python3
"""Run one isolated ES-MemEval retrieval condition through current EM-Graph."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
BASE_EXP = ROOT / "experiments/exp_2026_07_27_locomo_stack_refactor"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from common.llm import observe_model_usage, set_api_key_from_env
from em_graph import (
    EMGraph,
    EMGraphArtifactStore,
    QueryEmbeddingArtifact,
    assert_bipartite,
)
from em_graph.build.config import ENTITY_EXTRACTION_PROMPT, ENTITY_EXTRACT_VERSION
from em_graph.recall.embedding_index import L2_NORMALIZATION
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
)


def load_graph_runner():
    path = BASE_EXP / "run.py"
    spec = importlib.util.spec_from_file_location("locomo_graph_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import graph runner from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def audit_entity_cache_coverage(
    graph: EMGraph,
    store: EMGraphArtifactStore,
    extract_model: str,
) -> Dict[str, Any]:
    cache_path = store.entity_cache_path()
    if not cache_path.is_file():
        raise RuntimeError(f"entity cache is missing: {cache_path}")
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(cache, dict):
        raise RuntimeError(f"entity cache is not an object: {cache_path}")

    missing_memory_ids: List[str] = []
    empty_memory_ids: List[str] = []
    for memory_id, memory in graph.memories.items():
        digest = hashlib.sha256(
            memory.text_normalized.encode("utf-8")
        ).hexdigest()
        key = f"{ENTITY_EXTRACT_VERSION}::{extract_model}::{digest}"
        if key not in cache or not isinstance(cache[key], list):
            missing_memory_ids.append(memory_id)
        elif not cache[key]:
            empty_memory_ids.append(memory_id)

    linked_memory_ids = {edge.memory_id for edge in graph.edges}
    unlinked_memory_ids = sorted(set(graph.memories) - linked_memory_ids)
    unexpected_unlinked_memory_ids = sorted(
        set(unlinked_memory_ids) - set(empty_memory_ids)
    )
    coverage = {
        "status": (
            "pass"
            if not missing_memory_ids and not unexpected_unlinked_memory_ids
            else "fail"
        ),
        "cache_path": str(cache_path.resolve()),
        "cache_sha256": sha256_file(cache_path),
        "cache_namespace": f"{ENTITY_EXTRACT_VERSION}::{extract_model}",
        "memory_count": len(graph.memories),
        "cache_missing_count": len(missing_memory_ids),
        "cache_missing_memory_ids": sorted(missing_memory_ids),
        "cached_empty_count": len(empty_memory_ids),
        "cached_empty_memory_ids": sorted(empty_memory_ids),
        "unlinked_memory_count": len(unlinked_memory_ids),
        "unlinked_memory_ids": unlinked_memory_ids,
        "unexpected_unlinked_count": len(unexpected_unlinked_memory_ids),
        "unexpected_unlinked_memory_ids": unexpected_unlinked_memory_ids,
        "cached_empty_policy": "allowed, explicitly counted, sequence-linked only",
    }
    if coverage["status"] != "pass":
        raise RuntimeError(
            f"Entity cache coverage failed: {len(missing_memory_ids)} missing "
            f"records and {len(unexpected_unlinked_memory_ids)} unexplained "
            "unlinked Memory nodes"
        )
    return coverage


def load_existing_graph(
    graph_runner: Any,
    sample: Dict[str, Any],
    *,
    profile: Dict[str, Any],
    extract_model: str,
    store: EMGraphArtifactStore,
) -> tuple[Dict[str, Any], Path, EMGraph, Dict[str, Any]]:
    profiled = graph_runner._profiled_sample(sample, profile)
    if bool(profile["memory_only"]):
        identity = graph_runner._graph_identity(
            profiled,
            extract_model,
            memory_only=True,
            graph_profile=profile,
        )
    else:
        identity = compatible_graph_identity(
            graph_runner,
            profiled,
            extract_model,
            profile,
        )
    sample_id = str(sample.get("sample_id") or "")
    graph_path = store.graph_path(sample_id, identity=identity)
    if not graph_path.is_file():
        raise FileNotFoundError(
            f"required frozen graph is missing for {sample_id}: {graph_path}"
        )
    graph = EMGraph.load_from_file(str(graph_path))
    assert_bipartite(graph)
    if bool((graph.stats or {}).get("partial")):
        raise RuntimeError(f"required graph is partial: {graph_path}")
    if dict((graph.stats or {}).get("cache_identity") or {}) != identity:
        raise RuntimeError(f"graph cache identity mismatch: {graph_path}")
    return profiled, graph_path, graph, identity


def load_existing_recall(
    graph_runner: Any,
    sample: Dict[str, Any],
    *,
    graph: EMGraph,
    profiled_sample: Dict[str, Any],
    profile: Dict[str, Any],
    variant: str,
    extract_model: str,
    embedding_model: str,
    store: EMGraphArtifactStore,
    query_artifact: QueryEmbeddingArtifact,
    question_extractor: Any = None,
    question_cache: Any = None,
) -> tuple[Any, Path]:
    sample_id = str(sample.get("sample_id") or "")
    index_path = store.embedding_index_path(
        sample_id,
        identity=graph_runner._embedding_identity(
            profiled_sample,
            embedding_model,
            graph_profile=profile,
            normalization=L2_NORMALIZATION,
            runtime_identity=None,
        ),
    )
    if not index_path.is_file():
        raise FileNotFoundError(
            f"required frozen Memory embedding index is missing: {index_path}"
        )
    text_cache = graph_runner.TextEmbeddingCache(
        cache_file=str(store.text_embedding_cache_path(embedding_model))
    )
    embedding_index = graph_runner.MemoryEmbeddingIndex.build(
        graph,
        model_name=embedding_model,
        normalization=L2_NORMALIZATION,
        cache_path=str(index_path),
        text_cache=text_cache,
        query_cache=query_artifact,
        strict_query_cache=True,
        use_text_cache=True,
    )
    parameters = dict(graph_runner.VARIANTS[variant]["recall"])
    full_pool = bool(parameters["force_full_pool"])
    if full_pool:
        question_extractor = None
        question_cache = None
    elif question_extractor is None or question_cache is None:
        raise RuntimeError("B retrieval requires frozen compatible question extraction")
    recall = graph_runner.EMGraphRecall(
        graph,
        embedding_index,
        entity_bm25_index=(
            None if full_pool else graph_runner.EntityBM25Index.build(graph)
        ),
        extractor=question_extractor,
        question_cache=question_cache,
        **parameters,
    )
    return recall, index_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--data-file", required=True)
    parser.add_argument("--variant", choices=("A", "B_embed", "B"), required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--extract-model", required=True)
    parser.add_argument("--embedding-model", required=True)
    parser.add_argument("--query-artifact", required=True)
    parser.add_argument("--parameter-snapshot", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    data_path = Path(args.data_file).resolve()
    query_path = Path(args.query_artifact).resolve()
    parameter_path = Path(args.parameter_snapshot).resolve()
    output_dir = Path(args.output_dir).resolve()
    parameters_snapshot = json.loads(parameter_path.read_text(encoding="utf-8"))
    if parameters_snapshot.get("status") != "frozen":
        raise ValueError("parameter snapshot is not frozen")
    if parameters_snapshot.get("run_id") != args.run_id:
        raise ValueError("run id differs from parameter snapshot")
    expected_run_class = str(
        parameters_snapshot.get("classification") or "formal"
    )
    if os.environ.get("RESEARCH_RUN_CLASS") != expected_run_class:
        raise ValueError("RESEARCH_RUN_CLASS differs from frozen classification")
    if Path(os.environ.get("RESEARCH_PARAMETER_SNAPSHOT", "")).resolve() != parameter_path:
        raise ValueError("RESEARCH_PARAMETER_SNAPSHOT binding mismatch")
    if Path(os.environ.get("RESEARCH_CONDITION_DIR", "")).resolve() != output_dir:
        raise ValueError("RESEARCH_CONDITION_DIR binding mismatch")
    if output_dir.exists():
        raise FileExistsError(f"condition output already exists: {output_dir}")
    if parameters_snapshot.get("variant") != args.variant:
        raise ValueError("variant differs from parameter snapshot")
    if int(parameters_snapshot.get("top_k")) != args.top_k:
        raise ValueError("top-k differs from parameter snapshot")
    if parameters_snapshot.get("models", {}).get("extraction") != args.extract_model:
        raise ValueError("extraction model differs from parameter snapshot")
    if parameters_snapshot.get("models", {}).get("embedding") != args.embedding_model:
        raise ValueError("embedding model differs from parameter snapshot")
    if parameters_snapshot.get("dataset", {}).get("sha256") != sha256_file(data_path):
        raise ValueError("dataset SHA differs from parameter snapshot")
    if parameters_snapshot.get("query_artifact", {}).get("sha256") != sha256_file(query_path):
        raise ValueError("query-artifact SHA differs from parameter snapshot")
    output_dir.mkdir(parents=True)

    samples = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not samples:
        raise ValueError("adapter dataset must be a non-empty list")
    graph_runner = load_graph_runner()
    if args.variant not in graph_runner.VARIANTS:
        raise ValueError(f"unknown graph variant {args.variant}")
    profile = dict(graph_runner.VARIANTS[args.variant]["graph"])
    parameters = dict(graph_runner.VARIANTS[args.variant]["recall"])

    query_artifact = QueryEmbeddingArtifact.load(query_path)
    query_artifact.validate_exact_dataset(
        samples,
        dataset_sha256=sha256_file(data_path),
        model_name=args.embedding_model,
        role="context",
        normalization=L2_NORMALIZATION,
        protocol_identity={},
    )
    query_identity = query_artifact.identity(query_path)
    store = EMGraphArtifactStore.from_env(args.cache_dir)

    conversation_base_cache = store.entity_cache_path()
    conversation_compat_cache = CompatibleEntityCache(
        base_cache_file=conversation_base_cache,
        overlay_cache_file=(
            conversation_base_cache.parent / OVERLAY_CACHE_FILENAME
        ),
    )
    question_extractor = None
    question_cache = None
    budget = None
    if args.variant == "B":
        set_api_key_from_env()
        cost_limits = dict(parameters_snapshot.get("cost_limits") or {})
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
        question_base_cache = store.question_extraction_cache_path()
        question_compat_cache = CompatibleEntityCache(
            base_cache_file=question_base_cache,
            overlay_cache_file=(
                question_base_cache.parent
                / "question_extraction_instruction_guard_v2.json"
            ),
        )
        question_extractor = InstructionGuardEntityExtractor(
            model=args.extract_model,
            cache=question_compat_cache,
            budget=budget,
        )
        question_cache = graph_runner.QuestionEntityCache(
            cache_file=str(
                store.question_entity_cache_path().parent
                / "question_entities_instruction_guard_v2.json"
            ),
            namespace=f"{COMPAT_PROTOCOL}::{args.extract_model}",
        )

    def usage_observer(event: Dict[str, Any]) -> None:
        if args.variant != "B":
            raise RuntimeError(
                f"unexpected live model request in {args.variant}: {event}"
            )
        if event.get("operation") != "chat":
            raise RuntimeError(f"unexpected non-chat model request in B: {event}")
        if budget is None:
            raise RuntimeError("B usage budget is missing")
        budget.observe(event)

    rows: List[Dict[str, Any]] = []
    graph_records: List[Dict[str, Any]] = []
    usage_context = observe_model_usage(
        usage_observer,
        stage=f"es_memeval_{args.variant}_retrieval",
    )
    usage_context.__enter__()
    try:
        for sample in samples:
            profiled, graph_path, graph, graph_identity = load_existing_graph(
                graph_runner,
                sample,
                profile=profile,
                extract_model=args.extract_model,
                store=store,
            )
            entity_cache_coverage = (
                {
                    "status": "not-applicable",
                    "reason": "memory-only control performs no Entity extraction",
                }
                if bool(profile["memory_only"])
                else audit_compatible_cache_coverage(
                    profiled,
                    graph,
                    profile,
                    conversation_compat_cache,
                    args.extract_model,
                )
            )
            recall, index_path = load_existing_recall(
                graph_runner,
                sample,
                graph=graph,
                profiled_sample=profiled,
                profile=profile,
                variant=args.variant,
                extract_model=args.extract_model,
                embedding_model=args.embedding_model,
                store=store,
                query_artifact=query_artifact,
                question_extractor=question_extractor,
                question_cache=question_cache,
            )
            for qa_index, qa in enumerate(sample["qa"]):
                if set(qa) != {"question"}:
                    raise ValueError("retrieval QA input must contain question only")
                result = recall.recall(sample, qa_index, str(qa["question"]), args.top_k)
                rows.append({
                    "sample_id": str(sample["sample_id"]),
                    "qa_index": qa_index,
                    "question": str(qa["question"]),
                    "context_ids": [str(value) for value in result.context_ids],
                    "context": result.context,
                })
            graph_records.append(
                {
                    "sample_id": str(sample["sample_id"]),
                    "graph_path": str(graph_path.resolve()),
                    "graph_sha256": sha256_file(graph_path),
                    "graph_identity": graph_identity,
                    "embedding_index_path": str(index_path.resolve()),
                    "embedding_index_sha256": sha256_file(index_path),
                    "memory_count": len(graph.memories),
                    "entity_count": len(graph.entities),
                    "entity_edge_count": len(graph.edges),
                    "entity_cache_coverage": entity_cache_coverage,
                }
            )
    finally:
        if budget is not None:
            budget.persist()
        usage_context.__exit__(None, None, None)

    qa_count = sum(len(sample["qa"]) for sample in samples)
    if len(rows) != qa_count:
        raise RuntimeError("retrieval coverage incomplete")
    usage = query_artifact.usage(qa_count=qa_count, required_lookup_count=qa_count)
    entity_coverage_records = [
        record["entity_cache_coverage"]
        for record in graph_records
        if record["entity_cache_coverage"]["status"] != "not-applicable"
    ]
    entity_extraction_coverage = {
        "status": (
            "not-applicable"
            if not entity_coverage_records
            else (
                "pass"
                if all(
                    record["status"] == "pass"
                    for record in entity_coverage_records
                )
                else "fail"
            )
        ),
        "cache_missing_count": sum(
            int(record["cache_missing_count"])
            for record in entity_coverage_records
        ),
        "cached_empty_count": sum(
            int(record["cached_empty_count"])
            for record in entity_coverage_records
        ),
        "unlinked_memory_count": sum(
            int(record["unlinked_memory_count"])
            for record in entity_coverage_records
        ),
        "unexpected_unlinked_count": sum(
            int(record["unexpected_unlinked_count"])
            for record in entity_coverage_records
        ),
    }
    summary = {
        "schema": "es_memeval_retrieval_result_v1",
        "status": "complete",
        "classification": expected_run_class,
        "run_id": args.run_id,
        "variant": args.variant,
        "top_k": args.top_k,
        "dataset": {
            "path": str(data_path),
            "sha256": sha256_file(data_path),
            "sample_count": len(samples),
        },
        "models": {
            "extraction": args.extract_model,
            "embedding": args.embedding_model,
        },
        "graph_profile": profile,
        "retrieval_parameters": parameters,
        "query_artifact": query_identity,
        "query_usage": usage,
        "live_model_usage": (
            {
                "status": "zero-live-requests-required-and-observed",
                "request_count": 0,
            }
            if budget is None
            else {"status": "pass", **budget.stats()}
        ),
        "graph_records": graph_records,
        "entity_extraction_coverage": entity_extraction_coverage,
        "metrics": {"qa_count": qa_count, "context_count": sum(len(row["context_ids"]) for row in rows)},
        "graph_constraint": {
            "status": "pass",
            "construction_input": "sample.conversation only",
            "qa_question_used": False,
            "qa_answer_used": False,
            "qa_evidence_used": False,
            "qa_category_used": False,
            "judge_output_used": False,
            "answer_recall_used_graph": True,
        },
        "prompt_budget": {
            "entity_scaffold_chars": len(
                ENTITY_EXTRACTION_PROMPT.format(text="")
            ),
            "compatibility_fallback_scaffold_chars": FALLBACK_SCAFFOLD_CHARS,
            "limit_chars": 5000,
            "status": (
                "pass"
                if PRIMARY_SCAFFOLD_CHARS <= 5000
                and FALLBACK_SCAFFOLD_CHARS <= 5000
                else "fail"
            ),
        },
        "privacy": {
            "external_question_text": args.variant == "B",
            "external_answer": False,
            "external_evidence_annotation": False,
            "external_category": False,
            "external_judge_output": False,
            "external_historical_prediction": False,
            "local_only_fields": ["answer", "evidence", "capability", "category"],
        },
        "source": {
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "base_runner": str((BASE_EXP / "run.py").resolve()),
            "base_runner_sha256": sha256_file(BASE_EXP / "run.py"),
            "parameter_snapshot": str(parameter_path),
            "parameter_snapshot_sha256": sha256_file(parameter_path),
        },
        "rows": rows,
    }
    write_json(output_dir / "result.json", summary)
    write_json(
        output_dir / "audit.json",
        {
            "schema": "es_memeval_graph_audit_v1",
            "status": (
                "pass"
                if usage["status"] == "pass"
                and summary["prompt_budget"]["status"] == "pass"
                and entity_extraction_coverage["status"]
                in ("pass", "not-applicable")
                else "fail"
            ),
            "query_usage": usage,
            "entity_extraction_coverage": entity_extraction_coverage,
            "graph_constraint": summary["graph_constraint"],
            "prompt_budget": summary["prompt_budget"],
        },
    )
    print(json.dumps(summary["metrics"], indent=2))


if __name__ == "__main__":
    main()
