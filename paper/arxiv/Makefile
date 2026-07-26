MAIN = main

.PHONY: all clean

all:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -interaction=nonstopmode $(MAIN).tex; \
	else \
		pdflatex -interaction=nonstopmode $(MAIN).tex; \
		bibtex $(MAIN); \
		pdflatex -interaction=nonstopmode $(MAIN).tex; \
		pdflatex -interaction=nonstopmode $(MAIN).tex; \
	fi

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log \
		$(MAIN).out $(MAIN).toc $(MAIN).fdb_latexmk $(MAIN).fls \
		$(MAIN).synctex.gz $(MAIN).pdf
