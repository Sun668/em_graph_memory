#!/usr/bin/env python3
"""Build miss@25 analysis JSON + per-case full-graph PNG for latest offline hit.

Highlights on each PNG (all EM-graph nodes drawn):
  - query entity keys (matched entity nodes + unmatched keys as labels)
  - matched entity nodes (soft-match from q keys)
  - matched memory nodes (entity seeds + ±1 sequence neighbors)
  - gold / correct memory nodes
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import EMGraph, EntityBM25Index  # noqa: E402
from em_graph.build import normalize_entity_key  # noqa: E402
from em_graph.recall import expand_sequence_neighbors  # noqa: E402
from em_graph.recall.tokenize import tokenize_for_bm25  # noqa: E402

EXP_DIR = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "em_graph_gpt"
DEFAULT_HIT = OUT_DIR / "conv-26_offline_hit.json"
DEFAULT_GRAPH = OUT_DIR / "conv-26_em_graph.json"
DATA_PATH = ROOT / "data" / "locomo10.json"
ANALYSIS_PATH = EXP_DIR / "miss_analysis_hit166.json"
VIZ_DIR = OUT_DIR / "miss_viz_hit166"

_STOP = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "to",
    "of",
    "in",
    "on",
    "for",
    "and",
    "or",
    "with",
    "what",
    "when",
    "where",
    "who",
    "how",
    "why",
    "which",
    "did",
    "does",
    "do",
    "caroline",
    "melanie",
    "mel",
}


def _short(text: str, n: int = 90) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _content_tokens(text: str) -> Set[str]:
    toks = set(tokenize_for_bm25(text or ""))
    return {t for t in toks if len(t) > 2 and t not in _STOP}


def lexical_overlap(question: str, evid_texts: List[str]) -> Tuple[int, List[str]]:
    q = _content_tokens(question)
    e: Set[str] = set()
    for t in evid_texts:
        e |= _content_tokens(t)
    shared = sorted(q & e)
    return len(shared), shared


def primary_reason(rank: Optional[int], overlap: int) -> str:
    if rank is None or rank > 100:
        bucket = "A_absent_top100"
    elif rank <= 25:
        # miss@25 only — should not appear, keep for completeness
        bucket = "C_rank_9_25" if rank >= 9 else "hit"
    else:
        bucket = "B_rank_too_low_26plus"
    if overlap <= 0:
        ov = "zero_overlap"
    elif overlap <= 2:
        ov = "weak_overlap"
    else:
        ov = "has_overlap"
    return f"{bucket}__{ov}"


def match_activated_entities(
    graph: EMGraph,
    q_entity_keys: List[str],
    entity_bm25_index: Optional[EntityBM25Index] = None,
) -> Dict[str, Set[str]]:
    q_keys = {normalize_entity_key(k) for k in q_entity_keys if k}
    index = entity_bm25_index or EntityBM25Index.build(graph)
    matched = index.match_q_keys(q_keys)
    return {eid: set(scores) for eid, scores in matched.items()}


def activated_memories(
    graph: EMGraph, activated_entity_ids: Set[str]
) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """Return content seeds, ±1 seq from content, who-only seeds, all matched.

    Who hubs (Caroline/Melanie) would otherwise light up nearly the whole
    graph; viz/analysis treat content(+sequence) as the primary match set.
    """
    content_eids = {
        eid
        for eid in activated_entity_ids
        if graph.entities.get(eid) is not None
        and str(graph.entities[eid].type or "").lower() != "who"
    }
    who_eids = activated_entity_ids - content_eids
    content_seeds: Set[str] = set()
    who_seeds: Set[str] = set()
    for edge in graph.edges:
        if edge.entity_id in content_eids:
            content_seeds.add(edge.memory_id)
        elif edge.entity_id in who_eids:
            who_seeds.add(edge.memory_id)
    content_scores = {mid: 1.0 for mid in content_seeds}
    expanded = expand_sequence_neighbors(content_scores, graph, secondary_scale=0.5)
    seq_mids = set(expanded.keys()) - content_seeds
    who_only = who_seeds - content_seeds
    matched = set(expanded.keys())  # content seeds + their ±1 sequence
    return content_seeds, seq_mids, who_only, matched


def gold_memory_ids(graph: EMGraph, evidence: List[str]) -> Tuple[Set[str], List[str]]:
    dia_to_mid = {m.dia_id: m.id for m in graph.memories.values()}
    mids: Set[str] = set()
    missing: List[str] = []
    for dia in evidence or []:
        dia_id = str(dia).strip()
        parts = [p.strip() for p in dia_id.split(";") if p.strip()]
        for part in parts or [dia_id]:
            mid = dia_to_mid.get(part)
            if mid:
                mids.add(mid)
            else:
                missing.append(part)
    return mids, missing


def build_analysis(
    hit_payload: Dict[str, Any],
    sample: Dict[str, Any],
    graph: EMGraph,
) -> Dict[str, Any]:
    qa_list = list(sample.get("qa") or [])
    dia_text = {m.dia_id: (m.text_normalized or m.text) for m in graph.memories.values()}
    rows = hit_payload.get("rows") or []
    summary = dict(hit_payload.get("summary") or {})

    miss25_cases: List[Dict[str, Any]] = []
    miss8_cases: List[Dict[str, Any]] = []
    miss25_by_cat: Counter = Counter()
    miss8_by_cat: Counter = Counter()
    miss25_primary: Counter = Counter()
    miss8_primary: Counter = Counter()
    miss25_tags: Counter = Counter()
    miss8_tags: Counter = Counter()
    miss25_rank_buckets: Counter = Counter()
    miss8_rank_buckets: Counter = Counter()
    miss25_cat_x_primary: Dict[str, Counter] = defaultdict(Counter)

    for row in rows:
        qa_i = int(row["qa"])
        qa = qa_list[qa_i - 1] if 1 <= qa_i <= len(qa_list) else {}
        question = str(qa.get("question") or "").strip()
        gold = qa.get("answer")
        if isinstance(gold, list):
            gold = "; ".join(str(x) for x in gold)
        evidence = [str(x) for x in (qa.get("evidence") or []) if str(x)]
        evid_text = [dia_text.get(d, "") for d in evidence]
        overlap, shared = lexical_overlap(question, evid_text)
        rank = row.get("first_gold_rank")
        rank_i = int(rank) if rank is not None else None

        tags: List[str] = []
        if rank_i is None or rank_i > 100:
            tags.append("gold_absent_top100")
            rb = "not_in_top100"
        elif 9 <= rank_i <= 25:
            tags.append("gold_in_9_25_topk_shortfall")
            rb = "9-25"
        elif 26 <= rank_i <= 50:
            tags.append("gold_rank_26_100")
            rb = "26-50"
        elif 51 <= rank_i <= 100:
            tags.append("gold_rank_26_100")
            rb = "51-100"
        else:
            rb = "1-8"

        if overlap <= 0:
            tags.append("zero_lexical_overlap")
        elif overlap <= 2:
            tags.append("weak_lexical_overlap")
        else:
            tags.append("has_lexical_overlap")
        if len(evidence) > 1:
            tags.append("multi_evidence")

        primary = primary_reason(rank_i, overlap)
        cat = str(row.get("category") or qa.get("category") or "")

        case = {
            "qa": qa_i,
            "category": cat,
            "question": question,
            "gold": gold,
            "evidence": evidence,
            "first_gold_rank": rank_i,
            "overlap": overlap,
            "shared": shared,
            "evid_text": evid_text,
            "reason_tags": tags,
            "primary_reason": primary,
            "q_entity_keys": list(row.get("q_entity_keys") or []),
            "hit8": bool(row.get("hit8")),
            "hit25": bool(row.get("hit25")),
            "hit100": bool(row.get("hit100")),
        }

        if not row.get("hit8"):
            miss8_cases.append(case)
            miss8_by_cat[cat] += 1
            miss8_primary[primary] += 1
            miss8_rank_buckets[rb] += 1
            for t in tags:
                miss8_tags[t] += 1
        if not row.get("hit25"):
            miss25_cases.append(case)
            miss25_by_cat[cat] += 1
            miss25_primary[primary] += 1
            miss25_rank_buckets[rb] += 1
            miss25_cat_x_primary[cat][primary] += 1
            for t in tags:
                miss25_tags[t] += 1

    # activation stats for miss25
    for case in miss25_cases:
        act_map = match_activated_entities(graph, case.get("q_entity_keys") or [])
        act_e = set(act_map.keys())
        content_m, seq_m, who_m, matched_m = activated_memories(graph, act_e)
        gold_m, missing = gold_memory_ids(graph, case.get("evidence") or [])
        q_keys = {normalize_entity_key(k) for k in (case.get("q_entity_keys") or []) if k}
        matched_keys = {k for keys in act_map.values() for k in keys}
        case.update(
            {
                "activated_entity_ids": sorted(act_e),
                "activated_entity_matches": {
                    eid: sorted(v) for eid, v in act_map.items()
                },
                "matched_q_entity_keys": sorted(matched_keys),
                "unmatched_q_entity_keys": sorted(q_keys - matched_keys),
                "matched_memory_ids": sorted(matched_m),
                "content_seed_memory_ids": sorted(content_m),
                "sequence_memory_ids": sorted(seq_m),
                "who_only_seed_memory_ids": sorted(who_m),
                "gold_memory_ids": sorted(gold_m),
                "missing_evidence_dias": missing,
                "n_activated_entities": len(act_e),
                "n_matched_memories": len(matched_m),
                "n_content_seed_memories": len(content_m),
                "n_sequence_memories": len(seq_m),
                "n_who_only_memories": len(who_m),
                "n_gold_memories": len(gold_m),
                "n_gold_also_matched": len(gold_m & matched_m),
            }
        )

    miss25_cases.sort(key=lambda c: int(c["qa"]))
    return {
        "source_hit": str(DEFAULT_HIT.relative_to(ROOT)),
        "source_graph": str(DEFAULT_GRAPH.relative_to(ROOT)),
        "summary": summary,
        "miss8_count": len(miss8_cases),
        "miss25_count": len(miss25_cases),
        "miss100_count": sum(1 for r in rows if not r.get("hit100")),
        "miss8_by_category": dict(miss8_by_cat),
        "miss25_by_category": dict(miss25_by_cat),
        "miss8_rank_buckets": dict(miss8_rank_buckets),
        "miss25_rank_buckets": dict(miss25_rank_buckets),
        "miss8_reason_tags": dict(miss8_tags),
        "miss25_reason_tags": dict(miss25_tags),
        "miss8_primary": dict(miss8_primary),
        "miss25_primary": dict(miss25_primary),
        "miss25_cat_x_primary": {
            cat: dict(ctr) for cat, ctr in sorted(miss25_cat_x_primary.items())
        },
        "miss25_cases": miss25_cases,
        "miss8_cases": miss8_cases,
    }


def _compute_layout(graph: EMGraph) -> Dict[str, Tuple[float, float]]:
    """Stable bipartite-ish layout reused across all PNGs."""
    # Memory nodes by dialog order on a vertical strip; entities by type bands.
    mems = sorted(
        graph.memories.values(),
        key=lambda m: (int(m.session_num or 0), m.dia_id),
    )
    ents = sorted(
        graph.entities.values(),
        key=lambda e: (str(e.type or ""), e.value.lower()),
    )
    pos: Dict[str, Tuple[float, float]] = {}
    n_m = max(len(mems), 1)
    for i, m in enumerate(mems):
        # slight session-based x jitter so sessions form soft columns
        sess = int(m.session_num or 1)
        x = 1.0 + 0.08 * ((sess - 1) % 5)
        y = 1.0 - (i / (n_m - 1 if n_m > 1 else 1))
        pos[m.id] = (x, y)

    type_order = ["Who", "What", "When", "Where", "Why", "How", "Other"]
    by_type: Dict[str, List[Any]] = defaultdict(list)
    for e in ents:
        t = str(e.type or "Other")
        if t not in type_order:
            t = "Other"
        by_type[t].append(e)

    # place entities on left, stacked by type bands
    y_cursor = 1.0
    band_gap = 0.02
    for t in type_order:
        group = by_type.get(t) or []
        if not group:
            continue
        n = len(group)
        height = max(0.08, n / max(len(ents), 1))
        for j, e in enumerate(group):
            # fan out in x a little within band
            x = -0.15 - 0.12 * (j % 4)
            y = y_cursor - (j / max(n - 1, 1)) * height
            pos[e.id] = (x, y)
        y_cursor -= height + band_gap

    return pos


def render_case_png(
    graph: EMGraph,
    case: Dict[str, Any],
    pos: Dict[str, Tuple[float, float]],
    out_path: Path,
) -> None:
    act_e = set(case.get("activated_entity_ids") or [])
    matched_m = set(case.get("matched_memory_ids") or [])
    content_m = set(case.get("content_seed_memory_ids") or [])
    seq_m = set(case.get("sequence_memory_ids") or [])
    who_m = set(case.get("who_only_seed_memory_ids") or [])
    gold_m = set(case.get("gold_memory_ids") or [])
    unmatched_keys = list(case.get("unmatched_q_entity_keys") or [])
    q_keys = list(case.get("q_entity_keys") or [])
    # content entities only for hot edges (avoid Who-hub flood)
    act_content_e = {
        eid
        for eid in act_e
        if str(graph.entities[eid].type or "").lower() != "who"
    }

    G = nx.Graph()
    for mid in graph.memories:
        G.add_node(mid, kind="memory")
    for eid in graph.entities:
        G.add_node(eid, kind="entity")
    for edge in graph.edges:
        if edge.entity_id in G and edge.memory_id in G:
            G.add_edge(edge.entity_id, edge.memory_id)

    fig, ax = plt.subplots(figsize=(18, 14), dpi=140)
    ax.set_facecolor("#0b1220")
    fig.patch.set_facecolor("#0b1220")

    # idle edges (very faint)
    idle_edges = []
    hot_edges = []
    for u, v in G.edges():
        hot = (u in act_content_e and (v in matched_m or v in gold_m)) or (
            v in act_content_e and (u in matched_m or u in gold_m)
        )
        if hot:
            hot_edges.append((u, v))
        else:
            idle_edges.append((u, v))

    if idle_edges:
        nx.draw_networkx_edges(
            G, pos, edgelist=idle_edges, ax=ax, edge_color="#1e293b", width=0.15, alpha=0.25
        )
    if hot_edges:
        nx.draw_networkx_edges(
            G, pos, edgelist=hot_edges, ax=ax, edge_color="#fbbf24", width=1.2, alpha=0.85
        )

    # node groups
    idle_mem = [
        n
        for n in graph.memories
        if n not in matched_m and n not in gold_m and n not in who_m
    ]
    idle_ent = [n for n in graph.entities if n not in act_e]
    who_only = [n for n in who_m if n not in matched_m and n not in gold_m]
    content_only = [n for n in content_m if n not in gold_m]
    seq_only = [n for n in seq_m if n not in gold_m]
    gold_only = [n for n in gold_m if n not in matched_m]
    gold_and_matched = [n for n in gold_m if n in matched_m]
    act_who = [
        n
        for n in act_e
        if str(graph.entities[n].type or "").lower() == "who"
    ]
    act_other = [n for n in act_e if n not in act_who]

    def _draw(nodes, color, size, z, edgecolors="none", linewidths=0.0, alpha=1.0):
        if not nodes:
            return
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=nodes,
            ax=ax,
            node_color=color,
            node_size=size,
            alpha=alpha,
            edgecolors=edgecolors,
            linewidths=linewidths,
        )

    _draw(idle_ent, "#334155", 8, 1, alpha=0.45)
    _draw(idle_mem, "#475569", 14, 1, alpha=0.5)
    _draw(who_only, "#155e75", 40, 2, edgecolors="#67e8f9", linewidths=0.4)
    _draw(seq_only, "#0e7490", 55, 3, edgecolors="#22d3ee", linewidths=0.6)
    _draw(content_only, "#0891b2", 70, 4, edgecolors="#a5f3fc", linewidths=0.8)
    _draw(act_who, "#b45309", 90, 5, edgecolors="#fde68a", linewidths=1.0)
    _draw(act_other, "#f59e0b", 110, 6, edgecolors="#fef3c7", linewidths=1.2)
    _draw(gold_only, "#ef4444", 160, 7, edgecolors="#fecaca", linewidths=1.6)
    _draw(gold_and_matched, "#c084fc", 180, 8, edgecolors="#faf5ff", linewidths=1.8)

    # labels for activated entities + gold memories
    labels = {}
    for eid in act_e:
        ent = graph.entities[eid]
        labels[eid] = _short(ent.value, 22)
    for mid in gold_m | (content_m & matched_m):
        if mid in graph.memories:
            labels[mid] = graph.memories[mid].dia_id
    if labels:
        nx.draw_networkx_labels(
            G,
            pos,
            labels=labels,
            ax=ax,
            font_size=7,
            font_color="#f8fafc",
            font_family="DejaVu Sans",
        )

    # unmatched q-keys as text box
    key_lines = [
        f"q_keys: {', '.join(q_keys) if q_keys else '(none)'}",
        f"matched: {', '.join(case.get('matched_q_entity_keys') or []) or '(none)'}",
        f"unmatched: {', '.join(unmatched_keys) or '(none)'}",
    ]
    ax.text(
        0.01,
        0.01,
        "\n".join(key_lines),
        transform=ax.transAxes,
        fontsize=8,
        color="#e2e8f0",
        va="bottom",
        ha="left",
        family="DejaVu Sans",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#1e293b", edgecolor="#334155", alpha=0.92),
    )

    qa = case.get("qa")
    rank = case.get("first_gold_rank")
    title = (
        f"QA{qa} · cat{case.get('category')} · {case.get('primary_reason')}\n"
        f"rank={rank} · overlap={case.get('overlap')} · "
        f"actE={case.get('n_activated_entities')} "
        f"matchedM={case.get('n_matched_memories')} "
        f"gold={case.get('n_gold_memories')} "
        f"(∩matched {case.get('n_gold_also_matched')})"
    )
    ax.set_title(title, color="#e2e8f0", fontsize=11, pad=10)
    ax.text(
        0.01,
        0.98,
        f"Q: {_short(str(case.get('question') or ''), 140)}\n"
        f"Gold: {_short(str(case.get('gold') or ''), 100)}\n"
        f"Evidence: {', '.join(case.get('evidence') or [])}",
        transform=ax.transAxes,
        fontsize=8,
        color="#cbd5e1",
        va="top",
        ha="left",
        family="DejaVu Sans",
    )

    # legend
    legend_items = [
        ("#475569", "memory idle"),
        ("#334155", "entity idle"),
        ("#f59e0b", "matched entity (q-key)"),
        ("#0891b2", "matched memory (content seed)"),
        ("#0e7490", "matched memory (±1 sequence)"),
        ("#155e75", "who-only seed memory"),
        ("#ef4444", "gold memory"),
        ("#c084fc", "gold ∩ matched"),
    ]
    for i, (color, name) in enumerate(legend_items):
        ax.scatter(
            [],
            [],
            c=color,
            s=40,
            label=name,
            edgecolors="white",
            linewidths=0.3,
        )
    leg = ax.legend(
        loc="upper right",
        fontsize=7,
        framealpha=0.85,
        facecolor="#0f172a",
        edgecolor="#334155",
        labelcolor="#e2e8f0",
    )

    ax.set_axis_off()
    ax.set_xlim(-0.75, 1.45)
    ys = [p[1] for p in pos.values()]
    pad = 0.05
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    hit_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_HIT
    graph_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_GRAPH
    if not hit_path.exists():
        raise FileNotFoundError(hit_path)
    if not graph_path.exists():
        raise FileNotFoundError(graph_path)

    print(f"loading hit {hit_path}", flush=True)
    hit = json.loads(hit_path.read_text(encoding="utf-8"))
    print(f"loading graph {graph_path}", flush=True)
    graph = EMGraph.load_from_file(str(graph_path))
    sample = next(
        s
        for s in json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if s.get("sample_id") == "conv-26"
    )

    analysis = build_analysis(hit, sample, graph)
    ANALYSIS_PATH.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    s = analysis["summary"]
    print(
        f"wrote {ANALYSIS_PATH} · hit@25={s.get('hit25')}/{s.get('n')} "
        f"miss25={analysis['miss25_count']}",
        flush=True,
    )
    print("miss25_primary:", analysis["miss25_primary"], flush=True)

    print("computing shared layout ...", flush=True)
    pos = _compute_layout(graph)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in analysis["miss25_cases"]:
        qa = int(case["qa"])
        reason = re.sub(r"[^a-zA-Z0-9_]+", "_", str(case.get("primary_reason") or "miss"))
        fname = f"qa{qa:03d}_{reason}.png"
        out_path = VIZ_DIR / fname
        print(
            f"  render QA{qa}: actE={case.get('n_activated_entities')} "
            f"matchedM={case.get('n_matched_memories')} gold={case.get('n_gold_memories')}",
            flush=True,
        )
        render_case_png(graph, case, pos, out_path)
        manifest.append(
            {
                "qa": qa,
                "file": fname,
                "primary_reason": case.get("primary_reason"),
                "category": case.get("category"),
                "first_gold_rank": case.get("first_gold_rank"),
                "q_entity_keys": case.get("q_entity_keys"),
                "matched_q_entity_keys": case.get("matched_q_entity_keys"),
                "unmatched_q_entity_keys": case.get("unmatched_q_entity_keys"),
                "n_activated_entities": case.get("n_activated_entities"),
                "n_matched_memories": case.get("n_matched_memories"),
                "n_gold_memories": case.get("n_gold_memories"),
                "n_gold_also_matched": case.get("n_gold_also_matched"),
            }
        )

    (VIZ_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "n": len(manifest),
                "analysis": str(ANALYSIS_PATH.relative_to(ROOT)),
                "graph": str(graph_path.relative_to(ROOT)),
                "hit": str(hit_path.relative_to(ROOT)),
                "cases": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    pointer = EXP_DIR / "miss_viz_hit166.md"
    pointer.write_text(
        "\n".join(
            [
                "# Miss@25 visualizations (hit@25=166 track)",
                "",
                f"- Analysis: `{ANALYSIS_PATH.relative_to(ROOT)}`",
                f"- PNGs: `{VIZ_DIR.relative_to(ROOT)}/` ({len(manifest)} cases)",
                f"- Manifest: `{VIZ_DIR.relative_to(ROOT)}/manifest.json`",
                "- Colors: amber=matched entity (q-key), cyan=content seed memory,",
                "  teal=±1 sequence memory, red=gold, purple=gold∩matched",
                "- Generated by `analyze_miss_hit25_viz.py`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(manifest)} PNGs under {VIZ_DIR}", flush=True)
    print(f"wrote {pointer}", flush=True)


if __name__ == "__main__":
    main()
