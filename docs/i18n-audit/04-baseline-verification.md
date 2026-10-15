# 04 Baseline build verification

## Environment

- Repository: `preset-method`, commit `3d8fafa` on `main`
- OS: Windows host, Git Bash used to execute the POSIX script
- Pandoc: 3.12.1
- XeLaTeX: MiKTeX installation present
- Existing artifacts: `dist/polymaker-filament-preset-tuning-guide-local.pdf`
  and `dist/preset-method-v2.0-pre.pdf`

## Exact commands and results

1. `bash scripts/build-pdf.sh`
   - source/manifest validation: **passed** after the path change
   - Pandoc parsing: **passed**
   - XeLaTeX PDF generation: **passed on retry**
   - output: `dist/preset-method-v2.0-pre.pdf`
2. Temporary AST diagnostic using the same reader configuration and
   `--resource-path=sop -t json`.
   - exit code: **0**
   - JSON generated successfully.
3. The first local attempt was blocked by MiKTeX first-run initialization;
   after initialization, the same repository script completed successfully.

The diagnostic commands did not modify tracked sources or existing artifacts.

## Resource and warning checks

All 14 distinct Markdown image references resolve under `sop/assets/`, and the
production resource path is now `sop`. No current build got
far enough to validate fonts, cross-references, formula rendering or PDF
warnings. Those items are **NOT VERIFIED**.

## Reproducibility assessment

**Locally reproducible after MiKTeX initialization.** Existing PDFs cannot be treated as known-good baselines because
their generating command, source revision, tool versions, fonts and metadata
are not recorded. Even after the path fix, PDF byte equality must not be used
as the sole criterion; compare extracted text, page structure, links, formulas,
images and protected AST fields.
