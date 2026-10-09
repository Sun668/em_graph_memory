"""Offline paired description of immutable scores; no evaluator/model execution."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'experiments/exp_2026_07_27_locomo_stack_refactor'
PREFIX = 'gpt-3.5-turbo_dialog_top_25_'
NAMES = {1: 'Multi-hop', 2: 'Temporal', 3: 'Open-domain', 4: 'Single-hop', 5: 'Adversarial'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sign(a, b):
    return 'up' if b > a else 'down' if b < a else 'equal'

parser = argparse.ArgumentParser()
parser.add_argument('--artifact-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Use a fresh offline-analysis output directory.'
reference_path = OLD / 'snapshots/v40_corrected_primary_ab_significance/result.json'
reference = json.loads(reference_path.read_text())
inputs, data, stats = {}, {}, {}
for side in ('a', 'b'):
    condition = reference['conditions'][side]
    folder = args.artifact_root / 'outputs/locomo_formal' / condition['run_id']
    inputs[side] = {'run_id': condition['run_id'], 'source_commit': condition['source_commit']}
    for name, key in [('predictions', 'prediction_sha256'), ('stats', 'stats_sha256')]:
        path = folder / (name + '.json')
        assert sha(path) == condition[key], path
        inputs[side][name + '_sha256'] = sha(path)
    data[side] = json.loads((folder / 'predictions.json').read_text())
    stats[side] = json.loads((folder / 'stats.json').read_text())[PREFIX[:-1]]
assert len(data['a']) == len(data['b']) == 10
rows = []
for ca, cb in zip(data['a'], data['b']):
    assert ca['sample_id'] == cb['sample_id']
    assert len(ca['qa']) == len(cb['qa'])
    for index, (a, b) in enumerate(zip(ca['qa'], cb['qa'])):
        for key in ('question', 'answer', 'evidence', 'category'):
            assert a.get(key) == b.get(key), (ca['sample_id'], index, key)
        row = {key: a.get(key) for key in ('question', 'answer', 'evidence', 'category')}
        row.update(sample_id=ca['sample_id'], qa_index_zero_based=index)
        for side, source in [('a', a), ('b', b)]:
            row[side] = {key: source[PREFIX + key] for key in ('prediction', 'prediction_context', 'f1', 'recall')}
        row['f1_direction'] = sign(Decimal(str(row['a']['f1'])), Decimal(str(row['b']['f1'])))
        # Official category summary gives empty-evidence rows zero contribution.
        ra, rb = [Decimal(str(row[s]['recall'])) if a['evidence'] else Decimal(0) for s in ('a', 'b')]
        row['recall_direction'] = sign(ra, rb)
        rows.append(row)
assert len(rows) == 1986
categories = {}
for cat, name in NAMES.items():
    subset = [r for r in rows if int(r['category']) == cat]
    n = len(subset)
    assert n == reference['category_differences'][str(cat)]['qa']
    result = {'name': name, 'n': n, 'empty_evidence_rows': sum(not r['evidence'] for r in subset)}
    for side in ('a', 'b'):
        frozen = stats[side]
        assert frozen['category_counts'][str(cat)] == n
        f1 = frozen['cum_accuracy_by_category'][str(cat)] / n
        recall = frozen['recall_by_category'][str(cat)]
        assert abs(sum(r[side]['f1'] for r in subset) / n - f1) < 1e-12
        assert abs(sum(r[side]['recall'] if r['evidence'] else 0 for r in subset) / n - recall) < 1e-12
        result[side] = {'f1': f1, 'recall_acc': recall}
    result['difference_pp'] = {m: 100 * (result['b'][m] - result['a'][m]) for m in ('f1', 'recall_acc')}
    for m, old in [('f1', 'f1'), ('recall_acc', 'recall_at_25')]:
        assert abs(result['difference_pp'][m] / 100 - reference['category_differences'][str(cat)][old]) < 1e-12
    for m in ('f1', 'recall'):
        count = Counter(r[m + '_direction'] for r in subset)
        result[m + '_transitions'] = {s: count[s] for s in ('up', 'down', 'equal')}
    joint = Counter(r['recall_direction'] + '_' + r['f1_direction'] for r in subset)
    result['joint_recall_then_f1'] = {a + '_' + b: joint[a + '_' + b] for a in ('up', 'down', 'equal') for b in ('up', 'down', 'equal')}
    result['recall_up_f1_not_up'] = joint['up_down'] + joint['up_equal']
    categories[str(cat)] = result

# Four established illustrative cases plus the first temporal row. Multi-hop:
# choose the largest F1 increase among rows with recall increase, break ties by
# sample_id and QA index. This is deliberately favorable, not representative sampling.
multihop = sorted((r for r in rows if r['category'] == 1 and r['recall_direction'] == 'up' and r['f1_direction'] == 'up'), key=lambda r: (-(r['b']['f1'] - r['a']['f1']), r['sample_id'], r['qa_index_zero_based']))[0]
case_ids = [('conv-49', 41), ('conv-49', 115), ('conv-26', 22), ('conv-26', 172), ('conv-26', 0), (multihop['sample_id'], multihop['qa_index_zero_based'])]
cases = [next(r for r in rows if (r['sample_id'], r['qa_index_zero_based']) == key) for key in case_ids]
report = {'schema': 'icaart_category_description_v1', 'status': 'pass', 'scope': 'Post-hoc descriptive reanalysis of stored scores; not a new formal model run, category significance test, or causal error attribution.', 'analysis_source_sha256': sha(Path(__file__)), 'primary_snapshot_sha256': sha(reference_path), 'inputs': inputs, 'qa_count': len(rows), 'categories': categories, 'case_selection': 'Four existing manuscript cases; first temporal QA; maximal F1-gain multi-hop row among positive-recall/positive-F1 pairs, lexical sample/index tie-break. Illustrative and selected, not representative.', 'cases': cases, 'api_calls': 0, 'scoring_calls': 0, 'score_precision': 'Compare stored three-decimal scores exactly. Empty-evidence recall contributes zero, matching frozen aggregate; raw values preserved in rows.'}
args.output.mkdir(parents=True)
(args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
(args.output / 'paired_rows.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(categories, indent=2))
print('SELECTED MULTI-HOP', json.dumps(multihop, indent=2))
