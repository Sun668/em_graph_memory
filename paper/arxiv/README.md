# arXiv / Overleaf submission bundle

## Contents

| File | Role |
|---|---|
| `main.tex` | Camera-oriented paper body (anonymous author placeholder) |
| `references.bib` | Bibliography |
| `Makefile` | Local `latexmk` / `pdflatex` build |
| `../ARXIV_DRAFT.md` | Longer lab notebook draft (not for upload) |

## Build (Overleaf)

1. New Overleaf project → Upload `main.tex` + `references.bib`.
2. Set main document to `main.tex`.
3. Compiler: **pdfLaTeX** (or XeLaTeX). Bibliography via BibTeX.
4. Replace the anonymous `\author{...}` block before a named arXiv upload if desired.
5. Download PDF; for arXiv.org use “Submit” → LaTeX → upload this folder (or the generated `.tar.gz`).

## Build (local)

```bash
cd experiments/exp_2026_07_26_locomo_official_compare/paper/arxiv
make        # requires latexmk or pdflatex+bibtex
make clean
```

## Claim checklist before submit

- [ ] Main claim is **A vs B under gpt-3.5 + text-embedding-3-small**
- [ ] Paper Table 3 rows labeled **DRAGON / cite only**
- [ ] No Mem0 / LLM-judge numbers in main tables
- [ ] Author names / emails / acknowledgments filled as you prefer for arXiv
- [ ] Numbers match `../TABLE_GPT35_TES_COMPARE.md` / snapshot `v04`

## Suggested arXiv metadata

- **Category:** cs.CL (primary); optionally cs.IR
- **Title:** Entity–Memory Bipartite Graphs for Long-Conversation Dialog Retrieval on LoCoMo
- **Comments:** 9 pages incl. appendix; code/experiment bundle in companion repository
