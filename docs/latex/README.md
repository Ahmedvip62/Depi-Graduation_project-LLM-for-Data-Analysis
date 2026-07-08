# Universal Analyst — LaTeX Technical Documentation

A modular, book-style technical document (40+ pages) covering every part of the
Universal Analyst project. Designed to compile on **Overleaf** (or any TeX Live
distribution) with **pdfLaTeX**.

## Compiling

### On Overleaf (recommended)
1. Create a new project and upload this entire `latex/` folder (keep the
   `chapters/` subfolder structure).
2. Set the **main document** to `main.tex`.
3. Set the compiler to **pdfLaTeX** (Menu → Compiler → pdfLaTeX).
4. Compile. The first pass builds the table of contents; Overleaf runs the
   extra passes automatically, so the TOC, list of figures/tables, and
   cross-references resolve on the next compile.

### Locally
```bash
cd docs/latex
latexmk -pdf main.tex      # runs enough passes automatically
# or, manually:
pdflatex main.tex && pdflatex main.tex && pdflatex main.tex
```

## Structure

```
latex/
├── main.tex                 # master file: preamble, styling, \input list
└── chapters/
    ├── 00_cover.tex         # full-bleed cover page
    ├── 01_abstract.tex      # abstract + conventions
    ├── 02_introduction.tex  # Ch 1
    ├── 03_product.tex       # Ch 2
    ├── 04_architecture.tex  # Ch 3  (+ architecture & sequence diagrams)
    ├── 05_ingestion.tex     # Ch 4
    ├── 06_rag.tex           # Ch 5
    ├── 07_llm.tex           # Ch 6
    ├── 08_skills.tex        # Ch 7
    ├── 09_visualization.tex # Ch 8
    ├── 10_prediction.tex    # Ch 9
    ├── 11_reporting.tex     # Ch 10
    ├── 12_frontend.tex      # Ch 11
    ├── 13_api.tex           # Ch 12
    ├── 14_deployment.tex    # Ch 13
    ├── 15_testing.tex       # Ch 14
    ├── 16_security.tex      # Ch 15
    ├── 17_team.tex          # Ch 16
    ├── 18_future.tex        # Ch 17
    ├── 19_conclusion.tex    # Ch 18
    └── A_appendices.tex     # env template, event protocol, glossary, ...
```

## Notes

- **Fonts**: uses `newpxtext`/`newpxmath` (Palatino-style) with `beramono` for
  code — all standard on Overleaf. No custom fonts to upload.
- **Diagrams** are native **TikZ**/**PGFPlots** (vector, no external images), so
  nothing extra needs to be uploaded and they scale cleanly.
- **Colours** follow the project's indigo (`uaIndigo`) / amber (`uaAmber`)
  brand, defined once in `main.tex`.
- To edit a chapter, change the corresponding file in `chapters/` — the master
  file rarely needs touching.
