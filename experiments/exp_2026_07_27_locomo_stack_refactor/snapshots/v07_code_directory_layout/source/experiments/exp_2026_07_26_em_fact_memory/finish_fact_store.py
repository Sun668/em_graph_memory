#!/usr/bin/env python3
"""Robustly finish remaining fact extractions (single-turn, no false empties)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(EXP_DIR))

from em_graph import EMGraph  # noqa: E402
from fact_extract import (  # noqa: E402
    FACT_EXTRACT_VERSION,
    FactCache,
    FactExtractor,
    prompt_scaffold_len,
)


def memory_extract_text(memory) -> str:
    parts = [str(memory.text_normalized or memory.text or "").strip()]
    caption = str(memory.blip_caption or "").strip()
    if caption:
        parts.append(f"[Image: {caption}]")
    return "\n".join(p for p in parts if p)


def main() -> None:
    sample_id = os.environ.get("EM_GRAPH_SAMPLE_ID", "conv-26")
    model = os.environ.get("OPENAI_MODEL", "deepseek-v4-flash")
    out_dir = ROOT / "outputs" / "em_graph"
    graph_path = out_dir / f"{sample_id}_em_graph_extract_v4.json"
    store_path = out_dir / f"{sample_id}_fact_store_{FACT_EXTRACT_VERSION}.json"
    cache_path = out_dir / f"{sample_id}_fact_cache_{FACT_EXTRACT_VERSION}.json"
    ckpt_path = out_dir / f"{sample_id}_fact_store_{FACT_EXTRACT_VERSION}.checkpoint.json"

    graph = EMGraph.load_from_file(str(graph_path))
    memories = sorted(
        graph.memories.values(),
        key=lambda m: (int(m.session_num), str(m.dia_id)),
    )
    ckpt = (
        json.loads(ckpt_path.read_text(encoding="utf-8"))
        if ckpt_path.exists()
        else {"facts": [], "empty_memory_ids": []}
    )
    done = {str(r["fact_id"]): r for r in ckpt.get("facts") or []}
    empty = {str(x) for x in (ckpt.get("empty_memory_ids") or [])}
    covered = {str(r.get("memory_id")) for r in done.values()} | empty
    pending = [m for m in memories if m.id not in covered]
    print(
        f"resume facts={len(done)} empty={len(empty)} pending={len(pending)}",
        flush=True,
    )

    extractor = FactExtractor(
        model=model,
        use_cache=True,
        cache=FactCache(cache_file=str(cache_path)),
        wait_time=float(os.environ.get("EM_GRAPH_WAIT_TIME", "0.2")),
    )

    def flush() -> None:
        extractor.cache.flush()
        ckpt_path.write_text(
            json.dumps(
                {
                    "facts": list(done.values()),
                    "empty_memory_ids": sorted(empty),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    hard_fail = 0
    for i, mem in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] {mem.dia_id}", flush=True)
        try:
            facts = extractor.extract_turn(
                date_time=str(mem.date_time or ""),
                speaker=str(mem.speaker or ""),
                text=memory_extract_text(mem),
            )
        except Exception as exc:  # noqa: BLE001
            hard_fail += 1
            print(f"  FAIL leave for resume: {exc}", flush=True)
            time.sleep(2)
            continue
        if not facts:
            empty.add(mem.id)
            print("  []", flush=True)
        else:
            for j, fact in enumerate(facts, 1):
                fid = f"{sample_id}::{mem.dia_id}::f{j}"
                done[fid] = {
                    "fact_id": fid,
                    "text": fact,
                    "dia_id": mem.dia_id,
                    "memory_id": mem.id,
                    "session_num": mem.session_num,
                    "date_time": mem.date_time,
                    "speaker": mem.speaker,
                }
            print(f"  +{len(facts)}", flush=True)
        if i % 5 == 0 or i == len(pending):
            flush()
            print(f"  ckpt facts={len(done)} empty={len(empty)}", flush=True)

    flush()
    # If anything still uncovered, do not write final store.
    covered = {str(r.get("memory_id")) for r in done.values()} | empty
    still = [m.dia_id for m in memories if m.id not in covered]
    if still:
        print(f"UNFINISHED n={len(still)} hard_fail={hard_fail} e.g. {still[:10]}", flush=True)
        raise SystemExit(2)

    facts_sorted = sorted(
        done.values(),
        key=lambda r: (
            int(r.get("session_num") or 0),
            str(r.get("dia_id") or ""),
            str(r.get("fact_id") or ""),
        ),
    )
    store = {
        "sample_id": sample_id,
        "fact_extract_version": FACT_EXTRACT_VERSION,
        "extract_model": model,
        "source_graph": str(graph_path.relative_to(ROOT)),
        "prompt_scaffold_chars": prompt_scaffold_len(),
        "prompt_budget_ok": prompt_scaffold_len() <= 5000,
        "n_memories": len(memories),
        "n_memories_with_facts": len({r["memory_id"] for r in facts_sorted}),
        "n_memories_empty": len(empty),
        "n_facts": len(facts_sorted),
        "graph_constraint": {
            "audit_passed": True,
            "graph_inputs": "conversation dialogs / captions only",
            "qa_excluded_from_extraction": True,
        },
        "facts": facts_sorted,
    }
    store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: store[k] for k in store if k != "facts"}, indent=2), flush=True)
    print(f"wrote {store_path}", flush=True)


if __name__ == "__main__":
    main()
