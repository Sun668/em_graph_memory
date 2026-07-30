#!/usr/bin/env python3
"""conv-26 fact RAG with Entity boost + Fact embedding (+ optional Memory expand).

Default fusion matches dialog-RAG: ``0.30 * entity + 0.70 * fact_embed``
(Fact BM25 weight defaults to 0).

Retrieval path:
  Question
    → Entity BM25 soft-match (via existing EM graph) → Fact boost
    → Fact embedding
    → fuse onto Fact set
    → answer on Fact text (+ source Memory snippets)
    → LoCoMo CORRECT/WRONG judge

Baseline: dialog RAG extract-v4 top25 judge_all ≈ 72.86% (deepseek-v4-flash).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(EXP_DIR))

from em_graph import EMGraph, EntityBM25Index, assert_bipartite, ensure_memory_sequence_edges  # noqa: E402
from experiments.shared.llm_client import run_chatgpt, set_openai_key  # noqa: E402
from fact_extract import FACT_EXTRACT_VERSION  # noqa: E402
from fact_retrieval import (  # noqa: E402
    FactBM25Index,
    FactEmbeddingIndex,
    build_fact_context,
    retrieve_facts,
)

SAMPLE_ID = "conv-26"
# Align with dialog-RAG two-way fusion: 0.3 entity + 0.7 semantic (fact embed).
ENTITY_WEIGHT = float(os.environ.get("EM_FACT_ENTITY_WEIGHT", "0.30"))
FACT_BM25_WEIGHT = float(os.environ.get("EM_FACT_BM25_WEIGHT", "0.0"))
FACT_EMBED_WEIGHT = float(os.environ.get("EM_FACT_EMBED_WEIGHT", "0.70"))

QA_PROMPT = """
Based on the above context, write an answer in the form of a short phrase for the following question. Answer with exact words from the context whenever possible.

Question: {} Short answer:
"""

QA_PROMPT_CAT_5 = """
Based on the above context, answer the following question. If the answer is not mentioned in the conversation, reply exactly: Not mentioned in the conversation.

Question: {} Short answer:
"""

TEMPORAL_SUFFIX = " Use DATE of CONVERSATION to answer with an approximate date."
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
CAT_NAMES = {
    1: "Multi-hop",
    2: "Temporal",
    3: "Open-domain",
    4: "Single-hop",
    5: "Adversarial",
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


def answer_prompt_scaffold_len() -> int:
    return max(
        len(QA_PROMPT.format("")),
        len(QA_PROMPT_CAT_5.format("")) + len(TEMPORAL_SUFFIX),
    )


def build_answer_prompt(question: str, category: int, context: str) -> str:
    q = str(question or "").strip()
    if int(category) == 2:
        q = q + TEMPORAL_SUFFIX
    if int(category) == 5:
        tail = QA_PROMPT_CAT_5.format(q)
    else:
        tail = QA_PROMPT.format(q)
    return (context or "(no retrieved facts)") + "\n\n" + tail


def answer_one(
    question: str,
    category: int,
    context: str,
    model: str,
    max_retries: int = 4,
) -> str:
    prompt = build_answer_prompt(question, category, context)
    n_tokens = int(os.environ.get("EM_GRAPH_ANSWER_TOKENS", "2048"))
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
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
            last_err = RuntimeError(f"empty answer with tokens={n_tokens}")
            n_tokens = min(n_tokens * 2, 8192)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            n_tokens = min(n_tokens * 2, 8192)
            if attempt + 1 >= max_retries:
                break
    raise RuntimeError(f"answer failed after {max_retries}: {last_err}")


def run_one_topk(
    *,
    top_k: int,
    graph: EMGraph,
    facts: List[Dict[str, Any]],
    facts_by_id: Dict[str, Dict[str, Any]],
    fact_embed_index: FactEmbeddingIndex,
    fact_bm25_index: FactBM25Index,
    entity_bm25: EntityBM25Index,
    qa_rows: List[Dict[str, Any]],
    q_keys_by_qa: Dict[int, Set[str]],
    answer_model: str,
    judge_model: str,
    workers: int,
    append_source_memory: bool,
) -> Dict[str, Any]:
    from experiments.shared import judge_accuracy as judge_mod

    out_dir = ROOT / "outputs" / "em_graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    ew = int(round(ENTITY_WEIGHT * 100))
    bw = int(round(FACT_BM25_WEIGHT * 100))
    sw = int(round(FACT_EMBED_WEIGHT * 100))
    tag = f"fact_{FACT_EXTRACT_VERSION}_e{ew}b{bw}s{sw}_top{top_k}"
    if append_source_memory:
        tag += "_mem"
    pred_key = f"em_{tag}_prediction"
    context_key = pred_key + "_context"
    fact_context_key = pred_key + "_fact_ids"
    pred_path = out_dir / f"{SAMPLE_ID}_locomo_rag_{tag}_predictions.json"
    judge_path = out_dir / f"{SAMPLE_ID}_locomo_rag_{tag}_judge.json"
    ckpt_path = out_dir / f"{SAMPLE_ID}_locomo_rag_{tag}_predictions.checkpoint.json"
    judge_ckpt = Path(str(judge_path) + ".checkpoint")
    exp_result = EXP_DIR / f"result_conv26_fact_judge_e{ew}s{sw}_top{top_k}.json"
    snap_dir = (
        EXP_DIR
        / "snapshots"
        / f"v03_conv26_fact_e{ew}s{sw}_top{top_k}"
    )

    jobs = [
        (i, qa)
        for i, qa in enumerate(qa_rows, 1)
        if str(qa.get("question") or "").strip()
    ]

    retrieval: Dict[int, List[Tuple[str, float]]] = {}
    print(f"[top{top_k}] retrieving n={len(jobs)}", flush=True)
    for i, qa in jobs:
        retrieval[i] = retrieve_facts(
            str(qa.get("question") or ""),
            graph=graph,
            facts=facts,
            fact_embed_index=fact_embed_index,
            fact_bm25_index=fact_bm25_index,
            entity_bm25_index=entity_bm25,
            top_k=top_k,
            q_entity_keys=q_keys_by_qa.get(i),
            entity_weight=ENTITY_WEIGHT,
            fact_bm25_weight=FACT_BM25_WEIGHT,
            fact_embed_weight=FACT_EMBED_WEIGHT,
        )

    pred_by_qa: Dict[int, Dict[str, Any]] = {}
    if ckpt_path.exists() and os.environ.get("EM_GRAPH_ANSWER_RESUME", "1") in {
        "1",
        "true",
        "True",
    }:
        raw_ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
        pred_by_qa = {
            int(k): v
            for k, v in raw_ckpt.items()
            if str((v or {}).get("prediction") or "").strip()
        }
        print(f"[top{top_k}] resumed answers n={len(pred_by_qa)}", flush=True)

    scaffold = answer_prompt_scaffold_len()
    print(
        f"[top{top_k}] answering model={answer_model} scaffold={scaffold} "
        f"workers={workers} append_memory={append_source_memory}",
        flush=True,
    )

    def _answer_job(item: Tuple[int, Dict[str, Any]]):
        i, qa = item
        ranked = retrieval[i]
        context, fact_ids, dia_ids = build_fact_context(
            ranked,
            facts_by_id,
            graph,
            append_source_memory=append_source_memory,
            max_extra_memories=min(top_k, 8),
        )
        gold = str(qa.get("answer") or "")
        gset = {str(x) for x in (qa.get("evidence") or []) if str(x)}
        hit = bool(gset and set(dia_ids) & gset) if gset else None
        pred = answer_one(
            str(qa.get("question") or ""),
            int(qa.get("category") or 0),
            context,
            model=answer_model,
        )
        return i, pred, fact_ids, dia_ids, token_f1(gold, pred), hit

    pending = [job for job in jobs if job[0] not in pred_by_qa]
    done = len(pred_by_qa)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_answer_job, job): job[0] for job in pending}
        for fut in as_completed(futures):
            i, pred, fact_ids, dia_ids, f1, hit = fut.result()
            pred_by_qa[i] = {
                "prediction": pred,
                "fact_ids": fact_ids,
                "context_ids": dia_ids,
                "token_f1": round(f1, 4),
                "hit_at_k": hit,
            }
            done += 1
            if done % 10 == 0 or done == len(jobs):
                ckpt_path.write_text(
                    json.dumps(pred_by_qa, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"[top{top_k}] answered {done}/{len(jobs)}", flush=True)

    out_qa: List[Dict[str, Any]] = []
    hit_n = 0
    hit_d = 0
    f1_sum = 0.0
    for i, qa in enumerate(qa_rows, 1):
        row = dict(qa)
        info = pred_by_qa.get(i)
        if info is None:
            out_qa.append(row)
            continue
        row[pred_key] = info["prediction"]
        row[context_key] = info["context_ids"]
        row[fact_context_key] = info["fact_ids"]
        row[pred_key + "_token_f1"] = info["token_f1"]
        row[pred_key + f"_hit{top_k}"] = info["hit_at_k"]
        f1_sum += float(info["token_f1"])
        if info["hit_at_k"] is not None:
            hit_d += 1
            hit_n += int(bool(info["hit_at_k"]))
        out_qa.append(row)

    pred_path.write_text(
        json.dumps(
            [{"sample_id": SAMPLE_ID, "qa": out_qa}],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    tasks = []
    for idx, qa in enumerate(out_qa):
        pred = str(qa.get(pred_key) or "").strip()
        if not pred:
            continue
        tasks.append(
            (
                idx,
                SAMPLE_ID,
                str(qa.get("question") or ""),
                str(qa.get("answer") or ""),
                pred,
                int(qa.get("category") or 0),
            )
        )

    judgments: List[Dict[str, Any]] = []
    judged_keys = set()
    if judge_ckpt.exists() and os.environ.get("EM_GRAPH_ANSWER_RESUME", "1") in {
        "1",
        "true",
        "True",
    }:
        prev = json.loads(judge_ckpt.read_text(encoding="utf-8"))
        for j in prev.get("judgments") or []:
            judged_keys.add((j["sample_id"], j["question"][:100]))
            judgments.append(j)
        print(f"[top{top_k}] resumed judgments n={len(judgments)}", flush=True)

    remaining = [t for t in tasks if (t[1], t[2][:100]) not in judged_keys]
    print(
        f"[top{top_k}] judging remaining {len(remaining)}/{len(tasks)} "
        f"model={judge_model}",
        flush=True,
    )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(judge_mod.judge_task, t, judge_model, 3) for t in remaining
        ]
        finished = 0
        for fut in as_completed(futures):
            idx, sample_id, category, score_val, verdict, question, gold, predicted = (
                fut.result()
            )
            judgments.append(
                {
                    "sample_id": sample_id,
                    "qa_index": idx,
                    "category": category,
                    "category_name": CAT_NAMES.get(category, str(category)),
                    "question": question,
                    "gold_answer": gold,
                    "predicted_answer": predicted,
                    "judge_verdict": verdict,
                    "judge_score": score_val,
                }
            )
            finished += 1
            if finished % 20 == 0 or finished == len(remaining):
                judge_ckpt.write_text(
                    json.dumps({"judgments": judgments}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(
                    f"[top{top_k}] judged {len(judgments)}/{len(tasks)}",
                    flush=True,
                )

    by_cat: Dict[str, Dict[str, Any]] = {}
    correct = 0
    for j in judgments:
        cat = str(j["category"])
        bucket = by_cat.setdefault(cat, {"n": 0, "correct": 0})
        bucket["n"] += 1
        bucket["correct"] += int(j["judge_score"])
        correct += int(j["judge_score"])
    n_judge = len(judgments)
    for cat, bucket in by_cat.items():
        bucket["accuracy"] = round(bucket["correct"] / max(bucket["n"], 1), 4)
        bucket["name"] = CAT_NAMES.get(int(cat), cat)

    non_adv = [j for j in judgments if int(j["category"]) != 5]
    non_adv_correct = sum(int(j["judge_score"]) for j in non_adv)

    summary: Dict[str, Any] = {
        "sample_id": SAMPLE_ID,
        "env": "env_ark.sh",
        "fact_extract_version": FACT_EXTRACT_VERSION,
        "n_facts": len(facts),
        "answer_model": answer_model,
        "judge_model": judge_model,
        "embedding_model": fact_embed_index.model_name,
        "top_k": top_k,
        "n_qa": len(jobs),
        "n_judged": n_judge,
        "judge_accuracy_all": round(correct / max(n_judge, 1), 4),
        "judge_correct_all": correct,
        "judge_accuracy_ex_cat5": round(
            non_adv_correct / max(len(non_adv), 1), 4
        ),
        "judge_correct_ex_cat5": non_adv_correct,
        "n_ex_cat5": len(non_adv),
        "mean_token_f1": round(f1_sum / max(len(jobs), 1), 4),
        f"hit{top_k}": hit_n,
        f"hit{top_k}_denom": hit_d,
        f"hit{top_k}_rate": round(hit_n / max(hit_d, 1), 4),
        "by_category": by_cat,
        "retrieval": {
            "method": (
                "Entity BM25→Memory→Fact boost + Fact BM25 + Fact embedding; "
                "answer on facts"
                + (" + source Memory snippets" if append_source_memory else "")
            ),
            "entity_weight": ENTITY_WEIGHT,
            "fact_bm25_weight": FACT_BM25_WEIGHT,
            "fact_embed_weight": FACT_EMBED_WEIGHT,
            "append_source_memory": append_source_memory,
            "top_k": top_k,
        },
        "answer_generation": {
            "prompt_scaffold_chars": scaffold,
            "prompt_budget_ok": scaffold <= 5000,
        },
        "judge": {
            "method": "experiments/shared/judge_accuracy.py CORRECT/WRONG",
        },
        "baseline_dialog_rag_top25": {
            "judge_accuracy_all": 0.7286,
            "judge_accuracy_ex_cat5": 0.6974,
            "note": "extract-v4 entity+embed fusion 0.3/0.7 deepseek-v4-flash",
        },
        "graph_constraint": {
            "audit_passed": True,
            "graph_inputs": "conversation dialogs only → facts; Entity from conversation graph",
            "qa_excluded_from_fact_extraction": True,
            "recall": "graph Entity boost + Fact text retrieval over conversation-built facts",
            "answer": "LLM over retrieved facts (+ optional source dialogs); no gold answers",
        },
        "outputs": {
            "predictions": str(pred_path.relative_to(ROOT)),
            "judge": str(judge_path.relative_to(ROOT)),
            "fact_store": f"outputs/em_graph/{SAMPLE_ID}_fact_store_{FACT_EXTRACT_VERSION}.json",
        },
    }

    judge_path.write_text(
        json.dumps(
            {"summary": summary, "judgments": judgments},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    exp_result.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    snap_dir.mkdir(parents=True, exist_ok=True)
    for src, name in [
        (Path(__file__), "source_run_conv26_fact_rag_judge.py"),
        (EXP_DIR / "fact_extract.py", "source_fact_extract.py"),
        (EXP_DIR / "fact_retrieval.py", "source_fact_retrieval.py"),
        (EXP_DIR / "build_fact_store.py", "source_build_fact_store.py"),
    ]:
        shutil.copy2(src, snap_dir / name)
    (snap_dir / "result_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (snap_dir / "NOTES.md").write_text(
        "\n".join(
            [
                f"# Fact+Entity retrieval · {FACT_EXTRACT_VERSION} · top{top_k}",
                "",
                f"- Fusion: {ENTITY_WEIGHT}E + {FACT_BM25_WEIGHT}BM25 + {FACT_EMBED_WEIGHT}S",
                f"- Append source Memory: {append_source_memory}",
                f"- Facts: {len(facts)}",
                f"- Judge all: {summary['judge_accuracy_all']} ({correct}/{n_judge})",
                f"- Judge ex-cat5: {summary['judge_accuracy_ex_cat5']} "
                f"({non_adv_correct}/{len(non_adv)})",
                f"- Dialog-hit@{top_k}: {summary[f'hit{top_k}_rate']}",
                f"- Baseline dialog RAG top25: 0.7286",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "top_k": top_k,
                "judge_accuracy_all": summary["judge_accuracy_all"],
                "judge_accuracy_ex_cat5": summary["judge_accuracy_ex_cat5"],
                f"hit{top_k}_rate": summary[f"hit{top_k}_rate"],
                "mean_token_f1": summary["mean_token_f1"],
            },
            indent=2,
        ),
        flush=True,
    )
    return summary


def main() -> None:
    set_openai_key()
    out_dir = ROOT / "outputs" / "em_graph"
    store_path = out_dir / f"{SAMPLE_ID}_fact_store_{FACT_EXTRACT_VERSION}.json"
    graph_path = out_dir / f"{SAMPLE_ID}_em_graph_extract_v4.json"
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision")
    emb_cache = out_dir / (
        f"{SAMPLE_ID}_fact_emb_{FACT_EXTRACT_VERSION}_{emb_model.replace('/', '_')}.npz"
    )
    keys_path = out_dir / f"{SAMPLE_ID}_offline_locomo_recall_acc_extract_v4_e03s07.json"
    if not keys_path.exists():
        keys_path = out_dir / f"{SAMPLE_ID}_offline_locomo_recall_acc_extract_v4.json"

    answer_model = os.environ.get("OPENAI_MODEL", "deepseek-v4-flash")
    judge_model = os.environ.get("JUDGE_MODEL", answer_model)
    workers = int(os.environ.get("EM_GRAPH_MAX_WORKERS", "6"))
    top_ks = [
        int(x.strip())
        for x in os.environ.get("EM_FACT_TOP_KS", "25,50").split(",")
        if x.strip()
    ]
    append_memory = os.environ.get("EM_FACT_APPEND_MEMORY", "1") in {
        "1",
        "true",
        "True",
    }

    if not store_path.exists():
        raise FileNotFoundError(
            f"missing fact store {store_path}; run build_fact_store.py first"
        )
    if not graph_path.exists():
        raise FileNotFoundError(graph_path)

    store = json.loads(store_path.read_text(encoding="utf-8"))
    facts: List[Dict[str, Any]] = list(store.get("facts") or [])
    facts_by_id = {str(f["fact_id"]): f for f in facts}
    print(
        f"[{SAMPLE_ID}] facts={len(facts)} top_ks={top_ks} "
        f"fusion={ENTITY_WEIGHT}/{FACT_BM25_WEIGHT}/{FACT_EMBED_WEIGHT} "
        f"append_memory={append_memory} answer={answer_model}",
        flush=True,
    )

    graph = EMGraph.load_from_file(str(graph_path))
    ensure_memory_sequence_edges(graph)
    assert_bipartite(graph)
    entity_bm25 = EntityBM25Index.build(graph)
    fact_bm25 = FactBM25Index.build(facts)
    fact_embed = FactEmbeddingIndex.build(
        facts, model_name=emb_model, cache_path=str(emb_cache)
    )

    sample = next(
        s
        for s in json.loads((ROOT / "data" / "locomo10.json").read_text(encoding="utf-8"))
        if s.get("sample_id") == SAMPLE_ID
    )
    qa_rows = list(sample.get("qa") or [])

    q_keys_by_qa: Dict[int, Set[str]] = {}
    if keys_path.exists():
        prev = json.loads(keys_path.read_text(encoding="utf-8"))
        for row in prev.get("rows") or []:
            keys = row.get("q_entity_keys") or []
            if keys:
                q_keys_by_qa[int(row["qa"])] = set(keys)
        print(f"reused q_entity_keys n={len(q_keys_by_qa)} from {keys_path.name}")

    summaries = []
    for top_k in top_ks:
        summaries.append(
            run_one_topk(
                top_k=top_k,
                graph=graph,
                facts=facts,
                facts_by_id=facts_by_id,
                fact_embed_index=fact_embed,
                fact_bm25_index=fact_bm25,
                entity_bm25=entity_bm25,
                qa_rows=qa_rows,
                q_keys_by_qa=q_keys_by_qa,
                answer_model=answer_model,
                judge_model=judge_model,
                workers=workers,
                append_source_memory=append_memory,
            )
        )

    compare = {
        "sample_id": SAMPLE_ID,
        "fact_extract_version": FACT_EXTRACT_VERSION,
        "retrieval": "entity_boost + fact_bm25 + fact_embed (+ memory snippets)",
        "baseline_dialog_rag_top25_judge_all": 0.7286,
        "by_top_k": {
            str(s["top_k"]): {
                "judge_accuracy_all": s["judge_accuracy_all"],
                "judge_accuracy_ex_cat5": s["judge_accuracy_ex_cat5"],
                "mean_token_f1": s["mean_token_f1"],
                "hit_rate": s[f"hit{s['top_k']}_rate"],
                "n_judged": s["n_judged"],
            }
            for s in summaries
        },
    }
    compare_path = EXP_DIR / "result_conv26_fact_judge_compare.json"
    compare_path.write_text(json.dumps(compare, indent=2), encoding="utf-8")
    print(json.dumps(compare, indent=2), flush=True)


if __name__ == "__main__":
    main()
