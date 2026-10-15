# 01 Repository inventory

## Relevant tree

```text
README.md
3MF_CHANGELOG.md
All in one Test.3mf
scripts/build-pdf.sh
sop/
  entry.md
  overview.md
  printer-calibration.md
  base-preset-standard.md
  bed-temperature.md
  cooling.md
  temperature-tower.md
  max-volumetric-speed.md
  flow-ratio.md
  pressure-advance.md
  retraction.md
  pdf-order.txt
  assets/                 14 referenced raster images
dist/                      2 local PDF artifacts
docs/p0.md                 audit instruction, currently untracked
```

## Sources and assembly

There are 11 Markdown files under `sop/`, of which 10 are listed as PDF inputs
by `sop/pdf-order.txt`; `overview.md` is not in the PDF order list. The list and
script now use the `sop/` source root. The script
strips lines containing only `---`, appends the listed files into a temporary
file, and sends that temporary file to Pandoc.

`entry.md` is the practical entry point. `overview.md` is a workflow diagram
and appears to be a supporting document rather than a PDF input. The appendix
inputs are `printer-calibration.md` and `base-preset-standard.md`.

## Assets and outputs

All 14 distinct `assets/...` references resolve under `sop/assets/`. The
repository also contains `All in one Test.3mf` as the final verification model.
The two PDFs under `dist/` are existing local artifacts; their provenance and
build parameters are not recorded in the repository.

## Translation-sensitive resources

- Human-readable Markdown body, headings, list items, block quotes, table
  cells, image alt text and captions.
- Links' visible labels, while URL and reference targets must remain stable.
- LaTeX math and raw TeX commands, which must not be sent as ordinary text.
- Slicer names, parameter names, filenames, model names, units and numeric
  thresholds, which require glossary/protection rules.
- PDF order and appendix placement, which are structural rather than
  translatable content.
