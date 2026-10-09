#!/usr/bin/env python3
"""Split LoCoMo graph inputs from retrieval questions and offline labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/locomo10.json"
EXPECTED_SHA = "047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74"
DEST = ROOT / "outputs/locomo_hipporag2/data"


def main() -> None:
    global SOURCE, DEST
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEST)
    args = parser.parse_args()
    SOURCE, DEST = args.source.resolve(), args.output_dir.resolve()
    if DEST.exists():
        raise FileExistsError("data output must start absent")
    actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if actual != EXPECTED_SHA:
        raise ValueError(f"LoCoMo dataset SHA mismatch: {actual}")
    samples = json.loads(SOURCE.read_text(encoding="utf-8"))
    if len(samples) != 10 or sum(len(s["qa"]) for s in samples) != 1986:
        raise ValueError("unexpected LoCoMo sample or QA count")
    graph = [{"sample_id": s["sample_id"], "conversation": s["conversation"]} for s in samples]
    questions = [{"sample_id": s["sample_id"], "qa": [{"question": q["question"]} for q in s["qa"]]} for s in samples]
    labels = [{"sample_id": s["sample_id"], "qa": [{"evidence": q["evidence"], "category": q["category"]} for q in s["qa"]]} for s in samples]
    DEST.mkdir(parents=True, exist_ok=True)
    for name, value in (("graph_inputs", graph), ("retrieval_inputs", questions), ("offline_labels", labels)):
        (DEST / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset_sha256": actual, "samples": len(samples), "qa": 1986,
                      "turns": sum(len(v) for s in graph for k, v in s["conversation"].items() if k.startswith("session_") and isinstance(v, list))}))


if __name__ == "__main__":
    main()
