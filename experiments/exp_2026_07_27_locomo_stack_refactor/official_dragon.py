#!/usr/bin/env python3
"""Official LoCoMo Dialog+DRAGON retrieval outside the frozen evaluator.

Only device placement and experiment orchestration live here.  Dialog/query
text, model ids, CLS pooling, unnormalized vectors, raw dot product, ranking,
reader context, answer generation, and evaluation follow the pinned upstream
implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
CODE_DIR = ROOT / "code"
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(EXP_DIR))

from common.llm import observe_model_usage, set_api_key_from_env
from locomo_eval import (
    LoCoMoEvaluationConfig,
    OfficialLoCoMoEvaluator,
    RecalledQAContext,
)
from locomo_eval.vendor_runtime import load_official_modules
from validate_formal_result import (
    condition_fingerprint,
    validate_formal_result,
)

DATASET_SHA256 = (
    "047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74"
)
UPSTREAM_COMMIT = "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376"
QUERY_MODEL = "facebook/dragon-plus-query-encoder"
CONTEXT_MODEL = "facebook/dragon-plus-context-encoder"
TOKENIZER_MODEL = QUERY_MODEL
QUERY_REVISION = "2d3808c087119b953f8494b7638c216c71712cee"
CONTEXT_REVISION = "68074e7406bb0061b0d049b58592acafae00e9d4"
TOKENIZER_REVISION = QUERY_REVISION
RETRIEVER = "dragon"
EMBED_BATCH_SIZE = 24
CACHE_SCHEMA = "official_locomo_dialog_dragon_v3"
TOP_K_VALUES = (5, 10, 25, 50)
SCOPES = {"all10", "preflight"}
OFFICIAL_DEPENDENCY_VERSIONS = {
    "python": "3.9.18",
    "torch": "2.0.1",
    "transformers": "4.35.0",
    "tokenizers": "0.14.1",
    "numpy": "1.26.0",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_vendor_manifest() -> Dict[str, Any]:
    vendor_dir = CODE_DIR / "locomo_eval" / "vendor"
    manifest_path = vendor_dir / "MANIFEST.sha256"
    failures = []
    checked = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        actual = _sha256_file(vendor_dir / relative)
        checked.append(relative)
        if actual != expected:
            failures.append(
                {"path": relative, "expected": expected, "actual": actual}
            )
    if failures:
        raise RuntimeError(f"vendored LoCoMo manifest mismatch: {failures}")
    return {
        "manifest": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": _sha256_file(manifest_path),
        "checked_files": len(checked),
        "failures": failures,
        "upstream_commit": UPSTREAM_COMMIT,
    }


def assert_formal_source_clean() -> Dict[str, Any]:
    status = _git("status", "--porcelain=v1")
    if status:
        raise RuntimeError(
            "formal run requires a clean committed worktree; found:\n" + status
        )
    manifest = verify_vendor_manifest()
    return {
        "source_commit": _git("rev-parse", "HEAD"),
        "source_tree": _git("rev-parse", "HEAD^{tree}"),
        "worktree_clean": True,
        "locomo_eval_clean": True,
        "vendor": manifest,
    }


def load_dataset(
    data_path: Path,
    sample_ids: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    data_path = data_path.resolve()
    actual_sha = _sha256_file(data_path)
    if actual_sha != DATASET_SHA256:
        raise RuntimeError(
            f"dataset SHA-256 mismatch: expected {DATASET_SHA256}, "
            f"got {actual_sha}"
        )
    samples = json.loads(data_path.read_text(encoding="utf-8"))
    if sample_ids is None:
        return samples
    requested = list(sample_ids)
    by_id = {
        str(sample.get("sample_id") or ""): sample for sample in samples
    }
    missing = [sample_id for sample_id in requested if sample_id not in by_id]
    if missing:
        raise ValueError(f"unknown sample ids: {missing}")
    return [by_id[sample_id] for sample_id in requested]


def official_dialog_rows(
    sample: Mapping[str, Any],
) -> Tuple[List[str], List[str], List[str]]:
    """Mirror upstream gpt_utils.prepare_for_rag dialog construction."""
    conversation = sample["conversation"]
    session_nums = [
        int(key.split("_")[-1])
        for key in conversation.keys()
        if "session" in key and "date_time" not in key
    ]
    dialogs: List[str] = []
    date_times: List[str] = []
    context_ids: List[str] = []
    for session_num in range(min(session_nums), max(session_nums) + 1):
        date_time = conversation[f"session_{session_num}_date_time"]
        for dialog in conversation[f"session_{session_num}"]:
            context_ids.append(dialog["dia_id"])
            date_times.append(date_time)
            text = dialog["speaker"] + ' said, "' + dialog["text"] + '"'
            if "blip_caption" in dialog:
                text += " and shared " + dialog["blip_caption"]
            dialogs.append(text)
    return dialogs, date_times, context_ids


def _available_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda:0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def retrieval_runtime_identity(device: Optional[str] = None) -> Dict[str, Any]:
    import tokenizers
    import torch
    import transformers

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "device": str(device or _available_device()),
        "torch": str(torch.__version__).split("+", 1)[0],
        "torch_build": str(torch.__version__),
        "torch_cuda": torch.version.cuda,
        "transformers": str(transformers.__version__),
        "tokenizers": str(tokenizers.__version__),
        "numpy": str(np.__version__),
    }


def assert_official_dependency_versions(
    runtime: Mapping[str, Any],
) -> None:
    mismatches = {
        key: {
            "expected": expected,
            "actual": runtime.get(key),
        }
        for key, expected in OFFICIAL_DEPENDENCY_VERSIONS.items()
        if runtime.get(key) != expected
    }
    if mismatches:
        raise RuntimeError(
            "official DRAGON dependency mismatch; use the pinned O1 "
            f"runtime: {mismatches}"
        )


@dataclass
class DragonModels:
    tokenizer: Any
    context_encoder: Any
    query_encoder: Any
    device: str


def load_dragon_models(*, local_files_only: bool) -> DragonModels:
    from transformers import AutoModel, AutoTokenizer

    device = _available_device()
    tokenizer = AutoTokenizer.from_pretrained(
        TOKENIZER_MODEL,
        revision=TOKENIZER_REVISION,
        local_files_only=local_files_only,
    )
    context_encoder = AutoModel.from_pretrained(
        CONTEXT_MODEL,
        revision=CONTEXT_REVISION,
        local_files_only=local_files_only,
    ).to(device)
    query_encoder = AutoModel.from_pretrained(
        QUERY_MODEL,
        revision=QUERY_REVISION,
        local_files_only=local_files_only,
    ).to(device)
    context_encoder.eval()
    query_encoder.eval()
    return DragonModels(
        tokenizer=tokenizer,
        context_encoder=context_encoder,
        query_encoder=query_encoder,
        device=device,
    )


def embed_texts(
    texts: Sequence[str],
    *,
    tokenizer: Any,
    encoder: Any,
    device: str,
) -> np.ndarray:
    """Use upstream DRAGON padding/truncation and raw first-token vectors."""
    import torch

    batches = []
    encoder.eval()
    with torch.no_grad():
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            encoded = tokenizer(
                list(texts[start : start + EMBED_BATCH_SIZE]),
                padding=True,
                truncation=True,
                return_tensors="pt",
            ).to(device)
            vectors = encoder(**encoded).last_hidden_state[:, 0, :]
            batches.append(vectors.detach().cpu().numpy())
    return np.concatenate(batches, axis=0).astype(np.float32, copy=False)


def _stable_cache_metadata(
    sample: Mapping[str, Any],
    *,
    contexts: Sequence[str],
    questions: Sequence[str],
    runtime: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "schema": CACHE_SCHEMA,
        "dataset_sha256": DATASET_SHA256,
        "sample_id": str(sample["sample_id"]),
        "conversation_sha256": _sha256_json(sample["conversation"]),
        "qa_sha256": _sha256_json(sample["qa"]),
        "context_text_sha256": _sha256_json(list(contexts)),
        "question_text_sha256": _sha256_json(list(questions)),
        "query_model": QUERY_MODEL,
        "query_revision": QUERY_REVISION,
        "context_model": CONTEXT_MODEL,
        "context_revision": CONTEXT_REVISION,
        "tokenizer_model": TOKENIZER_MODEL,
        "tokenizer_revision": TOKENIZER_REVISION,
        "embedding_batch_size": EMBED_BATCH_SIZE,
        "pooling": "last_hidden_state[:, 0, :]",
        "normalization": "none",
        "similarity": "raw_dot_product",
        "ranking": "numpy_argsort_descending",
        "upstream_commit": UPSTREAM_COMMIT,
        "retrieval_runtime": dict(runtime),
    }


def cache_path(cache_dir: Path, sample_id: str) -> Path:
    return cache_dir / f"{sample_id}_official_dialog_dragon_v3.npz"


def build_sample_cache(
    sample: Mapping[str, Any],
    *,
    cache_dir: Path,
    models: DragonModels,
) -> Dict[str, Any]:
    contexts, date_times, context_ids = official_dialog_rows(sample)
    questions = [str(qa["question"]) for qa in sample["qa"]]
    runtime = retrieval_runtime_identity(models.device)
    assert_official_dependency_versions(runtime)
    context_vectors = embed_texts(
        contexts,
        tokenizer=models.tokenizer,
        encoder=models.context_encoder,
        device=models.device,
    )
    query_vectors = embed_texts(
        questions,
        tokenizer=models.tokenizer,
        encoder=models.query_encoder,
        device=models.device,
    )
    metadata = {
        **_stable_cache_metadata(
            sample,
            contexts=contexts,
            questions=questions,
            runtime=runtime,
        ),
    }
    path = cache_path(cache_dir, str(sample["sample_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        metadata=np.asarray(json.dumps(metadata, sort_keys=True)),
        contexts=np.asarray(contexts),
        date_times=np.asarray(date_times),
        context_ids=np.asarray(context_ids),
        questions=np.asarray(questions),
        context_vectors=context_vectors,
        query_vectors=query_vectors,
    )
    return {
        "sample_id": sample["sample_id"],
        "path": str(path.resolve()),
        "sha256": _sha256_file(path),
        "context_count": len(contexts),
        "question_count": len(questions),
        "vector_dimension": int(context_vectors.shape[1]),
        "metadata": metadata,
    }


@dataclass
class OfficialDialogDragonRecall:
    sample_id: str
    contexts: np.ndarray
    date_times: np.ndarray
    context_ids: np.ndarray
    questions: np.ndarray
    context_vectors: np.ndarray
    query_vectors: np.ndarray
    metadata: Mapping[str, Any]
    cache_file: Path

    @classmethod
    def load(
        cls,
        sample: Mapping[str, Any],
        *,
        cache_dir: Path,
    ) -> "OfficialDialogDragonRecall":
        path = cache_path(cache_dir, str(sample["sample_id"]))
        contexts, date_times, context_ids = official_dialog_rows(sample)
        questions = [str(qa["question"]) for qa in sample["qa"]]
        runtime = retrieval_runtime_identity()
        assert_official_dependency_versions(runtime)
        with np.load(path, allow_pickle=False) as cache:
            metadata = json.loads(str(cache["metadata"].item()))
            expected = _stable_cache_metadata(
                sample,
                contexts=contexts,
                questions=questions,
                runtime=runtime,
            )
            mismatches = {
                key: {"expected": value, "actual": metadata.get(key)}
                for key, value in expected.items()
                if metadata.get(key) != value
            }
            if mismatches:
                raise RuntimeError(
                    f"DRAGON cache identity mismatch for "
                    f"{sample['sample_id']}: {mismatches}"
                )
            arrays = {
                key: cache[key].copy()
                for key in (
                    "contexts",
                    "date_times",
                    "context_ids",
                    "questions",
                    "context_vectors",
                    "query_vectors",
                )
            }
        for key, expected_values in (
            ("contexts", contexts),
            ("date_times", date_times),
            ("context_ids", context_ids),
            ("questions", questions),
        ):
            if not np.array_equal(arrays[key], np.asarray(expected_values)):
                raise RuntimeError(
                    f"DRAGON cache {key} mismatch for {sample['sample_id']}"
                )
        if arrays["context_vectors"].shape[0] != len(contexts):
            raise RuntimeError("context vector count mismatch")
        if arrays["query_vectors"].shape[0] != len(questions):
            raise RuntimeError("query vector count mismatch")
        return cls(
            sample_id=str(sample["sample_id"]),
            metadata=metadata,
            cache_file=path,
            **arrays,
        )

    def ranked_indices(self, qa_index: int, top_k: int) -> np.ndarray:
        scores = np.dot(
            self.query_vectors[qa_index],
            self.context_vectors.T,
        )
        return np.argsort(scores)[::-1][: int(top_k)]

    def recall(
        self,
        sample: Mapping[str, Any],
        qa_index: int,
        question: str,
        top_k: int,
    ) -> RecalledQAContext:
        if str(sample.get("sample_id") or "") != self.sample_id:
            raise ValueError("sample id does not match DRAGON recall cache")
        if question != str(self.questions[qa_index]):
            raise ValueError(f"question mismatch at QA index {qa_index}")
        ranked = self.ranked_indices(qa_index, top_k)
        context = "\n".join(
            str(self.date_times[index]) + ": " + str(self.contexts[index])
            for index in ranked
        )
        context_ids: List[str] = []
        for index in ranked:
            context_id: Any = str(self.context_ids[index])
            if "," in context_id:
                context_id = [
                    item.strip() for item in context_id.split(",")
                ]
            if isinstance(context_id, list):
                context_ids.extend(context_id)
            else:
                context_ids.append(context_id)
        return RecalledQAContext(context=context, context_ids=context_ids)

    def identity_record(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "path": str(self.cache_file.resolve()),
            "sha256": _sha256_file(self.cache_file),
            "metadata": dict(self.metadata),
            "context_shape": list(self.context_vectors.shape),
            "query_shape": list(self.query_vectors.shape),
        }


class OfficialDialogDragonRouter:
    def __init__(
        self,
        recalls: Mapping[str, OfficialDialogDragonRecall],
    ):
        self._recalls = dict(recalls)

    def recall(
        self,
        sample: Mapping[str, Any],
        qa_index: int,
        question: str,
        top_k: int,
    ) -> RecalledQAContext:
        sample_id = str(sample.get("sample_id") or "")
        return self._recalls[sample_id].recall(
            sample,
            qa_index,
            question,
            top_k,
        )


def _resolved_samples(args: argparse.Namespace) -> Optional[List[str]]:
    if args.scope == "all10":
        if args.samples:
            raise ValueError("all10 scope cannot use --samples")
        return None
    if not args.samples:
        raise ValueError("preflight scope requires --samples")
    return list(args.samples)


def _formal_run_config(
    *,
    args: argparse.Namespace,
    samples: Sequence[Mapping[str, Any]],
    condition_dir: Path,
    source_audit: Mapping[str, Any],
    cache_records: Sequence[Mapping[str, Any]],
    runtime: Mapping[str, Any],
    command: str,
) -> Dict[str, Any]:
    model_key = f"{args.answer_model}_dialog_top_{args.top_k}"
    artifacts = {
        "prediction": "predictions.json",
        "stats": "stats.json",
        "audit": "audit.json",
        "validation": "validation.json",
        "progress": "progress.json",
        "provider_usage": "provider_usage.json",
    }
    config: Dict[str, Any] = {
        "schema": "locomo_formal_run_v1",
        "run_id": args.run_id,
        "condition_kind": "official_dialog_reference",
        "scope": args.scope,
        "sample_ids": [str(sample["sample_id"]) for sample in samples],
        "dataset_sha256": DATASET_SHA256,
        "official_upstream_commit": UPSTREAM_COMMIT,
        "source_commit": source_audit["source_commit"],
        "source_tree": source_audit["source_tree"],
        "started_at": datetime.now().astimezone().isoformat(),
        "command": command,
        "output_directory": str(condition_dir.resolve()),
        "start_state": {
            "output_directory_empty": True,
            "existing_entries": [],
            "prediction_file_existed": False,
            "directory_existed": False,
        },
        "resume": False,
        "overwrite": False,
        "models": {
            "extraction": None,
            "embedding": "official_dragon_query_context_pair",
            "answer": args.answer_model,
            "answer_actual": None,
            "query_encoder": QUERY_MODEL,
            "query_revision": QUERY_REVISION,
            "context_encoder": CONTEXT_MODEL,
            "context_revision": CONTEXT_REVISION,
        },
        "runtime": dict(runtime),
        "retrieval": {
            "variant": "O1_official_dialog_dragon",
            "rag_mode": "dialog",
            "top_k": int(args.top_k),
            "entity_weight": None,
            "semantic_weight": 1.0,
            "sequence_secondary_scale": None,
            "entity_min_rel_score": None,
            "entity_top_k_per_key": None,
            "who_only_dampen": None,
            "degree_discount": None,
            "pool": "all_dialogs",
            "pooling": "last_hidden_state[:, 0, :]",
            "normalization": "none",
            "similarity": "raw_dot_product",
            "ranking": "numpy_argsort_descending",
            "embedding_batch_size": EMBED_BATCH_SIZE,
        },
        "graph_profile": {
            "memory_only": None,
            "use_caption": True,
            "use_time_annotations": False,
            "add_speaker_as_entity": None,
        },
        "answer_protocol": {
            "message_role": "system",
            "temperature": 0,
            "max_tokens": 32,
            "batch_size": 1,
            "category5_option_order": (
                "unchanged unseeded upstream random.random()"
            ),
        },
        "cache_identity": {
            "schema": CACHE_SCHEMA,
            "records": list(cache_records),
        },
        "model_key": model_key,
        "prediction_key": f"{model_key}_prediction",
        "artifacts": artifacts,
        "source_audit": source_audit,
    }
    config["condition_fingerprint"] = condition_fingerprint(config)
    return config


def _reader_usage_summary(
    events: Sequence[Mapping[str, Any]],
    *,
    requested_model: str,
    expected_requests: int,
    status: str,
) -> Dict[str, Any]:
    if status not in {"in_progress", "complete"}:
        raise ValueError(f"unsupported provider usage status: {status}")
    invalid = [
        dict(event)
        for event in events
        if event.get("stage") != "official_reader"
        or event.get("operation") != "chat"
        or int(event.get("request_count") or 0) != 1
        or not str(event.get("actual_model") or "").strip()
    ]
    if invalid:
        raise RuntimeError(f"invalid Reader provider telemetry: {invalid[:3]}")
    actual_model_counts: Dict[str, int] = {}
    requested_model_counts: Dict[str, int] = {}
    for event in events:
        actual = str(event["actual_model"])
        requested = str(event.get("requested_model") or "")
        actual_model_counts[actual] = actual_model_counts.get(actual, 0) + 1
        requested_model_counts[requested] = (
            requested_model_counts.get(requested, 0) + 1
        )
    request_count = sum(int(event["request_count"]) for event in events)
    if status == "complete" and request_count != expected_requests:
        raise RuntimeError(
            "Reader provider request count mismatch: "
            f"expected {expected_requests}, got {request_count}"
        )
    if status == "complete" and len(actual_model_counts) != 1:
        raise RuntimeError(
            "Reader provider returned multiple model identities: "
            f"{actual_model_counts}"
        )
    actual_model = (
        next(iter(actual_model_counts))
        if len(actual_model_counts) == 1
        else None
    )
    if (
        status == "complete"
        and actual_model is not None
        and actual_model != requested_model
        and not actual_model.startswith(f"{requested_model}-")
    ):
        raise RuntimeError(
            "Reader provider model is not the requested official model "
            f"family: requested={requested_model}, actual={actual_model}"
        )
    return {
        "schema": "locomo_reader_provider_usage_v1",
        "status": status,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "expected_request_count": int(expected_requests),
        "request_count": request_count,
        "requested_model_counts": requested_model_counts,
        "actual_model_counts": actual_model_counts,
        "input_tokens": sum(
            int(event.get("input_tokens") or 0) for event in events
        ),
        "output_tokens": sum(
            int(event.get("output_tokens") or 0) for event in events
        ),
        "total_tokens": sum(
            int(event.get("total_tokens") or 0) for event in events
        ),
        "wall_seconds": sum(
            float(event.get("wall_seconds") or 0.0) for event in events
        ),
        "token_source": "provider response usage",
    }


def _official_reference_audit(
    samples: Sequence[Mapping[str, Any]],
    *,
    top_k: int,
) -> Dict[str, Any]:
    return {
        "mandatory_graph_constraint": "fail",
        "reporting_status": "non-compliant diagnostic/reference baseline",
        "reason": (
            "Official Dialog uses dense retrieval over flat conversation "
            "dialogs and does not construct or retrieve through a graph."
        ),
        "graph_construction": "none",
        "graph_inputs": [],
        "qa_or_judge_inputs_used_for_graph_construction": False,
        "answer_recall": "official DRAGON dense Dialog retrieval",
        "conversation_inputs": [
            "session order",
            "session date_time for reader wrapper only",
            "dialog dia_id",
            "speaker",
            "raw dialog text",
            "blip_caption when the key exists",
        ],
        "excluded_from_index_construction": [
            "QA questions",
            "QA answers",
            "QA evidence",
            "QA categories",
            "judge outputs",
            "previous predictions",
            "question-driven ledgers",
        ],
        "qa_usage": "raw question is embedded only at retrieval time",
        "sample_ids": [str(sample["sample_id"]) for sample in samples],
        "top_k": int(top_k),
        "prompt_budget": {
            "status": "unchanged official LoCoMo prompt",
            "added_experiment_scaffold_chars": 0,
            "limit_chars": 5000,
            "pass": True,
        },
    }


def command_build_cache(args: argparse.Namespace) -> None:
    data_path = Path(args.data_file).resolve()
    sample_ids = args.samples or None
    samples = load_dataset(data_path, sample_ids)
    verify_vendor_manifest()
    assert_official_dependency_versions(retrieval_runtime_identity())
    models = load_dragon_models(local_files_only=args.local_files_only)
    records = []
    for index, sample in enumerate(samples, start=1):
        print(
            f"[{index}/{len(samples)}] embedding {sample['sample_id']}",
            flush=True,
        )
        records.append(
            build_sample_cache(
                sample,
                cache_dir=Path(args.cache_dir).resolve(),
                models=models,
            )
        )
    output = Path(args.cache_dir).resolve() / "cache_manifest.json"
    _write_json(
        output,
        {
            "schema": CACHE_SCHEMA,
            "dataset_sha256": DATASET_SHA256,
            "records": records,
        },
    )
    print(f"cache manifest: {output}", flush=True)


def command_retrieval_check(args: argparse.Namespace) -> None:
    assert_official_dependency_versions(retrieval_runtime_identity())
    samples = load_dataset(
        Path(args.data_file).resolve(),
        args.samples or None,
    )
    recalls = {
        str(sample["sample_id"]): OfficialDialogDragonRecall.load(
            sample,
            cache_dir=Path(args.cache_dir).resolve(),
        )
        for sample in samples
    }
    rows = []
    for sample in samples:
        recall = recalls[str(sample["sample_id"])]
        for qa_index, qa in enumerate(sample["qa"]):
            result = recall.recall(
                sample,
                qa_index,
                str(qa["question"]),
                args.top_k,
            )
            rows.append(
                {
                    "sample_id": sample["sample_id"],
                    "qa_index": qa_index,
                    "context_count": len(result.context_ids),
                    "unique_context_count": len(set(result.context_ids)),
                    "context_ids": list(result.context_ids),
                }
            )
    expected = sum(len(sample["qa"]) for sample in samples)
    failures = [
        row
        for row in rows
        if row["context_count"] != args.top_k
        or row["unique_context_count"] != args.top_k
    ]
    report = {
        "status": "pass" if not failures and len(rows) == expected else "fail",
        "metric_bearing": False,
        "samples": len(samples),
        "qa": len(rows),
        "top_k": args.top_k,
        "failures": failures[:20],
        "cache_records": [
            recall.identity_record() for recall in recalls.values()
        ],
    }
    _write_json(Path(args.report).resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


def command_evaluate(args: argparse.Namespace) -> None:
    if args.top_k not in TOP_K_VALUES:
        raise ValueError(f"top_k must be one of {TOP_K_VALUES}")
    selected_ids = _resolved_samples(args)
    source_audit = assert_formal_source_clean()
    runtime = retrieval_runtime_identity()
    assert_official_dependency_versions(runtime)
    samples = load_dataset(Path(args.data_file).resolve(), selected_ids)
    condition_dir = Path(args.output_root).resolve() / args.run_id
    if condition_dir.exists():
        raise FileExistsError(
            f"formal condition directory already exists: {condition_dir}; "
            "delete that exact directory before a rerun"
        )
    cache_dir = Path(args.cache_dir).resolve()
    recalls = {
        str(sample["sample_id"]): OfficialDialogDragonRecall.load(
            sample,
            cache_dir=cache_dir,
        )
        for sample in samples
    }
    cache_records = [
        recalls[str(sample["sample_id"])].identity_record()
        for sample in samples
    ]
    command = " ".join(
        shlex.quote(value)
        for value in [str(Path(sys.executable).resolve()), *sys.argv]
    )
    condition_dir.mkdir(parents=True)
    config = _formal_run_config(
        args=args,
        samples=samples,
        condition_dir=condition_dir,
        source_audit=source_audit,
        cache_records=cache_records,
        runtime=runtime,
        command=command,
    )
    artifacts = config["artifacts"]
    _write_json(condition_dir / "run_config.json", config)
    _write_json(
        condition_dir / artifacts["audit"],
        _official_reference_audit(samples, top_k=args.top_k),
    )
    set_api_key_from_env()
    evaluator = OfficialLoCoMoEvaluator(
        OfficialDialogDragonRouter(recalls),
        LoCoMoEvaluationConfig(
            model=args.answer_model,
            top_k=args.top_k,
            rag_mode="dialog",
            batch_size=1,
            overwrite=False,
        ),
    )
    outputs = []
    provider_events: List[Dict[str, Any]] = []
    prediction_path = condition_dir / artifacts["prediction"]
    progress_path = condition_dir / artifacts["progress"]
    expected_requests = sum(len(sample["qa"]) for sample in samples)
    with observe_model_usage(
        lambda event: provider_events.append(dict(event)),
        stage="official_reader",
    ):
        for sample_index, sample in enumerate(samples, start=1):
            outputs.append(evaluator.evaluate_sample(sample))
            _write_json(prediction_path, outputs)
            _write_json(
                progress_path,
                {
                    "status": (
                        "complete"
                        if sample_index == len(samples)
                        else "in_progress"
                    ),
                    "completed_samples": sample_index,
                    "total_samples": len(samples),
                    "completed_qa": sum(len(row["qa"]) for row in outputs),
                },
            )
            _write_json(
                condition_dir / artifacts["provider_usage"],
                _reader_usage_summary(
                    provider_events,
                    requested_model=args.answer_model,
                    expected_requests=expected_requests,
                    status=(
                        "complete"
                        if sample_index == len(samples)
                        else "in_progress"
                    ),
                ),
            )
    provider_usage = _reader_usage_summary(
        provider_events,
        requested_model=args.answer_model,
        expected_requests=expected_requests,
        status="complete",
    )
    config["models"]["answer_actual"] = provider_usage["actual_model"]
    config["condition_fingerprint"] = condition_fingerprint(config)
    _write_json(condition_dir / "run_config.json", config)
    _evaluation, evaluation_stats, _gpt_utils = load_official_modules()
    evaluation_stats.analyze_aggr_acc(
        str(Path(args.data_file).resolve()),
        str(prediction_path),
        str(condition_dir / artifacts["stats"]),
        config["model_key"],
        f"{config['model_key']}_f1",
        rag=True,
    )
    report = validate_formal_result(
        condition_dir,
        data_file=Path(args.data_file),
    )
    _write_json(condition_dir / artifacts["validation"], report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if report["status"] != "pass":
        raise RuntimeError("formal result validation failed")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.set_defaults(
        data_file=str(ROOT / "data" / "locomo10.json"),
        cache_dir=str(
            ROOT / "outputs" / "locomo_formal_cache" / "official_dragon"
        ),
        output_root=str(ROOT / "outputs" / "locomo_formal"),
        answer_model="gpt-3.5-turbo",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    build = subcommands.add_parser("build-cache")
    build.add_argument("--data-file", default=parser.get_default("data_file"))
    build.add_argument("--cache-dir", default=parser.get_default("cache_dir"))
    build.add_argument("--samples", nargs="*")
    build.add_argument("--local-files-only", action="store_true")
    build.set_defaults(function=command_build_cache)

    retrieval = subcommands.add_parser("retrieval-check")
    retrieval.add_argument(
        "--data-file", default=parser.get_default("data_file")
    )
    retrieval.add_argument(
        "--cache-dir", default=parser.get_default("cache_dir")
    )
    retrieval.add_argument("--samples", nargs="*")
    retrieval.add_argument(
        "--top-k", type=int, choices=TOP_K_VALUES, required=True
    )
    retrieval.add_argument("--report", required=True)
    retrieval.set_defaults(function=command_retrieval_check)

    evaluate = subcommands.add_parser("evaluate")
    evaluate.add_argument(
        "--data-file", default=parser.get_default("data_file")
    )
    evaluate.add_argument(
        "--cache-dir", default=parser.get_default("cache_dir")
    )
    evaluate.add_argument(
        "--output-root", default=parser.get_default("output_root")
    )
    evaluate.add_argument(
        "--answer-model", default=parser.get_default("answer_model")
    )
    evaluate.add_argument("--run-id", required=True)
    evaluate.add_argument("--scope", choices=sorted(SCOPES), required=True)
    evaluate.add_argument("--samples", nargs="*")
    evaluate.add_argument(
        "--top-k", type=int, choices=TOP_K_VALUES, required=True
    )
    evaluate.set_defaults(function=command_evaluate)
    return parser

def main() -> None:
    args = _parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
