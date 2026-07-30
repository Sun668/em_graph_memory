#!/usr/bin/env python3
"""Build EM graphs and hand their single recall interface to LoCoMo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from common.llm import set_api_key_from_env
from em_graph import (
    DIALOG_NORMALIZATION_VERSION,
    MEMORY_SEARCH_TEXT_VERSION,
    EMGraph,
    EMGraphArtifactStore,
    EMGraphConfig,
    EMGraphRecall,
    EMGraphRecallRouter,
    EntityBM25Index,
    EntityCache,
    EntityExtractor,
    MemoryEmbeddingIndex,
    QuestionEntityCache,
    TextEmbeddingCache,
    assert_bipartite,
    build_em_graph,
    build_memory_graph,
)
from em_graph.build.config import (
    ENTITY_EXTRACTION_PROMPT,
    ENTITY_EXTRACT_VERSION,
)
from locomo_eval import LoCoMoEvaluationConfig, OfficialLoCoMoEvaluator


VARIANTS: Dict[str, Dict[str, Any]] = {
    "A": {
        "entity_weight": 0.0,
        "semantic_weight": 1.0,
        "expand_sequence": False,
        "force_full_pool": True,
    },
    "B": {
        "entity_weight": 0.30,
        "semantic_weight": 0.70,
        "expand_sequence": True,
        "force_full_pool": False,
    },
    "B_entity": {
        "entity_weight": 1.0,
        "semantic_weight": 0.0,
        "expand_sequence": True,
        "force_full_pool": False,
    },
    "B_embed": {
        "entity_weight": 0.0,
        "semantic_weight": 1.0,
        "expand_sequence": False,
        "force_full_pool": True,
    },
    "B_noseq": {
        "entity_weight": 0.30,
        "semantic_weight": 0.70,
        "expand_sequence": False,
        "force_full_pool": False,
    },
}


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_samples(path: Path, sample_ids: Optional[Iterable[str]]) -> List[dict]:
    samples = json.loads(path.read_text(encoding="utf-8"))
    if sample_ids is None:
        return list(samples)
    requested = {str(sample_id) for sample_id in sample_ids}
    selected = [
        sample for sample in samples
        if str(sample.get("sample_id") or "") in requested
    ]
    found = {str(sample.get("sample_id") or "") for sample in selected}
    missing = sorted(requested - found)
    if missing:
        raise ValueError(f"unknown sample ids: {missing}")
    return selected


def _graph_identity(
    sample: Mapping[str, Any],
    extract_model: str,
    *,
    memory_only: bool = False,
) -> dict:
    identity = {
        "schema": "em_graph_0.4.0",
        "graph_kind": "memory_only" if memory_only else "entity_memory",
        "sample_id": str(sample.get("sample_id") or ""),
        "conversation_sha256": _sha256_json(sample.get("conversation") or {}),
        "dialog_normalization_version": DIALOG_NORMALIZATION_VERSION,
    }
    if not memory_only:
        identity.update(
            {
                "entity_extract_version": ENTITY_EXTRACT_VERSION,
                "extract_model": extract_model,
            }
        )
    return identity


def _embedding_identity(sample: Mapping[str, Any], model: str) -> dict:
    return {
        "schema": "memory_embedding_index_v2",
        "sample_id": str(sample.get("sample_id") or ""),
        "conversation_sha256": _sha256_json(sample.get("conversation") or {}),
        "dialog_normalization_version": DIALOG_NORMALIZATION_VERSION,
        "embedding_model": model,
        "memory_search_text_version": MEMORY_SEARCH_TEXT_VERSION,
    }


def _conversation_extractor(
    model: str,
    store: EMGraphArtifactStore,
) -> EntityExtractor:
    return EntityExtractor(
        model=model,
        cache=EntityCache(cache_file=str(store.entity_cache_path())),
    )


def _question_extractor(
    model: str,
    store: EMGraphArtifactStore,
) -> EntityExtractor:
    # This cache is deliberately separate from conversation extraction so a
    # QA-derived value can never be consumed while constructing a graph.
    return EntityExtractor(
        model=model,
        cache=EntityCache(
            cache_file=str(store.question_extraction_cache_path())
        ),
    )


def build_graph(
    sample: Dict[str, Any],
    *,
    extract_model: str,
    store: EMGraphArtifactStore,
    memory_only: bool = False,
) -> Path:
    identity = _graph_identity(
        sample,
        extract_model,
        memory_only=memory_only,
    )
    path = store.graph_path(
        str(sample.get("sample_id") or ""),
        identity=identity,
    )
    if path.exists():
        graph = EMGraph.load_from_file(str(path))
        assert_bipartite(graph)
        if not bool((graph.stats or {}).get("partial")):
            return path
        print(f"resuming partial graph: {path}", flush=True)

    if memory_only:
        graph = build_memory_graph(sample)
    else:
        graph = build_em_graph(
            sample,
            config=EMGraphConfig(model=extract_model),
            extractor=_conversation_extractor(extract_model, store),
            checkpoint_path=str(path),
            checkpoint_every=40,
            max_workers=int(os.environ.get("EM_GRAPH_EXTRACT_WORKERS", "6")),
        )
    graph.stats = {
        **dict(graph.stats or {}),
        "cache_identity": identity,
        "prompt_scaffold_chars": (
            0
            if memory_only
            else len(ENTITY_EXTRACTION_PROMPT.format(text=""))
        ),
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
        },
        "memory_only": memory_only,
    }
    assert_bipartite(graph)
    graph.save_to_file(str(path))
    return path


def _load_recall(
    sample: Dict[str, Any],
    *,
    variant: str,
    extract_model: str,
    embedding_model: str,
    store: EMGraphArtifactStore,
) -> EMGraphRecall:
    memory_only = variant == "A"
    graph_identity = _graph_identity(
        sample,
        extract_model,
        memory_only=memory_only,
    )
    sample_id = str(sample.get("sample_id") or "")
    graph_path = store.graph_path(sample_id, identity=graph_identity)
    if not graph_path.exists():
        raise FileNotFoundError(
            f"graph not built for {sample_id}: run build-graphs first"
        )
    graph = EMGraph.load_from_file(str(graph_path))
    assert_bipartite(graph)

    text_cache = TextEmbeddingCache(
        cache_file=str(store.text_embedding_cache_path(embedding_model))
    )
    index_path = store.embedding_index_path(
        sample_id,
        identity=_embedding_identity(sample, embedding_model),
    )
    embedding_index = MemoryEmbeddingIndex.build(
        graph,
        model_name=embedding_model,
        cache_path=str(index_path),
        text_cache=text_cache,
        use_text_cache=True,
    )

    parameters = VARIANTS[variant]
    full_pool = bool(parameters["force_full_pool"])
    question_extractor = (
        None if full_pool else _question_extractor(extract_model, store)
    )
    question_cache = (
        None
        if full_pool
        else QuestionEntityCache(
            cache_file=str(store.question_entity_cache_path()),
            namespace=f"{ENTITY_EXTRACT_VERSION}::{extract_model}",
        )
    )
    return EMGraphRecall(
        graph,
        embedding_index,
        entity_bm25_index=(
            None if full_pool else EntityBM25Index.build(graph)
        ),
        extractor=question_extractor,
        question_cache=question_cache,
        **parameters,
    )


def command_build_graphs(args: argparse.Namespace) -> None:
    set_api_key_from_env()
    data_path = Path(args.data_file).resolve()
    samples = _load_samples(data_path, args.samples)
    store = EMGraphArtifactStore.from_env(args.cache_dir)
    for sample in samples:
        memory_path = build_graph(
            sample,
            extract_model=args.extract_model,
            store=store,
            memory_only=True,
        )
        print(f"memory graph {sample['sample_id']}: {memory_path}", flush=True)
        em_path = build_graph(
            sample,
            extract_model=args.extract_model,
            store=store,
        )
        print(f"EM graph {sample['sample_id']}: {em_path}", flush=True)


def command_evaluate(args: argparse.Namespace) -> None:
    set_api_key_from_env()
    data_path = Path(args.data_file).resolve()
    samples = _load_samples(data_path, args.samples)
    store = EMGraphArtifactStore.from_env(args.cache_dir)
    recalls = {
        str(sample["sample_id"]): _load_recall(
            sample,
            variant=args.variant,
            extract_model=args.extract_model,
            embedding_model=args.embedding_model,
            store=store,
        )
        for sample in samples
    }
    evaluator = OfficialLoCoMoEvaluator(
        EMGraphRecallRouter(recalls),
        LoCoMoEvaluationConfig(
            model=args.answer_model,
            top_k=args.top_k,
            overwrite=args.overwrite,
        ),
    )
    scope = "all10" if args.samples is None else "_".join(args.samples)
    stem = (
        f"{scope}_{args.variant}_{args.answer_model}_"
        f"{args.embedding_model}_top{args.top_k}"
    ).replace("/", "_")
    output_dir = Path(args.output_dir).resolve()
    output_file = output_dir / f"{stem}.json"
    stats_file = output_dir / f"{stem}_stats.json"
    audit_file = output_dir / f"{stem}_graph_audit.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_file.write_text(
        json.dumps(
            {
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
                "variant": args.variant,
                "recall_parameters": VARIANTS[args.variant],
                "sample_ids": [str(sample["sample_id"]) for sample in samples],
                "prompt_budget": {
                    "entity_scaffold_chars": len(
                        ENTITY_EXTRACTION_PROMPT.format(text="")
                    ),
                    "limit_chars": 5000,
                    "pass": len(
                        ENTITY_EXTRACTION_PROMPT.format(text="")
                    ) <= 5000,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    evaluator.evaluate_dataset(
        samples,
        output_file=output_file,
        annotation_file=data_path,
        stats_file=stats_file,
    )
    print(f"official output: {output_file}", flush=True)
    print(f"official stats: {stats_file}", flush=True)
    print(f"graph audit: {audit_file}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.set_defaults(
        data_file=str(ROOT / "data" / "locomo10.json"),
        cache_dir=str(ROOT / "outputs" / "em_graph"),
        output_dir=str(ROOT / "outputs" / "locomo_eval"),
        extract_model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
        embedding_model=os.environ.get(
            "EM_GRAPH_EMBED_MODEL",
            "text-embedding-3-small",
        ),
        answer_model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    build = subcommands.add_parser("build-graphs")
    build.add_argument("--data-file", default=parser.get_default("data_file"))
    build.add_argument("--cache-dir", default=parser.get_default("cache_dir"))
    build.add_argument(
        "--extract-model",
        default=parser.get_default("extract_model"),
    )
    build.add_argument("--samples", nargs="*")
    build.set_defaults(function=command_build_graphs)

    evaluate = subcommands.add_parser("evaluate")
    evaluate.add_argument("--data-file", default=parser.get_default("data_file"))
    evaluate.add_argument("--cache-dir", default=parser.get_default("cache_dir"))
    evaluate.add_argument(
        "--output-dir",
        default=parser.get_default("output_dir"),
    )
    evaluate.add_argument(
        "--extract-model",
        default=parser.get_default("extract_model"),
    )
    evaluate.add_argument(
        "--embedding-model",
        default=parser.get_default("embedding_model"),
    )
    evaluate.add_argument(
        "--answer-model",
        default=parser.get_default("answer_model"),
    )
    evaluate.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    evaluate.add_argument("--top-k", type=int, required=True)
    evaluate.add_argument("--overwrite", action="store_true")
    evaluate.add_argument("--samples", nargs="*")
    evaluate.set_defaults(function=command_evaluate)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
