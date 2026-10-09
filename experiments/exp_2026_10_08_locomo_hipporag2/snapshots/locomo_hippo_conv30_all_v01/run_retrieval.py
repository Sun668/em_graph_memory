#!/usr/bin/env python3
"""Run one isolated, conversation-only HippoRAG 2 LoCoMo condition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Any

from hipporag import HippoRAG
from hipporag.utils.config_utils import BaseConfig
from hipporag.utils.misc_utils import Chunk


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_dialogues(sample: dict[str, Any]) -> list[Chunk]:
    conversation = sample["conversation"]
    chunks: list[Chunk] = []
    seen_ids: set[str] = set()
    seen_contents: set[str] = set()
    for session, turns in conversation.items():
        if not (session.startswith("session_") and isinstance(turns, list)):
            continue
        timestamp = str(conversation.get(session + "_date_time") or "").strip()
        for turn in turns:
            dialog_id = str(turn["dia_id"])
            speaker = str(turn.get("speaker") or "").strip()
            utterance = str(turn.get("text") or "").strip()
            content = f"Session time: {timestamp}\nSpeaker: {speaker}\nUtterance: {utterance}"
            caption = str(turn.get("blip_caption") or "").strip()
            if caption:
                content += f"\nImage caption: {caption}"
            if not dialog_id or dialog_id in seen_ids:
                raise ValueError(f"missing or duplicated dialog ID {dialog_id!r}")
            if content in seen_contents:
                raise ValueError("duplicate passage content would collapse source IDs")
            seen_ids.add(dialog_id)
            seen_contents.add(content)
            chunks.append(Chunk(content=content, source_id=dialog_id, metadata={"session": session}))
    if not chunks:
        raise ValueError("no original dialogue turns")
    return chunks


def prompt_scaffold_lengths(rag: HippoRAG) -> dict[str, int]:
    filter_prompt = rag.rerank_filter
    filter_fixed = sum(len(message["content"]) for message in filter_prompt.message_template)
    filter_fixed += len(filter_prompt.one_input_template) + len(filter_prompt.one_output_template)
    manager = rag.prompt_template_manager
    ner_messages = manager.render(name="ner", passage="")
    triple_messages = manager.render(name="triple_extraction", passage="", named_entity_json="")
    lengths = {
        "ner": sum(len(message["content"]) for message in ner_messages),
        "triple_extraction": sum(len(message["content"]) for message in triple_messages),
        "fact_filter": filter_fixed,
    }
    if any(length > 5000 for length in lengths.values()):
        raise ValueError(f"non-data prompt scaffold exceeds 5000 chars: {lengths}")
    return lengths


class UsageGate:
    def __init__(self, max_chat_attempts: int):
        self.max_chat_attempts = max_chat_attempts
        self.lock = threading.Lock()
        self.chat_attempts = 0
        self.chat_live = 0
        self.chat_cache_hits = 0
        self.chat_errors = 0
        self.chat_input_tokens = 0
        self.chat_output_tokens = 0
        self.embedding_requests = 0
        self.embedding_input_tokens = 0
        self.budget_exceeded = False

    def attach(self, rag: HippoRAG) -> None:
        original_infer = rag.extraction_llm.infer
        original_encode = rag.embedding_model.encode

        def observed_infer(*args: Any, **kwargs: Any):
            with self.lock:
                if self.chat_attempts >= self.max_chat_attempts:
                    self.budget_exceeded = True
                    raise RuntimeError("HippoRAG chat-attempt budget exhausted")
                self.chat_attempts += 1
            try:
                response, metadata, cache_hit = original_infer(*args, **kwargs)
            except Exception:
                with self.lock:
                    self.chat_errors += 1
                raise
            with self.lock:
                if cache_hit:
                    self.chat_cache_hits += 1
                else:
                    self.chat_live += 1
                    self.chat_input_tokens += int(metadata.get("prompt_tokens") or 0)
                    self.chat_output_tokens += int(metadata.get("completion_tokens") or 0)
            return response, metadata, cache_hit

        def observed_encode(*args: Any, **kwargs: Any):
            vectors = original_encode(*args, **kwargs)
            usage = rag.embedding_model.last_usage
            if not isinstance(usage, dict) or not isinstance(usage.get("prompt_tokens"), int):
                raise ValueError("embedding request has no complete provider usage")
            with self.lock:
                self.embedding_requests += 1
                self.embedding_input_tokens += usage["prompt_tokens"]
            return vectors

        rag.extraction_llm.infer = observed_infer
        rag.rerank_filter.llm_infer_fn = observed_infer
        rag.embedding_model.encode = observed_encode

    def report(self) -> dict[str, Any]:
        with self.lock:
            return {
                "chat_attempts": self.chat_attempts,
                "chat_live": self.chat_live,
                "chat_cache_hits": self.chat_cache_hits,
                "chat_errors": self.chat_errors,
                "chat_input_tokens": self.chat_input_tokens,
                "chat_output_tokens": self.chat_output_tokens,
                "embedding_requests": self.embedding_requests,
                "embedding_input_tokens": self.embedding_input_tokens,
                "budget_exceeded": self.budget_exceeded,
            }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", type=Path, required=True)
    args = parser.parse_args()
    parameter_path = args.parameters.resolve()
    parameters = json.loads(parameter_path.read_text(encoding="utf-8"))
    if parameters.get("status") != "frozen":
        raise ValueError("parameter snapshot is not frozen")
    if os.environ.get("RESEARCH_PARAMETER_SNAPSHOT") != str(parameter_path):
        raise ValueError("RESEARCH_PARAMETER_SNAPSHOT does not match --parameters")
    if os.environ.get("RESEARCH_RUN_CLASS") != "diagnostic":
        raise ValueError("LoCoMo adapted retrieval-only comparison must be labeled diagnostic")
    output_dir = Path(parameters["output_dir"]).resolve()
    if os.environ.get("RESEARCH_CONDITION_DIR") != str(output_dir):
        raise ValueError("RESEARCH_CONDITION_DIR does not match frozen output")
    if output_dir.exists():
        raise FileExistsError(f"output directory must be absent: {output_dir}")

    upstream = Path(parameters["upstream_root"]).resolve()
    upstream_commit = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if upstream_commit != parameters["upstream_commit"]:
        raise ValueError("upstream commit changed")
    graph_file = Path(parameters["graph_input"]).resolve()
    retrieval_file = Path(parameters["retrieval_input"]).resolve()
    prompt_file = Path(parameters["rerank_prompt"]).resolve()
    for label, path in (("graph", graph_file), ("retrieval", retrieval_file), ("prompt", prompt_file)):
        if file_sha(path) != parameters["sha256"][label]:
            raise ValueError(f"{label} artifact identity changed")

    user_id = parameters["user_id"]
    graph_samples = json.loads(graph_file.read_text(encoding="utf-8"))
    graph_sample = next((sample for sample in graph_samples if sample["sample_id"] == user_id), None)
    if graph_sample is None:
        raise ValueError(f"user {user_id} missing from graph input")
    all_chunks = source_dialogues(graph_sample)
    expected_turns = int(parameters["full_turn_count"])
    if len(all_chunks) != expected_turns:
        raise ValueError(f"dialogue count changed: {len(all_chunks)} != {expected_turns}")
    mode = parameters["mode"]
    if mode == "pilot":
        chunks = all_chunks[:int(parameters["pilot_turns"])]
    elif mode == "full":
        chunks = all_chunks
    else:
        raise ValueError(f"unknown mode {mode}")

    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is missing")
    endpoint = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if endpoint != parameters["openai_base_url"]:
        raise ValueError("OpenAI endpoint differs from frozen config")
    output_dir.mkdir(parents=True)
    started = time.monotonic()
    usage_gate = UsageGate(int(parameters["max_chat_attempts"]))
    rag = None
    try:
        config = BaseConfig(
            save_dir=str(output_dir / "index"),
            llm_name=parameters["llm_model"],
            llm_base_url=endpoint,
            embedding_model_name=parameters["embedding_model"],
            embedding_provider="openai",
            embedding_base_url=endpoint,
            rerank_dspy_file_path=str(prompt_file),
            openie_mode="online",
            openie_max_workers=int(parameters["openie_max_workers"]),
            openie_ner_max_tokens=int(parameters["openie_ner_max_tokens"]),
            openie_triple_max_tokens=int(parameters["openie_triple_max_tokens"]),
            max_retry_attempts=int(parameters["max_retry_attempts"]),
            temperature=float(parameters["temperature"]),
            llm_supports_max_completion_tokens=bool(parameters["llm_supports_max_completion_tokens"]),
            linking_top_k=int(parameters["linking_top_k"]),
            retrieval_top_k=int(parameters["top_k"]),
            damping=float(parameters["damping"]),
            passage_node_weight=float(parameters["passage_node_weight"]),
        )
        rag = HippoRAG(global_config=config)
        prompt_lengths = prompt_scaffold_lengths(rag)
        usage_gate.attach(rag)
        rag.index(chunks)
        if usage_gate.budget_exceeded:
            raise RuntimeError("chat-attempt budget exceeded during indexing")
        if len(rag.chunk_embedding_store.get_all_ids()) != len(chunks):
            raise ValueError("HippoRAG passage count does not match original turns")
        if rag.graph.vcount() == 0 or rag.graph.ecount() == 0:
            raise ValueError("HippoRAG graph has no nodes or edges")

        # QA is loaded only after the graph has been constructed.
        retrieval_samples = json.loads(retrieval_file.read_text(encoding="utf-8"))
        retrieval_sample = next((sample for sample in retrieval_samples if sample["sample_id"] == user_id), None)
        if retrieval_sample is None:
            raise ValueError(f"user {user_id} missing from retrieval input")
        qa = retrieval_sample["qa"]
        if mode == "pilot":
            qa = qa[:int(parameters["pilot_qa"])]
        questions = [row["question"] for row in qa]
        solutions = rag.retrieve(queries=questions, num_to_retrieve=int(parameters["top_k"]))
        if len(solutions) != len(questions):
            raise ValueError("question count and retrieval count differ")
        permitted_ids = {chunk.source_id for chunk in chunks}
        rows = []
        for qa_index, solution in enumerate(solutions):
            metadata = solution.doc_metadata or []
            context_ids = [item.get("source_id") for item in metadata]
            if len(context_ids) != min(int(parameters["top_k"]), len(chunks)):
                raise ValueError(f"incomplete top-k at QA {qa_index}: {len(context_ids)}")
            if len(set(context_ids)) != len(context_ids) or any(item not in permitted_ids for item in context_ids):
                raise ValueError(f"invalid source-ID mapping at QA {qa_index}")
            rows.append({"sample_id": user_id, "qa_index": qa_index, "context_ids": context_ids})
        if usage_gate.budget_exceeded:
            raise RuntimeError("chat-attempt budget exceeded during retrieval")
        result = {
            "status": "complete",
            "classification": "adapted_local_retrieval_only" if mode == "full" else "non_metric_wiring_diagnostic",
            "run_id": parameters["run_id"],
            "mode": mode,
            "user_id": user_id,
            "source_commit": upstream_commit,
            "parameter_snapshot_sha256": file_sha(parameter_path),
            "graph_input_sha256": file_sha(graph_file),
            "retrieval_input_sha256": file_sha(retrieval_file),
            "rerank_prompt_sha256": file_sha(prompt_file),
            "turn_count": len(chunks),
            "qa_count": len(questions),
            "top_k": int(parameters["top_k"]),
            "prompt_scaffold_chars": prompt_lengths,
            "graph_nodes": rag.graph.vcount(),
            "graph_edges": rag.graph.ecount(),
            "entity_count": len(rag.entity_embedding_store.get_all_ids()),
            "fact_count": len(rag.fact_embedding_store.get_all_ids()),
            "usage": usage_gate.report(),
            "elapsed_seconds": time.monotonic() - started,
            "graph_constraint": "pass: conversation-only chunks; QA read after index; source-ID graph retrieval",
            "answer_judge": "not run",
            "rows": rows,
        }
        write_json(output_dir / "result.json", result)
        print(json.dumps({key: result[key] for key in ("status", "run_id", "turn_count", "qa_count", "graph_nodes", "graph_edges", "usage", "elapsed_seconds")}, indent=2))
    except BaseException as error:
        write_json(output_dir / "failure.json", {
            "status": "failed",
            "run_id": parameters["run_id"],
            "error_type": type(error).__name__,
            "error": str(error),
            "usage": usage_gate.report(),
            "elapsed_seconds": time.monotonic() - started,
        })
        raise
    finally:
        if rag is not None:
            rag.close()


if __name__ == "__main__":
    main()
