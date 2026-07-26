#!/usr/bin/env python3
"""Matched publish stack: gpt-3.5 extract + text-embedding-3-small + gpt-3.5 F1.

Modes:
  build-graphs  — Entity→Memory graphs (gpt-3.5 extract-v4)
  A             — plain Dialog embedding RAG (no entity gate)
  B             — Entity→Memory 0.3/0.7 + sequence
  ablation      — B-entity / B-embed / B-noseq (+ B-full if missing)
  summarize     — write TABLE_GPT35_TES_COMPARE.md from result jsons

Artifact tag: gpt35_tes
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from em_graph import (  # noqa: E402
    EMGraph,
    EMGraphConfig,
    EntityBM25Index,
    EntityExtractor,
    MemoryEmbeddingIndex,
    TextEmbeddingCache,
    assert_bipartite,
    build_em_graph_from_file,
    ensure_memory_sequence_edges,
    extract_question_entity_keys,
    retrieve_dialog_ids,
)
from em_graph.config import ENTITY_EXTRACT_VERSION  # noqa: E402
from em_graph.models import MemoryNode  # noqa: E402
from em_graph.replace_pronouns import replace_pronouns  # noqa: E402
from experiments.shared.llm_client import run_chatgpt, set_openai_key  # noqa: E402

TAG = "gpt35_tes"
KS = (5, 10, 25, 50)
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
CAT_NAMES = {
    1: "Multi-hop",
    2: "Temporal",
    3: "Open-domain",
    4: "Single-hop",
    5: "Adversarial",
}
QA_PROMPT = """
Based on the above context, write an answer in the form of a short phrase for the following question. Answer with exact words from the context whenever possible.

Question: {} Short answer:
"""
QA_PROMPT_CAT_5 = """
Based on the above context, answer the following question. If the answer is not mentioned in the conversation, reply exactly: Not mentioned in the conversation.

Question: {} Short answer:
"""
TEMPORAL_SUFFIX = " Use DATE of CONVERSATION to answer with an approximate date."

VARIANTS = {
    "A": {
        "label": "plain_dialog_embed",
        "entity_weight": 0.0,
        "semantic_weight": 1.0,
        "expand_sequence": False,
        "force_full_pool": True,
        "need_entities": False,
    },
    "B": {
        "label": "em_full_0.3_0.7",
        "entity_weight": 0.3,
        "semantic_weight": 0.7,
        "expand_sequence": True,
        "force_full_pool": False,
        "need_entities": True,
    },
    "B_entity": {
        "label": "em_entity_only",
        "entity_weight": 1.0,
        "semantic_weight": 0.0,
        "expand_sequence": True,
        "force_full_pool": False,
        "need_entities": True,
    },
    "B_embed": {
        "label": "em_embed_fullpool",
        "entity_weight": 0.0,
        "semantic_weight": 1.0,
        "expand_sequence": False,
        "force_full_pool": True,
        "need_entities": True,  # uses same graph memories; entities unused
    },
    "B_noseq": {
        "label": "em_full_noseq",
        "entity_weight": 0.3,
        "semantic_weight": 0.7,
        "expand_sequence": False,
        "force_full_pool": False,
        "need_entities": True,
    },
}


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(str(text or "").lower())


def token_f1(gold: str, pred: str) -> float:
    g, p = tokenize(gold), tokenize(pred)
    if not g and not p:
        return 1.0
    if not g or not p:
        return 0.0
    common = len(set(g) & set(p))
    if common == 0:
        return 0.0
    precision = common / len(set(p))
    recall = common / len(set(g))
    return 2 * precision * recall / (precision + recall)


def recall_acc(gold: List[str], retrieved: List[str]) -> float:
    if not gold:
        return 1.0
    ctx = set(retrieved)
    return float(sum(1 for ev in gold if ev in ctx)) / float(len(gold))


def out_dir() -> Path:
    p = ROOT / "outputs" / "em_graph"
    p.mkdir(parents=True, exist_ok=True)
    return p


def graph_path(sample_id: str) -> Path:
    return out_dir() / f"{sample_id}_em_graph_extract_v4_{TAG}.json"


def memory_only_graph_path(sample_id: str) -> Path:
    return out_dir() / f"{sample_id}_em_graph_memory_only_{TAG}.json"


def emb_path(sample_id: str, emb_model: str, *, memory_only: bool = False) -> Path:
    safe = emb_model.replace("/", "_")
    if memory_only:
        return out_dir() / f"{sample_id}_memory_emb_memory_only_{TAG}_{safe}.npz"
    return out_dir() / f"{sample_id}_memory_emb_extract_v4_{TAG}_{safe}.npz"


def qkeys_path(sample_id: str) -> Path:
    return out_dir() / f"{sample_id}_qkeys_{TAG}.json"


def sample_ids() -> List[str]:
    data = json.loads((ROOT / "data" / "locomo10.json").read_text(encoding="utf-8"))
    return [str(s["sample_id"]) for s in data]


def format_dialog_line(memory: MemoryNode) -> str:
    line = f'{memory.speaker} said, "{memory.text}"'
    caption = str(memory.blip_caption or "").strip()
    if caption:
        line += f" and shared {caption}"
    return line


def build_context(graph: EMGraph, dia_ids: Sequence[str]) -> str:
    dia_to_mem = {m.dia_id: m for m in graph.memories.values()}
    lines = []
    for dia_id in dia_ids:
        memory = dia_to_mem.get(dia_id)
        if memory is None:
            continue
        lines.append(f"{memory.date_time}: {format_dialog_line(memory)}")
    return "\n".join(lines)


def build_answer_prompt(question: str, category: int, context: str) -> str:
    q = str(question or "").strip()
    if int(category) == 2:
        q = q + TEMPORAL_SUFFIX
    tail = QA_PROMPT_CAT_5.format(q) if int(category) == 5 else QA_PROMPT.format(q)
    return (context or "(no retrieved dialogs)") + "\n\n" + tail


def answer_one(question: str, category: int, context: str, model: str) -> str:
    prompt = build_answer_prompt(question, category, context)
    n_tokens = int(os.environ.get("EM_GRAPH_ANSWER_TOKENS", "512"))
    last_err: Optional[Exception] = None
    for _ in range(4):
        try:
            raw = run_chatgpt(
                prompt,
                model=model,
                num_tokens_request=n_tokens,
                temperature=0,
                wait_time=float(os.environ.get("EM_GRAPH_WAIT_TIME", "0.15")),
                max_retries=3,
                timeout=float(os.environ.get("EM_GRAPH_LLM_TIMEOUT", "180")),
            )
            text = str(raw or "").strip()
            if text:
                return text
            last_err = RuntimeError("empty answer")
            n_tokens = min(n_tokens * 2, 2048)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            n_tokens = min(n_tokens * 2, 2048)
    raise RuntimeError(f"answer failed: {last_err}")


def _build_one_graph(sample_id: str) -> Dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from em_graph import (
        EMGraph,
        EMGraphConfig,
        EntityExtractor,
        assert_bipartite,
        build_em_graph_from_file,
        ensure_memory_sequence_edges,
    )
    from em_graph.config import ENTITY_EXTRACT_VERSION

    set_openai_key()
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    data_file = ROOT / "data" / "locomo10.json"
    path = graph_path(sample_id)
    if path.exists():
        g = EMGraph.load_from_file(str(path))
        if not bool((g.stats or {}).get("partial")):
            return {
                "sample_id": sample_id,
                "status": "reused",
                "stats": g.stats,
                "path": str(path),
            }
    if ENTITY_EXTRACT_VERSION != "v4":
        raise RuntimeError(f"need extract v4, got {ENTITY_EXTRACT_VERSION}")
    cfg = EMGraphConfig(model=model)
    extractor = EntityExtractor(model=model)
    graph = build_em_graph_from_file(
        str(data_file),
        sample_id,
        config=cfg,
        extractor=extractor,
        checkpoint_path=str(path),
        checkpoint_every=40,
        max_workers=int(os.environ.get("EM_GRAPH_EXTRACT_WORKERS", "6")),
    )
    seq_n = ensure_memory_sequence_edges(graph)
    graph.stats = {
        **dict(graph.stats or {}),
        "memory_count": len(graph.memories),
        "entity_count": len(graph.entities),
        "edge_count": len(graph.edges),
        "memory_edge_count": seq_n,
        "entity_extract_version": "v4",
        "extract_model": model,
        "stack_tag": TAG,
    }
    assert_bipartite(graph)
    graph.save_to_file(str(path))
    return {
        "sample_id": sample_id,
        "status": "built",
        "stats": graph.stats,
        "path": str(path),
    }


def cmd_build_graphs(args: argparse.Namespace) -> None:
    set_openai_key()
    ids = args.samples or sample_ids()
    workers = int(args.graph_workers)
    print(
        f"[build-graphs] n={len(ids)} model={os.environ.get('OPENAI_MODEL')} "
        f"workers={workers}",
        flush=True,
    )
    results = []
    if workers <= 1:
        for sid in ids:
            print(f"[build-graphs] start {sid}", flush=True)
            results.append(_build_one_graph(sid))
            print(f"[build-graphs] done {sid} {results[-1]['status']}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_build_one_graph, sid): sid for sid in ids}
            for fut in as_completed(futs):
                sid = futs[fut]
                row = fut.result()
                results.append(row)
                print(f"[build-graphs] done {sid} {row['status']}", flush=True)
    out = EXP_DIR / f"result_build_graphs_{TAG}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}", flush=True)


def _iter_session_dialogs(conversation: Dict[str, Any]):
    import re

    sess_re = re.compile(r"^session_(\d+)$", re.I)
    for key, dialogs in conversation.items():
        m = sess_re.match(str(key))
        if not m or not isinstance(dialogs, list):
            continue
        sess_num = int(m.group(1))
        date_time = str(conversation.get(f"session_{sess_num}_date_time") or "")
        yield sess_num, date_time, dialogs


def build_or_load_memory_only_graph(sample: Dict[str, Any]) -> EMGraph:
    """Dialog Memory nodes only — no LLM extract (for system A parallelism)."""
    sid = str(sample.get("sample_id") or "")
    path = memory_only_graph_path(sid)
    if path.exists():
        graph = EMGraph.load_from_file(str(path))
        ensure_memory_sequence_edges(graph)
        return graph
    conversation = sample.get("conversation") or {}
    graph = EMGraph(sample_id=sid)
    for sess_num, date_time, dialogs in _iter_session_dialogs(conversation):
        previous_speaker = None
        for dialog in dialogs:
            if not isinstance(dialog, dict):
                continue
            dia_id = str(dialog.get("dia_id") or "").strip()
            if not dia_id:
                continue
            speaker = str(dialog.get("speaker") or "").strip()
            text = str(dialog.get("text") or "")
            normalized = replace_pronouns(
                text,
                speaker=speaker,
                previous_speaker=previous_speaker,
                dialog_time=date_time,
            )
            graph.add_memory(
                MemoryNode(
                    id=f"memory:{dia_id}",
                    dia_id=dia_id,
                    session_num=sess_num,
                    date_time=date_time,
                    speaker=speaker,
                    text=text,
                    text_normalized=normalized,
                    query=str(dialog.get("query") or ""),
                    img_url=str(dialog.get("img_url") or ""),
                    blip_caption=str(
                        dialog.get("blip_caption") or dialog.get("img_caption") or ""
                    ),
                )
            )
            previous_speaker = speaker or previous_speaker
    seq_n = ensure_memory_sequence_edges(graph)
    graph.stats = {
        "memory_count": len(graph.memories),
        "entity_count": 0,
        "edge_count": 0,
        "memory_edge_count": seq_n,
        "memory_only": True,
        "stack_tag": TAG,
    }
    graph.save_to_file(str(path))
    return graph


def load_graph_and_emb(
    sample_id: str,
    emb_model: str,
    *,
    memory_only: bool = False,
    sample: Optional[Dict[str, Any]] = None,
) -> Tuple[EMGraph, MemoryEmbeddingIndex]:
    if memory_only:
        if sample is None:
            raise ValueError("sample required for memory_only graph")
        graph = build_or_load_memory_only_graph(sample)
    else:
        path = graph_path(sample_id)
        if not path.exists():
            raise FileNotFoundError(path)
        graph = EMGraph.load_from_file(str(path))
        ensure_memory_sequence_edges(graph)
        assert_bipartite(graph)
    # Disable shared text cache: default cache may mix doubao(2048) + TES(1536).
    # Per-sample npz cache_path is enough for resume.
    emb = MemoryEmbeddingIndex.build(
        graph,
        model_name=emb_model,
        cache_path=str(emb_path(sample_id, emb_model, memory_only=memory_only)),
        use_text_cache=False,
    )
    return graph, emb


def ensure_qkeys(sample_id: str, sample: Dict[str, Any], extractor: EntityExtractor) -> Dict[int, Set[str]]:
    """Extract question entity keys with resume + per-call retries on transient API errors."""
    import time

    path = qkeys_path(sample_id)
    out: Dict[int, Set[str]] = {}
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        out = {int(k): set(v) for k, v in raw.items()}

    qa_list = sample.get("qa") or []
    needed = [
        (i, str(qa.get("question") or "").strip())
        for i, qa in enumerate(qa_list, 1)
        if str(qa.get("question") or "").strip()
    ]
    pending = [(i, q) for i, q in needed if i not in out]
    if not pending:
        return out

    print(
        f"[qkeys] {sample_id} resume {len(out)}/{len(needed)}; pending {len(pending)}",
        flush=True,
    )
    retries = int(os.environ.get("EM_GRAPH_QKEYS_RETRIES", "6"))
    for n_done, (i, q) in enumerate(pending, 1):
        last_err: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                out[i] = extract_question_entity_keys(q, extractor=extractor)
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                sleep_s = min(2.0 * attempt, 20.0)
                print(
                    f"[qkeys] {sample_id} qa={i} attempt {attempt}/{retries} "
                    f"failed: {type(exc).__name__}: {exc}; sleep {sleep_s:.1f}s",
                    flush=True,
                )
                time.sleep(sleep_s)
        if last_err is not None:
            path.write_text(
                json.dumps(
                    {str(k): sorted(v) for k, v in out.items()},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            raise RuntimeError(
                f"qkeys extract failed for {sample_id} qa={i} after {retries} tries"
            ) from last_err
        if n_done % 20 == 0 or n_done == len(pending):
            path.write_text(
                json.dumps(
                    {str(k): sorted(v) for k, v in out.items()},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(
                f"[qkeys] {sample_id} wrote {len(out)}/{len(needed)}",
                flush=True,
            )
    return out


def summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_k: Dict[str, Dict[str, Any]] = {}
    for k in KS:
        bucket: Dict[str, Dict[str, float]] = {}
        for r in rows:
            cat = str(r["category"])
            for key in ("overall", cat):
                b = bucket.setdefault(key, {"n": 0, "ra": 0.0, "hit": 0, "f1": 0.0, "f1n": 0})
                b["n"] += 1
                b["ra"] += float(r[f"recall_acc{k}"])
                b["hit"] += int(bool(r[f"hit{k}"]))
                if k == 25 and r.get("token_f1") is not None:
                    b["f1"] += float(r["token_f1"])
                    b["f1n"] += 1
        out_k: Dict[str, Any] = {}
        for key, b in bucket.items():
            n = max(int(b["n"]), 1)
            row = {
                "n": int(b["n"]),
                "recall_acc": round(b["ra"] / n, 4),
                "hit_rate": round(b["hit"] / n, 4),
            }
            if b["f1n"]:
                row["token_f1_pct"] = round(100.0 * b["f1"] / b["f1n"], 2)
            if key != "overall":
                row["name"] = CAT_NAMES.get(int(key), key)
            out_k[key] = row
        by_k[str(k)] = out_k
    ex = [r for r in rows if int(r["category"]) != 5 and r.get("token_f1") is not None]
    return {
        "n": len(rows),
        "by_k": by_k,
        "f1_25_overall_pct": by_k["25"]["overall"].get("token_f1_pct"),
        "f1_25_ex_cat5_pct": round(
            100.0 * sum(float(r["token_f1"]) for r in ex) / max(len(ex), 1), 2
        )
        if ex
        else None,
    }


def run_variant(variant_key: str) -> Dict[str, Any]:
    set_openai_key()
    cfg = VARIANTS[variant_key]
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "text-embedding-3-small")
    answer_model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    workers = int(os.environ.get("EM_GRAPH_MAX_WORKERS", "8"))
    top_answer_k = 25
    ckpt = out_dir() / f"all10_{TAG}_{cfg['label']}_answers.checkpoint.json"
    result_path = EXP_DIR / f"result_{TAG}_{cfg['label']}.json"

    answers: Dict[str, Dict[str, Any]] = {}
    if ckpt.exists() and os.environ.get("EM_GRAPH_ANSWER_RESUME", "1") in {"1", "true", "True"}:
        answers = json.loads(ckpt.read_text(encoding="utf-8"))
        print(f"[{variant_key}] resumed answers n={len(answers)}", flush=True)

    samples = json.loads((ROOT / "data" / "locomo10.json").read_text(encoding="utf-8"))
    extractor = EntityExtractor(model=answer_model) if cfg["need_entities"] else None
    metric_rows: List[Dict[str, Any]] = []

    print(
        f"[{variant_key}] {cfg['label']} emb={emb_model} answer={answer_model} "
        f"ew={cfg['entity_weight']} sw={cfg['semantic_weight']} "
        f"seq={cfg['expand_sequence']}",
        flush=True,
    )

    for sample in samples:
        sid = str(sample.get("sample_id") or "")
        memory_only = variant_key == "A"
        graph, emb_index = load_graph_and_emb(
            sid, emb_model, memory_only=memory_only, sample=sample
        )
        entity_bm25 = (
            EntityBM25Index.build(graph)
            if cfg["need_entities"] and not memory_only
            else None
        )
        qkeys = (
            ensure_qkeys(sid, sample, extractor)
            if cfg["need_entities"] and extractor is not None and not memory_only
            else {}
        )

        jobs = []
        for i, qa in enumerate(sample.get("qa") or [], 1):
            q = str(qa.get("question") or "").strip()
            if not q:
                continue
            key = f"{sid}::{q[:120]}"
            gold = [str(x) for x in (qa.get("evidence") or []) if str(x)]
            jobs.append((key, i, qa, q, gold))

        # Retrieve all (CPU/embed)
        retrieval: Dict[str, List[str]] = {}
        for key, i, qa, q, gold in jobs:
            q_entity_keys: Optional[Set[str]]
            if cfg["force_full_pool"]:
                q_entity_keys = set()
            else:
                q_entity_keys = qkeys.get(i, set())
            ranked = retrieve_dialog_ids(
                graph,
                q,
                top_k=max(KS),
                embedding_index=emb_index,
                entity_bm25_index=entity_bm25,
                q_entity_keys=q_entity_keys,
                entity_weight=float(cfg["entity_weight"]),
                semantic_weight=float(cfg["semantic_weight"]),
                expand_sequence=bool(cfg["expand_sequence"]),
            )
            retrieval[key] = [d for d, _ in ranked]

        pending = []
        for key, i, qa, q, gold in jobs:
            dias = retrieval[key]
            prev = answers.get(key) or {}
            if (
                str(prev.get("prediction") or "").strip()
                and prev.get("context_ids") == dias[:top_answer_k]
                and prev.get("token_f1") is not None
            ):
                continue
            pending.append((key, i, qa, dias))

        print(f"[{variant_key}] {sid} answer pending {len(pending)}/{len(jobs)}", flush=True)

        def _ans(item: Tuple[str, int, Dict[str, Any], List[str]]):
            key, i, qa, dias = item
            ctx = build_context(graph, dias[:top_answer_k])
            pred = answer_one(
                str(qa.get("question") or ""),
                int(qa.get("category") or 0),
                ctx,
                model=answer_model,
            )
            f1 = token_f1(str(qa.get("answer") or ""), pred)
            return key, i, qa, dias, pred, f1

        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_ans, job) for job in pending]
            for fut in as_completed(futs):
                key, i, qa, dias, pred, f1 = fut.result()
                answers[key] = {
                    "sample_id": sid,
                    "qa_index": i,
                    "question": str(qa.get("question") or ""),
                    "category": int(qa.get("category") or 0),
                    "gold_answer": str(qa.get("answer") or ""),
                    "context_ids": dias[:top_answer_k],
                    "retrieved50": dias[:50],
                    "prediction": pred,
                    "token_f1": round(f1, 4),
                }
                done += 1
                if done % 40 == 0 or done == len(pending):
                    ckpt.write_text(
                        json.dumps(answers, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    print(
                        f"[{variant_key}] {sid} answered {done}/{len(pending)}",
                        flush=True,
                    )

        for key, i, qa, q, gold in jobs:
            info = answers[key]
            dias50 = info.get("retrieved50") or info.get("context_ids") or []
            row = {
                "sample_id": sid,
                "qa": i,
                "category": int(qa.get("category") or 0),
                "token_f1": info.get("token_f1"),
            }
            for k in KS:
                top = dias50[:k]
                row[f"recall_acc{k}"] = recall_acc(gold, top) if gold else 1.0
                row[f"hit{k}"] = bool(gold and set(gold) & set(top)) if gold else True
            metric_rows.append(row)

    summary = summarize_rows(metric_rows)
    payload = {
        "stack_tag": TAG,
        "variant": variant_key,
        "label": cfg["label"],
        "config": cfg,
        "embedding_model": emb_model,
        "answer_model": answer_model,
        "extract_model": os.environ.get("OPENAI_MODEL"),
        "entity_extract_version": ENTITY_EXTRACT_VERSION,
        "summary": summary,
        "n_rows": len(metric_rows),
        "checkpoint": str(ckpt),
        "graph_constraint_audit": {
            "graph_inputs": "conversation-only extract-v4 EM graphs (gpt-3.5)",
            "qa_excluded_from_graph": True,
            "answer_uses_graph_retrieval": True,
        },
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[{variant_key}] F1@25={summary.get('f1_25_overall_pct')} "
        f"recall@25={summary['by_k']['25']['overall']['recall_acc']} -> {result_path}",
        flush=True,
    )
    return payload


def cmd_summarize(_: argparse.Namespace) -> None:
    paper = {
        "dialog_f1_25": 41.0,
        "dialog_r_25": 76.7,
        "obs_best_f1": 43.3,
        "summary_f1_10": 32.0,
    }
    rows = []
    for key, meta in VARIANTS.items():
        path = EXP_DIR / f"result_{TAG}_{meta['label']}.json"
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        s = d["summary"]
        o25 = s["by_k"]["25"]["overall"]
        rows.append(
            {
                "variant": key,
                "label": meta["label"],
                "f1_25": s.get("f1_25_overall_pct"),
                "f1_ex5": s.get("f1_25_ex_cat5_pct"),
                "recall_acc25": o25["recall_acc"],
                "hit25": o25["hit_rate"],
                "recall_acc5": s["by_k"]["5"]["overall"]["recall_acc"],
                "recall_acc10": s["by_k"]["10"]["overall"]["recall_acc"],
                "recall_acc50": s["by_k"]["50"]["overall"]["recall_acc"],
            }
        )
    a = next((r for r in rows if r["variant"] == "A"), None)
    b = next((r for r in rows if r["variant"] == "B"), None)
    gate = "incomplete"
    if a and b and a["f1_25"] is not None and b["f1_25"] is not None:
        if b["f1_25"] > a["f1_25"] and b["recall_acc25"] >= a["recall_acc25"]:
            gate = "publish_ok_method_helps"
        elif b["f1_25"] >= a["f1_25"]:
            gate = "publish_ok_f1_non_worse"
        elif b["f1_25"] < a["f1_25"]:
            gate = "method_weaker_on_f1_diagnose"
        else:
            gate = "parity"
    lines = [
        "# Matched stack compare (gpt-3.5 extract + text-embedding-3-small + gpt-3.5 F1)",
        "",
        f"**Gate:** `{gate}`",
        "",
        "| Variant | F1@25 | ex-cat5 F1 | recall_acc@25 | hit@25 | R@5 | R@10 | R@50 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['variant']} ({r['label']}) | {r['f1_25']} | {r['f1_ex5']} | "
            f"{100*r['recall_acc25']:.2f} | {100*r['hit25']:.2f} | "
            f"{100*r['recall_acc5']:.2f} | {100*r['recall_acc10']:.2f} | "
            f"{100*r['recall_acc50']:.2f} |"
        )
    lines += [
        "",
        "## Paper Table 3 anchors (DRAGON + gpt-3.5; not same embedder)",
        "",
        f"- Dialog F1@25 / R@25: {paper['dialog_f1_25']} / {paper['dialog_r_25']}",
        f"- Observation best F1: {paper['obs_best_f1']}",
        f"- Summary F1@10: {paper['summary_f1_10']}",
        "",
        "## Fair claim",
        "",
        "- **A vs B** is the matched-stack comparison.",
        "- Paper rows are cited only; retriever differs (DRAGON vs text-embedding-3-small).",
        "",
    ]
    if a and b and a["f1_25"] is not None and b["f1_25"] is not None:
        lines.append(
            f"- ΔF1 (B−A) = {b['f1_25'] - a['f1_25']:+.2f} pp; "
            f"Δrecall@25 = {100*(b['recall_acc25']-a['recall_acc25']):+.2f} pp"
        )
    path = EXP_DIR / "TABLE_GPT35_TES_COMPARE.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_path = EXP_DIR / f"result_{TAG}_compare_summary.json"
    summary_path.write_text(
        json.dumps(
            {"gate": gate, "rows": rows, "paper_anchors": paper},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"gate={gate}\nwrote {path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bg = sub.add_parser("build-graphs")
    p_bg.add_argument("--samples", nargs="*", default=None)
    p_bg.add_argument("--graph-workers", type=int, default=2)
    p_bg.set_defaults(func=cmd_build_graphs)

    for name in ("A", "B", "B_entity", "B_embed", "B_noseq"):
        p = sub.add_parser(name)
        p.set_defaults(func=lambda args, n=name: run_variant(n))

    p_ab = sub.add_parser("ablation")
    p_ab.set_defaults(
        func=lambda args: [run_variant(n) for n in ("B_entity", "B_embed", "B_noseq")]
    )

    p_sum = sub.add_parser("summarize")
    p_sum.set_defaults(func=cmd_summarize)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
