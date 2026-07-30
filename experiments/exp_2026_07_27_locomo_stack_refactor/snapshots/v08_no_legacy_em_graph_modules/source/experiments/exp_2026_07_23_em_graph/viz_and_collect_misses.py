#!/usr/bin/env python3
"""Visualize EM graph (session_1 focus) and dump hit@8 miss cases with diagnostics."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import EMGraph, retrieve_dialog_ids  # noqa: E402
from em_graph.recall.tokenize import tokenize_for_bm25  # noqa: E402


def _tokens(value: str) -> set[str]:
    return set(tokenize_for_bm25(value))


GRAPH_PATH = ROOT / "outputs" / "em_graph" / "conv-26_em_graph.json"
HIT_PATH = ROOT / "outputs" / "em_graph" / "conv-26_offline_hit.json"
DATA_PATH = ROOT / "data" / "locomo10.json"
OUT_DIR = ROOT / "outputs" / "em_graph"
EXP_DIR = Path(__file__).resolve().parent


def _short(text: str, n: int = 90) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def build_session1_focus(graph: EMGraph, max_memories: int = 8) -> dict:
    """First N session_1 memories + all linked entities (readable layout)."""
    memories = sorted(
        [m for m in graph.memories.values() if m.session_num == 1],
        key=lambda m: m.dia_id,
    )[:max_memories]
    mem_ids = {m.id for m in memories}
    linked_entity_ids = {
        e.entity_id for e in graph.edges if e.memory_id in mem_ids
    }
    # Drop ultra-hub entities that would clutter the focus view.
    degree = Counter(e.entity_id for e in graph.edges)
    keep_entities = []
    for eid in linked_entity_ids:
        ent = graph.entities[eid]
        if degree[eid] > 80 and ent.type == "Who":
            # Keep person hubs only if they link ≥2 of the focus memories.
            focus_links = sum(
                1 for e in graph.edges if e.entity_id == eid and e.memory_id in mem_ids
            )
            if focus_links < 2:
                continue
        keep_entities.append(ent)

    nodes = []
    for m in memories:
        nodes.append(
            {
                "id": m.id,
                "type": "memory",
                "label": m.dia_id,
                "subtitle": _short(m.text_normalized or m.text, 60),
                "content": f"[{m.speaker}] {m.text_normalized or m.text}",
            }
        )
    for ent in keep_entities:
        nodes.append(
            {
                "id": ent.id,
                "type": "entity",
                "label": f"{ent.value}",
                "subtitle": ent.type,
                "content": f"{ent.value} ({ent.type})",
            }
        )
    keep_ids = {n["id"] for n in nodes}
    edges = [
        {
            "from": e.entity_id,
            "to": e.memory_id,
            "type": e.edge_type.value if hasattr(e.edge_type, "value") else str(e.edge_type),
            "w": e.weight,
        }
        for e in graph.edges
        if e.entity_id in keep_ids and e.memory_id in keep_ids
    ]
    return {
        "note": f"conv-26 session_1 first {len(memories)} memories + linked entities",
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges),
            "memories": len(memories),
            "entities": len(keep_entities),
        },
    }


def write_vis_html(payload: dict, out_html: Path, title: str) -> None:
    raw = json.dumps(payload, ensure_ascii=False)
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"/>
<title>{title}</title>
<style>
body{{margin:0;font-family:ui-sans-serif,system-ui;background:#0f172a;color:#e2e8f0}}
header{{padding:12px 16px;border-bottom:1px solid #334155}}
#mynetwork{{width:100vw;height:calc(100vh - 70px)}}
.legend span{{display:inline-block;margin-right:12px;font-size:13px}}
.dot{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:4px}}
</style>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
</head><body>
<header>
  <div><b>EM Graph</b> · {title}</div>
  <div class="legend">
    <span><i class="dot" style="background:#059669"></i>Memory (dia)</span>
    <span><i class="dot" style="background:#d97706"></i>Entity</span>
    <span>nodes={payload['stats']['nodes']} · edges={payload['stats']['edges']}</span>
  </div>
</header>
<div id="mynetwork"></div>
<script>
const raw = {raw};
const colors = {{memory:'#059669', entity:'#d97706'}};
const nodes = new vis.DataSet(raw.nodes.map(n => ({{
  id: n.id,
  label: n.type==='memory' ? (n.label + '\\n' + n.subtitle) : (n.label + '\\n' + n.subtitle),
  title: n.content || n.label,
  color: colors[n.type] || '#64748b',
  font: {{color:'#fff', size:12}},
  shape: n.type==='memory' ? 'box' : 'ellipse',
}})));
const edges = new vis.DataSet(raw.edges.map((e,i) => ({{
  id: i, from: e.from, to: e.to, label: 'mentions',
  font:{{size:9, color:'#94a3b8'}},
  color: {{color:'#94a3b8'}},
  arrows: 'to'
}})));
new vis.Network(document.getElementById('mynetwork'), {{nodes, edges}}, {{
  physics: {{barnesHut: {{gravitationalConstant: -6000, springLength: 110}}}},
  interaction: {{hover: true, tooltipDelay: 80}},
}});
</script>
</body></html>
"""
    out_html.write_text(html, encoding="utf-8")


def diagnose_miss(
    graph: EMGraph,
    question: str,
    gold: list[str],
    category: str,
    qa_idx: int,
    answer,
) -> dict:
    q_tokens = _tokens(question)
    mid_by_dia = {m.dia_id: m for m in graph.memories.values()}
    entity_by_id = graph.entities
    edges_by_mem = defaultdict(list)
    for e in graph.edges:
        edges_by_mem[e.memory_id].append(e.entity_id)

    # Matched entities for the question
    matched_entities = []
    for ent in entity_by_id.values():
        e_toks = _tokens(ent.value) | _tokens(ent.key)
        ov = sorted(q_tokens & e_toks)
        if ov:
            n_mem = sum(1 for edge in graph.edges if edge.entity_id == ent.id)
            matched_entities.append(
                {
                    "entity": ent.value,
                    "type": ent.type,
                    "overlap": ov,
                    "degree": n_mem,
                }
            )
    matched_entities.sort(key=lambda x: (-len(x["overlap"]), -x["degree"], x["entity"]))

    gold_details = []
    for g in gold:
        mem = mid_by_dia.get(g)
        if not mem:
            gold_details.append({"dia_id": g, "in_graph": False})
            continue
        search = " ".join(
            [mem.text_normalized, mem.text, mem.speaker, mem.blip_caption, mem.query]
        )
        lex_ov = sorted(q_tokens & _tokens(search))
        linked = []
        for eid in edges_by_mem.get(mem.id, []):
            ent = entity_by_id[eid]
            e_ov = sorted(q_tokens & (_tokens(ent.value) | _tokens(ent.key)))
            if e_ov:
                linked.append({"entity": ent.value, "type": ent.type, "overlap": e_ov})
        gold_details.append(
            {
                "dia_id": g,
                "in_graph": True,
                "speaker": mem.speaker,
                "date_time": mem.date_time,
                "text": mem.text,
                "text_normalized": mem.text_normalized,
                "lexical_overlap": lex_ov,
                "matched_linked_entities": linked,
            }
        )

    ranked100 = retrieve_dialog_ids(graph, question, top_k=100)
    ranked25 = ranked100[:25]
    ranked8 = ranked100[:8]
    gset = set(gold)
    first = None
    for i, (dia, score) in enumerate(ranked100, 1):
        if dia in gset:
            first = {"rank": i, "dia_id": dia, "score": score}
            break

    top8 = []
    for dia, score in ranked8:
        mem = mid_by_dia.get(dia)
        top8.append(
            {
                "dia_id": dia,
                "score": round(score, 4),
                "snippet": _short((mem.text_normalized if mem else ""), 100),
            }
        )

    # Failure taxonomy
    gold_in_graph = all(d.get("in_graph") for d in gold_details)
    any_lex = any(d.get("lexical_overlap") for d in gold_details if d.get("in_graph"))
    any_ent = any(
        d.get("matched_linked_entities") for d in gold_details if d.get("in_graph")
    )
    if not gold_in_graph:
        reason = "gold_absent_from_graph"
    elif not any_lex and not any_ent:
        reason = "no_token_bridge"  # paraphrase / no shared content tokens
    elif first and first["rank"] > 8:
        reason = "ranked_but_outside_top8"
    elif first is None:
        reason = "scored_zero_or_buried_beyond_100"
    else:
        reason = "other"

    # Hub dilution signal: top matched entities are very high degree
    hubby = [e for e in matched_entities[:5] if e["degree"] >= 50]

    return {
        "qa": qa_idx,
        "category": category,
        "question": question,
        "gold_answer": answer,
        "gold": gold,
        "failure_reason": reason,
        "first_gold": first,
        "hit25": bool({d for d, _ in ranked25} & gset),
        "hit100": first is not None,
        "q_tokens": sorted(q_tokens),
        "matched_entities_top": matched_entities[:12],
        "hub_entities_in_top_matches": hubby,
        "gold_details": gold_details,
        "top8_predicted": top8,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graph = EMGraph.load_from_file(str(GRAPH_PATH))
    sample = next(
        s for s in json.loads(DATA_PATH.read_text()) if s["sample_id"] == "conv-26"
    )
    hit_rows = {
        r["qa"]: r for r in json.loads(HIT_PATH.read_text())["rows"]
    }

    # 1) Visualization
    focus = build_session1_focus(graph, max_memories=8)
    focus_json = OUT_DIR / "conv-26_em_viz_session1_focus.json"
    focus_html = OUT_DIR / "conv-26_em_viz_session1_focus.html"
    focus_json.write_text(json.dumps(focus, indent=2, ensure_ascii=False), encoding="utf-8")
    write_vis_html(focus, focus_html, "conv-26 session_1 focus")
    # also copy html into experiment dir for easy browsing
    (EXP_DIR / "viz_session1_focus.html").write_text(
        focus_html.read_text(encoding="utf-8"), encoding="utf-8"
    )
    print("wrote", focus_html)
    print("wrote", EXP_DIR / "viz_session1_focus.html")

    # 2) Miss dump
    misses = []
    reason_counts = Counter()
    for i, qa in enumerate(sample["qa"], 1):
        row = hit_rows.get(i)
        if not row or row.get("hit8"):
            continue
        question = str(qa.get("question") or "").strip()
        gold = [str(x) for x in (qa.get("evidence") or []) if str(x)]
        if not question or not gold:
            continue
        item = diagnose_miss(
            graph,
            question,
            gold,
            str(qa.get("category")),
            i,
            qa.get("answer"),
        )
        misses.append(item)
        reason_counts[item["failure_reason"]] += 1

    miss_path = EXP_DIR / "misses_hit8.json"
    miss_md = EXP_DIR / "misses_hit8.md"
    payload = {
        "sample_id": "conv-26",
        "metric": "evidence_hit@8",
        "n_miss": len(misses),
        "n_total_scored": 197,
        "reason_counts": dict(reason_counts),
        "misses": misses,
    }
    miss_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# conv-26 EM Graph — hit@8 misses",
        "",
        f"- Total scored: 197 · miss@8: **{len(misses)}**",
        f"- Reason counts: `{dict(reason_counts)}`",
        "",
    ]
    for m in misses:
        lines.append(f"## QA#{m['qa']} · cat {m['category']} · `{m['failure_reason']}`")
        lines.append(f"- Q: {m['question']}")
        lines.append(f"- Gold answer: {m['gold_answer']}")
        lines.append(f"- Gold dia: {m['gold']}")
        if m["first_gold"]:
            lines.append(
                f"- First gold rank: #{m['first_gold']['rank']} "
                f"({m['first_gold']['dia_id']}, score={m['first_gold']['score']:.4f})"
            )
        else:
            lines.append("- First gold rank: not in top100")
        lines.append(f"- Q tokens: {', '.join(m['q_tokens'])}")
        if m["matched_entities_top"][:5]:
            lines.append("- Top matched entities:")
            for e in m["matched_entities_top"][:5]:
                lines.append(
                    f"  - {e['entity']} ({e['type']}) ov={e['overlap']} degree={e['degree']}"
                )
        for g in m["gold_details"]:
            if not g.get("in_graph"):
                lines.append(f"- Gold {g['dia_id']}: ABSENT from graph")
                continue
            lines.append(
                f"- Gold {g['dia_id']} [{g['speaker']}]: {_short(g.get('text_normalized') or g.get('text'), 140)}"
            )
            lines.append(f"  - lexical_ov: {g.get('lexical_overlap')}")
            lines.append(
                f"  - entity_ov: {[x['entity']+str(x['overlap']) for x in g.get('matched_linked_entities') or []]}"
            )
        lines.append("- Top8 predicted:")
        for t in m["top8_predicted"][:5]:
            lines.append(f"  - {t['dia_id']} ({t['score']}): {t['snippet']}")
        lines.append("")
    miss_md.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", miss_path)
    print("wrote", miss_md)
    print("reason_counts", dict(reason_counts))


if __name__ == "__main__":
    main()
