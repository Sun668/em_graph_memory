#!/usr/bin/env python3
"""Build conversation-only dense-control graphs without model calls."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "code")]
from em_graph import EMGraph, EMGraphArtifactStore, assert_bipartite


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-file", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, required=True)
    p.add_argument("--extract-model", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    spec = importlib.util.spec_from_file_location("current_stack", ROOT / "experiments/exp_2026_07_27_locomo_stack_refactor/run.py")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    samples = json.loads(args.data_file.read_text())
    if any(set(sample) != {"sample_id", "conversation"} for sample in samples):
        raise ValueError("graph input may contain only sample_id and conversation")
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    store = EMGraphArtifactStore.from_env(str(args.cache_dir))
    profile = dict(base.VARIANTS["A"]["graph"])
    records = []
    for sample in samples:
        path = base.build_graph(sample, extract_model=args.extract_model, store=store, memory_only=True, graph_profile=profile)
        graph = EMGraph.load_from_file(str(path))
        assert_bipartite(graph)
        records.append({"sample_id": sample["sample_id"], "graph_path": str(path.resolve()), "graph_sha256": sha(path), "memory_count": len(graph.memories), "entity_count": len(graph.entities)})
    result = {"status": "pass", "data_sha256": sha(args.data_file), "source_commit": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "graph_profile": profile, "records": records, "qa_fields_absent": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
