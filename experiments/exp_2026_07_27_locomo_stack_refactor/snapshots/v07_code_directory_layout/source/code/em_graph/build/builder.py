"""Layer-1 EM heterogeneous graph builder.

Mentions: Entity ↔ Memory. Sequence: Memory ↔ Memory in chronological order.
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from em_graph.build.config import EMGraphConfig
from em_graph.build.entity_keys import normalize_entity_key
from em_graph.build.entity_extractor import EntityExtractor, ExtractedEntity
from em_graph.build.models import (
    EMEdge,
    EMGraph,
    EdgeType,
    EntityNode,
    MemoryEdge,
    MemoryNode,
)
from em_graph.build.replace_pronouns import (
    DIALOG_NORMALIZATION_VERSION,
    normalize_dialog_text,
)
_DIA_RE = re.compile(r"^D(\d+):(\d+)$", re.I)
_LOCOMO_DATETIME_FORMAT = "%I:%M %p on %d %B, %Y"


def _memory_id(dia_id: str) -> str:
    return f"memory:{dia_id}"


def _entity_id(key: str) -> str:
    return f"entity:{key}"


def _edge_id(entity_id: str, memory_id: str) -> str:
    return f"edge:{entity_id}->{memory_id}"


def _memory_edge_id(src_id: str, dst_id: str, edge_type: EdgeType) -> str:
    return f"medge:{edge_type.value}:{src_id}->{dst_id}"


def _parse_memory_datetime(value: str) -> Optional[datetime]:
    """Parse supported conversation timestamps into a comparable datetime."""
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None

    try:
        return datetime.strptime(text, _LOCOMO_DATETIME_FORMAT)
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def memory_sort_key(memory: MemoryNode) -> Tuple[int, datetime, int, int, str]:
    """Order by real session datetime, then conversation turn order.

    LoCoMo timestamps are session-level, so turns sharing the same timestamp
    retain their ``D{session}:{turn}`` order. Missing or malformed timestamps
    sort after parsed timestamps and fall back to session/turn order.
    """
    match = _DIA_RE.match(str(memory.dia_id or "").strip())
    if match:
        session_num = int(match.group(1))
        turn_num = int(match.group(2))
    else:
        session_num = int(memory.session_num)
        turn_num = 0

    parsed = _parse_memory_datetime(memory.date_time)
    if parsed is None:
        return (1, datetime.max, session_num, turn_num, memory.dia_id)
    return (0, parsed, session_num, turn_num, memory.dia_id)


def ensure_memory_sequence_edges(graph: EMGraph) -> int:
    """Link chronological Memories with bidirectional NEXT/PREV edges.

    Idempotent: clears existing sequence edges and rebuilds from parsed session
    datetime, with session/turn order as the deterministic tie-break/fallback.
    Returns the number of directed MemoryEdges written (2 per adjacent pair).
    """
    ordered = sorted(graph.memories.values(), key=memory_sort_key)
    graph.memory_edges = []
    if len(ordered) < 2:
        return 0

    for left, right in zip(ordered, ordered[1:]):
        graph.add_memory_edge(
            MemoryEdge(
                id=_memory_edge_id(left.id, right.id, EdgeType.NEXT),
                src_memory_id=left.id,
                dst_memory_id=right.id,
                edge_type=EdgeType.NEXT,
                weight=1.0,
                metadata={
                    "src_dia_id": left.dia_id,
                    "dst_dia_id": right.dia_id,
                },
            )
        )
        graph.add_memory_edge(
            MemoryEdge(
                id=_memory_edge_id(right.id, left.id, EdgeType.PREV),
                src_memory_id=right.id,
                dst_memory_id=left.id,
                edge_type=EdgeType.PREV,
                weight=1.0,
                metadata={
                    "src_dia_id": right.dia_id,
                    "dst_dia_id": left.dia_id,
                },
            )
        )
    return len(graph.memory_edges)


def _iter_sessions(
    conversation: Dict[str, Any],
    session_num: Optional[int] = None,
) -> List[Tuple[int, str, List[Dict[str, Any]]]]:
    session_keys = [
        key
        for key in conversation.keys()
        if str(key).startswith("session_") and not str(key).endswith("_date_time")
    ]
    sessions: List[Tuple[int, str, List[Dict[str, Any]]]] = []
    for key in session_keys:
        try:
            num = int(str(key).split("_")[1])
        except (IndexError, ValueError):
            continue
        if session_num is not None and num != session_num:
            continue
        dialogs = conversation.get(key) or []
        if not isinstance(dialogs, list):
            continue
        date_time = str(conversation.get(f"{key}_date_time", "") or "")
        sessions.append((num, date_time, dialogs))
    sessions.sort(key=lambda item: item[0])
    return sessions


def _dialog_extraction_text(dialog: Dict[str, Any], normalized_text: str) -> str:
    parts: List[str] = []
    if normalized_text:
        parts.append(normalized_text)
    caption = str(dialog.get("blip_caption") or "").strip()
    if caption:
        parts.append(f"[Image: {caption}]")
    return " ".join(parts).strip()


def _attach_entities_to_memory(
    graph: EMGraph,
    memory: MemoryNode,
    entities: List[ExtractedEntity],
    *,
    add_speaker_as_entity: bool,
    edge_keys: set,
) -> None:
    entity_values: List[Tuple[str, str, str]] = []
    for entity in entities:
        value = entity.value.strip()
        if not value:
            continue
        key = normalize_entity_key(value)
        if key:
            entity_values.append((key, value, entity.type))

    if add_speaker_as_entity and memory.speaker:
        speaker_key = normalize_entity_key(memory.speaker)
        if speaker_key and speaker_key not in {k for k, _, _ in entity_values}:
            entity_values.append((speaker_key, memory.speaker, "Who"))

    for key, value, entity_type in entity_values:
        eid = _entity_id(key)
        if eid not in graph.entities:
            graph.add_entity(
                EntityNode(
                    id=eid,
                    key=key,
                    value=value,
                    type=entity_type,
                    merged_from=[value],
                )
            )
        else:
            node = graph.entities[eid]
            if value not in node.merged_from:
                node.merged_from.append(value)
            if len(value) > len(node.value):
                node.value = value
            if not node.type and entity_type:
                node.type = entity_type

        edge_key = (eid, memory.id)
        if edge_key in edge_keys:
            continue
        edge_keys.add(edge_key)
        graph.add_edge(
            EMEdge(
                id=_edge_id(eid, memory.id),
                entity_id=eid,
                memory_id=memory.id,
                edge_type=EdgeType.MENTIONS,
                weight=1.0,
                metadata={"dia_id": memory.dia_id},
            )
        )


def build_em_graph(
    sample: Dict[str, Any],
    *,
    config: Optional[EMGraphConfig] = None,
    extractor: Optional[EntityExtractor] = None,
    session_num: Optional[int] = None,
    time_words: Optional[Sequence[str]] = None,
    checkpoint_path: Optional[str] = None,
    checkpoint_every: int = 40,
    max_workers: Optional[int] = None,
) -> EMGraph:
    """
    Build an Entity–Memory graph from one conversation sample.

    Pipeline:
      1. Sequentially create Memory nodes with evidence-preserving normalization.
      2. Parallel LLM entity extract on normalized texts.
      3. Attach Entity nodes and Entity→Memory Mentions edges.
      4. Link chronological Memories with bidirectional NEXT/PREV edges.
    """
    cfg = config or EMGraphConfig()
    extractor = extractor or EntityExtractor(model=cfg.model, use_cache=cfg.use_cache)
    workers = int(
        max_workers
        if max_workers is not None
        else os.environ.get("EM_GRAPH_MAX_WORKERS", "8")
    )
    workers = max(workers, 1)

    sample_id = str(sample.get("sample_id") or "")
    conversation = sample.get("conversation") or {}
    if not isinstance(conversation, dict):
        raise ValueError("sample.conversation must be a dict")

    graph = EMGraph(sample_id=sample_id)
    if checkpoint_path and os.path.exists(checkpoint_path):
        graph = EMGraph.load_from_file(checkpoint_path)
        print(
            f"Resuming from checkpoint {checkpoint_path} "
            f"(memories={len(graph.memories)}, entities={len(graph.entities)})",
            flush=True,
        )

    # Memories that already have at least one edge are treated as fully processed.
    linked_memory_ids = {e.memory_id for e in graph.edges}
    edge_keys = {(e.entity_id, e.memory_id) for e in graph.edges}

    pending: List[Tuple[str, str]] = []  # (memory_id, extract_text)
    for sess_num, date_time, dialogs in _iter_sessions(conversation, session_num):
        for dialog in dialogs:
            if not isinstance(dialog, dict):
                continue
            dia_id = str(dialog.get("dia_id") or "").strip()
            if not dia_id:
                continue
            speaker = str(dialog.get("speaker") or "").strip()
            mid = _memory_id(dia_id)

            if mid not in graph.memories:
                text = str(dialog.get("text") or "")
                normalized = normalize_dialog_text(
                    text,
                    dialog_time=date_time,
                    time_words=time_words,
                    auto_time_words=cfg.auto_time_words,
                )
                graph.add_memory(
                    MemoryNode(
                        id=mid,
                        dia_id=dia_id,
                        session_num=sess_num,
                        date_time=date_time,
                        speaker=speaker,
                        text=text,
                        text_normalized=normalized,
                        blip_caption=str(
                            dialog.get("blip_caption") or ""
                        ),
                    )
                )
            memory = graph.memories[mid]

            if mid in linked_memory_ids:
                continue
            extract_text = _dialog_extraction_text(dialog, memory.text_normalized)
            if extract_text:
                pending.append((mid, extract_text))
            else:
                linked_memory_ids.add(mid)

    print(
        f"Memory nodes ready: {len(graph.memories)}; "
        f"pending entity extracts: {len(pending)}; workers={workers}",
        flush=True,
    )

    done_extracts = 0

    def _extract_one(item: Tuple[str, str]) -> Tuple[str, List[ExtractedEntity]]:
        mid, text = item
        try:
            return mid, extractor.extract(text)
        except Exception as exc:  # noqa: BLE001 — keep sample build alive
            print(f"  extract failed for {mid}: {exc}", flush=True)
            return mid, []

    def _flush_checkpoint(partial: bool = True) -> None:
        if not checkpoint_path:
            return
        graph.stats = {
            "memory_count": len(graph.memories),
            "entity_count": len(graph.entities),
            "edge_count": len(graph.edges),
            "memory_edge_count": len(graph.memory_edges),
            "memory_sequence": (
                "bidirectional NEXT/PREV by parsed date_time; "
                "session/turn tie-break"
            ),
            "dialog_normalization_version": DIALOG_NORMALIZATION_VERSION,
            "mentions_bipartite": True,
            "partial": partial,
        }
        graph.save_to_file(checkpoint_path)
        cache = getattr(extractor, "cache", None)
        if cache is not None and hasattr(cache, "flush"):
            cache.flush()
        print(f"  checkpoint saved -> {checkpoint_path}", flush=True)

    if pending:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_extract_one, item) for item in pending]
            for future in as_completed(futures):
                mid, entities = future.result()
                memory = graph.memories[mid]
                _attach_entities_to_memory(
                    graph,
                    memory,
                    entities,
                    add_speaker_as_entity=cfg.add_speaker_as_entity,
                    edge_keys=edge_keys,
                )
                linked_memory_ids.add(mid)
                done_extracts += 1
                if done_extracts % 10 == 0 or done_extracts == len(pending):
                    print(
                        f"  extracted {done_extracts}/{len(pending)} "
                        f"(entities={len(graph.entities)}, edges={len(graph.edges)})",
                        flush=True,
                    )
                if (
                    checkpoint_every > 0
                    and done_extracts % checkpoint_every == 0
                ):
                    _flush_checkpoint(partial=True)

    cache = getattr(extractor, "cache", None)
    if cache is not None and hasattr(cache, "flush"):
        cache.flush()

    seq_n = ensure_memory_sequence_edges(graph)
    graph.stats = {
        "memory_count": len(graph.memories),
        "entity_count": len(graph.entities),
        "edge_count": len(graph.edges),
        "memory_edge_count": seq_n,
        "mentions_bipartite": True,
        "allowed_mentions_endpoints": ["entity", "memory"],
        "memory_sequence": (
            "bidirectional NEXT/PREV by parsed date_time; "
            "session/turn tie-break"
        ),
        "dialog_normalization_version": DIALOG_NORMALIZATION_VERSION,
    }
    if checkpoint_path:
        _flush_checkpoint(partial=False)
    return graph


def build_memory_graph(
    sample: Dict[str, Any],
    *,
    session_num: Optional[int] = None,
    time_words: Optional[Sequence[str]] = None,
    auto_time_words: bool = True,
) -> EMGraph:
    """Build the dense Dialog baseline without entity extraction."""
    sample_id = str(sample.get("sample_id") or "")
    conversation = sample.get("conversation") or {}
    if not isinstance(conversation, dict):
        raise ValueError("sample.conversation must be a dict")

    graph = EMGraph(sample_id=sample_id)
    for sess_num, date_time, dialogs in _iter_sessions(conversation, session_num):
        for dialog in dialogs:
            if not isinstance(dialog, dict):
                continue
            dia_id = str(dialog.get("dia_id") or "").strip()
            if not dia_id:
                continue
            text = str(dialog.get("text") or "")
            graph.add_memory(
                MemoryNode(
                    id=_memory_id(dia_id),
                    dia_id=dia_id,
                    session_num=sess_num,
                    date_time=date_time,
                    speaker=str(dialog.get("speaker") or "").strip(),
                    text=text,
                    text_normalized=normalize_dialog_text(
                        text,
                        dialog_time=date_time,
                        time_words=time_words,
                        auto_time_words=auto_time_words,
                    ),
                    blip_caption=str(dialog.get("blip_caption") or ""),
                )
            )
    sequence_edges = ensure_memory_sequence_edges(graph)
    graph.stats = {
        "memory_count": len(graph.memories),
        "entity_count": 0,
        "edge_count": 0,
        "memory_edge_count": sequence_edges,
        "mentions_bipartite": True,
        "memory_sequence": (
            "bidirectional NEXT/PREV by parsed date_time; "
            "session/turn tie-break"
        ),
        "dialog_normalization_version": DIALOG_NORMALIZATION_VERSION,
        "memory_only": True,
    }
    return graph


def build_em_graph_from_file(
    data_file: str,
    sample_id: str,
    *,
    config: Optional[EMGraphConfig] = None,
    extractor: Optional[EntityExtractor] = None,
    session_num: Optional[int] = None,
    time_words: Optional[Sequence[str]] = None,
    checkpoint_path: Optional[str] = None,
    checkpoint_every: int = 40,
    max_workers: Optional[int] = None,
) -> EMGraph:
    data_file = os.path.abspath(data_file)
    with open(data_file, "r", encoding="utf-8") as f:
        samples = json.load(f)
    sample = None
    for item in samples:
        if item.get("sample_id") == sample_id:
            sample = item
            break
    if sample is None:
        raise ValueError(f"Sample ID '{sample_id}' not found in {data_file}")
    return build_em_graph(
        sample,
        config=config,
        extractor=extractor,
        session_num=session_num,
        time_words=time_words,
        checkpoint_path=checkpoint_path,
        checkpoint_every=checkpoint_every,
        max_workers=max_workers,
    )


def assert_bipartite(graph: EMGraph) -> None:
    """Raise if Mentions or Memory-sequence edges violate schema."""
    for edge in graph.edges:
        if edge.entity_id not in graph.entities:
            raise AssertionError(f"Edge entity missing: {edge.entity_id}")
        if edge.memory_id not in graph.memories:
            raise AssertionError(f"Edge memory missing: {edge.memory_id}")
        if edge.entity_id.startswith("memory:") or edge.memory_id.startswith("entity:"):
            raise AssertionError(f"Edge endpoints swapped or invalid: {edge.id}")
        if edge.edge_type != EdgeType.MENTIONS:
            raise AssertionError(f"Mentions list has non-MENTIONS edge: {edge.id}")
    for edge in graph.memory_edges:
        if edge.src_memory_id not in graph.memories:
            raise AssertionError(f"MemoryEdge src missing: {edge.src_memory_id}")
        if edge.dst_memory_id not in graph.memories:
            raise AssertionError(f"MemoryEdge dst missing: {edge.dst_memory_id}")
        if edge.edge_type not in (EdgeType.NEXT, EdgeType.PREV):
            raise AssertionError(f"MemoryEdge bad type: {edge.id}")
