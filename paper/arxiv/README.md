# arXiv / Overleaf submission bundle

## Contents

| File | Role |
|---|---|
| `main.tex` | Paper body |
| `references.bib` | Bibliography |
| `main.pdf` | Compiled PDF (regenerate after edits) |
| `Makefile` | Local `latexmk` / `pdflatex` build |
| `../ARXIV_DRAFT.md` | Longer lab notebook draft (not for upload) |

## Build (local)

```bash
export PATH="/Library/TeX/texbin:$PATH"   # macOS MacTeX
cd experiments/exp_2026_07_26_locomo_official_compare/paper/arxiv
latexmk -pdf main.tex
```

## Build (Overleaf)

1. Upload `main.tex` + `references.bib`.
2. Compiler: **pdfLaTeX**; main document `main.tex`.
3. Replace anonymous author block for a named arXiv upload if desired.

## Claim checklist before submit

- [ ] Main claim is **A vs B under gpt-3.5 + text-embedding-3-small** (reimplementation scores)
- [ ] Paper Table 3 rows labeled **DRAGON / cite only**
- [ ] No Mem0 / LLM-judge numbers in main tables
- [ ] Author names filled as you prefer for arXiv
- [ ] Numbers match `../TABLE_GPT35_TES_COMPARE.md` / snapshot `v04`
- [ ] README / arXiv Comments field use the **actual** `main.pdf` page count (do not force a page target by deleting content)

## Suggested arXiv metadata

- **Category:** cs.CL (primary); optionally cs.IR
- **Title:** Entity–Memory Bipartite Graphs for Long-Conversation Dialog Retrieval on LoCoMo
- **Comments:** set from compiled PDF page count; code at https://github.com/Sun668/em_graph_memory

## Current build

- **Compiled PDF:** 10 pages (content-complete; page count is informational only)
