"""Predeclared paired all-ten F1 analysis over validated formal outputs."""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs/locomo_formal"
BASE_ID = "pt_all10_B_v02"
TREAT_ID = "pt_all10_T_v03"
PREFLIGHT = ROOT / "outputs/point_time_all10/preflight_run01.json"
RESULT = EXP / "result.json"
KEY = "gpt-3.5-turbo_dialog_top_25"
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20261017


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(sorted_values: list[float], fraction: float) -> float:
    position = (len(sorted_values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] * (high - position) + sorted_values[high] * (position - low)


def provenance_only_changes(base_commit: str, treat_commit: str) -> list[str]:
    """Allow lifecycle notes between conditions, never executable/input changes."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base_commit, treat_commit],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    changed = [line for line in result.stdout.splitlines() if line]
    permitted_exact = {
        "experiments/exp_2026_10_17_point_time_all10/README.md",
        "experiments/exp_2026_10_17_point_time_all10/conclusion.md",
        "experiments/exp_2026_10_17_point_time_all10/next_steps.md",
        "experiments/exp_2026_10_17_point_time_all10/compare.py",
        "plans/codex/graph-evidence-localization/PLAN.md",
        "plans/codex/graph-evidence-localization/TODO.md",
    }
    snapshot_prefix = "experiments/exp_2026_10_17_point_time_all10/snapshots/"
    disallowed = [
        path for path in changed
        if path not in permitted_exact and not path.startswith(snapshot_prefix)
    ]
    if disallowed:
        raise ValueError(f"executable/input source changed between conditions: {disallowed}")
    return changed


def load_condition(run_id: str):
    directory = OUTPUT / run_id
    config = read(directory / "run_config.json")
    validation = read(directory / "validation.json")
    if validation.get("status") != "pass" or config.get("run_id") != run_id:
        raise ValueError(f"formal condition did not validate: {run_id}")
    predictions = read(directory / "predictions.json")
    stats = read(directory / "stats.json")
    query_usage = read(directory / "query_cache_usage.json")
    if query_usage.get("status") != "pass" or query_usage.get("cache_misses") != 0 or query_usage.get("live_embedding_requests") != 0:
        raise ValueError(f"query-vector control failed: {run_id}")
    return directory, config, predictions, stats, query_usage


def main() -> None:
    if RESULT.exists():
        raise FileExistsError(RESULT)
    preflight = read(PREFLIGHT)
    if preflight.get("status") != "pass" or preflight.get("qa_count") != 1986 or preflight.get("changed_question_count") != 99:
        raise ValueError("frozen preflight identity mismatch")
    base_dir, bcfg, base, bstats, busage = load_condition(BASE_ID)
    treat_dir, tcfg, treat, tstats, tusage = load_condition(TREAT_ID)
    if bcfg["source_commit"] == tcfg["source_commit"]:
        if bcfg["source_tree"] != tcfg["source_tree"]:
            raise ValueError("paired source tree mismatch at same commit")
        provenance_changes = []
    else:
        provenance_changes = provenance_only_changes(
            bcfg["source_commit"], tcfg["source_commit"]
        )
    if bcfg["retrieval"].get("reader_context_mode") != "raw" or tcfg["retrieval"].get("reader_context_mode") != "point_time_first":
        raise ValueError("reader-context mode mismatch")
    bretrieval = dict(bcfg["retrieval"])
    tretrieval = dict(tcfg["retrieval"])
    bretrieval.pop("reader_context_mode")
    tretrieval.pop("reader_context_mode")
    for field, left, right in (
        ("retrieval", bretrieval, tretrieval),
        ("models", bcfg["models"], tcfg["models"]),
        ("graph_profile", bcfg["graph_profile"], tcfg["graph_profile"]),
        ("answer_protocol", bcfg["answer_protocol"], tcfg["answer_protocol"]),
        ("cache_records", bcfg["cache_identity"]["records"], tcfg["cache_identity"]["records"]),
        ("query_identity", bcfg["cache_identity"]["query_embedding_artifact"], tcfg["cache_identity"]["query_embedding_artifact"]),
    ):
        if left != right:
            raise ValueError(f"paired {field} mismatch")
    if [s["sample_id"] for s in base] != [s["sample_id"] for s in treat] or len(base) != 10:
        raise ValueError("paired conversation order mismatch")
    active = {(row["sample_id"], row["qa_index"]) for row in preflight["changed_rows"]}
    all_deltas: list[float] = []
    active_deltas: list[float] = []
    inactive_deltas: list[float] = []
    by_conversation: dict[str, list[float]] = {}
    per_sample: list[dict[str, object]] = []
    all_five: list[float] = []
    ids_equal = recall_equal = 0
    for bs, ts in zip(base, treat):
        sid = bs["sample_id"]
        if len(bs["qa"]) != len(ts["qa"]):
            raise ValueError(f"paired QA count mismatch in {sid}")
        conv_all: list[float] = []
        conv_active: list[float] = []
        conv_inactive: list[float] = []
        for index, (brow, trow) in enumerate(zip(bs["qa"], ts["qa"])):
            for field in ("question", "answer", "evidence", "category"):
                if brow.get(field) != trow.get(field):
                    raise ValueError(f"paired {field} mismatch in {sid}:{index}")
            if brow[f"{KEY}_prediction_context"] != trow[f"{KEY}_prediction_context"]:
                raise ValueError(f"Top25 IDs differ in {sid}:{index}")
            ids_equal += 1
            if brow[f"{KEY}_recall"] != trow[f"{KEY}_recall"]:
                raise ValueError(f"official recall_acc row differs in {sid}:{index}")
            recall_equal += 1
            delta = float(trow[f"{KEY}_f1"]) - float(brow[f"{KEY}_f1"])
            all_five.append(delta)
            if int(brow["category"]) in (1, 2, 3, 4):
                all_deltas.append(delta)
                conv_all.append(delta)
                if (sid, index) in active:
                    active_deltas.append(delta)
                    conv_active.append(delta)
                else:
                    inactive_deltas.append(delta)
                    conv_inactive.append(delta)
        by_conversation[sid] = conv_all
        per_sample.append({
            "sample_id": sid, "category_1_4_qa": len(conv_all),
            "active_category_1_4_qa": len(conv_active),
            "category_1_4_f1_delta": mean(conv_all),
            "active_f1_delta": mean(conv_active) if conv_active else None,
            "inactive_f1_delta": mean(conv_inactive) if conv_inactive else None,
        })
    if ids_equal != 1986 or recall_equal != 1986 or len(all_deltas) != 1540:
        raise ValueError("paired all-ten coverage mismatch")
    names = list(by_conversation)
    rng = random.Random(BOOTSTRAP_SEED)
    draws = []
    for _ in range(BOOTSTRAP_DRAWS):
        picked = [by_conversation[rng.choice(names)] for _ in names]
        draws.append(sum(sum(rows) for rows in picked) / sum(len(rows) for rows in picked))
    draws.sort()
    wins = sum(delta > 0 for delta in active_deltas)
    losses = sum(delta < 0 for delta in active_deltas)
    result = {
        "schema": "point_time_all10_paired_f1_v1", "status": "complete",
        "run_ids": {"B": BASE_ID, "treatment": TREAT_ID},
        "source_commit": {"B": bcfg["source_commit"], "treatment": tcfg["source_commit"]},
        "source_tree": {"B": bcfg["source_tree"], "treatment": tcfg["source_tree"]},
        "provenance_only_changed_files": provenance_changes,
        "preflight_sha256": sha(PREFLIGHT),
        "prediction_sha256": {"B": sha(base_dir / "predictions.json"), "treatment": sha(treat_dir / "predictions.json")},
        "validation_sha256": {"B": sha(base_dir / "validation.json"), "treatment": sha(treat_dir / "validation.json")},
        "query_artifact_sha256": bcfg["cache_identity"]["query_embedding_artifact"]["sha256"],
        "query_usage": {"B": busage, "treatment": tusage},
        "paired_top25_ids_equal_rows": ids_equal,
        "paired_official_recall_acc_equal_rows": recall_equal,
        "category_1_4_subset_f1": {
            "qa_count": len(all_deltas), "paired_mean_delta": mean(all_deltas),
            "conversation_cluster_bootstrap_95": [percentile(draws, .025), percentile(draws, .975)],
            "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": BOOTSTRAP_SEED,
            "claim_gate_pass": mean(all_deltas) > 0 and percentile(draws, .025) > 0,
        },
        "active_category_1_4": {
            "qa_count": len(active_deltas), "paired_mean_delta": mean(active_deltas),
            "wins": wins, "losses": losses, "ties": len(active_deltas) - wins - losses,
        },
        "inactive_category_1_4": {"qa_count": len(inactive_deltas), "paired_mean_delta": mean(inactive_deltas)},
        "all_categories_descriptive": {"qa_count": len(all_five), "paired_mean_delta": mean(all_five)},
        "by_conversation": per_sample,
        "official_stats": {"B": bstats, "treatment": tstats},
        "note": "Categories 1-4 subset F1 is a repository-defined mean of frozen official per-QA F1, not an official LoCoMo aggregate. Category 5 option order is unseeded.",
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "primary": result["category_1_4_subset_f1"], "active": result["active_category_1_4"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
