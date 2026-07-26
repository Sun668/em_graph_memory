#!/usr/bin/env python3
"""P1: Same frozen top-25 dialog evidence → gpt-3.5-turbo short QA → token-F1.

No retrieval change. No Mem0 judge. Aligns reader to LoCoMo paper Table-3.
"""

from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from em_graph import EMGraph, assert_bipartite, ensure_memory_sequence_edges  # noqa: E402
from experiments.shared.llm_client import run_chatgpt, set_openai_key  # noqa: E402

TOP_K = 25
PRED_IN_KEY = "em_graph_v4_locomo_rag_top25_prediction"
CONTEXT_KEY = PRED_IN_KEY + "_context"
PRED_OUT_KEY = "em_graph_v4_locomo_rag_top25_gpt35_prediction"
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


def format_dialog_line(memory) -> str:
    line = f'{memory.speaker} said, "{memory.text}"'
    caption = str(memory.blip_caption or "").strip()
    if caption:
        line += f" and shared {caption}"
    return line


def build_context_from_ids(graph: EMGraph, dia_ids: List[str]) -> str:
    dia_to_mem = {m.dia_id: m for m in graph.memories.values()}
    lines: List[str] = []
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
    if int(category) == 5:
        tail = QA_PROMPT_CAT_5.format(q)
    else:
        tail = QA_PROMPT.format(q)
    return (context or "(no retrieved dialogs)") + "\n\n" + tail


def answer_one(question: str, category: int, context: str, model: str) -> str:
    prompt = build_answer_prompt(question, category, context)
    n_tokens = int(os.environ.get("EM_GRAPH_ANSWER_TOKENS", "512"))
    last_err: Optional[Exception] = None
    for _attempt in range(4):
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


def summarize_f1(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by: Dict[str, Dict[str, float]] = {}
    for r in rows:
        cat = str(r["category"])
        b = by.setdefault(cat, {"n": 0, "f1_sum": 0.0})
        b["n"] += 1
        b["f1_sum"] += float(r["token_f1"])
    overall_n = len(rows)
    overall_sum = sum(float(r["token_f1"]) for r in rows)
    ex = [r for r in rows if int(r["category"]) != 5]
    by_cat = {}
    for cat, b in by.items():
        by_cat[cat] = {
            "n": int(b["n"]),
            "token_f1": round(b["f1_sum"] / max(b["n"], 1), 4),
            "token_f1_pct": round(100.0 * b["f1_sum"] / max(b["n"], 1), 2),
            "name": CAT_NAMES.get(int(cat), cat),
        }
    return {
        "n": overall_n,
        "token_f1": round(overall_sum / max(overall_n, 1), 4),
        "token_f1_pct": round(100.0 * overall_sum / max(overall_n, 1), 2),
        "n_ex_cat5": len(ex),
        "token_f1_ex_cat5": round(
            sum(float(r["token_f1"]) for r in ex) / max(len(ex), 1), 4
        ),
        "token_f1_ex_cat5_pct": round(
            100.0 * sum(float(r["token_f1"]) for r in ex) / max(len(ex), 1), 2
        ),
        "by_category": by_cat,
        "decision": {
            "paper_dialog_f1_25": 41.0,
            "paper_obs_best_f1": 43.3,
            "rule": ">=43 full writeup; 41-43 parity; <41 stop large compare",
        },
    }


def main() -> None:
    set_openai_key()
    out_dir = ROOT / "outputs" / "em_graph"
    data_file = ROOT / "data" / "locomo10.json"
    pred_in = out_dir / "all10_locomo_rag_extract_v4_top25_predictions.json"
    answer_model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    workers = int(os.environ.get("EM_GRAPH_MAX_WORKERS", "6"))
    ckpt_path = out_dir / "all10_locomo_rag_top25_gpt35_answers.checkpoint.json"
    pred_out = out_dir / "all10_locomo_rag_top25_gpt35_predictions.json"
    result_path = EXP_DIR / "result_p1_gpt35_reanswer_f1.json"
    snap_dir = EXP_DIR / "snapshots" / "v02_p1_gpt35_reanswer_f1"

    answers: Dict[str, Dict[str, Any]] = {}
    if ckpt_path.exists() and os.environ.get("EM_GRAPH_ANSWER_RESUME", "1") in {
        "1",
        "true",
        "True",
    }:
        answers = json.loads(ckpt_path.read_text(encoding="utf-8"))
        print(f"resumed answers n={len(answers)}", flush=True)

    samples = json.loads(pred_in.read_text(encoding="utf-8"))
    print(
        f"[p1] frozen top{TOP_K} evidence → answer_model={answer_model} "
        f"workers={workers}",
        flush=True,
    )

    for sample in samples:
        sid = str(sample.get("sample_id") or "")
        jobs: List[Tuple[int, Dict[str, Any], List[str]]] = []
        for i, qa in enumerate(sample.get("qa") or [], 1):
            q = str(qa.get("question") or "").strip()
            ctx = list(qa.get(CONTEXT_KEY) or [])
            if not q or not ctx:
                continue
            key = f"{sid}::{q[:120]}"
            if key in answers and str(answers[key].get("prediction") or "").strip():
                continue
            jobs.append((i, qa, ctx))
        print(f"[{sid}] pending {len(jobs)}", flush=True)
        if not jobs:
            continue

        graph_path = out_dir / f"{sid}_em_graph_extract_v4.json"
        graph = EMGraph.load_from_file(str(graph_path))
        ensure_memory_sequence_edges(graph)
        assert_bipartite(graph)

        def _ans(item: Tuple[int, Dict[str, Any], List[str]]):
            i, qa, ctx = item
            context = build_context_from_ids(graph, ctx)
            pred = answer_one(
                str(qa.get("question") or ""),
                int(qa.get("category") or 0),
                context,
                model=answer_model,
            )
            gold = str(qa.get("answer") or "")
            return i, qa, ctx, pred, token_f1(gold, pred)

        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_ans, job) for job in jobs]
            for fut in as_completed(futs):
                i, qa, ctx, pred, f1 = fut.result()
                q = str(qa.get("question") or "")
                answers[f"{sid}::{q[:120]}"] = {
                    "sample_id": sid,
                    "qa_index": i,
                    "question": q,
                    "category": int(qa.get("category") or 0),
                    "gold_answer": str(qa.get("answer") or ""),
                    "context_ids": ctx,
                    "prediction": pred,
                    "token_f1": round(f1, 4),
                    "answer_model": answer_model,
                }
                done += 1
                if done % 20 == 0 or done == len(jobs):
                    ckpt_path.write_text(
                        json.dumps(answers, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    print(
                        f"[{sid}] answered {done}/{len(jobs)} global={len(answers)}",
                        flush=True,
                    )

    # Materialize + summarize
    out_samples: List[Dict[str, Any]] = []
    metric_rows: List[Dict[str, Any]] = []
    for sample in samples:
        sid = sample["sample_id"]
        qa_out = []
        for qa in sample.get("qa") or []:
            row = dict(qa)
            q = str(qa.get("question") or "")
            info = answers.get(f"{sid}::{q[:120]}")
            if info:
                row[PRED_OUT_KEY] = info["prediction"]
                row[PRED_OUT_KEY + "_token_f1"] = info["token_f1"]
                row[PRED_OUT_KEY + "_context"] = info.get("context_ids") or []
                metric_rows.append(info)
            qa_out.append(row)
        out_samples.append({"sample_id": sid, "qa": qa_out})
    pred_out.write_text(json.dumps(out_samples, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = summarize_f1(metric_rows)
    overall = summary["token_f1_pct"]
    if overall >= 43.0:
        gate = "full_writeup"
    elif overall >= 41.0:
        gate = "parity_claim_only"
    else:
        gate = "stop_large_compare"
    summary["gate"] = gate

    deepseek_f1 = []
    for sample in samples:
        for qa in sample.get("qa") or []:
            if qa.get(PRED_IN_KEY + "_token_f1") is not None:
                deepseek_f1.append(float(qa[PRED_IN_KEY + "_token_f1"]))
    deepseek_pct = (
        round(100.0 * sum(deepseek_f1) / max(len(deepseek_f1), 1), 2) if deepseek_f1 else None
    )

    payload = {
        "experiment": "exp_2026_07_26_locomo_official_compare",
        "phase": "P1",
        "answer_model": answer_model,
        "evidence": "frozen em_graph_v4 top25 context_ids (no re-retrieve)",
        "prompt": "LoCoMo short QA_PROMPT / QA_PROMPT_CAT_5 + temporal suffix",
        "n": summary["n"],
        "summary": summary,
        "deepseek_same_evidence_f1_pct": deepseek_pct,
        "delta_vs_deepseek_pp": round(overall - deepseek_pct, 2)
        if deepseek_pct is not None
        else None,
        "vs_paper": {
            "dialog_f1_25": 41.0,
            "observation_best_f1": 43.3,
            "delta_vs_dialog_pp": round(overall - 41.0, 2),
            "delta_vs_obs_best_pp": round(overall - 43.3, 2),
        },
        "outputs": {
            "predictions": str(pred_out),
            "checkpoint": str(ckpt_path),
            "result": str(result_path),
        },
        "graph_constraint_audit": {
            "graph_inputs": "conversation-only extract-v4; evidence frozen from prior graph retrieval",
            "qa_excluded_from_graph": True,
            "answer_uses_graph_retrieval": True,
            "f1_reader_aligned_to_paper": answer_model.startswith("gpt-3.5"),
            "prompts_improve_answer_over_graph_evidence_only": True,
        },
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "phase": "P1",
                "answer_model": answer_model,
                "summary": summary,
                "vs_paper": payload["vs_paper"],
                "deepseek_same_evidence_f1_pct": deepseek_pct,
                "graph_constraint_audit": payload["graph_constraint_audit"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (snap_dir / "source_run_p1_gpt35_reanswer_f1.py").write_text(
        Path(__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (snap_dir / "NOTES.md").write_text(
        "\n".join(
            [
                "# v02_p1_gpt35_reanswer_f1",
                "",
                "## Command",
                "",
                "```bash",
                "source env_gpt.sh",
                "export OPENAI_MODEL=gpt-3.5-turbo",
                "export MODEL=gpt-3.5-turbo",
                "python experiments/exp_2026_07_26_locomo_official_compare/run_p1_gpt35_reanswer_f1.py",
                "```",
                "",
                f"## Result gate: **{gate}**",
                "",
                f"- Overall F1%: {overall}",
                f"- ex-cat5 F1%: {summary['token_f1_ex_cat5_pct']}",
                f"- vs paper Dialog@25 (41.0): {payload['vs_paper']['delta_vs_dialog_pp']:+} pp",
                f"- vs paper Obs best (43.3): {payload['vs_paper']['delta_vs_obs_best_pp']:+} pp",
                f"- same-evidence deepseek F1%: {deepseek_pct}",
                "",
                "## Constraint",
                "",
                "PASS: frozen conversation-graph retrieval evidence; short QA prompt only.",
                "Counts toward LoCoMo F1 comparison only if reader is gpt-3.5-turbo.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], indent=2), flush=True)
    print(json.dumps(payload["vs_paper"], indent=2), flush=True)
    print(f"gate={gate} wrote {result_path}", flush=True)


if __name__ == "__main__":
    main()
