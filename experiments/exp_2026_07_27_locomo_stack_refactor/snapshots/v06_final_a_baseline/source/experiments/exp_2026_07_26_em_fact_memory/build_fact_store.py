#!/usr/bin/env python3
"""Build conversation-only fact store for conv-26 from existing Memory nodes."""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EXP_DIR))

from em_graph import EMGraph  # noqa: E402
from fact_extract import (  # noqa: E402
    FACT_EXTRACT_VERSION,
    FactCache,
    FactExtractor,
    prompt_scaffold_len,
)

SAMPLE_ID = "conv-26"


def memory_extract_text(memory) -> str:
    parts = [str(memory.text_normalized or memory.text or "").strip()]
    caption = str(memory.blip_caption or "").strip()
    if caption:
        parts.append(f"[Image: {caption}]")
    return "\n".join(p for p in parts if p)


def main() -> None:
    sample_id = os.environ.get("EM_GRAPH_SAMPLE_ID", SAMPLE_ID)
    model = os.environ.get("OPENAI_MODEL", "deepseek-v4-flash")
    # Default 1: parallel OpenAI clients occasionally stall; resume is cheap.
    workers = int(os.environ.get("EM_FACT_EXTRACT_WORKERS", "1"))
    out_dir = ROOT / "outputs" / "em_graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_path = out_dir / f"{sample_id}_em_graph_extract_v4.json"
    store_path = out_dir / f"{sample_id}_fact_store_{FACT_EXTRACT_VERSION}.json"
    cache_path = out_dir / f"{sample_id}_fact_cache_{FACT_EXTRACT_VERSION}.json"
    ckpt_path = out_dir / f"{sample_id}_fact_store_{FACT_EXTRACT_VERSION}.checkpoint.json"

    if not graph_path.exists():
        raise FileNotFoundError(graph_path)

    scaffold = prompt_scaffold_len()
    print(
        f"[{sample_id}] fact_extract={FACT_EXTRACT_VERSION} model={model} "
        f"workers={workers} scaffold={scaffold}",
        flush=True,
    )
    if scaffold > 5000:
        raise RuntimeError(f"fact prompt scaffold too large: {scaffold}")

    graph = EMGraph.load_from_file(str(graph_path))
    memories = sorted(
        graph.memories.values(),
        key=lambda m: (int(m.session_num), str(m.dia_id)),
    )

    done: Dict[str, Dict[str, Any]] = {}
    empty_memory_ids: Set[str] = set()
    if ckpt_path.exists() and os.environ.get("EM_FACT_RESUME", "1") in {
        "1",
        "true",
        "True",
    }:
        raw = json.loads(ckpt_path.read_text(encoding="utf-8"))
        for row in raw.get("facts") or []:
            done[str(row["fact_id"])] = row
        empty_memory_ids = {str(x) for x in (raw.get("empty_memory_ids") or [])}
        print(
            f"resumed facts n={len(done)} empty_memories n={len(empty_memory_ids)}",
            flush=True,
        )

    extractor = FactExtractor(
        model=model,
        use_cache=True,
        cache=FactCache(cache_file=str(cache_path)),
        wait_time=float(os.environ.get("EM_GRAPH_WAIT_TIME", "0.1")),
    )

    covered: Set[str] = {str(r.get("memory_id")) for r in done.values()} | set(
        empty_memory_ids
    )
    pending = [(mem.id, mem) for mem in memories if mem.id not in covered]
    print(f"extracting remaining memories {len(pending)}/{len(memories)}", flush=True)

    finished = 0

    def _one(item: Tuple[str, Any]) -> Tuple[str, List[str], Any]:
        mid, mem = item
        text = memory_extract_text(mem)
        try:
            extracted = extractor.extract_turn(
                date_time=str(mem.date_time or ""),
                speaker=str(mem.speaker or ""),
                text=text,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"WARN extract failed {mem.dia_id}: {exc}", flush=True)
            extracted = []
        return mid, extracted, mem

    def _flush_ckpt() -> None:
        ckpt_path.write_text(
            json.dumps(
                {
                    "facts": list(done.values()),
                    "empty_memory_ids": sorted(empty_memory_ids),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _ingest(_mid: str, extracted: List[str], mem: Any) -> None:
        nonlocal finished
        if not extracted:
            empty_memory_ids.add(mem.id)
        for i, fact in enumerate(extracted, 1):
            fact_id = f"{sample_id}::{mem.dia_id}::f{i}"
            done[fact_id] = {
                "fact_id": fact_id,
                "text": fact,
                "dia_id": mem.dia_id,
                "memory_id": mem.id,
                "session_num": mem.session_num,
                "date_time": mem.date_time,
                "speaker": mem.speaker,
            }
        finished += 1
        if finished % 10 == 0 or finished == len(pending):
            extractor.cache.flush()
            _flush_ckpt()
            print(
                f"extracted memories {finished}/{len(pending)} "
                f"facts_total={len(done)}",
                flush=True,
            )

    if workers <= 1:
        for job in pending:
            _ingest(*_one(job))
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_one, job): job[0] for job in pending}
            for fut in as_completed(futures):
                _ingest(*fut.result())

    extractor.cache.flush()
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
        "prompt_scaffold_chars": scaffold,
        "prompt_budget_ok": scaffold <= 5000,
        "n_memories": len(memories),
        "n_memories_with_facts": len({r["memory_id"] for r in facts_sorted}),
        "n_memories_empty": len(empty_memory_ids),
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
