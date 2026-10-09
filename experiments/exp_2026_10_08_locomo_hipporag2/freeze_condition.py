#!/usr/bin/env python3
"""Create an immutable per-conversation parameter/source snapshot before API use."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import shlex
import subprocess


ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
UPSTREAM = ROOT / "outputs/hipporag_upstream"
UPSTREAM_COMMIT = "d5c8329422e0a0b834a15874545cb6a74b4f9b26"
GRAPH_FILE = ROOT / "outputs/locomo_hipporag2/data/graph_inputs.json"
RETRIEVAL_FILE = ROOT / "outputs/locomo_hipporag2/data/retrieval_inputs.json"
PROMPT_FILE = EXP / "rerank_2demo.json"
OUTPUT_ROOT = ROOT / "outputs/locomo_hipporag2/conditions"
BASE_URL = "https://api.openai.com/v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    global UPSTREAM, GRAPH_FILE, RETRIEVAL_FILE, OUTPUT_ROOT, BASE_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--mode", choices=("pilot", "full"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-chat-attempts", type=int, required=True)
    parser.add_argument("--upstream", type=Path, default=UPSTREAM)
    parser.add_argument("--data-dir", type=Path, default=GRAPH_FILE.parent)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--snapshot-root", type=Path, default=EXP / "snapshots")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--python", default=str(ROOT / "outputs/hipporag_venv/bin/python"))
    args = parser.parse_args()
    UPSTREAM = args.upstream.resolve()
    GRAPH_FILE = args.data_dir.resolve() / "graph_inputs.json"
    RETRIEVAL_FILE = args.data_dir.resolve() / "retrieval_inputs.json"
    OUTPUT_ROOT = args.output_root.resolve()
    BASE_URL = args.base_url
    if args.max_chat_attempts < 1:
        raise ValueError("max chat attempts must be positive")
    if subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip() != UPSTREAM_COMMIT:
        raise ValueError("upstream commit differs from pinned commit")
    graph_samples = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    retrieval_samples = json.loads(RETRIEVAL_FILE.read_text(encoding="utf-8"))
    graph_sample = next((s for s in graph_samples if s["sample_id"] == args.user_id), None)
    retrieval_sample = next((s for s in retrieval_samples if s["sample_id"] == args.user_id), None)
    if graph_sample is None or retrieval_sample is None:
        raise ValueError("user is not present in both frozen data files")
    turn_count = sum(len(v) for k, v in graph_sample["conversation"].items() if k.startswith("session_") and isinstance(v, list))
    qa_count = len(retrieval_sample["qa"])
    if args.mode == "pilot" and (turn_count < 20 or qa_count < 3):
        raise ValueError("pilot requires at least 20 turns and three QA")
    output_dir = OUTPUT_ROOT / args.run_id
    snapshot_dir = args.snapshot_root.resolve() / args.run_id
    if output_dir.exists() or snapshot_dir.exists():
        raise FileExistsError("condition output and snapshot must start absent")
    parameters = {
        "schema": "locomo_hipporag2_parameters_v1",
        "status": "frozen",
        "run_class": "diagnostic",
        "run_id": args.run_id,
        "mode": args.mode,
        "user_id": args.user_id,
        "full_turn_count": turn_count,
        "full_qa_count": qa_count,
        "dataset_sha256": "047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74",
        "pilot_turns": 20 if args.mode == "pilot" else None,
        "pilot_qa": 3 if args.mode == "pilot" else None,
        "graph_input": str(GRAPH_FILE),
        "retrieval_input": str(RETRIEVAL_FILE),
        "rerank_prompt": str(PROMPT_FILE),
        "upstream_root": str(UPSTREAM),
        "upstream_commit": UPSTREAM_COMMIT,
        "output_dir": str(output_dir),
        "sha256": {"graph": sha(GRAPH_FILE), "retrieval": sha(RETRIEVAL_FILE), "prompt": sha(PROMPT_FILE)},
        "openai_base_url": BASE_URL,
        "llm_model": "gpt-3.5-turbo-0125",
        "embedding_model": "text-embedding-3-small",
        "temperature": 0.0,
        "llm_supports_max_completion_tokens": False,
        "max_retry_attempts": 2,
        "openie_max_workers": 4,
        "openie_ner_max_tokens": 2048,
        "openie_triple_max_tokens": 4096,
        "linking_top_k": 5,
        "damping": 0.5,
        "passage_node_weight": 0.05,
        "top_k": 25,
        "max_chat_attempts": args.max_chat_attempts,
        "answer_model": None,
        "judge_model": None,
        "random_seed": None,
        "source_files": {name: sha(EXP / name) for name in ("run_retrieval.py", "freeze_condition.py", "make_rerank_prompt.py", "prepare_data.py")},
    }
    snapshot_dir.mkdir(parents=True)
    parameter_file = snapshot_dir / "parameters.json"
    parameter_file.write_text(json.dumps(parameters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(EXP / "run_retrieval.py", snapshot_dir / "run_retrieval.py")
    shutil.copy2(PROMPT_FILE, snapshot_dir / "rerank_2demo.json")
    command = (
        "#!/bin/zsh\n"
        "set -e\n"
        f"cd {shlex.quote(str(ROOT))}\n"
        ": ${OPENAI_API_KEY:?Export OPENAI_API_KEY before running}\n"
        f"export OPENAI_BASE_URL={shlex.quote(BASE_URL)}\n"
        f"export RESEARCH_RUN_CLASS=diagnostic\n"
        f"export RESEARCH_PARAMETER_SNAPSHOT={shlex.quote(str(parameter_file))}\n"
        f"export RESEARCH_CONDITION_DIR={shlex.quote(str(output_dir))}\n"
        f"{shlex.quote(args.python)} {shlex.quote(str(EXP / 'run_retrieval.py'))} --parameters {shlex.quote(str(parameter_file))}\n"
    )
    (snapshot_dir / "command.sh").write_text(command, encoding="utf-8")
    (snapshot_dir / "NOTES.md").write_text(
        f"# {args.run_id}\n\nFrozen before API calls. Mode: {args.mode}; user: {args.user_id}; "
        "gold is absent from the runner. If interrupted, treat the condition as diagnostic.\n",
        encoding="utf-8",
    )
    print(parameter_file)


if __name__ == "__main__":
    main()
