#!/usr/bin/env python3
"""Adapt EvoEmo/ES-MemEval QA data to this repo's graph QA format.

The converted graph input intentionally keeps graph construction conservative:
only session timestamps, speaker identities, dialog ids, dialog roles, and
dialog text are converted into conversation graph nodes. Official questions,
answers, evidence annotations, capabilities, summaries, observations, profiles,
and event timelines are preserved only where needed for offline evaluation or
dataset accounting, not as graph construction inputs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


GRAPH_INPUTS = [
    "dialog_history.timestamp",
    "dialog_history.id",
    "dialog_history.dialogue.idx",
    "dialog_history.dialogue.role",
    "dialog_history.dialogue.content",
    "speaker_identity_from_basic_info.name",
]

FORBIDDEN_GRAPH_INPUTS = [
    "questions.question",
    "questions.answer",
    "questions.evidence",
    "questions.capability",
    "summaries",
    "subsequent_topics",
    "event_experience",
    "social_relationship",
    "dialog_history.summary",
    "dialog_history.observation",
    "basic_info.except_name",
    "judge",
    "previous_predictions",
]


CAPABILITY_TO_CATEGORY = {
    "information extraction": 4,
    "temporal reasoning": 2,
    "conflict detection": 3,
    "abstention": 5,
    "user modeling": 1,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def iter_qa_groups(seeker: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for group in seeker.get("questions", []) or []:
        if isinstance(group, dict):
            yield group


def convert_seeker(seeker: Dict[str, Any]) -> Dict[str, Any]:
    seeker_id = safe_text(seeker.get("id"))
    user_name = safe_text((seeker.get("basic_info") or {}).get("name")) or seeker_id
    conversation: Dict[str, Any] = {
        "speaker_a": user_name,
        "speaker_b": "supporter",
    }
    id_to_session_num: Dict[str, int] = {}
    dialog_history = seeker.get("dialog_history", []) or []
    for session_num, session in enumerate(dialog_history, 1):
        session_id = safe_text(session.get("id")) or f"{seeker_id}_session_{session_num}"
        id_to_session_num[session_id] = session_num
        conversation[f"session_{session_num}_date_time"] = safe_text(session.get("timestamp"))
        turns = []
        for turn in session.get("dialogue", []) or []:
            role = safe_text(turn.get("role"))
            speaker = user_name if role == "seeker" else "supporter"
            turn_idx = safe_text(turn.get("idx"))
            dia_id = f"{session_id}:{turn_idx}" if turn_idx else session_id
            turns.append(
                {
                    "speaker": speaker,
                    "role": role,
                    "dia_id": dia_id,
                    "text": safe_text(turn.get("content")),
                }
            )
        conversation[f"session_{session_num}"] = turns

    qa_items: List[Dict[str, Any]] = []
    for group in iter_qa_groups(seeker):
        group_id = safe_text(group.get("id")) or "timeline"
        for qa in group.get("questions", []) or []:
            capability = safe_text(qa.get("capability")).lower()
            qa_items.append(
                {
                    "question": safe_text(qa.get("question")),
                    "answer": safe_text(qa.get("answer")),
                    "evidence": list(qa.get("evidence", []) or []),
                    "category": CAPABILITY_TO_CATEGORY.get(capability, 3),
                    "capability": capability,
                    "source_group_id": group_id,
                    "source_idx": qa.get("idx"),
                }
            )

    return {
        "sample_id": seeker_id,
        "conversation": conversation,
        "qa": qa_items,
        "event_summary": {},
        "observation": {},
        "session_summary": {},
        "evo_emo_meta": {
            "source_dataset": "ES-MemEval/EvoEmo",
            "user_name": user_name,
            "sessions": len(dialog_history),
            "qa_count": len(qa_items),
            "graph_construction_inputs": GRAPH_INPUTS,
            "forbidden_graph_inputs": FORBIDDEN_GRAPH_INPUTS,
            "id_to_session_num": id_to_session_num,
        },
    }


def make_turn_event(
    sample: Dict[str, Any],
    session_num: int,
    turn: Dict[str, Any],
    date: str,
    idx: int,
    *,
    role_aware_terms: bool = False,
) -> Dict[str, Any]:
    speaker = safe_text(turn.get("speaker"))
    role = safe_text(turn.get("role"))
    text = safe_text(turn.get("text"))
    dia_id = safe_text(turn.get("dia_id"))
    slot = "user_utterance" if role == "seeker" else "supporter_utterance"
    role_terms = []
    if role_aware_terms:
        role_terms = ["user", "seeker", "client", "person", "speaker_a"] if role == "seeker" else [
            "supporter",
            "helper",
            "counselor",
            "speaker_b",
        ]
    return {
        "sample_id": sample["sample_id"],
        "event_id": f"{sample['sample_id']}_s{session_num:02d}_u{idx:03d}",
        "session_num": session_num,
        "session_date": date,
        "subject": speaker,
        "predicate": "said",
        "object": text,
        "slot": slot,
        "time_text": date,
        "normalized_date": date,
        "source_dia_ids": [dia_id] if dia_id else [],
        "quote": text[:280],
        "search_terms": [speaker, role, date, dia_id, *role_terms],
        "text": f"{speaker} said: {text}",
        "graph_node_type": "dialog_turn",
    }


def build_turn_events(samples: List[Dict[str, Any]], *, role_aware_terms: bool = False) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = []
    for sample in samples:
        conversation = sample.get("conversation", {})
        session_nums = sorted(
            int(key.split("_")[-1])
            for key, value in conversation.items()
            if key.startswith("session_")
            and not key.endswith("_date_time")
            and isinstance(value, list)
        )
        for session_num in session_nums:
            date = safe_text(conversation.get(f"session_{session_num}_date_time"))
            for idx, turn in enumerate(conversation.get(f"session_{session_num}", []) or [], 1):
                if safe_text(turn.get("text")):
                    events.append(
                        make_turn_event(
                            sample,
                            session_num,
                            turn,
                            date,
                            idx,
                            role_aware_terms=role_aware_terms,
                        )
                    )
    return {
        "dataset": "ES-MemEval/EvoEmo",
        "graph_construction_inputs": GRAPH_INPUTS,
        "forbidden_graph_inputs": FORBIDDEN_GRAPH_INPUTS,
        "events": events,
        "stats": {
            "samples": len(samples),
            "events": len(events),
            "qa": sum(len(sample.get("qa", [])) for sample in samples),
            "role_aware_terms": bool(role_aware_terms),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", default="data/evo_emo.json")
    parser.add_argument("--output-data-file", default="data/evo_emo_graph_qa.json")
    parser.add_argument("--output-events-file", default="outputs/evo_emo_dialog_turn_events_v01.json")
    parser.add_argument(
        "--role-aware-terms",
        action="store_true",
        help="Add role aliases to turn-node search terms. Use only for role-aware experiments.",
    )
    args = parser.parse_args()

    raw = load_json(Path(args.input_file))
    if not isinstance(raw, list):
        raise TypeError("Expected EvoEmo JSON root to be a list of seekers.")
    samples = [convert_seeker(seeker) for seeker in raw]
    events = build_turn_events(samples, role_aware_terms=args.role_aware_terms)
    write_json(Path(args.output_data_file), samples)
    write_json(Path(args.output_events_file), events)
    print(
        json.dumps(
            {
                "samples": len(samples),
                "qa": sum(len(sample["qa"]) for sample in samples),
                "events": len(events["events"]),
                "output_data_file": args.output_data_file,
                "output_events_file": args.output_events_file,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
