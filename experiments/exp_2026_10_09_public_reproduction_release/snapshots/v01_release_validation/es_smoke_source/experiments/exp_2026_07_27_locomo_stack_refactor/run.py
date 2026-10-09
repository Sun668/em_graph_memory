#!/usr/bin/env python3
"""Build EM graphs and hand their single recall interface to LoCoMo."""

from __future__ import annotations

import argparse
import copy
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
    RETRIEVAL_SCORE_VERSION,
    EMGraph,
    EMGraphArtifactStore,
    EMGraphConfig,
    EMGraphRecall,
    EMGraphRecallRouter,
    EntityBM25Index,
    EntityCache,
    EntityExtractor,
    MemoryEmbeddingIndex,
    QueryEmbeddingArtifact,
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
from em_graph.recall.embedding_index import (
    L2_NORMALIZATION,
    SUPPORTED_NORMALIZATIONS,
    dragon_encoder_ids,
    dragon_encoder_revisions,
    embedding_protocol_identity,
    embedding_runtime_identity,
)
from em_graph.recall.retrieval import SEMANTIC_SCORE_NORMALIZATIONS

_DEFAULT_GRAPH_PROFILE: Dict[str, Any] = {
    "memory_only": False,
    "use_caption": True,
    "use_time_annotations": True,
    "add_speaker_as_entity": True,
}
_DEFAULT_RECALL: Dict[str, Any] = {
    "entity_weight": 0.30,
    "semantic_weight": 0.70,
    "semantic_score_normalization": "none",
    "expand_sequence": True,
    "force_full_pool": False,
    "sequence_secondary_scale": 0.5,
    "entity_min_rel_score": 0.5,
    "entity_top_k_per_key": 20,
    "who_only_dampen": 0.25,
    "degree_discount": True,
}


def _variant(
    *,
    graph: Optional[Mapping[str, Any]] = None,
    recall: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "graph": {**_DEFAULT_GRAPH_PROFILE, **dict(graph or {})},
        "recall": {**_DEFAULT_RECALL, **dict(recall or {})},
    }


VARIANTS: Dict[str, Dict[str, Any]] = {
    "A": {
        **_variant(
            graph={"memory_only": True},
            recall={
                "entity_weight": 0.0,
                "semantic_weight": 1.0,
                "expand_sequence": False,
                "force_full_pool": True,
            },
        )
    },
    "B": _variant(),
    "B_gate": _variant(
        recall={
            "entity_weight": 0.0,
            "semantic_weight": 1.0,
            "expand_sequence": False,
        }
    ),
    "B_gate_seq": _variant(
        recall={
            "entity_weight": 0.0,
            "semantic_weight": 1.0,
            "expand_sequence": True,
        }
    ),
    "B_entity": _variant(
        recall={"entity_weight": 1.0, "semantic_weight": 0.0}
    ),
    "B_embed": _variant(
        recall={
            "entity_weight": 0.0,
            "semantic_weight": 1.0,
            "expand_sequence": False,
            "force_full_pool": True,
        }
    ),
    "B_noseq": _variant(recall={"expand_sequence": False}),
    "A_no_caption": _variant(
        graph={"memory_only": True, "use_caption": False},
        recall={
            "entity_weight": 0.0,
            "semantic_weight": 1.0,
            "expand_sequence": False,
            "force_full_pool": True,
        },
    ),
    "B_no_caption": _variant(graph={"use_caption": False}),
    "A_raw_text": _variant(
        graph={"memory_only": True, "use_time_annotations": False},
        recall={
            "entity_weight": 0.0,
            "semantic_weight": 1.0,
            "expand_sequence": False,
            "force_full_pool": True,
        },
    ),
    "B_raw_text": _variant(graph={"use_time_annotations": False}),
    "B_no_speaker": _variant(
        graph={"add_speaker_as_entity": False}
    ),
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


def _profiled_sample(
    sample: Mapping[str, Any],
    graph_profile: Mapping[str, Any],
) -> Dict[str, Any]:
    profiled = copy.deepcopy(dict(sample))
    if bool(graph_profile.get("use_caption", True)):
        return profiled
    for key, dialogs in (profiled.get("conversation") or {}).items():
        if (
            str(key).startswith("session_")
            and not str(key).endswith("_date_time")
            and isinstance(dialogs, list)
        ):
            for dialog in dialogs:
                if isinstance(dialog, dict):
                    dialog.pop("blip_caption", None)
    return profiled


def _graph_identity(
    sample: Mapping[str, Any],
    extract_model: str,
    *,
    memory_only: bool = False,
    graph_profile: Optional[Mapping[str, Any]] = None,
) -> dict:
    resolved_memory_only = bool(
        dict(graph_profile or {}).get("memory_only", memory_only)
    )
    profile = {
        **_DEFAULT_GRAPH_PROFILE,
        **dict(graph_profile or {}),
        "memory_only": resolved_memory_only,
    }
    identity = {
        "schema": "em_graph_publish_v1",
        "graph_kind": (
            "memory_only" if resolved_memory_only else "entity_memory"
        ),
        "sample_id": str(sample.get("sample_id") or ""),
        "conversation_sha256": _sha256_json(sample.get("conversation") or {}),
        "dialog_normalization_version": DIALOG_NORMALIZATION_VERSION,
        "graph_profile": profile,
    }
    if not resolved_memory_only:
        identity.update(
            {
                "entity_extract_version": ENTITY_EXTRACT_VERSION,
                "extract_model": extract_model,
            }
        )
    return identity


def _embedding_identity(
    sample: Mapping[str, Any],
    model: str,
    *,
    graph_profile: Optional[Mapping[str, Any]] = None,
    normalization: str = L2_NORMALIZATION,
    runtime_identity: Optional[Mapping[str, Any]] = None,
) -> dict:
    profile = {**_DEFAULT_GRAPH_PROFILE, **dict(graph_profile or {})}
    identity = {
        "schema": "memory_embedding_index_publish_v1",
        "sample_id": str(sample.get("sample_id") or ""),
        "conversation_sha256": _sha256_json(sample.get("conversation") or {}),
        "dialog_normalization_version": DIALOG_NORMALIZATION_VERSION,
        "embedding_model": model,
        "memory_search_text_version": MEMORY_SEARCH_TEXT_VERSION,
        "use_caption": bool(profile["use_caption"]),
        "use_time_annotations": bool(profile["use_time_annotations"]),
    }
    if normalization != L2_NORMALIZATION:
        encoders = dragon_encoder_ids(model)
        revisions = dragon_encoder_revisions(model)
        identity.update(
            {
                "embedding_protocol": "raw_dual_encoder_dot_product_v1",
                "protocol_identity": embedding_protocol_identity(
                    model,
                    normalization,
                    runtime_identity=(
                        dict(runtime_identity)
                        if runtime_identity is not None
                        else None
                    ),
                ),
                "normalization": normalization,
                "query_encoder": encoders[0] if encoders else None,
                "context_encoder": encoders[1] if encoders else None,
                "query_encoder_revision": (
                    revisions[0] if revisions else None
                ),
                "context_encoder_revision": (
                    revisions[1] if revisions else None
                ),
            }
        )
    return identity


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
    graph_profile: Optional[Mapping[str, Any]] = None,
) -> Path:
    profile = {**_DEFAULT_GRAPH_PROFILE, **dict(graph_profile or {})}
    memory_only = bool(profile.get("memory_only", memory_only))
    profiled_sample = _profiled_sample(sample, profile)
    identity = _graph_identity(
        profiled_sample,
        extract_model,
        memory_only=memory_only,
        graph_profile=profile,
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
        graph = build_memory_graph(
            profiled_sample,
            auto_time_words=bool(profile["use_time_annotations"]),
        )
    else:
        graph = build_em_graph(
            profiled_sample,
            config=EMGraphConfig(
                model=extract_model,
                add_speaker_as_entity=bool(
                    profile["add_speaker_as_entity"]
                ),
                auto_time_words=bool(profile["use_time_annotations"]),
            ),
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
        "graph_profile": profile,
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
    embedding_normalization: str = L2_NORMALIZATION,
    embedding_runtime: Optional[Mapping[str, Any]] = None,
    recall_parameters: Optional[Mapping[str, Any]] = None,
    text_cache: Optional[TextEmbeddingCache] = None,
    query_cache: Optional[QueryEmbeddingArtifact] = None,
    strict_query_cache: bool = False,
    use_text_cache: bool = True,
    question_extractor: Optional[EntityExtractor] = None,
    question_cache: Optional[QuestionEntityCache] = None,
) -> EMGraphRecall:
    variant_spec = VARIANTS[variant]
    graph_profile = dict(variant_spec["graph"])
    profiled_sample = _profiled_sample(sample, graph_profile)
    memory_only = bool(graph_profile["memory_only"])
    graph_identity = _graph_identity(
        profiled_sample,
        extract_model,
        memory_only=memory_only,
        graph_profile=graph_profile,
    )
    sample_id = str(sample.get("sample_id") or "")
    graph_path = store.graph_path(sample_id, identity=graph_identity)
    if not graph_path.exists():
        raise FileNotFoundError(
            f"graph not built for {sample_id}: run build-graphs first"
        )
    graph = EMGraph.load_from_file(str(graph_path))
    assert_bipartite(graph)

    if text_cache is None and use_text_cache:
        text_cache = TextEmbeddingCache(
            cache_file=str(store.text_embedding_cache_path(embedding_model))
        )
    index_path = store.embedding_index_path(
        sample_id,
        identity=_embedding_identity(
            profiled_sample,
            embedding_model,
            graph_profile=graph_profile,
            normalization=embedding_normalization,
            runtime_identity=embedding_runtime,
        ),
    )
    embedding_index = MemoryEmbeddingIndex.build(
        graph,
        model_name=embedding_model,
        normalization=embedding_normalization,
        cache_path=str(index_path),
        text_cache=text_cache,
        query_cache=query_cache,
        strict_query_cache=strict_query_cache,
        use_text_cache=use_text_cache,
    )

    parameters = {
        **dict(variant_spec["recall"]),
        **dict(recall_parameters or {}),
    }
    full_pool = bool(parameters["force_full_pool"])
    if full_pool:
        question_extractor = None
        question_cache = None
    else:
        if question_extractor is None:
            question_extractor = _question_extractor(extract_model, store)
        if question_cache is None:
            question_cache = QuestionEntityCache(
                cache_file=str(store.question_entity_cache_path()),
                namespace=f"{ENTITY_EXTRACT_VERSION}::{extract_model}",
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
    data_path = Path(args.data_file).resolve()
    samples = _load_samples(data_path, args.samples)
    requested_variants = list(args.variants or ["A", "B"])
    if any(
        not bool(VARIANTS[variant]["graph"]["memory_only"])
        for variant in requested_variants
    ):
        set_api_key_from_env()
    store = EMGraphArtifactStore.from_env(args.cache_dir)
    for sample in samples:
        built_paths = set()
        for variant in requested_variants:
            profile = VARIANTS[variant]["graph"]
            path = build_graph(
                sample,
                extract_model=args.extract_model,
                store=store,
                memory_only=bool(profile["memory_only"]),
                graph_profile=profile,
            )
            if path in built_paths:
                continue
            built_paths.add(path)
            print(
                f"{variant} graph {sample['sample_id']}: {path}",
                flush=True,
            )


def _recall_parameters_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    parameters = dict(VARIANTS[args.variant]["recall"])
    overrides = {
        "entity_weight": args.entity_weight,
        "semantic_weight": args.semantic_weight,
        "semantic_score_normalization": getattr(
            args, "semantic_score_normalization", None
        ),
        "sequence_secondary_scale": args.sequence_scale,
        "entity_min_rel_score": args.entity_min_rel_score,
        "entity_top_k_per_key": args.entity_top_k_per_key,
        "who_only_dampen": args.who_only_dampen,
    }
    for key, value in overrides.items():
        if value is not None:
            parameters[key] = value
    if args.no_degree_discount:
        parameters["degree_discount"] = False
    if float(parameters["entity_weight"]) < 0.0:
        raise ValueError("entity_weight must be non-negative")
    if float(parameters["semantic_weight"]) < 0.0:
        raise ValueError("semantic_weight must be non-negative")
    if (
        parameters["semantic_score_normalization"]
        not in SEMANTIC_SCORE_NORMALIZATIONS
    ):
        raise ValueError("unsupported semantic_score_normalization")
    if (
        float(parameters["entity_weight"]) == 0.0
        and float(parameters["semantic_weight"]) == 0.0
    ):
        raise ValueError("entity_weight and semantic_weight cannot both be zero")
    if float(parameters["sequence_secondary_scale"]) < 0.0:
        raise ValueError("sequence_scale must be non-negative")
    if not 0.0 <= float(parameters["entity_min_rel_score"]) <= 1.0:
        raise ValueError("entity_min_rel_score must be in [0, 1]")
    if int(parameters["entity_top_k_per_key"]) <= 0:
        raise ValueError("entity_top_k_per_key must be positive")
    if float(parameters["who_only_dampen"]) < 0.0:
        raise ValueError("who_only_dampen must be non-negative")
    return parameters


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def command_evaluate(args: argparse.Namespace) -> None:
    set_api_key_from_env()
    data_path = Path(args.data_file).resolve()
    samples = _load_samples(data_path, args.samples)
    recall_parameters = _recall_parameters_from_args(args)
    store = EMGraphArtifactStore.from_env(args.cache_dir)
    use_text_cache = args.embedding_normalization == L2_NORMALIZATION
    embedding_runtime = (
        None
        if use_text_cache
        else embedding_runtime_identity(args.embedding_model)
    )
    text_cache = (
        TextEmbeddingCache(
            cache_file=str(
                store.text_embedding_cache_path(args.embedding_model)
            )
        )
        if use_text_cache
        else None
    )
    full_pool = bool(recall_parameters["force_full_pool"])
    shared_question_extractor = (
        None if full_pool else _question_extractor(args.extract_model, store)
    )
    shared_question_cache = (
        None
        if full_pool
        else QuestionEntityCache(
            cache_file=str(store.question_entity_cache_path()),
            namespace=f"{ENTITY_EXTRACT_VERSION}::{args.extract_model}",
        )
    )
    recalls = {
        str(sample["sample_id"]): _load_recall(
            sample,
            variant=args.variant,
            extract_model=args.extract_model,
            embedding_model=args.embedding_model,
            embedding_normalization=args.embedding_normalization,
            embedding_runtime=embedding_runtime,
            store=store,
            recall_parameters=recall_parameters,
            text_cache=text_cache,
            use_text_cache=use_text_cache,
            question_extractor=shared_question_extractor,
            question_cache=shared_question_cache,
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
    _write_json(
        audit_file,
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
                "dialog query",
                "img_url",
            ],
            "answer_recall": "EM graph retrieval",
            "variant": args.variant,
            "graph_profile": VARIANTS[args.variant]["graph"],
            "recall_parameters": recall_parameters,
            "retrieval_score_version": RETRIEVAL_SCORE_VERSION,
            "retrieval_target_top_k": int(args.top_k),
            "sample_ids": [str(sample["sample_id"]) for sample in samples],
            "official_category5_scope": (
                "compatibility diagnostic; gold answer appears in the "
                "unchanged official multiple-choice prompt"
            ),
            "categories_1_4_scope": (
                "conversation-only graph and graph-retrieval promotion scope"
            ),
            "prompt_budget": {
                "entity_scaffold_chars": len(
                    ENTITY_EXTRACTION_PROMPT.format(text="")
                ),
                "limit_chars": 5000,
                "pass": len(
                    ENTITY_EXTRACTION_PROMPT.format(text="")
                )
                <= 5000,
            },
        },
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
    build.add_argument(
        "--variants",
        nargs="+",
        choices=sorted(VARIANTS),
        default=["A", "B"],
        help=(
            "Build the distinct graph/input profiles required by these "
            "variants; identical profiles are deduplicated."
        ),
    )
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
        "--embedding-normalization",
        choices=sorted(SUPPORTED_NORMALIZATIONS),
        default=L2_NORMALIZATION,
    )
    evaluate.add_argument(
        "--answer-model",
        default=parser.get_default("answer_model"),
    )
    evaluate.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    evaluate.add_argument("--top-k", type=int, required=True)
    evaluate.add_argument("--entity-weight", type=float)
    evaluate.add_argument("--semantic-weight", type=float)
    evaluate.add_argument(
        "--semantic-score-normalization",
        choices=sorted(SEMANTIC_SCORE_NORMALIZATIONS),
    )
    evaluate.add_argument("--sequence-scale", type=float)
    evaluate.add_argument("--entity-min-rel-score", type=float)
    evaluate.add_argument("--entity-top-k-per-key", type=int)
    evaluate.add_argument("--who-only-dampen", type=float)
    evaluate.add_argument("--no-degree-discount", action="store_true")
    evaluate.add_argument("--overwrite", action="store_true")
    evaluate.add_argument("--samples", nargs="*")
    evaluate.set_defaults(function=command_evaluate)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
