# 04 Baseline build verification

## Environment

- Repository: `preset-method`, commit `3d8fafa` on `main`
- OS: Windows host, Git Bash used to execute the POSIX script
- Pandoc: 3.12.1
- XeLaTeX: MiKTeX installation present
- Existing artifacts: `dist/polymaker-filament-preset-tuning-guide-local.pdf`
  and `dist/preset-method-v2.0-pre.pdf`

## Exact commands and results

1. `PDF_NAME=preset-method-audit-baseline.pdf PDF_VERSION=audit bash scripts/build-pdf.sh`
   - source/manifest validation: **passed** after the path change
   - Pandoc parsing: **passed**
   - final exit code: **43**
   - error: MiKTeX fresh-install setup denied creation of
     `C:\Users\zhengyang\AppData\Roaming\MiKTeX\2.9`.
2. Temporary AST diagnostic using the same reader configuration and
   `--resource-path=sop -t json`.
   - exit code: **0**
   - JSON generated successfully.
3. Same temporary input through the PDF command with XeLaTeX.
   - exit code: **43** from Pandoc's PDF process
   - MiKTeX reported fresh-install setup and denied creation of
     `C:\Users\zhengyang\AppData\Roaming\MiKTeX\2.9`.

The diagnostic commands did not modify tracked sources or existing artifacts.

## Resource and warning checks

All 14 distinct Markdown image references resolve under `sop/assets/`, and the
production resource path is now `sop`. No current build got
far enough to validate fonts, cross-references, formula rendering or PDF
warnings. Those items are **NOT VERIFIED**.

## Reproducibility assessment

**Conditionally reproducible.** The repository path error is fixed, but the
local PDF build remains environment-blocked. Existing PDFs cannot be treated as known-good baselines because
their generating command, source revision, tool versions, fonts and metadata
are not recorded. Even after the path fix, PDF byte equality must not be used
as the sole criterion; compare extracted text, page structure, links, formulas,
images and protected AST fields.
