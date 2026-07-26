#!/usr/bin/env python3
"""P3 Step1: Oracle Observation / Summary RAG from locomo10 dataset fields.

Uses dataset ``observation`` / ``session_summary`` (NOT self-built).
Labeled oracle_dataset_fields=true — diagnostic upper bound, not a system claim.

Retriever: embedding cosine (default text-embedding-3-small via env_gpt).
Reader: gpt-3.5-turbo + LoCoMo short QA prompt (same as P1).
Metric: token-F1. Compare to Dialog P1 F1 46.18.
"""

from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from em_graph.embedding_index import (  # noqa: E402
    MemoryEmbeddingIndex,
    TextEmbeddingCache,
    _l2_normalize,
    _text_digest,
)
from experiments.shared.llm_client import run_chatgpt, set_openai_key  # noqa: E402

TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
CAT_NAMES = {
    1: "Multi-hop",
    2: "Temporal",
    3: "Open-domain",
    4: "Single-hop",
    5: "Adversarial",
}
DIALOG_P1_F1_PCT = 46.18

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


def build_answer_prompt(question: str, category: int, context: str) -> str:
    q = str(question or "").strip()
    if int(category) == 2:
        q = q + TEMPORAL_SUFFIX
    if int(category) == 5:
        tail = QA_PROMPT_CAT_5.format(q)
    else:
        tail = QA_PROMPT.format(q)
    return (context or "(no retrieved context)") + "\n\n" + tail


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


@dataclass
class Unit:
    unit_id: str
    text: str
    meta: Dict[str, Any]


def flatten_observations(sample: Dict[str, Any]) -> List[Unit]:
    out: List[Unit] = []
    obs = sample.get("observation") or {}
    for sess_key, by_speaker in obs.items():
        if not isinstance(by_speaker, dict):
            continue
        for speaker, items in by_speaker.items():
            if not isinstance(items, list):
                continue
            for j, item in enumerate(items):
                if isinstance(item, (list, tuple)) and item:
                    text = str(item[0] or "").strip()
                    dia = str(item[1] or "").strip() if len(item) > 1 else ""
                elif isinstance(item, dict):
                    text = str(item.get("text") or item.get("observation") or "").strip()
                    dia = str(item.get("dia_id") or "").strip()
                else:
                    text = str(item or "").strip()
                    dia = ""
                if not text:
                    continue
                uid = f"obs::{sess_key}::{speaker}::{j}"
                out.append(
                    Unit(
                        unit_id=uid,
                        text=f"{speaker}: {text}",
                        meta={
                            "speaker": speaker,
                            "session_key": sess_key,
                            "source_dia_id": dia,
                            "raw_text": text,
                        },
                    )
                )
    return out


def flatten_summaries(sample: Dict[str, Any]) -> List[Unit]:
    out: List[Unit] = []
    ss = sample.get("session_summary") or {}
    for sess_key, text in ss.items():
        body = str(text or "").strip()
        if not body:
            continue
        out.append(
            Unit(
                unit_id=f"sum::{sess_key}",
                text=body,
                meta={"session_key": sess_key},
            )
        )
    return out


def build_text_index(
    units: List[Unit],
    *,
    model_name: str,
    cache_path: Path,
    text_cache: TextEmbeddingCache,
) -> MemoryEmbeddingIndex:
    ids = [u.unit_id for u in units]
    texts = [u.text for u in units]
    digests = [_text_digest(t) for t in texts]
    if cache_path.exists():
        loaded = MemoryEmbeddingIndex.load(str(cache_path))
        if loaded is not None and loaded.matches(
            model_name=model_name, memory_ids=ids, text_digests=digests
        ):
            loaded.use_text_cache = True
            loaded._text_cache = text_cache
            print(f"Reusing index cache {cache_path}", flush=True)
            return loaded
    print(f"Embedding {len(texts)} units → {cache_path.name}", flush=True)
    helper = MemoryEmbeddingIndex(
        memory_ids=[],
        vectors=np.zeros((0, 0), dtype=np.float32),
        model_name=model_name,
        use_text_cache=True,
        _text_cache=text_cache,
    )
    vectors = helper._embed_texts(
        texts, role="context", show_progress=True, text_cache=text_cache
    )
    index = MemoryEmbeddingIndex(
        memory_ids=ids,
        vectors=vectors,
        model_name=model_name,
        text_digests=digests,
        use_text_cache=True,
        _text_cache=text_cache,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    index.save(str(cache_path))
    text_cache.flush()
    return index


def retrieve_top_with_qvec(
    index: MemoryEmbeddingIndex,
    units: List[Unit],
    qvec: np.ndarray,
    top_k: int,
) -> List[Unit]:
    if not units or top_k <= 0:
        return []
    scores = index.vectors @ np.asarray(qvec, dtype=np.float32).reshape(-1)
    order = np.argsort(-scores)[: max(int(top_k), 0)]
    id_to_unit = {u.unit_id: u for u in units}
    out: List[Unit] = []
    for i in order:
        uid = index.memory_ids[int(i)]
        u = id_to_unit.get(uid)
        if u is not None:
            out.append(u)
    return out


def embed_queries_batched(
    index: MemoryEmbeddingIndex, questions: Sequence[str]
) -> Dict[str, np.ndarray]:
    """Embed unique questions once (uses text cache)."""
    uniq = sorted({str(q or "").strip() for q in questions if str(q or "").strip()})
    if not uniq:
        return {}
    print(f"  embedding {len(uniq)} unique queries ...", flush=True)
    role = "query" if index._is_dragon() else "context"
    cache = index._get_text_cache() if index.use_text_cache else None
    vecs = index._embed_texts(
        uniq, role=role, show_progress=True, text_cache=cache
    )
    return {q: vecs[i] for i, q in enumerate(uniq)}


def summarize_f1(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by: Dict[str, Dict[str, float]] = {}
    for r in rows:
        cat = str(r["category"])
        b = by.setdefault(cat, {"n": 0, "f1_sum": 0.0})
        b["n"] += 1
        b["f1_sum"] += float(r["token_f1"])
    overall_n = len(rows)
    overall_sum = sum(float(r["token_f1"]) for r in rows)
    ex = [r for r in rows if int(r["category"]) != 5]
    by_cat = {
        cat: {
            "n": int(b["n"]),
            "token_f1_pct": round(100.0 * b["f1_sum"] / max(b["n"], 1), 2),
            "name": CAT_NAMES.get(int(cat), cat),
        }
        for cat, b in by.items()
    }
    pct = round(100.0 * overall_sum / max(overall_n, 1), 2)
    return {
        "n": overall_n,
        "token_f1_pct": pct,
        "token_f1_ex_cat5_pct": round(
            100.0 * sum(float(r["token_f1"]) for r in ex) / max(len(ex), 1), 2
        ),
        "by_category": by_cat,
        "vs_dialog_p1_pp": round(pct - DIALOG_P1_F1_PCT, 2),
        "beats_dialog_p1": pct > DIALOG_P1_F1_PCT,
    }


def run_variant(
    *,
    variant: str,
    top_k: int,
    samples: List[Dict[str, Any]],
    indexes: Dict[str, Tuple[List[Unit], MemoryEmbeddingIndex]],
    answer_model: str,
    workers: int,
    ckpt_path: Path,
) -> Dict[str, Any]:
    answers: Dict[str, Dict[str, Any]] = {}
    if ckpt_path.exists() and os.environ.get("EM_GRAPH_ANSWER_RESUME", "1") in {
        "1",
        "true",
        "True",
    }:
        answers = json.loads(ckpt_path.read_text(encoding="utf-8"))
        print(f"[{variant}@k{top_k}] resumed n={len(answers)}", flush=True)

    # Pre-embed questions per sample (batch) so retrieval is fast.
    qvecs_by_sample: Dict[str, Dict[str, np.ndarray]] = {}
    for sample in samples:
        sid = str(sample.get("sample_id") or "")
        units, index = indexes[sid]
        qs = [
            str(qa.get("question") or "").strip()
            for qa in (sample.get("qa") or [])
            if str(qa.get("question") or "").strip()
        ]
        print(f"[{variant}@k{top_k}] {sid} retrieve prep n={len(qs)}", flush=True)
        qvecs_by_sample[sid] = embed_queries_batched(index, qs)

    for sample in samples:
        sid = str(sample.get("sample_id") or "")
        units, index = indexes[sid]
        qvecs = qvecs_by_sample[sid]
        for i, qa in enumerate(sample.get("qa") or [], 1):
            q = str(qa.get("question") or "").strip()
            if not q:
                continue
            key = f"{sid}::{q[:120]}"
            ranked = retrieve_top_with_qvec(index, units, qvecs[q], top_k)
            context = "\n".join(u.text for u in ranked)
            gold_ev = {str(x) for x in (qa.get("evidence") or []) if str(x)}
            src = {str(u.meta.get("source_dia_id") or "") for u in ranked}
            src.discard("")
            hit_ev = (
                bool(gold_ev and (src & gold_ev)) if variant.startswith("obs") else None
            )
            prev = answers.get(key) or {}
            keep_pred = str(prev.get("prediction") or "").strip()
            prev_ids = prev.get("context_unit_ids") or []
            cur_ids = [u.unit_id for u in ranked]
            if keep_pred and prev_ids == cur_ids and prev.get("token_f1") is not None:
                answers[key] = {
                    **prev,
                    "context": context,
                    "hit_evidence_via_source_dia": hit_ev,
                    "source_dia_ids": sorted(src),
                }
                continue
            answers[key] = {
                "sample_id": sid,
                "qa_index": i,
                "question": q,
                "category": int(qa.get("category") or 0),
                "gold_answer": str(qa.get("answer") or ""),
                "context": context,
                "context_unit_ids": cur_ids,
                "source_dia_ids": sorted(src),
                "hit_evidence_via_source_dia": hit_ev,
                "prediction": "",
                "token_f1": None,
            }

    pending: List[Tuple[str, Dict[str, Any], str]] = []
    for sample in samples:
        sid = str(sample.get("sample_id") or "")
        for qa in sample.get("qa") or []:
            q = str(qa.get("question") or "").strip()
            if not q:
                continue
            key = f"{sid}::{q[:120]}"
            info = answers.get(key)
            if not info or str(info.get("prediction") or "").strip():
                continue
            pending.append((key, qa, str(info.get("context") or "")))

    print(f"[{variant}@k{top_k}] answer pending {len(pending)}", flush=True)

    def _ans(item: Tuple[str, Dict[str, Any], str]):
        key, qa, context = item
        pred = answer_one(
            str(qa.get("question") or ""),
            int(qa.get("category") or 0),
            context,
            model=answer_model,
        )
        f1 = token_f1(str(qa.get("answer") or ""), pred)
        return key, pred, f1

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_ans, job) for job in pending]
        for fut in as_completed(futs):
            key, pred, f1 = fut.result()
            answers[key]["prediction"] = pred
            answers[key]["token_f1"] = round(f1, 4)
            answers[key]["answer_model"] = answer_model
            done += 1
            if done % 40 == 0 or done == len(pending):
                ckpt_path.write_text(
                    json.dumps(answers, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(
                    f"[{variant}@k{top_k}] answered {done}/{len(pending)} "
                    f"global={len(answers)}",
                    flush=True,
                )

    rows = [
        {
            "sample_id": v["sample_id"],
            "category": v["category"],
            "token_f1": float(v["token_f1"] or 0.0),
            "hit_evidence_via_source_dia": v.get("hit_evidence_via_source_dia"),
        }
        for v in answers.values()
        if v.get("token_f1") is not None
    ]
    summary = summarize_f1(rows)
    hit_rows = [
        r for r in rows if r.get("hit_evidence_via_source_dia") is not None
    ]
    if hit_rows:
        summary["diag_source_dia_hit_rate"] = round(
            sum(1 for r in hit_rows if r["hit_evidence_via_source_dia"])
            / max(len(hit_rows), 1),
            4,
        )
    return {
        "variant": variant,
        "top_k": top_k,
        "oracle_dataset_fields": True,
        "not_a_system_claim": True,
        "summary": summary,
        "n_answers": len(rows),
        "checkpoint": str(ckpt_path),
    }


def main() -> None:
    set_openai_key()
    out_dir = ROOT / "outputs" / "em_graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    data_file = ROOT / "data" / "locomo10.json"
    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "text-embedding-3-small")
    answer_model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    workers = int(os.environ.get("EM_GRAPH_MAX_WORKERS", "8"))
    # Paper anchors: Obs best @5; Summary @10. Also Obs@25 vs Dialog@25.
    variants = [
        ("obs_oracle", 5),
        ("obs_oracle", 25),
        ("summary_oracle", 10),
    ]
    only = os.environ.get("P3_ONLY_VARIANT", "").strip()
    if only:
        # e.g. P3_ONLY_VARIANT=obs_oracle:5
        name, k_s = only.split(":")
        variants = [(name, int(k_s))]

    samples = json.loads(data_file.read_text(encoding="utf-8"))
    text_cache = TextEmbeddingCache(
        cache_file=str(out_dir / f"text_embed_cache_p3_{emb_model.replace('/', '_')}.npz")
    )

    print(
        f"[p3-step1] emb={emb_model} answer={answer_model} workers={workers} "
        f"variants={variants}",
        flush=True,
    )

    obs_indexes: Dict[str, Tuple[List[Unit], MemoryEmbeddingIndex]] = {}
    sum_indexes: Dict[str, Tuple[List[Unit], MemoryEmbeddingIndex]] = {}
    for sample in samples:
        sid = str(sample.get("sample_id") or "")
        obs_units = flatten_observations(sample)
        sum_units = flatten_summaries(sample)
        obs_indexes[sid] = (
            obs_units,
            build_text_index(
                obs_units,
                model_name=emb_model,
                cache_path=out_dir / f"{sid}_oracle_obs_emb_{emb_model.replace('/', '_')}.npz",
                text_cache=text_cache,
            ),
        )
        sum_indexes[sid] = (
            sum_units,
            build_text_index(
                sum_units,
                model_name=emb_model,
                cache_path=out_dir / f"{sid}_oracle_summary_emb_{emb_model.replace('/', '_')}.npz",
                text_cache=text_cache,
            ),
        )
        print(
            f"[{sid}] oracle units obs={len(obs_units)} summary={len(sum_units)}",
            flush=True,
        )

    results: List[Dict[str, Any]] = []
    for variant, top_k in variants:
        indexes = obs_indexes if variant.startswith("obs") else sum_indexes
        ckpt = out_dir / f"all10_p3_{variant}_k{top_k}_gpt35.checkpoint.json"
        payload = run_variant(
            variant=variant,
            top_k=top_k,
            samples=samples,
            indexes=indexes,
            answer_model=answer_model,
            workers=workers,
            ckpt_path=ckpt,
        )
        results.append(payload)
        print(
            f"[{variant}@k{top_k}] F1={payload['summary']['token_f1_pct']} "
            f"vs_dialog={payload['summary']['vs_dialog_p1_pp']:+} "
            f"beats={payload['summary']['beats_dialog_p1']}",
            flush=True,
        )

    # Decision
    obs5 = next((r for r in results if r["variant"] == "obs_oracle" and r["top_k"] == 5), None)
    obs25 = next((r for r in results if r["variant"] == "obs_oracle" and r["top_k"] == 25), None)
    sum10 = next(
        (r for r in results if r["variant"] == "summary_oracle" and r["top_k"] == 10), None
    )
    best_obs = None
    for cand in (obs5, obs25):
        if cand is None:
            continue
        if best_obs is None or cand["summary"]["token_f1_pct"] > best_obs["summary"]["token_f1_pct"]:
            best_obs = cand
    if best_obs and best_obs["summary"]["beats_dialog_p1"]:
        gate = "worth_self_build_obs"
    elif best_obs:
        gate = "stop_p3_main_spend"
    else:
        gate = "incomplete"

    out = {
        "experiment": "exp_2026_07_26_locomo_official_compare",
        "phase": "P3_step1_oracle",
        "oracle_dataset_fields": True,
        "not_a_system_claim": True,
        "embedding_model": emb_model,
        "answer_model": answer_model,
        "dialog_p1_f1_pct": DIALOG_P1_F1_PCT,
        "paper_anchors": {
            "obs_best_f1": 43.3,
            "summary_f1_k10": 32.0,
            "dialog_f1_k25": 41.0,
        },
        "results": results,
        "gate": gate,
        "graph_constraint_audit": {
            "note": "Oracle uses dataset observation/session_summary fields from LoCoMo generation pipeline; not conversation-only self-built memory. Diagnostic only.",
            "qa_excluded_from_index_construction": True,
            "answer_uses_retrieved_oracle_units_only": True,
        },
    }
    result_path = EXP_DIR / "result_p3_step1_oracle_obs_summary.json"
    result_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# P3 Step1 — Oracle Obs / Summary (dataset fields)",
        "",
        "**Label:** `oracle_dataset_fields=true` — not a system claim.",
        f"Embed: `{emb_model}` · Reader: `{answer_model}` · Dialog P1 F1: **{DIALOG_P1_F1_PCT}**",
        f"Gate: **{gate}**",
        "",
        "| Variant | k | F1% | ex-cat5 F1% | vs Dialog P1 (pp) | beats Dialog? |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        s = r["summary"]
        md_lines.append(
            f"| {r['variant']} | {r['top_k']} | {s['token_f1_pct']} | "
            f"{s['token_f1_ex_cat5_pct']} | {s['vs_dialog_p1_pp']:+} | "
            f"{s['beats_dialog_p1']} |"
        )
    md_lines += [
        "",
        "Paper anchors (gpt-3.5 + DRAGON): Obs best F1 43.3 (@5); Summary @10 F1 32.0; Dialog @25 F1 41.0.",
        "",
        "## Decision rule",
        "",
        "- If best oracle Obs F1 > Dialog 46.18 → consider self-build Obs.",
        "- Else → stop major P3 spend; Dialog remains preferred memory form.",
        "",
    ]
    sheet = EXP_DIR / "P3_STEP1_ORACLE_COMPARE.md"
    sheet.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    snap = EXP_DIR / "snapshots" / "v03_p3_step1_oracle_obs_summary"
    snap.mkdir(parents=True, exist_ok=True)
    (snap / "result_summary.json").write_text(
        json.dumps(
            {
                "gate": gate,
                "dialog_p1_f1_pct": DIALOG_P1_F1_PCT,
                "results": [
                    {
                        "variant": r["variant"],
                        "top_k": r["top_k"],
                        "summary": r["summary"],
                    }
                    for r in results
                ],
                "oracle_dataset_fields": True,
                "not_a_system_claim": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (snap / "source_run_p3_step1_oracle_obs_summary.py").write_text(
        Path(__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (snap / "P3_STEP1_ORACLE_COMPARE.md").write_text(
        sheet.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (snap / "NOTES.md").write_text(
        "\n".join(
            [
                "# v03_p3_step1_oracle_obs_summary",
                "",
                "## Command",
                "",
                "```bash",
                "source env_gpt.sh",
                "export OPENAI_MODEL=gpt-3.5-turbo",
                "export MODEL=gpt-3.5-turbo",
                "export EM_GRAPH_EMBED_MODEL=text-embedding-3-small",
                "python experiments/exp_2026_07_26_locomo_official_compare/run_p3_step1_oracle_obs_summary.py",
                "```",
                "",
                f"## Gate: {gate}",
                "",
                "Oracle only. Does not count as compliant self-built memory system result.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"gate": gate, "results": [
        {"v": r["variant"], "k": r["top_k"], "f1": r["summary"]["token_f1_pct"]}
        for r in results
    ]}, indent=2), flush=True)
    print(f"wrote {result_path}", flush=True)


if __name__ == "__main__":
    main()
