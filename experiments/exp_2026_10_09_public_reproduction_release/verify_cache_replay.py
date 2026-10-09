#!/usr/bin/env python3
"""Execute all ES retrieval paths offline and require historical ordered-ID parity."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/exp_2026_10_08_es_memeval_full_ab"


def read(path):
    return json.loads(path.read_text())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-root", type=Path, required=True, help="Root containing data/, conditions/, query_vectors_retrieval.npz")
    p.add_argument("--cache-dir", type=Path, required=True, help="Use a copy of validated caches, not the original archive")
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    reports = []
    env = dict(os.environ, OPENAI_API_KEY="offline-cache-replay", OPENAI_BASE_URL="http://127.0.0.1:9/v1", EM_GRAPH_LLM_TIMEOUT="1", PYTHONDONTWRITEBYTECODE="1")
    for variant in ("A", "B_embed", "B"):
        run_id = f"release_v109_{variant}_cache_replay"
        snapshot, condition = output / "snapshots" / variant, output / "conditions" / variant
        freeze = [sys.executable, str(EXP / "freeze_stage.py"), "--stage", variant, "--run-id", run_id, "--data-file", str(args.artifact_root / "data/retrieval_inputs.json"), "--cache-dir", str(args.cache_dir), "--query-artifact", str(args.artifact_root / "query_vectors_retrieval.npz"), "--output-dir", str(condition), "--snapshot-dir", str(snapshot)]
        subprocess.run(freeze, check=True, cwd=ROOT, env=env)
        with (output / f"{variant}.log").open("w") as log:
            subprocess.run(["sh", str(snapshot / "command.sh")], check=True, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        result = read(condition / "result.json")
        historical = read(args.artifact_root / "conditions" / f"es1427_{variant}_top25_v01/result.json")
        current_ids = [(r["sample_id"], r["qa_index"], r["context_ids"]) for r in result["rows"]]
        previous_ids = [(r["sample_id"], r["qa_index"], r["context_ids"]) for r in historical["rows"]]
        if current_ids != previous_ids or len(current_ids) != 1427:
            raise ValueError(f"{variant}: ordered historical retrieval parity failed")
        query = result["query_usage"]
        if query["cache_misses"] or query["live_embedding_requests"]:
            raise ValueError("query artifact was not read-only and complete")
        if variant == "B":
            usage = read(condition / "provider_usage.json")
            # The endpoint is deliberately unreachable: cached replay must not call it.
            if usage.get("request_attempts", 0) or usage.get("request_count", 0) or usage.get("events"):
                raise ValueError("unexpected live chat attempt")
        reports.append({"variant": variant, "qa_count": len(current_ids), "ordered_context_parity": "pass", "query_cache_misses": 0, "live_embedding_requests": 0, "graph_audit": result["graph_constraint"]["status"], "prompt_audit": result["prompt_budget"]["status"]})
    a, be = (read(output / "conditions" / v / "result.json")["rows"] for v in ("A", "B_embed"))
    if [r["context_ids"] for r in a] != [r["context_ids"] for r in be]:
        raise ValueError("A/B_embed ordered control parity failed")
    report = {"status": "pass", "classification": "software migration validation; no new paper metric", "conditions": reports, "a_b_embed_parity": "pass", "models": {"extraction": "gpt-3.5-turbo-0125 cached", "embedding": "text-embedding-3-small frozen", "answer": "not run", "judge": "not run"}, "top_k": 25, "network": "unreachable localhost endpoint; zero live calls required"}
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
