"""No-provider all-ten B retrieval and point-time context parity audit."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STACK = ROOT / "experiments/exp_2026_07_27_locomo_stack_refactor"
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(STACK))

import numpy
import run as stack_runner
from em_graph.build.config import ENTITY_EXTRACT_VERSION
from em_graph.cache import EMGraphArtifactStore, QueryEmbeddingArtifact, QuestionEntityCache
from em_graph.recall.service import format_recalled_context
from point_time_context import PointTimeFirstEvidenceRecall

MAIN = Path("/Users/sun/Documents/git/graph_memory")
SAVED_B = MAIN / "outputs/locomo_formal/formal_all10_M1_B_top25_41a7812_qfrozen_run01"
DATA = ROOT / "data/locomo10.json"
QUERY = ROOT / "outputs/em_graph/query_embeddings/locomo10_047d8e25_text-embedding-3-small_v1.npz"
OUT = ROOT / "outputs/point_time_all10/preflight_run01.json"
DATA_SHA = "047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74"
QUERY_SHA = "bef99a912383f201e18f2ccecfda0e28ae745b006016a6b38e6ce661eb986f9f"
KEY = "gpt-3.5-turbo_dialog_top_25_prediction_context"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NeverExtract:
    def extract(self, _text):
        raise RuntimeError("question Entity cache miss; no provider calls allowed")


def main() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    if sha(DATA) != DATA_SHA or sha(QUERY) != QUERY_SHA:
        raise ValueError("dataset or query-artifact SHA mismatch")
    validation = json.loads((SAVED_B / "validation.json").read_text())
    if validation.get("status") != "pass":
        raise ValueError("saved B validation did not pass")
    samples = stack_runner._load_samples(DATA, None)
    saved = json.loads((SAVED_B / "predictions.json").read_text())
    saved_by = {row["sample_id"]: row for row in saved}
    if set(saved_by) != {s["sample_id"] for s in samples}:
        raise ValueError("saved B conversation coverage mismatch")
    artifact = QueryEmbeddingArtifact.load(QUERY)
    artifact.validate_exact_dataset(
        samples, dataset_sha256=DATA_SHA,
        model_name="text-embedding-3-small", role="context",
    )
    store = EMGraphArtifactStore.from_env(str(MAIN / "outputs/em_graph"))
    qcache = QuestionEntityCache(
        cache_file=str(store.question_entity_cache_path()),
        namespace=f"{ENTITY_EXTRACT_VERSION}::gpt-3.5-turbo",
    )
    counts: dict[str, int] = {}
    total = 0
    changed_examples: list[dict[str, object]] = []
    for sample in samples:
        sid = str(sample["sample_id"])
        recall = stack_runner._load_recall(
            sample, variant="B", extract_model="gpt-3.5-turbo",
            embedding_model="text-embedding-3-small", store=store,
            query_cache=artifact, strict_query_cache=True,
            use_text_cache=False, question_extractor=NeverExtract(),
            question_cache=qcache,
        )
        treatment = PointTimeFirstEvidenceRecall(recall, {sid: recall})
        changed = 0
        saved_qa = saved_by[sid]["qa"]
        if len(saved_qa) != len(sample["qa"]):
            raise ValueError(f"saved B QA count mismatch in {sid}")
        for index, qa in enumerate(sample["qa"]):
            question = str(qa["question"])
            baseline = recall.recall(sample, index, question, 25)
            ids = list(baseline.context_ids)
            if len(ids) != 25 or len(set(ids)) != 25 or ids != saved_qa[index][KEY]:
                raise ValueError(f"saved B ordered Top25 mismatch in {sid}:{index}")
            if baseline.context != format_recalled_context(recall.graph, ids):
                raise ValueError(f"B formatter mismatch in {sid}:{index}")
            candidate = treatment.recall(sample, index, question, 25)
            if list(candidate.context_ids) != ids:
                raise ValueError(f"treatment Top25 mismatch in {sid}:{index}")
            if candidate.context != baseline.context:
                changed += 1
                suffix = "\n" + format_recalled_context(recall.graph, ids[1:])
                if not candidate.context.endswith(suffix):
                    raise ValueError(f"non-first-Memory text changed in {sid}:{index}")
                changed_examples.append({"sample_id": sid, "qa_index": index})
            total += 1
        if recall.embedding_index.embedding_usage()["request_count"] != 0:
            raise RuntimeError(f"live Memory embedding request in {sid}")
        counts[sid] = changed
        print(f"{sid}: {len(sample['qa'])} QA, {changed} changed", flush=True)
    usage = artifact.usage(qa_count=total, required_lookup_count=total)
    if total != 1986 or usage["status"] != "pass":
        raise RuntimeError("query-vector coverage failure")
    result = {
        "schema": "point_time_all10_preflight_v1", "status": "pass",
        "dataset_sha256": DATA_SHA, "query_artifact_sha256": QUERY_SHA,
        "saved_B_run_id": SAVED_B.name,
        "saved_B_predictions_sha256": sha(SAVED_B / "predictions.json"),
        "sample_count": len(samples), "qa_count": total,
        "ordered_B_top25_parity_rows": total,
        "treatment_top25_parity_rows": total,
        "first_memory_only_parity_rows": total,
        "changed_question_count": sum(counts.values()),
        "changed_by_sample": counts, "changed_rows": changed_examples,
        "query_usage": usage, "live_memory_embedding_requests": 0,
        "python_version": sys.version.split()[0], "numpy_version": numpy.__version__,
        "preflight_source_sha256": sha(Path(__file__)),
        "treatment_source_sha256": sha(Path(__file__).parent / "point_time_context.py"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"all {total} QA matched; {sum(counts.values())} changed; query usage pass")


if __name__ == "__main__":
    main()
