#!/usr/bin/env python3
"""Build interactive fail-case report for extract-v4 recall_acc@25.

For each fail (ra@25 < 1):
  - re-retrieve top-25 (v4 graphs + embeddings + saved q_entity_keys)
  - write per-case HTML with collapsed retrieved list + interactive EM graph
  - nodes show no labels by default; gold / recalled highlighted
  - hover highlights the neighborhood and reveals short labels

Uses ``em_graph.recall.retrieval_audit`` (not the production ranking path).
Default fusion matches package default / v05 rescore: 0.30E+0.70S.
Outputs under outputs/em_graph/fail_viz_recall_acc25_extract_v4_e03s07/.
"""

from __future__ import annotations

import html
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from em_graph import (  # noqa: E402
    EMGraph,
    EntityBM25Index,
    MemoryEmbeddingIndex,
    retrieve_dialog_ids_with_audit,
)
from em_graph.build import normalize_entity_key  # noqa: E402

# Graphs / emb stay on extract_v4; scores come from the 0.30/0.70 rescore.
EXTRACT_TAG = "extract_v4"
SCORE_TAG = os.environ.get("EM_GRAPH_SCORE_TAG", "extract_v4_e03s07")
ENTITY_WEIGHT = float(os.environ.get("EM_GRAPH_ENTITY_WEIGHT", "0.30"))
SEMANTIC_WEIGHT = float(os.environ.get("EM_GRAPH_SEMANTIC_WEIGHT", "0.70"))
FAIL_JSON = EXP_DIR / f"fail_cases_recall_acc25_{SCORE_TAG}_detail.json"
DATA_PATH = ROOT / "data" / "locomo10.json"
OUT_DIR = ROOT / "outputs" / "em_graph" / f"fail_viz_recall_acc25_{SCORE_TAG}"
CAT = {
    "1": "single-hop",
    "2": "temporal",
    "3": "multi-hop",
    "4": "open-domain",
    "5": "adversarial",
}


def dump_fail_cases() -> Dict[str, Any]:
    """Build fail list (ra@25 < 1) from per-sample scored offline files."""
    data = {
        s["sample_id"]: s for s in json.loads(DATA_PATH.read_text(encoding="utf-8"))
    }
    cases: List[Dict[str, Any]] = []
    out_dir = ROOT / "outputs" / "em_graph"
    for sample_id, sample in data.items():
        result_path = (
            out_dir / f"{sample_id}_offline_locomo_recall_acc_{SCORE_TAG}.json"
        )
        if not result_path.exists():
            raise FileNotFoundError(f"missing {result_path}")
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        qa_list = sample.get("qa") or []
        dia_text: Dict[str, Dict[str, str]] = {}
        conv = sample.get("conversation") or {}
        for key, dialogs in conv.items():
            if not (str(key).startswith("session_") and isinstance(dialogs, list)):
                continue
            date = str(conv.get(f"{key}_date_time") or "")
            for d in dialogs:
                if not isinstance(d, dict):
                    continue
                dia = str(d.get("dia_id") or "")
                if dia:
                    dia_text[dia] = {
                        "speaker": str(d.get("speaker") or ""),
                        "date": date,
                        "text": str(d.get("text") or ""),
                    }
        for row in payload.get("rows") or []:
            ra = float(row.get("recall_acc25") or 0.0)
            if ra >= 1.0:
                continue
            qa_i = int(row["qa"])
            qa = qa_list[qa_i - 1] if 0 <= qa_i - 1 < len(qa_list) else {}
            evidence = [str(x) for x in (qa.get("evidence") or []) if str(x)]
            if not evidence:
                evidence = list(row.get("covered25") or [])
            covered = list(row.get("covered25") or [])
            missing = [e for e in evidence if e not in set(covered)]
            cat = str(row.get("category") or qa.get("category") or "")
            fr = row.get("first_gold_rank")
            tags = []
            if ra == 0.0:
                tags.append("full_miss")
            else:
                tags.append("partial")
            if fr is None:
                tags.append("absent_gt100")
            elif int(fr) <= 25:
                tags.append("gold_in_top25")
            elif int(fr) <= 50:
                tags.append("gold_rank_26_50")
            elif int(fr) <= 100:
                tags.append("gold_rank_51_100")
            cases.append(
                {
                    "sample_id": sample_id,
                    "qa": qa_i,
                    "category": cat,
                    "category_name": CAT.get(cat, "?"),
                    "question": str(qa.get("question") or ""),
                    "answer": str(qa.get("answer") or ""),
                    "n_evidence": int(row.get("n_evidence") or len(evidence)),
                    "evidence": evidence,
                    "covered25": covered,
                    "missing25": missing,
                    "recall_acc25": ra,
                    "hit25": bool(row.get("hit25")),
                    "first_gold_rank": fr,
                    "q_entity_keys": list(row.get("q_entity_keys") or []),
                    "gold_dialogs": [
                        {
                            "dia_id": dia,
                            "in_top25": dia in set(covered),
                            **dia_text.get(dia, {}),
                        }
                        for dia in evidence
                    ],
                    "tags": tags,
                }
            )
    payload = {
        "n": len(cases),
        "extract": EXTRACT_TAG,
        "score_tag": SCORE_TAG,
        "entity_weight": ENTITY_WEIGHT,
        "semantic_weight": SEMANTIC_WEIGHT,
        "mean_ra_of_fails": round(
            sum(float(c["recall_acc25"]) for c in cases) / len(cases), 4
        )
        if cases
        else 0.0,
        "cases": cases,
    }
    FAIL_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"wrote {FAIL_JSON} n_fails={len(cases)}", flush=True)
    return payload


def _esc(s: Any) -> str:
    return html.escape(str(s or ""))


def _short(text: str, n: int = 90) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _split_evidence(raw: List[str]) -> List[str]:
    out: List[str] = []
    for item in raw or []:
        for part in str(item).split(";"):
            part = part.strip()
            if part:
                out.append(part)
    return out


def gold_memory_ids(graph: EMGraph, evidence: List[str]) -> Tuple[Set[str], List[str]]:
    dia_to_mid = {m.dia_id: m.id for m in graph.memories.values()}
    mids: Set[str] = set()
    missing: List[str] = []
    for dia in _split_evidence(evidence):
        mid = dia_to_mid.get(dia)
        if mid:
            mids.add(mid)
        else:
            missing.append(dia)
    return mids, missing


def match_activated_entities(
    graph: EMGraph,
    q_entity_keys: List[str],
    entity_bm25_index: EntityBM25Index,
) -> Dict[str, Set[str]]:
    q_keys = {normalize_entity_key(k) for k in q_entity_keys if k}
    matched = entity_bm25_index.match_q_keys(q_keys)
    return {eid: set(scores) for eid, scores in matched.items()}


def build_shared_graph(graph: EMGraph, sample_id: str) -> Dict[str, Any]:
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
                "text": m.text_normalized or m.text,
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
        "sample_id": sample_id,
        "stats": dict(graph.stats or {}),
        "nodes": nodes,
        "edges": edges,
    }


CASE_HTML = """<!doctype html>
<html lang="zh"><head>
<meta charset="utf-8"/>
<title>{sample_id} QA{qa} · ra={ra}</title>
<style>
body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:#0b1220;color:#e2e8f0}}
header{{padding:10px 14px;border-bottom:1px solid #1e293b}}
header h1{{margin:0 0 6px;font-size:16px;font-weight:650}}
header p{{margin:2px 0;font-size:12px;color:#cbd5e1;line-height:1.4}}
.row{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}
.meta{{flex:1;min-width:300px}}
.legend{{font-size:12px;display:grid;grid-template-columns:auto auto;gap:4px 14px;min-width:240px}}
.dot{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:middle}}
.badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;margin-right:6px}}
.miss{{background:#7f1d1d;color:#fecaca}}
.part{{background:#78350f;color:#fde68a}}
details.panel{{margin-top:8px;background:#020617;border:1px solid #1e293b;border-radius:8px;padding:6px 10px}}
details.panel summary{{cursor:pointer;color:#93c5fd;font-size:12px;font-weight:600}}
details.panel .body{{margin-top:8px;font-size:12px;color:#cbd5e1}}
table.ret{{border-collapse:collapse;width:100%;font-size:12px}}
table.ret th,table.ret td{{border-bottom:1px solid #1e293b;padding:5px 6px;vertical-align:top;text-align:left}}
table.ret .y{{color:#4ade80;font-weight:700}}
table.ret .n{{color:#f87171}}
#mynetwork{{width:100vw;height:calc(100vh - 220px);min-height:420px;background:#020617}}
#status{{padding:6px 14px;font-size:11px;color:#94a3b8;border-top:1px solid #1e293b}}
a{{color:#38bdf8}}
code{{background:#1e293b;padding:1px 5px;border-radius:4px;font-size:11px}}
</style>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
</head><body>
<header>
  <div class="row">
    <div class="meta">
      <h1>{sample_id} QA{qa} · cat{category} {cat_name}
        <span class="badge {outcome_cls}">{outcome}</span>
        <span class="badge">ra@25={ra}</span>
      </h1>
      <p><b>Q:</b> {question}</p>
      <p><b>Gold A:</b> {answer}</p>
      <p><b>Evidence:</b> {evidence} · <b>first_gold_rank</b>={rank}</p>
      <p><b>Covered@25:</b> {covered} · <b>Missing@25:</b> {missing}</p>
      <p><b>q_entities:</b> {q_entities}</p>
      <p><b>tags:</b> {tags} · <a href="index.html">index</a></p>
      <details class="panel" open>
        <summary>Q entities extracted ({n_q_entities})</summary>
        <div class="body">{q_entities_table}</div>
      </details>
      <details class="panel" open>
        <summary>BM25 matched entities ({n_bm25_entities}) · gated={gated}</summary>
        <div class="body">{bm25_table}</div>
      </details>
      <details class="panel">
        <summary>Gold evidence dialogs ({n_gold_rows}) — click to expand</summary>
        <div class="body">{gold_table}</div>
      </details>
      <details class="panel" open>
        <summary>Retrieved top-25 ({n_retrieved}) · fusion={ew:.2f}*E+{sw:.2f}*S</summary>
        <div class="body">{retrieved_table}</div>
      </details>
    </div>
    <div class="legend">
      <span><i class="dot" style="background:#334155"></i>memory (idle)</span>
      <span><i class="dot" style="background:#1e293b"></i>entity (idle)</span>
      <span><i class="dot" style="background:#f59e0b"></i>matched entity</span>
      <span><i class="dot" style="background:#22d3ee"></i>recalled memory (top25)</span>
      <span><i class="dot" style="background:#ef4444"></i>gold memory</span>
      <span><i class="dot" style="background:#a855f7"></i>gold ∩ recalled</span>
      <span>labels hidden by default · hover = neighborhood</span>
    </div>
  </div>
</header>
<div id="mynetwork"></div>
<div id="status">Loading graph…</div>
<script src="{graph_js}"></script>
<script>
const CASE = {case_json};
const g = window.EM_GRAPH;
const actE = new Set(CASE.activated_entity_ids || []);
const recalledM = new Set(CASE.recalled_memory_ids || []);
const goldM = new Set(CASE.gold_memory_ids || []);

function nodeStyle(n) {{
  if (n.kind === 'memory') {{
    const isGold = goldM.has(n.id);
    const isRec = recalledM.has(n.id);
    if (isGold && isRec) return {{background:'#a855f7', border:'#faf5ff', borderWidth:3}};
    if (isGold) return {{background:'#ef4444', border:'#fecaca', borderWidth:3}};
    if (isRec) return {{background:'#0891b2', border:'#67e8f9', borderWidth:2}};
    return {{background:'#334155', border:'#475569', borderWidth:1}};
  }}
  if (actE.has(n.id)) {{
    const isWho = (n.etype || '').toLowerCase() === 'who';
    return {{
      background: isWho ? '#b45309' : '#d97706',
      border: '#fde68a',
      borderWidth: 3
    }};
  }}
  return {{background:'#1e293b', border:'#334155', borderWidth:1}};
}}

const baseNodeById = {{}};
const nodes = new vis.DataSet(g.nodes.map(n => {{
  const style = nodeStyle(n);
  const isMem = n.kind === 'memory';
  const hot = actE.has(n.id) || recalledM.has(n.id) || goldM.has(n.id);
  const item = {{
    id: n.id,
    label: '',  // no labels by default to avoid overlap
    title: n.title || n.label,
    shape: 'dot',
    size: isMem
      ? (goldM.has(n.id) ? 15 : (recalledM.has(n.id) ? 12 : 6))
      : (actE.has(n.id) ? 13 : 5),
    color: style,
    font: {{color:'#f8fafc', size:0, face:'system-ui', strokeWidth:0}},
    borderWidth: style.borderWidth,
    kind: n.kind,
  }};
  baseNodeById[n.id] = {{
    color: JSON.parse(JSON.stringify(style)),
    borderWidth: style.borderWidth,
    size: item.size,
    hot,
  }};
  return item;
}}));

const baseEdgeById = {{}};
const edges = new vis.DataSet(g.edges.map((e, i) => {{
  const hot = (actE.has(e.from) && (recalledM.has(e.to) || goldM.has(e.to)))
    || (goldM.has(e.to) && actE.has(e.from));
  const warm = actE.has(e.from) || recalledM.has(e.to) || goldM.has(e.to);
  const item = {{
    id: i,
    from: e.from,
    to: e.to,
    color: {{
      color: hot ? '#fbbf24' : (warm ? '#334155' : '#0f172a'),
      opacity: hot ? 0.9 : (warm ? 0.22 : 0.05),
    }},
    width: hot ? 2.0 : (warm ? 0.7 : 0.25),
    smooth: false,
  }};
  baseEdgeById[i] = {{
    color: JSON.parse(JSON.stringify(item.color)),
    width: item.width,
  }};
  return item;
}}));

const status = document.getElementById('status');
const network = new vis.Network(
  document.getElementById('mynetwork'),
  {{nodes, edges}},
  {{
    nodes: {{shape:'dot', scaling:{{min:4, max:18}}}},
    edges: {{selectionWidth:2, hoverWidth:1.5}},
    physics: {{
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {{
        gravitationalConstant: -45,
        centralGravity: 0.005,
        springLength: 120,
        springConstant: 0.06,
        damping: 0.5,
        avoidOverlap: 1,
      }},
      stabilization: {{enabled:true, iterations:260, updateInterval:25, fit:true}},
    }},
    interaction: {{
      hover:true, tooltipDelay:70, multiselect:true,
      navigationButtons:true, keyboard:true,
    }},
  }}
);

function restoreAll() {{
  nodes.update(Object.keys(baseNodeById).map(id => {{
    const b = baseNodeById[id];
    return {{
      id,
      color: b.color,
      borderWidth: b.borderWidth,
      size: b.size,
      label: '',
      font: {{color:'#f8fafc', size:0, face:'system-ui'}},
    }};
  }}));
  edges.update(Object.keys(baseEdgeById).map(id => {{
    const b = baseEdgeById[id];
    return {{id:Number(id), color:b.color, width:b.width}};
  }}));
}}

function highlightNeighborhood(nodeId) {{
  const connected = new Set(network.getConnectedNodes(nodeId));
  connected.add(nodeId);
  const connectedEdges = new Set(network.getConnectedEdges(nodeId));
  const nUp = [];
  for (const id of Object.keys(baseNodeById)) {{
    const b = baseNodeById[id];
    const on = connected.has(id);
    const src = g.nodes.find(x => x.id === id);
    nUp.push({{
      id,
      color: {{
        background: b.color.background,
        border: on ? '#f8fafc' : b.color.border,
        opacity: on ? 1 : 0.07,
      }},
      borderWidth: on ? Math.max(b.borderWidth, 2) : b.borderWidth,
      size: on ? b.size * (id === nodeId ? 1.4 : 1.15) : b.size,
      label: on && src ? src.label : '',
      font: {{
        color: on ? '#f8fafc' : '#1e293b',
        size: on ? 11 : 0,
        face: 'system-ui',
      }},
    }});
  }}
  const eUp = [];
  for (const id of Object.keys(baseEdgeById)) {{
    const eid = Number(id);
    const b = baseEdgeById[id];
    const on = connectedEdges.has(eid);
    eUp.push({{
      id: eid,
      color: {{color: on ? '#38bdf8' : b.color.color, opacity: on ? 0.95 : 0.03}},
      width: on ? Math.max(2.2, b.width * 2) : Math.max(0.2, b.width * 0.35),
    }});
  }}
  nodes.update(nUp);
  edges.update(eUp);
}}

network.on('hoverNode', params => {{
  highlightNeighborhood(params.node);
  const n = g.nodes.find(x => x.id === params.node);
  status.textContent = n
    ? `hover ${{n.kind}} ${{n.label}} · neighbors=${{network.getConnectedNodes(params.node).length}} · ${{(n.title || '').slice(0, 140)}}`
    : 'hover';
}});
network.on('blurNode', () => {{
  restoreAll();
  status.textContent =
    `nodes=${{g.nodes.length}} edges=${{g.edges.length}} · ` +
    `matchedE=${{actE.size}} recalledM=${{recalledM.size}} goldM=${{goldM.size}} · ` +
    `labels hidden · hover a node to highlight neighbors`;
}});

network.once('stabilizationIterationsDone', () => {{
  network.setOptions({{physics: {{enabled: false}}}});
  const focus = [...goldM, ...recalledM];
  if (focus.length) network.fit({{nodes: focus, animation: true}});
  else network.fit({{animation: true}});
  status.textContent =
    `nodes=${{g.nodes.length}} edges=${{g.edges.length}} · ` +
    `matchedE=${{actE.size}} recalledM=${{recalledM.size}} goldM=${{goldM.size}} · ` +
    `physics off · labels hidden · hover a node to highlight neighbors`;
}});
</script>
</body></html>
"""


def _gold_table(gold_dialogs: List[Dict[str, Any]]) -> str:
    rows = [
        "<table class='ret'><tr><th>@25</th><th>dia</th><th>speaker</th><th>text</th></tr>"
    ]
    for g in gold_dialogs:
        mark = "<span class='y'>Y</span>" if g.get("in_top25") else "<span class='n'>N</span>"
        rows.append(
            "<tr>"
            f"<td>{mark}</td>"
            f"<td><code>{_esc(g.get('dia_id'))}</code></td>"
            f"<td>{_esc(g.get('speaker'))}</td>"
            f"<td>{_esc(g.get('text'))}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "".join(rows)


def _q_entities_table(q_keys: List[str]) -> str:
    if not q_keys:
        return "<p>(none extracted)</p>"
    rows = ["<table class='ret'><tr><th>#</th><th>q_entity_key</th></tr>"]
    for i, key in enumerate(q_keys, 1):
        rows.append(f"<tr><td>{i}</td><td><code>{_esc(key)}</code></td></tr>")
    rows.append("</table>")
    return "".join(rows)


def _bm25_table(entities: List[Dict[str, Any]]) -> str:
    if not entities:
        return "<p>(no BM25 entity matches ≥ threshold)</p>"
    rows = [
        "<table class='ret'><tr>"
        "<th>#</th><th>entity</th><th>type</th><th>key</th>"
        "<th>best_match</th><th>match_strength</th><th>raw(E)</th>"
        "<th>matched q_keys → scores</th>"
        "</tr>"
    ]
    for i, ent in enumerate(entities, 1):
        scores = ent.get("match_scores") or {}
        score_txt = ", ".join(
            f"{_esc(qk)}={float(sc):.3f}" for qk, sc in sorted(scores.items())
        )
        rows.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{_esc(ent.get('value'))}</td>"
            f"<td>{_esc(ent.get('type'))}</td>"
            f"<td><code>{_esc(ent.get('key'))}</code></td>"
            f"<td>{float(ent.get('best_match_score') or 0):.3f}</td>"
            f"<td>{float(ent.get('match_strength') or 0):.3f}</td>"
            f"<td>{float(ent.get('entity_raw_score') or 0):.3f}</td>"
            f"<td>{score_txt or '(none)'}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "".join(rows)


def _retrieved_table(retrieved: List[Dict[str, Any]], gold_set: Set[str]) -> str:
    rows = [
        "<table class='ret'><tr>"
        "<th>rank</th><th>gold?</th><th>dia</th>"
        "<th>fusion</th><th>entity(E)</th><th>embed(S)</th>"
        "<th>seed_E</th><th>seq?</th>"
        "<th>speaker</th><th>text</th></tr>"
    ]
    for item in retrieved:
        dia = str(item.get("dia_id") or "")
        is_gold = bool(item.get("is_gold")) or dia in gold_set
        mark = "<span class='y'>GOLD</span>" if is_gold else "<span class='n'>—</span>"
        fusion = float(
            item.get("fusion_score", item.get("score", 0.0)) or 0.0
        )
        ent_s = float(item.get("entity_score") or 0.0)
        emb_s = float(item.get("embedding_score") or 0.0)
        seed_s = float(item.get("seed_entity_score") or 0.0)
        seq = "Y" if item.get("via_sequence_only") else ""
        rows.append(
            "<tr>"
            f"<td>{int(item.get('rank') or 0)}</td>"
            f"<td>{mark}</td>"
            f"<td><code>{_esc(dia)}</code></td>"
            f"<td>{fusion:.4f}</td>"
            f"<td>{ent_s:.4f}</td>"
            f"<td>{emb_s:.4f}</td>"
            f"<td>{seed_s:.4f}</td>"
            f"<td>{seq}</td>"
            f"<td>{_esc(item.get('speaker'))}</td>"
            f"<td>{_esc(item.get('text'))}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "".join(rows)

def main() -> None:
    fail_payload = dump_fail_cases()
    cases: List[Dict[str, Any]] = list(fail_payload.get("cases") or [])
    data = {s["sample_id"]: s for s in json.loads(DATA_PATH.read_text(encoding="utf-8"))}

    wanted = os.environ.get("EM_GRAPH_SAMPLE_IDS", "").strip()
    if wanted:
        keep = {x.strip() for x in wanted.split(",") if x.strip()}
        cases = [c for c in cases if c["sample_id"] in keep]

    by_sample: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in cases:
        by_sample[c["sample_id"]].append(c)

    emb_model = os.environ.get("EM_GRAPH_EMBED_MODEL", "doubao-embedding-vision")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index_rows: List[str] = []
    enriched_all: List[Dict[str, Any]] = []

    for sample_id in sorted(by_sample):
        graph_path = (
            ROOT
            / "outputs"
            / "em_graph"
            / f"{sample_id}_em_graph_{EXTRACT_TAG}.json"
        )
        emb_cache_v4 = (
            ROOT
            / "outputs"
            / "em_graph"
            / f"{sample_id}_memory_emb_{EXTRACT_TAG}_{emb_model.replace('/', '_')}.npz"
        )
        emb_cache_v3 = (
            ROOT
            / "outputs"
            / "em_graph"
            / f"{sample_id}_memory_emb_extract_v3_{emb_model.replace('/', '_')}.npz"
        )
        emb_cache = emb_cache_v4 if emb_cache_v4.exists() else emb_cache_v3
        if not graph_path.exists() or not emb_cache.exists():
            raise FileNotFoundError(f"missing graph/emb for {sample_id}")

        print(f"[{sample_id}] load graph/emb · fails={len(by_sample[sample_id])}", flush=True)
        graph = EMGraph.load_from_file(str(graph_path))
        emb_index = MemoryEmbeddingIndex.build(
            graph, model_name=emb_model, cache_path=str(emb_cache)
        )
        entity_bm25 = EntityBM25Index.build(graph)
        shared = build_shared_graph(graph, sample_id)
        graph_js_name = f"graph_data_{sample_id}.js"
        (OUT_DIR / graph_js_name).write_text(
            "window.EM_GRAPH = " + json.dumps(shared, ensure_ascii=False) + ";\n",
            encoding="utf-8",
        )

        dia_to_mem = {m.dia_id: m for m in graph.memories.values()}
        sample = data[sample_id]
        qa_list = sample.get("qa") or []

        for case in sorted(by_sample[sample_id], key=lambda x: int(x["qa"])):
            qa_i = int(case["qa"])
            qa = qa_list[qa_i - 1] if 0 <= qa_i - 1 < len(qa_list) else {}
            question = str(qa.get("question") or case.get("question") or "")
            q_keys = list(case.get("q_entity_keys") or [])
            _ranked, audit = retrieve_dialog_ids_with_audit(
                graph,
                question,
                top_k=25,
                embedding_index=emb_index,
                entity_bm25_index=entity_bm25,
                q_entity_keys=set(q_keys),
                entity_weight=ENTITY_WEIGHT,
                semantic_weight=SEMANTIC_WEIGHT,
            )
            # Prefer live extracted keys from audit when present.
            q_keys = list(audit.get("q_entity_keys") or q_keys)
            bm25_entities = list(audit.get("bm25_matched_entities") or [])
            gold_dias = _split_evidence(
                case.get("evidence") or [str(x) for x in (qa.get("evidence") or [])]
            )
            gold_set = set(gold_dias)
            retrieved_rows: List[Dict[str, Any]] = []
            recalled_mids: Set[str] = set()
            for row in list(audit.get("ranked") or []):
                dia_id = str(row.get("dia_id") or "")
                mem = dia_to_mem.get(dia_id)
                mid = str(row.get("memory_id") or (mem.id if mem else ""))
                if mid:
                    recalled_mids.add(mid)
                retrieved_rows.append(
                    {
                        "rank": int(row.get("rank") or 0),
                        "dia_id": dia_id,
                        "memory_id": mid,
                        "score": float(row.get("fusion_score") or 0.0),
                        "fusion_score": float(row.get("fusion_score") or 0.0),
                        "entity_score": float(row.get("entity_score") or 0.0),
                        "seed_entity_score": float(
                            row.get("seed_entity_score") or 0.0
                        ),
                        "embedding_score": float(row.get("embedding_score") or 0.0),
                        "via_sequence_only": bool(row.get("via_sequence_only")),
                        "is_gold": dia_id in gold_set,
                        "speaker": str(
                            row.get("speaker")
                            or (mem.speaker if mem else "")
                        ),
                        "text": str(
                            row.get("text")
                            or (
                                (mem.text_normalized or mem.text)
                                if mem
                                else ""
                            )
                        ),
                    }
                )

            gold_mids, missing_dias = gold_memory_ids(graph, gold_dias)
            act_eids = {
                str(ent.get("entity_id"))
                for ent in bm25_entities
                if ent.get("entity_id")
            }
            covered = [d for d in gold_dias if d in {r["dia_id"] for r in retrieved_rows}]
            missing = [d for d in gold_dias if d not in set(covered)]
            # refresh gold_dialogs in_top25 from live retrieval
            gold_dialogs = []
            for d in gold_dias:
                mem = dia_to_mem.get(d)
                gold_dialogs.append(
                    {
                        "dia_id": d,
                        "in_top25": d in set(covered),
                        "speaker": mem.speaker if mem else "",
                        "text": (mem.text_normalized or mem.text) if mem else "",
                    }
                )

            ra = float(case.get("recall_acc25") or 0.0)
            outcome = "FULL_MISS" if ra == 0 else f"PARTIAL {len(covered)}/{len(gold_dias)}"
            outcome_cls = "miss" if ra == 0 else "part"
            fr = case.get("first_gold_rank")
            fr_s = "absent>100" if fr is None else str(fr)

            case_payload = {
                "sample_id": sample_id,
                "qa": qa_i,
                "category": str(case.get("category")),
                "q_entity_keys": q_keys,
                "bm25_matched_entities": bm25_entities,
                "activated_entity_ids": sorted(act_eids),
                "recalled_memory_ids": sorted(recalled_mids),
                "gold_memory_ids": sorted(gold_mids),
                "missing_evidence_dias": missing_dias,
                "entity_weight": ENTITY_WEIGHT,
                "semantic_weight": SEMANTIC_WEIGHT,
                "gated": bool(audit.get("gated")),
                "retrieved": retrieved_rows,
            }

            page = CASE_HTML.format(
                sample_id=_esc(sample_id),
                qa=qa_i,
                category=_esc(case.get("category")),
                cat_name=_esc(CAT.get(str(case.get("category")), "?")),
                outcome=_esc(outcome),
                outcome_cls=outcome_cls,
                ra=f"{ra:.3f}",
                question=_esc(question),
                answer=_esc(case.get("answer") or qa.get("answer")),
                evidence=_esc(", ".join(gold_dias)),
                rank=_esc(fr_s),
                covered=_esc(", ".join(covered) or "(none)"),
                missing=_esc(", ".join(missing) or "(none)"),
                q_entities=_esc(", ".join(q_keys) or "(none)"),
                tags=_esc(", ".join(case.get("tags") or [])),
                n_q_entities=len(q_keys),
                n_bm25_entities=len(bm25_entities),
                gated=_esc(str(bool(audit.get("gated")))),
                q_entities_table=_q_entities_table(q_keys),
                bm25_table=_bm25_table(bm25_entities),
                n_gold_rows=len(gold_dialogs),
                n_retrieved=len(retrieved_rows),
                ew=ENTITY_WEIGHT,
                sw=SEMANTIC_WEIGHT,
                gold_table=_gold_table(gold_dialogs),
                retrieved_table=_retrieved_table(retrieved_rows, gold_set),
                graph_js=graph_js_name,
                case_json=json.dumps(case_payload, ensure_ascii=False),
            )
            fname = f"{sample_id}_qa{qa_i:03d}.html"
            (OUT_DIR / fname).write_text(page, encoding="utf-8")

            enriched = {
                **case,
                "evidence": gold_dias,
                "covered25": covered,
                "missing25": missing,
                "gold_dialogs": gold_dialogs,
                "q_entity_keys": q_keys,
                "bm25_matched_entities": bm25_entities,
                "retrieval_audit": {
                    "gated": bool(audit.get("gated")),
                    "candidate_memory_count": int(
                        audit.get("candidate_memory_count") or 0
                    ),
                    "entity_weight": ENTITY_WEIGHT,
                    "semantic_weight": SEMANTIC_WEIGHT,
                },
                "retrieved_top25": retrieved_rows,
                "viz_html": f"outputs/em_graph/fail_viz_recall_acc25/{fname}",
            }
            enriched_all.append(enriched)

            index_rows.append(
                "<tr>"
                f"<td><a href='{fname}'>{_esc(sample_id)} QA{qa_i}</a></td>"
                f"<td>{_esc(case.get('category'))}-{_esc(CAT.get(str(case.get('category')), '?'))}</td>"
                f"<td><span class='badge {outcome_cls}'>{_esc(outcome)}</span></td>"
                f"<td>{ra:.3f}</td>"
                f"<td>{_esc(fr_s)}</td>"
                f"<td>{len(recalled_mids)}</td>"
                f"<td>{len(gold_mids)}</td>"
                f"<td>{_esc(question)}</td>"
                "</tr>"
            )
            print(
                f"  [{sample_id}] QA{qa_i} ra={ra:.3f} recalled={len(retrieved_rows)} "
                f"gold_in_top25={len(covered)}/{len(gold_dias)}",
                flush=True,
            )

    index_html = f"""<!doctype html>
<html lang="zh"><head>
<meta charset="utf-8"/>
<title>Fail viz · recall_acc@25</title>
<style>
body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:24px;background:#0b1220;color:#e2e8f0}}
h1{{font-size:20px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #1e293b;padding:8px 10px;text-align:left;vertical-align:top}}
th{{color:#94a3b8;font-weight:600}}
a{{color:#38bdf8;text-decoration:none}}
.badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px}}
.miss{{background:#7f1d1d;color:#fecaca}}
.part{{background:#78350f;color:#fde68a}}
</style></head><body>
<h1>Official recall_acc@25 fail cases — interactive viz</h1>
<p>n={len(enriched_all)}. Per-case page: collapsed retrieved top-25 + EM graph
(no node labels by default; cyan=recalled, red=gold, purple=both; hover highlights neighbors).</p>
<table>
<thead><tr>
<th>case</th><th>cat</th><th>outcome</th><th>ra@25</th><th>rank</th>
<th>recalled</th><th>gold</th><th>question</th>
</tr></thead>
<tbody>
{''.join(index_rows)}
</tbody></table>
</body></html>
"""
    (OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

    enriched_path = EXP_DIR / f"fail_cases_recall_acc25_{SCORE_TAG}_with_retrieved.json"
    enriched_path.write_text(
        json.dumps(
            {
                "n": len(enriched_all),
                "extract": EXTRACT_TAG,
                "score_tag": SCORE_TAG,
                "entity_weight": ENTITY_WEIGHT,
                "semantic_weight": SEMANTIC_WEIGHT,
                "cases": enriched_all,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Rewrite report HTML with collapsed retrieved + viz links
    report_parts = [
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'/>",
        f"<title>fail cases recall_acc@25 {SCORE_TAG} "
        f"(E{ENTITY_WEIGHT:.2f}/S{SEMANTIC_WEIGHT:.2f})</title>",
        "<style>",
        "body{font:14px/1.45 ui-sans-serif,system-ui,sans-serif;margin:0;background:#f6f7f9;color:#111}",
        "header{position:sticky;top:0;background:#111;color:#fff;padding:12px 16px;z-index:2}",
        "header a{color:#9cf;margin-right:12px}",
        ".wrap{max-width:1100px;margin:0 auto;padding:16px}",
        ".case{background:#fff;border:1px solid #e2e2e2;border-radius:10px;padding:14px 16px;margin:12px 0}",
        ".badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#eee;margin-right:6px;font-size:12px}",
        ".badge.miss{background:#ffe1e1}.badge.part{background:#fff3cd}",
        "details{margin-top:8px;border:1px solid #eee;border-radius:8px;padding:6px 10px;background:#fafafa}",
        "details summary{cursor:pointer;color:#2563eb;font-weight:600}",
        "table{border-collapse:collapse;width:100%;margin-top:8px;font-size:13px}",
        "td,th{border:1px solid #ddd;padding:6px 8px;vertical-align:top} th{background:#fafafa;text-align:left}",
        ".y{color:#0a0;font-weight:700}.n{color:#a00;font-weight:700}",
        "</style></head><body>",
        f"<header><div><b>extract-v4 fail cases @ "
        f"{ENTITY_WEIGHT:.2f}E+{SEMANTIC_WEIGHT:.2f}S</b> — n={len(enriched_all)}</div>",
        "<div style='margin-top:6px;font-size:13px'>",
        f"<a href='../../outputs/em_graph/fail_viz_recall_acc25_{SCORE_TAG}/index.html'>"
        "Interactive graph index</a>",
        "</div></header><div class='wrap'>",
        "<p>Each case includes: extracted q entities, BM25-matched entities, "
        "retrieved top-25 with entity/embedding/fusion scores, and a graph link. "
        f"Graph pages: <code>outputs/em_graph/fail_viz_recall_acc25_{SCORE_TAG}/</code>.</p>",
    ]

    for c in enriched_all:
        ra = float(c["recall_acc25"])
        outcome = "FULL_MISS" if ra == 0 else f"PARTIAL {len(c['covered25'])}/{c['n_evidence']}"
        ocls = "miss" if ra == 0 else "part"
        fr = c.get("first_gold_rank")
        fr_s = "absent>100" if fr is None else str(fr)
        viz = c.get("viz_html") or ""
        # link relative from experiment dir
        viz_rel = "../../" + viz if not viz.startswith("..") else viz
        q_keys = list(c.get("q_entity_keys") or [])
        bm25_ents = list(c.get("bm25_matched_entities") or [])
        audit = c.get("retrieval_audit") or {}
        report_parts.append("<div class='case'>")
        report_parts.append(
            f"<h3>{_esc(c['sample_id'])} QA#{c['qa']} · cat{_esc(c['category'])} "
            f"{_esc(c.get('category_name'))} "
            f"<span class='badge {ocls}'>{_esc(outcome)}</span> "
            f"<span class='badge'>ra={ra:.3f}</span> "
            f"<span class='badge'>rank={_esc(fr_s)}</span></h3>"
        )
        report_parts.append(
            f"<p><a href='{_esc(viz_rel)}'>Open interactive graph</a></p>"
        )
        report_parts.append(f"<p><b>Q:</b> {_esc(c.get('question'))}</p>")
        report_parts.append(f"<p><b>A:</b> {_esc(c.get('answer'))}</p>")
        report_parts.append(
            f"<p><b>evidence:</b> {_esc(', '.join(c.get('evidence') or []))}<br/>"
            f"<b>covered@25:</b> {_esc(', '.join(c.get('covered25') or []) or '(none)')}<br/>"
            f"<b>missing@25:</b> {_esc(', '.join(c.get('missing25') or []) or '(none)')}</p>"
        )
        report_parts.append(
            f"<details open><summary>Q entities extracted ({len(q_keys)})</summary>"
        )
        report_parts.append(_q_entities_table(q_keys))
        report_parts.append("</details>")
        report_parts.append(
            f"<details open><summary>BM25 matched entities ({len(bm25_ents)}) · "
            f"gated={_esc(str(bool(audit.get('gated'))))}</summary>"
        )
        report_parts.append(_bm25_table(bm25_ents))
        report_parts.append("</details>")
        report_parts.append(
            f"<details><summary>Gold evidence dialogs "
            f"({len(c.get('gold_dialogs') or [])})</summary>"
        )
        report_parts.append(_gold_table(c.get("gold_dialogs") or []))
        report_parts.append("</details>")
        report_parts.append(
            f"<details open><summary>Retrieved top-25 "
            f"({len(c.get('retrieved_top25') or [])}) · "
            f"fusion={ENTITY_WEIGHT:.2f}*E+{SEMANTIC_WEIGHT:.2f}*S</summary>"
        )
        report_parts.append(
            _retrieved_table(
                c.get("retrieved_top25") or [], set(c.get("evidence") or [])
            )
        )
        report_parts.append("</details></div>")
    report_parts.append("</div></body></html>")
    report_path = EXP_DIR / f"fail_cases_recall_acc25_{SCORE_TAG}_detail.html"
    report_path.write_text("".join(report_parts), encoding="utf-8")

    print("wrote", OUT_DIR / "index.html")
    print("wrote", enriched_path)
    print("wrote", report_path)
    print(
        f"cases={len(enriched_all)} extract={EXTRACT_TAG} "
        f"score={SCORE_TAG} fusion={ENTITY_WEIGHT}/{SEMANTIC_WEIGHT}"
    )


if __name__ == "__main__":
    main()
