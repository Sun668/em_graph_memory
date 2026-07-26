"""Layer-1 EM heterogeneous graph models.

Node types:
  - Memory: one node per dialog turn (dia)
  - Entity: extracted from pronoun/time-normalized dialog text

Edges:
  - Entity --mentions--> Memory (bipartite Mentions)
  - Memory --next/prev--> Memory (conversation-order adjacency)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    MEMORY = "memory"
    ENTITY = "entity"


class EdgeType(str, Enum):
    MENTIONS = "mentions"
    NEXT = "next"
    PREV = "prev"


@dataclass
class MemoryNode:
    """One Memory node ↔ one dialog turn."""

    id: str
    dia_id: str
    session_num: int
    date_time: str
    speaker: str
    text: str
    text_normalized: str
    # Optional raw dialog fields kept for fidelity.
    query: str = ""
    img_url: str = ""
    blip_caption: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_type(self) -> NodeType:
        return NodeType.MEMORY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "dia_id": self.dia_id,
            "session_num": self.session_num,
            "date_time": self.date_time,
            "speaker": self.speaker,
            "text": self.text,
            "text_normalized": self.text_normalized,
            "query": self.query,
            "img_url": self.img_url,
            "blip_caption": self.blip_caption,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        return cls(
            id=str(data["id"]),
            dia_id=str(data.get("dia_id", "")),
            session_num=int(data.get("session_num", 0) or 0),
            date_time=str(data.get("date_time", "")),
            speaker=str(data.get("speaker", "")),
            text=str(data.get("text", "")),
            text_normalized=str(data.get("text_normalized", "")),
            query=str(data.get("query", "")),
            img_url=str(data.get("img_url", "")),
            blip_caption=str(data.get("blip_caption", "")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class EntityNode:
    """Merged entity mention across memories."""

    id: str
    key: str
    value: str
    type: str
    merged_from: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_type(self) -> NodeType:
        return NodeType.ENTITY

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "id": self.id,
            "node_type": self.node_type.value,
            "key": self.key,
            "value": self.value,
            "type": self.type,
            "metadata": dict(self.metadata),
        }
        if self.merged_from:
            payload["merged_from"] = list(self.merged_from)
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityNode":
        return cls(
            id=str(data["id"]),
            key=str(data.get("key", "")),
            value=str(data.get("value", "")),
            type=str(data.get("type", "")),
            merged_from=[str(x) for x in (data.get("merged_from") or [])],
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class EMEdge:
    """Undirected logical link stored as entity → memory (Mentions)."""

    id: str
    entity_id: str
    memory_id: str
    edge_type: EdgeType = EdgeType.MENTIONS
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "memory_id": self.memory_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "metadata": dict(self.metadata),
            "endpoints": ["entity", "memory"],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EMEdge":
        edge_type = data.get("edge_type", EdgeType.MENTIONS.value)
        return cls(
            id=str(data["id"]),
            entity_id=str(data["entity_id"]),
            memory_id=str(data["memory_id"]),
            edge_type=EdgeType(edge_type),
            weight=float(data.get("weight", 1.0) or 1.0),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class MemoryEdge:
    """Directed Memory↔Memory adjacency in conversation order."""

    id: str
    src_memory_id: str
    dst_memory_id: str
    edge_type: EdgeType  # NEXT or PREV
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "src_memory_id": self.src_memory_id,
            "dst_memory_id": self.dst_memory_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "metadata": dict(self.metadata),
            "endpoints": ["memory", "memory"],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEdge":
        edge_type = EdgeType(data.get("edge_type", EdgeType.NEXT.value))
        return cls(
            id=str(data["id"]),
            src_memory_id=str(data["src_memory_id"]),
            dst_memory_id=str(data["dst_memory_id"]),
            edge_type=edge_type,
            weight=float(data.get("weight", 1.0) or 1.0),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class EMGraph:
    """Entity–Memory graph for one conversation sample.

    Mentions edges stay bipartite (Entity↔Memory). Sequential Memory↔Memory
    edges are stored separately in ``memory_edges``.
    """

    sample_id: str
    memories: Dict[str, MemoryNode] = field(default_factory=dict)
    entities: Dict[str, EntityNode] = field(default_factory=dict)
    edges: List[EMEdge] = field(default_factory=list)
    memory_edges: List[MemoryEdge] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def add_memory(self, node: MemoryNode) -> None:
        self.memories[node.id] = node

    def add_entity(self, node: EntityNode) -> None:
        self.entities[node.id] = node

    def add_edge(self, edge: EMEdge) -> None:
        if edge.entity_id not in self.entities:
            raise ValueError(f"Unknown entity endpoint: {edge.entity_id}")
        if edge.memory_id not in self.memories:
            raise ValueError(f"Unknown memory endpoint: {edge.memory_id}")
        if edge.edge_type != EdgeType.MENTIONS:
            raise ValueError(
                f"Mentions list only accepts MENTIONS edges, got {edge.edge_type}"
            )
        self.edges.append(edge)

    def add_memory_edge(self, edge: MemoryEdge) -> None:
        if edge.src_memory_id not in self.memories:
            raise ValueError(f"Unknown memory endpoint: {edge.src_memory_id}")
        if edge.dst_memory_id not in self.memories:
            raise ValueError(f"Unknown memory endpoint: {edge.dst_memory_id}")
        if edge.edge_type not in (EdgeType.NEXT, EdgeType.PREV):
            raise ValueError(
                f"Memory edges only accept NEXT/PREV, got {edge.edge_type}"
            )
        self.memory_edges.append(edge)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "memories": {k: v.to_dict() for k, v in self.memories.items()},
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "edges": [e.to_dict() for e in self.edges],
            "memory_edges": [e.to_dict() for e in self.memory_edges],
            "stats": dict(self.stats),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EMGraph":
        graph = cls(sample_id=str(data.get("sample_id", "")))
        for payload in (data.get("memories") or {}).values():
            graph.add_memory(MemoryNode.from_dict(payload))
        for payload in (data.get("entities") or {}).values():
            graph.add_entity(EntityNode.from_dict(payload))
        for payload in data.get("edges") or []:
            graph.add_edge(EMEdge.from_dict(payload))
        for payload in data.get("memory_edges") or []:
            graph.add_memory_edge(MemoryEdge.from_dict(payload))
        graph.stats = dict(data.get("stats") or {})
        return graph

    def save_to_file(self, filepath: str) -> None:
        import json
        import os

        os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, filepath: str) -> "EMGraph":
        import json

        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
