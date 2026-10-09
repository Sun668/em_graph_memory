#!/usr/bin/env python3
"""Fetch a checksum-pinned public release and run the original local adapter."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
COMMIT = "692624208acc077b8867698c1d6fcd998dee641a"
URL = f"https://raw.githubusercontent.com/slptongji/ES-MemEval/{COMMIT}/data/evo_emo.json"
RAW_SHA = "f30698e87fddaeff51270a666c654da604f487a3456ec60d2b6ae08a6fecd420"
ADAPTED_SHA = "a81824fdbfc9e94ee9c2e510b8d9f45a6430d0cfe84d324cfaf2ea5a74686ed9"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw-file", type=Path, help="Use an existing official raw file instead of downloading")
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    raw = args.raw_file.read_bytes() if args.raw_file else urllib.request.urlopen(URL, timeout=60).read()
    if hashlib.sha256(raw).hexdigest() != RAW_SHA:
        raise ValueError("official release checksum differs; do not silently substitute another release")
    spec = importlib.util.spec_from_file_location("release_adapter", ROOT / "experiments/shared/evo_emo_adapter.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    adapted = [adapter.convert_seeker(seeker) for seeker in json.loads(raw)]
    encoded = json.dumps(adapted, ensure_ascii=False, indent=2).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != ADAPTED_SHA:
        raise ValueError("adapted dataset differs from the paper's data identity")
    output.mkdir(parents=True)
    (output / "raw.json").write_bytes(raw)
    (output / "adapted.json").write_bytes(encoded)
    subprocess.run([sys.executable, str(EXP / "prepare_full.py"), "--source", str(output / "adapted.json"), "--output-dir", str(output / "split")], check=True)
    (output / "provenance.json").write_text(json.dumps({"upstream_commit": COMMIT, "url": URL, "raw_sha256": RAW_SHA, "adapted_sha256": ADAPTED_SHA, "adapter": "experiments/shared/evo_emo_adapter.py", "graph_inputs": "conversation only", "gold": "offline labels only"}, indent=2) + "\n")


if __name__ == "__main__":
    main()
