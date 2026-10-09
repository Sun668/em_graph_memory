#!/usr/bin/env python3
"""Freeze portable stage paths and identities without changing retrieval settings."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
TEMPLATES = {"graph": "v03_b_graph_frozen", "A": "v10_a_top25_frozen", "B_embed": "v11_b_embed_top25_frozen", "B": "v12_b_top25_frozen"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=TEMPLATES, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--data-file", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, required=True)
    p.add_argument("--query-artifact", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--snapshot-dir", type=Path, required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--prior-estimated-spend-usd", type=float, default=0.0,
                   help="Carry the already-spent candidate budget into the next paid stage")
    args = p.parse_args()
    for path in (args.output_dir, args.snapshot_dir):
        if path.exists():
            raise FileExistsError(path)
    data, cache, output, snapshot = (x.resolve() for x in (args.data_file, args.cache_dir, args.output_dir, args.snapshot_dir))
    samples = json.loads(data.read_text())
    turns = sum(len(v) for s in samples for v in s["conversation"].values() if isinstance(v, list))
    qa_count = sum(len(s.get("qa", [])) for s in samples)
    parameters = json.loads((EXP / "snapshots" / TEMPLATES[args.stage] / "parameters.json").read_text())
    parameters.update(run_id=args.run_id, classification="diagnostic")
    parameters["source"] = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "public_release": "v1.0.9", "historical_template": TEMPLATES[args.stage]}
    parameters["dataset"] = {"path": str(data), "sha256": sha(data), "sample_ids": [s["sample_id"] for s in samples], "sample_count": len(samples), "memory_count": turns, "qa_count": qa_count}
    parameters["cache_dir"] = str(cache)
    parameters["output_dir"] = str(output)
    parameters["cost_limits"]["prior_estimated_spend_usd"] = args.prior_estimated_spend_usd
    parameters["publication_use"] = "non-metric diagnostic" if qa_count < 100 else "retrieval-only; validate and snapshot before publication"
    parameters.pop("command", None)
    parameters.pop("caches", None)  # Never carry old file identities into a new run.
    parameters["resources"] = {"entity_workers": args.workers, "workers": 1, "output_dir": str(output)}
    parameters["gates"] = {"output_dir_absent": True, "qa_coverage": qa_count, "query_misses": 0, "live_embedding_requests": 0, "graph_conversation_only": True, "prompt_scaffold_max_chars": 5000}
    parameters["sampling"] = {"scope": "exact supplied data; no sampling", "seed": "not-applicable"}
    parameters["evaluation"] = {"status": "not-run", "gold_offline_only": True}
    parameter_path = snapshot / "parameters.json"
    command = [sys.executable, str(EXP / ("build_b_graphs.py" if args.stage == "graph" else "run_retrieval.py")), "--run-id", args.run_id, "--parameter-snapshot", str(parameter_path), "--data-file", str(data), "--cache-dir", str(cache), "--extract-model", parameters["models"]["extraction"], "--output-dir", str(output)]
    if args.stage == "graph":
        command += ["--workers", str(args.workers)]
        parameters.pop("source_commit", None)
    else:
        if args.query_artifact is None:
            p.error("retrieval stages require --query-artifact")
        query = args.query_artifact.resolve()
        sys.path.insert(0, str(ROOT / "code"))
        from em_graph import QueryEmbeddingArtifact
        from em_graph.recall.embedding_index import L2_NORMALIZATION
        artifact = QueryEmbeddingArtifact.load(query)
        artifact.validate_exact_dataset(samples, dataset_sha256=sha(data), model_name=parameters["models"]["embedding"], role="context", normalization=L2_NORMALIZATION, protocol_identity={})
        parameters["query_artifact"] = artifact.identity(query)
        command += ["--variant", args.stage, "--top-k", "25", "--embedding-model", parameters["models"]["embedding"], "--query-artifact", str(query)]
    parameters["source"]["files"] = {str(path.relative_to(ROOT)): sha(path) for path in [EXP / "entity_compat.py", Path(command[1]), ROOT / "experiments/exp_2026_07_27_locomo_stack_refactor/run.py", ROOT / "code/em_graph/recall/retrieval.py"]}
    parameters["command"] = shlex.join(command)
    snapshot.mkdir(parents=True)
    parameter_path.write_text(json.dumps(parameters, ensure_ascii=False, indent=2) + "\n")
    (snapshot / "command.sh").write_text("#!/bin/sh\nset -eu\n" + f"export RESEARCH_RUN_CLASS=diagnostic\nexport RESEARCH_PARAMETER_SNAPSHOT={shlex.quote(str(parameter_path))}\nexport RESEARCH_CONDITION_DIR={shlex.quote(str(output))}\n" + shlex.join(command) + "\n")
    # Record the actual executable sources before the stage starts.
    import shutil
    for relative in parameters["source"]["files"]:
        target = snapshot / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    print(parameter_path)


if __name__ == "__main__":
    main()
