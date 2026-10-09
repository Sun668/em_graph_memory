#!/usr/bin/env python3
"""Fresh ES graph/embedding/retrieval smoke, explicitly without metric scoring."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/exp_2026_10_08_es_memeval_full_ab"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, required=True, help="prepare_release_data.py split directory")
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    if not os.environ.get("OPENAI_API_KEY"):
        p.error("Export OPENAI_API_KEY and OPENAI_BASE_URL for the authorized API smoke")
    graph = json.loads((args.data_dir / "graph_inputs.json").read_text())[0]
    query = json.loads((args.data_dir / "questions.json").read_text())[0]
    remaining = 20
    conversation = {}
    for key, value in graph["conversation"].items():
        if isinstance(value, list):
            if remaining:
                conversation[key] = value[:remaining]
                remaining -= len(conversation[key])
        else:
            conversation[key] = value
    if remaining or len(query["qa"]) < 3:
        raise ValueError("smoke requires 20 turns and 3 questions")
    graph = [{"sample_id": graph["sample_id"], "conversation": conversation}]
    retrieval = [{**graph[0], "qa": query["qa"][:3]}]
    output.mkdir(parents=True)
    for name, payload in (("graph", graph), ("retrieval", retrieval)):
        (output / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    manifest = {}
    for source in list(EXP.glob("*.py")) + [Path(__file__), ROOT / "experiments/exp_2026_07_27_locomo_stack_refactor/run.py"]:
        relative = source.relative_to(ROOT)
        target = output / "source_snapshot" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest[str(relative)] = hashlib.sha256(source.read_bytes()).hexdigest()
    (output / "source_snapshot/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    commands = []
    def run(command):
        commands.append(command)
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        subprocess.run(command, check=True, cwd=ROOT)
    cache = output / "cache"
    run([sys.executable, str(EXP / "prepare_a.py"), "--data-file", str(output / "graph.json"), "--cache-dir", str(cache), "--extract-model", "gpt-3.5-turbo-0125", "--output", str(output / "a_graphs.json")])
    run([sys.executable, str(EXP / "prepare_query_embeddings.py"), "--data-file", str(output / "retrieval.json"), "--output", str(output / "query.npz"), "--report", str(output / "query_report.json")])
    run([sys.executable, str(EXP / "prepare_indexes.py"), "--data-file", str(output / "retrieval.json"), "--query-artifact", str(output / "query.npz"), "--cache-dir", str(cache), "--extract-model", "gpt-3.5-turbo-0125", "--embedding-model", "text-embedding-3-small", "--expected-memory-count", "20", "--output", str(output / "indexes.json")])
    reports = []
    for stage in ("graph", "A", "B_embed", "B"):
        snapshot, condition = output / "snapshots" / stage, output / "conditions" / stage
        command = [sys.executable, str(EXP / "freeze_stage.py"), "--stage", stage, "--run-id", f"release_v109_smoke_{stage}", "--data-file", str(output / ("graph.json" if stage == "graph" else "retrieval.json")), "--cache-dir", str(cache), "--output-dir", str(condition), "--snapshot-dir", str(snapshot), "--workers", "2"]
        if stage != "graph":
            command += ["--query-artifact", str(output / "query.npz")]
        run(command)
        run(["sh", str(snapshot / "command.sh")])
        result = json.loads((condition / "result.json").read_text())
        if result["status"] != "complete":
            raise ValueError(f"{stage}: incomplete")
        if stage != "graph":
            if len(result["rows"]) != 3 or any(len(r["context_ids"]) != 20 or len(set(r["context_ids"])) != 20 for r in result["rows"]):
                raise ValueError("wrong smoke retrieval coverage")
            if result["query_usage"]["cache_misses"] or result["query_usage"]["live_embedding_requests"]:
                raise ValueError("query vectors changed during retrieval")
            reports.append({"variant": stage, "qa_count": 3, "context_ids_per_question": 20, "graph_audit": result["graph_constraint"]["status"], "prompt_audit": result["prompt_budget"]["status"]})
    a, be = (json.loads((output / "conditions" / v / "result.json").read_text())["rows"] for v in ("A", "B_embed"))
    if [r["context_ids"] for r in a] != [r["context_ids"] for r in be]:
        raise ValueError("A/B_embed ordered parity failed")
    report = {"status": "pass", "classification": "non-metric diagnostic", "sample_id": graph[0]["sample_id"], "conversation_turns": 20, "qa_count": 3, "conditions": reports, "a_b_embed_parity": "pass", "answer_generation": "not run", "judge": "not run", "metrics": "not scored", "commands": "commands.json", "source": "source_snapshot/manifest.json"}
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
