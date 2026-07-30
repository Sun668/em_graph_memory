#!/usr/bin/env python3
"""Per-case full EM-graph viz for zero-overlap miss buckets.

Targets (from miss_analysis.json miss@25):
  - B_rank_too_low_26plus__zero_overlap  (gold rank 26–100 + zero overlap)
  - A_absent_top100__zero_overlap        (gold absent from top-100 + zero overlap)

For each case, write an interactive HTML with the full bipartite graph and:
  - activated entities  = soft-matched q_entity_keys
  - activated memories  = 1-hop Memory nodes from those entities
  - gold memories       = evidence dia_ids
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import EMGraph, EntityBM25Index  # noqa: E402
from em_graph.build import normalize_entity_key  # noqa: E402

EXP_DIR = Path(__file__).resolve().parent
GRAPH_PATH = ROOT / "outputs" / "em_graph_gpt" / "conv-26_em_graph.json"
MISS_PATH = EXP_DIR / "miss_analysis.json"
OUT_DIR = ROOT / "outputs" / "em_graph_gpt" / "miss_viz_zero_overlap"

TARGET_REASONS = {
    "B_rank_too_low_26plus__zero_overlap",
    "A_absent_top100__zero_overlap",
}

REASON_LABEL = {
    "B_rank_too_low_26plus__zero_overlap": "gold_rank_26_100__zero_overlap",
    "A_absent_top100__zero_overlap": "gold_absent_top100__zero_overlap",
}


def _short(text: str, n: int = 70) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def match_activated_entities(
    graph: EMGraph,
    q_entity_keys: List[str],
    entity_bm25_index: Optional[EntityBM25Index] = None,
) -> Dict[str, Set[str]]:
    """entity_id -> matched question keys."""
    q_keys = {normalize_entity_key(k) for k in q_entity_keys if k}
    index = entity_bm25_index or EntityBM25Index.build(graph)
    matched = index.match_q_keys(q_keys)
    return {eid: set(scores) for eid, scores in matched.items()}


def activated_memories(
    graph: EMGraph, activated_entity_ids: Set[str]
) -> Tuple[Set[str], Set[str]]:
    """Return (content-activated memories, who-only-activated memories).

    Who hubs (Caroline/Melanie) would otherwise light up nearly the whole
    graph; content activations are the useful highlight.
    """
    content_eids = {
        eid
        for eid in activated_entity_ids
        if graph.entities.get(eid) is not None
        and str(graph.entities[eid].type or "").lower() != "who"
    }
    who_eids = activated_entity_ids - content_eids
    content_mids: Set[str] = set()
    who_mids: Set[str] = set()
    for edge in graph.edges:
        if edge.entity_id in content_eids:
            content_mids.add(edge.memory_id)
        elif edge.entity_id in who_eids:
            who_mids.add(edge.memory_id)
    who_only = who_mids - content_mids
    return content_mids, who_only


def gold_memory_ids(graph: EMGraph, evidence: List[str]) -> Tuple[Set[str], List[str]]:
    dia_to_mid = {m.dia_id: m.id for m in graph.memories.values()}
    mids: Set[str] = set()
    missing: List[str] = []
    for dia in evidence or []:
        dia_id = str(dia).strip()
        # tolerate "D8:6; D9:17" style annotation glitches
        parts = [p.strip() for p in dia_id.split(";") if p.strip()]
        for part in parts or [dia_id]:
            mid = dia_to_mid.get(part)
            if mid:
                mids.add(mid)
            else:
                missing.append(part)
    return mids, missing


def build_shared_graph(graph: EMGraph) -> Dict[str, Any]:
    nodes = []
    for m in graph.memories.values():
        nodes.append(
            {
                "id": m.id,
                "kind": "memory",
                "label": m.dia_id,
                "subtitle": _short(m.text_normalized or m.text, 48),
                "title": f"[{m.speaker}] {m.text_normalized or m.text}",
                "dia_id": m.dia_id,
                "session": m.session_num,
                "speaker": m.speaker,
            }
        )
    for ent in graph.entities.values():
        nodes.append(
            {
                "id": ent.id,
                "kind": "entity",
                "label": ent.value,
                "subtitle": ent.type,
                "title": f"{ent.value} ({ent.type}) key={ent.key}",
                "etype": ent.type,
                "key": ent.key,
            }
        )
    edges = [
        {"from": e.entity_id, "to": e.memory_id, "w": float(e.weight or 1.0)}
        for e in graph.edges
    ]
    return {
        "sample_id": "conv-26",
        "stats": dict(graph.stats),
        "nodes": nodes,
        "edges": edges,
    }


CASE_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>QA{qa} · {reason_short}</title>
<style>
body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:#0b1220;color:#e2e8f0}}
header{{padding:10px 14px;border-bottom:1px solid #1e293b;display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}
header .meta{{flex:1;min-width:280px}}
header h1{{margin:0 0 6px;font-size:16px;font-weight:650}}
header p{{margin:2px 0;font-size:12px;color:#cbd5e1;line-height:1.35}}
.legend{{font-size:12px;display:grid;grid-template-columns:auto auto;gap:4px 14px}}
.dot{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:middle}}
#mynetwork{{width:100vw;height:calc(100vh - 132px);background:#020617}}
#status{{padding:6px 14px;font-size:11px;color:#94a3b8;border-top:1px solid #1e293b}}
a{{color:#38bdf8}}
</style>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
</head><body>
<header>
  <div class="meta">
    <h1>QA{qa} · cat{category} · {reason_short}</h1>
    <p><b>Q:</b> {question}</p>
    <p><b>Gold:</b> {gold}</p>
    <p><b>Evidence:</b> {evidence} · first_gold_rank={rank} · overlap={overlap}</p>
    <p><b>q_entities:</b> {q_entities}</p>
    <p><b>Activated:</b> {n_act_e} entities → {n_act_m} content-mem
       (+{n_who_m} who-only) · <b>Gold:</b> {n_gold}
       (<a href="index.html">index</a>)</p>
  </div>
  <div class="legend">
    <span><i class="dot" style="background:#64748b"></i>memory (idle)</span>
    <span><i class="dot" style="background:#475569"></i>entity (idle)</span>
    <span><i class="dot" style="background:#f59e0b"></i>activated entity</span>
    <span><i class="dot" style="background:#22d3ee"></i>content-activated memory</span>
    <span><i class="dot" style="background:#155e75"></i>who-only-activated memory</span>
    <span><i class="dot" style="background:#ef4444"></i>gold memory</span>
    <span><i class="dot" style="background:#c084fc"></i>gold ∩ content-activated</span>
  </div>
</header>
<div id="mynetwork"></div>
<div id="status">Loading graph…</div>
<script src="graph_data.js"></script>
<script>
const CASE = {case_json};
const g = window.EM_GRAPH;
const actE = new Set(CASE.activated_entity_ids);
const actM = new Set(CASE.activated_memory_ids);
const whoM = new Set(CASE.who_only_memory_ids || []);
const goldM = new Set(CASE.gold_memory_ids);

function nodeStyle(n) {{
  const idleMem = {{background:'#334155', border:'#475569'}};
  const idleEnt = {{background:'#1e293b', border:'#334155'}};
  if (n.kind === 'memory') {{
    const isGold = goldM.has(n.id);
    const isAct = actM.has(n.id);
    const isWho = whoM.has(n.id);
    if (isGold && isAct) return {{background:'#a855f7', border:'#faf5ff', borderWidth:3}};
    if (isGold) return {{background:'#ef4444', border:'#fecaca', borderWidth:3}};
    if (isAct) return {{background:'#0891b2', border:'#67e8f9', borderWidth:2}};
    if (isWho) return {{background:'#155e75', border:'#0e7490', borderWidth:1}};
    return {{...idleMem, borderWidth:1}};
  }}
  if (actE.has(n.id)) {{
    const isWhoEnt = (n.etype || '').toLowerCase() === 'who';
    return {{
      background: isWhoEnt ? '#b45309' : '#d97706',
      border: '#fde68a',
      borderWidth: 3
    }};
  }}
  return {{...idleEnt, borderWidth:1}};
}}

const nodes = new vis.DataSet(g.nodes.map(n => {{
  const highlight = actE.has(n.id) || actM.has(n.id) || goldM.has(n.id);
  return {{
    id: n.id,
    label: highlight ? (n.label + '\\n' + (n.subtitle || '')) : n.label,
    title: n.title || n.label,
    shape: n.kind === 'memory' ? 'box' : 'dot',
    size: n.kind === 'entity' ? (actE.has(n.id) ? 16 : 6) : undefined,
    color: nodeStyle(n),
    font: {{
      color: highlight ? '#f8fafc' : '#64748b',
      size: highlight ? 12 : 9,
      face: 'system-ui'
    }},
    borderWidth: nodeStyle(n).borderWidth,
  }};
}}));

const edges = new vis.DataSet(g.edges.map((e, i) => {{
  const hot = actE.has(e.from) && (actM.has(e.to) || goldM.has(e.to));
  const warm = actE.has(e.from) || actM.has(e.to) || goldM.has(e.to);
  return {{
    id: i,
    from: e.from,
    to: e.to,
    color: {{
      color: hot ? '#fbbf24' : (warm ? '#334155' : '#0f172a'),
      opacity: hot ? 0.9 : (warm ? 0.25 : 0.06)
    }},
    width: hot ? 2.0 : (warm ? 0.7 : 0.3),
    smooth: false,
  }};
}}));

const status = document.getElementById('status');
const network = new vis.Network(
  document.getElementById('mynetwork'),
  {{nodes, edges}},
  {{
    physics: {{
      enabled: true,
      barnesHut: {{
        gravitationalConstant: -2200,
        centralGravity: 0.12,
        springLength: 90,
        springConstant: 0.02,
        damping: 0.4,
        avoidOverlap: 0.2
      }},
      stabilization: {{iterations: 120, updateInterval: 25}}
    }},
    interaction: {{hover: true, tooltipDelay: 60, multiselect: true}},
  }}
);

network.once('stabilizationIterationsDone', () => {{
  network.setOptions({{physics: {{enabled: false}}}});
  const focus = [...goldM, ...[...actE].filter(id => {{
    const n = g.nodes.find(x => x.id === id);
    return n && (n.etype || '').toLowerCase() !== 'who';
  }})];
  if (focus.length) {{
    network.fit({{nodes: focus, animation: true}});
  }}
  status.textContent =
    `nodes=${{g.nodes.length}} edges=${{g.edges.length}} · ` +
    `act entities=${{actE.size}} content-mem=${{actM.size}} who-only-mem=${{whoM.size}} · ` +
    `gold=${{goldM.size}} · physics off`;
}});
</script>
</body></html>
"""


INDEX_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>Zero-overlap miss viz index</title>
<style>
body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:24px;background:#0b1220;color:#e2e8f0}}
h1{{font-size:20px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #1e293b;padding:8px 10px;text-align:left;vertical-align:top}}
th{{color:#94a3b8;font-weight:600}}
a{{color:#38bdf8;text-decoration:none}}
.badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;background:#1e293b}}
.A{{background:#7f1d1d;color:#fecaca}}
.B{{background:#78350f;color:#fde68a}}
</style></head><body>
<h1>EM-graph miss viz · zero lexical overlap</h1>
<p>Full bipartite graph with activated entity/memory (1-hop) and gold memories highlighted.
Source: miss_analysis.json · graph: outputs/em_graph_gpt/conv-26_em_graph.json</p>
<p>A = gold absent top-100 + zero overlap ({n_a}) ·
B = gold rank 26–100 + zero overlap ({n_b})</p>
<table>
<thead><tr>
<th>QA</th><th>bucket</th><th>cat</th><th>rank</th><th>act E/M</th><th>gold</th><th>question</th>
</tr></thead>
<tbody>
{rows}
</tbody></table>
</body></html>
"""


def main() -> None:
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(GRAPH_PATH)
    if not MISS_PATH.exists():
        raise FileNotFoundError(MISS_PATH)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graph = EMGraph.load_from_file(str(GRAPH_PATH))
    miss = json.loads(MISS_PATH.read_text(encoding="utf-8"))
    cases = [
        c
        for c in miss.get("miss25_cases") or []
        if c.get("primary_reason") in TARGET_REASONS
    ]
    cases.sort(key=lambda c: (c.get("primary_reason") or "", int(c.get("qa") or 0)))
    print(f"cases={len(cases)} graph={graph.stats}", flush=True)

    shared = build_shared_graph(graph)
    graph_js = "window.EM_GRAPH = " + json.dumps(shared, ensure_ascii=False) + ";\n"
    (OUT_DIR / "graph_data.js").write_text(graph_js, encoding="utf-8")
    print(f"wrote {OUT_DIR / 'graph_data.js'} ({len(graph_js)//1024} KB)", flush=True)

    index_rows: List[str] = []
    manifest: List[Dict[str, Any]] = []

    for case in cases:
        qa = int(case["qa"])
        reason = str(case["primary_reason"])
        reason_short = REASON_LABEL[reason]
        act_map = match_activated_entities(graph, case.get("q_entity_keys") or [])
        act_e = set(act_map.keys())
        act_m, who_m = activated_memories(graph, act_e)
        gold_m, missing = gold_memory_ids(graph, case.get("evidence") or [])

        case_payload = {
            "qa": qa,
            "category": case.get("category"),
            "question": case.get("question"),
            "gold": case.get("gold"),
            "evidence": case.get("evidence") or [],
            "first_gold_rank": case.get("first_gold_rank"),
            "overlap": case.get("overlap"),
            "primary_reason": reason,
            "reason_short": reason_short,
            "q_entity_keys": case.get("q_entity_keys") or [],
            "activated_entity_ids": sorted(act_e),
            "activated_entity_matches": {
                eid: sorted(v) for eid, v in act_map.items()
            },
            "activated_memory_ids": sorted(act_m),
            "who_only_memory_ids": sorted(who_m),
            "gold_memory_ids": sorted(gold_m),
            "missing_evidence_dias": missing,
            "n_activated_entities": len(act_e),
            "n_activated_memories": len(act_m),
            "n_who_only_memories": len(who_m),
            "n_gold_memories": len(gold_m),
            "n_gold_also_activated": len(gold_m & act_m),
            "n_gold_in_who_only": len(gold_m & who_m),
        }
        fname = f"qa{qa:03d}_{reason_short}.html"
        html = CASE_HTML.format(
            qa=qa,
            category=case.get("category"),
            reason_short=reason_short,
            question=_short(str(case.get("question") or ""), 220),
            gold=_short(str(case.get("gold") or ""), 160),
            evidence=", ".join(str(x) for x in (case.get("evidence") or [])),
            rank=case.get("first_gold_rank"),
            overlap=case.get("overlap"),
            q_entities=", ".join(case.get("q_entity_keys") or []),
            n_act_e=len(act_e),
            n_act_m=len(act_m),
            n_who_m=len(who_m),
            n_gold=len(gold_m),
            case_json=json.dumps(case_payload, ensure_ascii=False),
        )
        (OUT_DIR / fname).write_text(html, encoding="utf-8")

        badge = "A" if reason.startswith("A_") else "B"
        index_rows.append(
            "<tr>"
            f"<td><a href='{fname}'>QA{qa}</a></td>"
            f"<td><span class='badge {badge}'>{badge}</span> {reason_short}</td>"
            f"<td>{case.get('category')}</td>"
            f"<td>{case.get('first_gold_rank')}</td>"
            f"<td>{len(act_e)} / {len(act_m)} (+{len(who_m)} who)</td>"
            f"<td>{len(gold_m)} (∩content {len(gold_m & act_m)})</td>"
            f"<td>{_short(str(case.get('question') or ''), 100)}</td>"
            "</tr>"
        )
        manifest.append(
            {
                "file": fname,
                **{
                    k: case_payload[k]
                    for k in (
                        "qa",
                        "category",
                        "primary_reason",
                        "reason_short",
                        "question",
                        "gold",
                        "evidence",
                        "first_gold_rank",
                        "overlap",
                        "q_entity_keys",
                        "n_activated_entities",
                        "n_activated_memories",
                        "n_who_only_memories",
                        "n_gold_memories",
                        "n_gold_also_activated",
                        "n_gold_in_who_only",
                        "missing_evidence_dias",
                    )
                },
            }
        )
        print(
            f"  QA{qa}: actE={len(act_e)} contentM={len(act_m)} "
            f"whoM={len(who_m)} gold={len(gold_m)} "
            f"∩content={len(gold_m & act_m)} -> {fname}",
            flush=True,
        )

    n_a = sum(1 for c in cases if str(c["primary_reason"]).startswith("A_"))
    n_b = len(cases) - n_a
    (OUT_DIR / "index.html").write_text(
        INDEX_HTML.format(n_a=n_a, n_b=n_b, rows="\n".join(index_rows)),
        encoding="utf-8",
    )
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "n": len(cases),
                "n_absent_top100_zero_overlap": n_a,
                "n_rank_26_100_zero_overlap": n_b,
                "graph": str(GRAPH_PATH.relative_to(ROOT)),
                "miss_analysis": str(MISS_PATH.relative_to(ROOT)),
                "cases": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    notes = EXP_DIR / "snapshots" / "v07_miss_viz_zero_overlap"
    # keep a pointer in experiment dir (not bulky graph js)
    pointer = EXP_DIR / "miss_viz_zero_overlap.md"
    pointer.write_text(
        "\n".join(
            [
                "# Zero-overlap miss visualizations",
                "",
                f"- Cases: **{len(cases)}** "
                f"(absent@100+zero={n_a}, rank26–100+zero={n_b})",
                f"- Open: `outputs/em_graph_gpt/miss_viz_zero_overlap/index.html`",
                "- Colors: amber=activated entity, cyan=content-activated memory,",
                "  dark-teal=who-only-activated, red=gold, purple=gold∩content",
                "- Generated by `viz_miss_activation.py`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT_DIR / 'index.html'}", flush=True)
    print(f"wrote {pointer}", flush=True)


if __name__ == "__main__":
    main()
