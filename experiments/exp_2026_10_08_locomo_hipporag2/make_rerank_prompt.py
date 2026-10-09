#!/usr/bin/env python3
"""Freeze a bounded variant of HippoRAG 2's upstream fact-filter examples."""

import argparse
import ast
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.upstream / "src/hipporag/prompts/filter_default_prompt.py"
    assignment = ast.parse(source.read_text(encoding="utf-8")).body[0]
    default = ast.literal_eval(assignment.value)
    selected = dict(default)
    selected["prog"] = dict(default["prog"])
    selected["prog"]["demos"] = default["prog"]["demos"][:2]
    if len(default["prog"]["demos"]) != 10 or len(selected["prog"]["demos"]) != 2:
        raise ValueError("unexpected upstream fact-filter example count")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
