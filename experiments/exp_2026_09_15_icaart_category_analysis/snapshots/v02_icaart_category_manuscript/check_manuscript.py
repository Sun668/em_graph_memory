"""Read-only manuscript/evidence checks; never runs models or recalculates QA metrics."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXP = ROOT / 'experiments/exp_2026_07_27_locomo_stack_refactor'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def snapshot(prefix):
    paths = list((EXP / 'snapshots').glob(prefix + '*/result.json'))
    assert len(paths) == 1, paths
    p = paths[0]
    evidence[str(p.relative_to(ROOT))] = digest(p)
    return json.loads(p.read_text())

def table(label, text):
    pos = text.index('\\label{' + label + '}')
    start = text.rfind('\\begin{table', 0, pos)
    end = text.index('\\end{table', pos)
    return text[start:end]

def require_number(value, section, places=4, scale=100):
    shown = f'{value * scale:.{places}f}'
    assert shown in section.replace(',', ''), f'Missing frozen value: {shown}'
    numeric_checks.append(shown)

parser = argparse.ArgumentParser()
parser.add_argument('--pdf', type=Path, required=True)
parser.add_argument('--log', type=Path, required=True)
args = parser.parse_args()
evidence, numeric_checks = {}, []
src = (HERE / 'review/main.tex').read_text()
base = (ROOT / 'paper/v109/main.tex').read_text()
manifest = json.loads((HERE / 'audit/baseline_manifest.json').read_text())
for name, sha in manifest['base_files'].items():
    assert digest(ROOT / 'paper/v109' / name) == sha, name
for name, sha in manifest['template_files'].items():
    assert digest(HERE / 'review' / name) == sha, name

primary = snapshot('v40_')['overall']
primary_table = table('tab:primary', src)
for metric in primary.values():
    for side in ('a', 'b'):
        require_number(metric[side], primary_table)
    require_number(abs(metric['difference']), src)
    for estimator in ('paired_qa_ci95', 'cluster_ci95'):
        for bound in metric[estimator]:
            require_number(abs(bound), src)
assert primary['f1']['significant'] is False
assert primary['recall_at_25']['significant'] is True
control = snapshot('v36_')
for key in ('official_overall_f1', 'official_recall_at_25'):
    require_number(control['metrics'][key], primary_table)
assert control['dense_control']['mismatches'] == 0
cutoffs = table('tab:cutoffs', src)
for prefix, k in [('v55_', 5), ('v57_', 10), ('v60_', 50)]:
    result = snapshot(prefix)
    comparison = result[f'comparison_vs_a_top{k}']
    for m, diff in [('official_f1', 'f1_difference'), ('official_recall_acc', 'recall_difference')]:
        require_number(result['metrics'][m], cutoffs)
        require_number(result['metrics'][m] - comparison[diff], cutoffs)
        require_number(abs(comparison[diff]), cutoffs)
    for key in ('recall_paired_qa_ci95', 'recall_conversation_cluster_ci95'):
        assert all(x > 0 for x in comparison[key])
        for bound in comparison[key]:
            require_number(bound, cutoffs)

# Preserve every component-table number and sign from the audited baseline;
# consult the frozen family decisions without rebuilding its statistics.
assert table('tab:components', src) == table('tab:components', base)
family = snapshot('v46_')
assert family['supported_after_holm']['f1'] == ['semantic_signal']
assert len(family['supported_after_holm']['recall_at_25']) == 4
for prefix in ('v52_', 'v53_', 'v66_', 'v70_'):
    snapshot(prefix)
robust_path = EXP / 'paper/robustness_audit.json'
evidence[str(robust_path.relative_to(ROOT))] = digest(robust_path)
robust = json.loads(robust_path.read_text())
for cell in robust['valid_four_cell_matrix']['cells'].values():
    for key in ('f1', 'recall_acc_at_25'):
        require_number(cell[key], table('tab:model-robustness', src))
assert robust['valid_four_cell_matrix']['holm']['embedding_recall']['adjusted_rejections'] == 2
# Bind the added descriptive table to the frozen offline result and v40 inputs.
category_path = ROOT / 'experiments/exp_2026_09_15_icaart_category_analysis/snapshots/v01_primary_ab_descriptive/result.json'
evidence[str(category_path.relative_to(ROOT))] = digest(category_path)
category_result = json.loads(category_path.read_text())
assert category_result['qa_count'] == 1986
assert category_result['api_calls'] == category_result['scoring_calls'] == 0
assert category_result['primary_snapshot_sha256'] == digest(EXP / 'snapshots/v40_corrected_primary_ab_significance/result.json')
assert category_result == json.loads((category_path.parents[2] / 'result.json').read_text())
assert category_result['analysis_source_sha256'] == digest(category_path.parents[2] / 'analyze_categories.py')
category_table = table('tab:category-paired', src)
for c in category_result['categories'].values():
    values = [f"{c[side][metric] * 100:.2f}" for metric in ('f1', 'recall_acc') for side in ('a', 'b')]
    row = f"{c['name']} & {c['n']} & {values[0]} & {values[1]} & ${c['difference_pp']['f1']:+.2f}$ & {values[2]} & {values[3]} & ${c['difference_pp']['recall_acc']:+.2f}$"
    assert row in category_table, row
    counts = ['/'.join(str(c[m + '_transitions'][d]) for d in ('up', 'down', 'equal')) for m in ('f1', 'recall')]
    assert f"{c['name']} & {counts[0]} & {counts[1]} & {c['recall_up_f1_not_up']}" in category_table
    for m in ('f1', 'recall'):
        assert sum(c[m + '_transitions'].values()) == c['n']
    numeric_checks.extend(values + [str(c['difference_pp'][m]) for m in ('f1', 'recall_acc')])

cost = snapshot('v97_')
for stage in ('conversation_entity', 'memory_embedding', 'question_entity'):
    for key in ('requests', 'input_tokens', 'output_tokens'):
        shown = f"{cost['cold'][stage][key]:,}"
        assert shown in table('tab:cost', src), shown
        numeric_checks.append(shown)
    require_number(cost['cold'][stage]['wall_seconds'], table('tab:cost', src), 2, 1)
for state, places in [('cold', 4), ('warm', 6)]:
    for key in ('mean_seconds', 'p95_seconds'):
        require_number(cost[state]['retrieval'][key], table('tab:cost', src), places, 1)
assert 'Live query embeddings' in table('tab:cost', src)
assert 'cold retrieval also makes the question-Entity requests above' in src

bib = (HERE / 'review/references.bib').read_text()
keys = set(re.findall(r'@\w+\{([^,]+),', bib))
cited = {k for group in re.findall(r'\\cite\{([^}]+)\}', src) for k in group.split(',')}
assert keys == cited, (keys - cited, cited - keys)
labels = re.findall(r'\\label\{([^}]+)\}', src)
assert len(labels) == len(set(labels))
assert set(re.findall(r'\\ref\{([^}]+)\}', src)) <= set(labels)
abstract = src.split('\\abstract{', 1)[1].split('}\n\\onecolumn', 1)[0]
abstract_words = len(abstract.split())
assert 70 <= abstract_words <= 200
pdf = PdfReader(args.pdf)
text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
nonwhite = len(''.join(text.split()))
assert 10000 <= nonwhite <= 49000, nonwhite
assert len(pdf.pages) <= 12
for page in pdf.pages:
    assert abs(float(page.mediabox.width) - 595.276) < 1
    assert abs(float(page.mediabox.height) - 841.89) < 1
assert not pdf.metadata.get('/Author')
identity_terms = ['Shumao Sun', 'Tsinghua', 'Sun668', '/Users/', 'thesis-draft-references']
for term in identity_terms:
    assert term.lower() not in (text + src + bib + str(pdf.metadata)).lower(), term
for page in pdf.pages:
    for item in page.get('/Annots', []):
        assert not any(term.lower() in str(item.get_object()).lower() for term in identity_terms)
log = args.log.read_text(errors='replace')
assert not re.search(r'Overfull|undefined|LaTeX Warning|Package .+ Warning', log)
report = {
    'status': 'pass',
    'scope': 'Manuscript consistency and frozen-summary checks; no new formal experiment or full raw-output validation.',
    'pdf_pages': len(pdf.pages), 'pdf_nonwhitespace_characters': nonwhite,
    'character_count_method': 'pypdf extraction, including references, tables, vector diagram text and appendix; portal counter remains authoritative',
    'abstract_words_whitespace_count': abstract_words,
    'bibliography_entries_and_cited_keys': len(keys),
    'checked_numeric_displays': len(numeric_checks),
    'component_table_byte_identical_to_v109': True,
    'official_template_sha256_matches': True,
    'v109_files_unchanged': True,
    'author_identity_scan_passed': True,
    'unresolved_references_and_overfull_boxes': 0,
    'manuscript_sha256': digest(HERE / 'review/main.tex'),
    'pdf_sha256': digest(args.pdf), 'evidence_sha256': evidence,
}
(HERE / 'audit/validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'evidence_sha256'}, indent=2))
