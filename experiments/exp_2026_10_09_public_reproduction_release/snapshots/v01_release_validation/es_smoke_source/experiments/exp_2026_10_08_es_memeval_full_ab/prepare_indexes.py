#!/usr/bin/env python3
"""Build one shared Memory embedding index per user from A graphs."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "code")]
from common.llm import set_api_key_from_env
from em_graph import EMGraph, EMGraphArtifactStore, MemoryEmbeddingIndex, QueryEmbeddingArtifact
from em_graph.recall.embedding_index import L2_NORMALIZATION
from em_graph.recall.tokenize import memory_search_text


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-file", type=Path, required=True)
    p.add_argument("--query-artifact", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, required=True)
    p.add_argument("--extract-model", required=True)
    p.add_argument("--embedding-model", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expected-memory-count", type=int, default=9368,
                   help="Full release defaults to 9368; override explicitly for non-metric smoke data")
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    samples = json.loads(args.data_file.read_text())
    query = QueryEmbeddingArtifact.load(args.query_artifact)
    query.validate_exact_dataset(samples, dataset_sha256=sha(args.data_file), model_name=args.embedding_model, role="context", normalization=L2_NORMALIZATION, protocol_identity={})
    set_api_key_from_env()
    spec = importlib.util.spec_from_file_location("current_stack", ROOT / "experiments/exp_2026_07_27_locomo_stack_refactor/run.py")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    store = EMGraphArtifactStore.from_env(str(args.cache_dir))
    text_cache = base.TextEmbeddingCache(cache_file=str(store.text_embedding_cache_path(args.embedding_model)), flush_every=10)
    unique_texts = {}
    for sample in samples:
        path = base.build_graph(sample, extract_model=args.extract_model, store=store, memory_only=True, graph_profile=base.VARIANTS["A"]["graph"])
        graph = EMGraph.load_from_file(str(path))
        for memory in graph.memories.values():
            text = memory_search_text(memory) or memory.dia_id
            key = text_cache.cache_key(text, args.embedding_model, "context")
            if key in unique_texts and unique_texts[key] != text:
                raise RuntimeError(f"text-cache key collision: {key}")
            unique_texts.setdefault(key, text)
    memory_count = sum(
        sum(len(turns) for key, turns in sample["conversation"].items() if isinstance(turns, list))
        for sample in samples
    )
    if memory_count != args.expected_memory_count or not 0 < len(unique_texts) <= memory_count:
        raise RuntimeError(
            f"unexpected Memory coverage: {len(unique_texts)} unique texts / {memory_count} turns"
        )
    prewarm = MemoryEmbeddingIndex(memory_ids=[], vectors=np.zeros((0, 0), dtype=np.float32), model_name=args.embedding_model, normalization=L2_NORMALIZATION, use_text_cache=False)
    prewarm._embed_texts(list(unique_texts.values()), role="context", show_progress=True, text_cache=text_cache)
    text_cache.flush()
    records = []
    for sample in samples:
        recall = base._load_recall(sample, variant="A", extract_model=args.extract_model, embedding_model=args.embedding_model, store=store, text_cache=text_cache, query_cache=query, strict_query_cache=True)
        profiled = base._profiled_sample(sample, base.VARIANTS["A"]["graph"])
        path = store.embedding_index_path(sample["sample_id"], identity=base._embedding_identity(profiled, args.embedding_model, graph_profile=base.VARIANTS["A"]["graph"], normalization=L2_NORMALIZATION, runtime_identity=None))
        records.append({"sample_id": sample["sample_id"], "index_path": str(path.resolve()), "index_sha256": sha(path), "memory_count": len(recall.graph.memories), "embedding_usage": recall.embedding_index.embedding_usage()})
        print(f"prepared {sample['sample_id']}: {len(recall.graph.memories)} vectors", flush=True)
    text_cache.flush()
    result = {"status": "pass", "dataset_sha256": sha(args.data_file), "query_artifact_sha256": sha(args.query_artifact), "embedding_model": args.embedding_model, "normalization": L2_NORMALIZATION, "records": records, "query_lookup_count": query.hits, "query_misses": query.misses}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "pass", "memory_count": sum(x["memory_count"] for x in records)}, indent=2))


if __name__ == "__main__":
    main()
