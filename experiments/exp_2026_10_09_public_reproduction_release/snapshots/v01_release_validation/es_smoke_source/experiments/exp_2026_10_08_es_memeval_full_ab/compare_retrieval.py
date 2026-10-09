#!/usr/bin/env python3
"""Validate paired top-25 retrieval and score direct-dialog evidence offline."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keyed(rows):
    result = {(r["sample_id"], r["qa_index"]): r for r in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate sample/QA row")
    return result


def metrics(rows):
    n = len(rows)
    return {
        "eligible": n,
        "a_any": sum(r["a_any"] for r in rows) / n,
        "b_any": sum(r["b_any"] for r in rows) / n,
        "b_minus_a_any": sum(r["b_any"] - r["a_any"] for r in rows) / n,
        "a_all": sum(r["a_all"] for r in rows) / n,
        "b_all": sum(r["b_all"] for r in rows) / n,
        "b_minus_a_all": sum(r["b_all"] - r["a_all"] for r in rows) / n,
    }


def main():
    parser = argparse.ArgumentParser()
    for name in ("a", "b_embed", "b", "graph_input", "gold", "output"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    a, be, b = load(args.a), load(args.b_embed), load(args.b)
    for name, result in (("A", a), ("B_embed", be), ("B", b)):
        if result.get("status") != "complete" or result.get("top_k") != 25:
            raise ValueError(f"{name} must be complete top-25")
        usage = result["query_usage"]
        if usage["status"] != "pass" or usage["cache_misses"] or usage["live_embedding_requests"] or usage["cache_hits"] < 1427:
            raise ValueError(f"{name} query vector coverage invalid")
        if result["entity_extraction_coverage"]["status"] not in ("pass", "not-applicable"):
            raise ValueError(f"{name} graph extraction coverage invalid")
        if result["prompt_budget"]["status"] != "pass" or result["graph_constraint"]["status"] != "pass":
            raise ValueError(f"{name} prompt or graph audit invalid")
    if len({x["query_artifact"]["sha256"] for x in (a, be, b)}) != 1:
        raise ValueError("query artifact identity differs")
    indexes = [{r["sample_id"]: r["embedding_index_sha256"] for r in x["graph_records"]} for x in (a, be, b)]
    if indexes[0] != indexes[1] or indexes[0] != indexes[2]:
        raise ValueError("Memory index identities differ")
    ar, ber, br = keyed(a["rows"]), keyed(be["rows"]), keyed(b["rows"])
    keys = list(ar)
    if len(keys) != 1427 or set(keys) != set(ber) or set(keys) != set(br):
        raise ValueError("QA coverage differs")
    if any(ar[key]["context_ids"] != ber[key]["context_ids"] for key in keys):
        raise ValueError("A/B_embed ordered context IDs differ")
    if any(len(x[key]["context_ids"]) != 25 or len(set(x[key]["context_ids"])) != 25 for x in (ar, ber, br) for key in keys):
        raise ValueError("top-25 context IDs incomplete or duplicated")
    gold = load(args.gold)
    if [(r["sample_id"], r["qa_index"]) for r in gold] != keys:
        raise ValueError("gold order differs")
    graph = load(args.graph_input)
    original_ids = {sample["sample_id"]: {str(turn["dia_id"]) for turns in sample["conversation"].values() if isinstance(turns, list) for turn in turns} for sample in graph}
    eligible = []
    unscored = Counter()
    for key, reference in zip(keys, gold):
        if str(reference["capability"]).lower() == "abstention":
            unscored["abstention"] += 1
            continue
        direct = {str(e) for e in reference["evidence"] if str(e) in original_ids[key[0]]}
        if not direct:
            unscored[reference["capability"]] += 1
            continue
        ai, bi = set(ar[key]["context_ids"]), set(br[key]["context_ids"])
        eligible.append({"sample_id": key[0], "qa_index": key[1], "capability": reference["capability"], "direct_gold_count": len(direct), "a_any": int(bool(ai & direct)), "b_any": int(bool(bi & direct)), "a_all": int(direct <= ai), "b_all": int(direct <= bi), "context_overlap_count": len(ai & bi)})
    if len(eligible) < 100:
        raise ValueError("fewer than 100 evidence-eligible QA")
    rng = np.random.default_rng(20261008)
    ci = {}
    for metric in ("any", "all"):
        delta = np.array([row["b_" + metric] - row["a_" + metric] for row in eligible])
        means = np.array([rng.choice(delta, size=len(delta), replace=True).mean() for _ in range(10000)])
        ci[metric] = [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]
    cluster_ci = {}
    user_ids = sorted({row["sample_id"] for row in eligible})
    for metric in ("any", "all"):
        sums = np.array([sum(row["b_" + metric] - row["a_" + metric] for row in eligible if row["sample_id"] == user) for user in user_ids])
        counts = np.array([sum(row["sample_id"] == user for row in eligible) for user in user_ids])
        picks = rng.integers(0, len(user_ids), size=(10000, len(user_ids)))
        means = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
        cluster_ci[metric] = [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]
    by_capability, by_user = defaultdict(list), defaultdict(list)
    for row in eligible:
        by_capability[row["capability"]].append(row)
        by_user[row["sample_id"]].append(row)
    result = {"schema": "es_memeval_full_retrieval_compare_v1", "status": "pass", "classification": "adapted_local_retrieval_only", "scope": "official GitHub release-derived all 18 users; 1427 QA", "top_k": 25, "context_unit": "original dialog turn", "qa_count": 1427, "evidence_eligible_qa": len(eligible), "ineligible_qa_by_capability": dict(unscored), "query_artifact_sha256": a["query_artifact"]["sha256"], "memory_index_sha256_by_user": indexes[0], "a_b_embed_ordered_context_parity": {"status": "pass", "mismatch_count": 0}, "overall": metrics(eligible), "paired_qa_bootstrap_95pct_ci_b_minus_a": ci, "paired_user_cluster_bootstrap_95pct_ci_b_minus_a": cluster_ci, "bootstrap_seed": 20261008, "bootstrap_replicates": 10000, "by_capability": {k: metrics(v) for k, v in sorted(by_capability.items())}, "by_user": {k: metrics(v) for k, v in sorted(by_user.items())}, "paired_any_outcomes": dict(Counter("B_only" if r["b_any"] and not r["a_any"] else "A_only" if r["a_any"] and not r["b_any"] else "both" if r["a_any"] else "neither" for r in eligible)), "source_sha256": {name: sha(getattr(args, name)) for name in ("a", "b_embed", "b", "graph_input", "gold")}, "limitation": "Only non-abstention gold evidence IDs that directly match original dialog IDs are scored. Event IDs and other annotations lack a complete adapter mapping; these rates are not official ES-MemEval R@25.", "rows": eligible}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"overall": result["overall"], "paired_any_outcomes": result["paired_any_outcomes"], "ci": ci}, indent=2))


if __name__ == "__main__":
    main()
