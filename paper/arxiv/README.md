# arXiv v108 submission bundle

## Upload files

Upload main.tex and references.bib from this directory, or use the generated
paper/entity_memory_graph_retrieval_arxiv_en_v108_arxiv_source.zip bundle.
The PDF is provided separately as
paper/entity_memory_graph_retrieval_arxiv_en_v108.pdf.

The exact code and manuscript snapshot is pinned at:
https://github.com/Sun668/em_graph_memory/tree/v1.0.8

## Build

    export PATH="/Library/TeX/texbin:$PATH"
    latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

The manuscript uses inline TikZ for its figure and has no external image files.
