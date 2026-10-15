# 02 Pandoc build pipeline audit

## Actual command flow

```text
scripts/build-pdf.sh
  -> load PDF_NAME/PDF_VERSION from .env (without eval)
  -> require pandoc, xelatex, sed, mktemp
  -> read sop/pdf-order.txt
  -> validate listed files
  -> sed out standalone --- from each source
  -> concatenate into temporary Markdown
  -> pandoc reader + extensions
  -> XeLaTeX PDF writer
  -> dist/<PDF_NAME>-<PDF_VERSION>.pdf
```

The current script does not execute Lua filters, external filters, a template,
metadata file, bibliography processor, cross-reference filter, or post-Pandoc
step. Metadata and variables are passed directly on the command line.

## Reader and writer configuration

The declared reader is:

```text
markdown+pipe_tables+strikeout+task_lists+autolink_bare_uris+
tex_math_dollars+raw_tex+raw_attribute+header_attributes-smart
```

The writer is Pandoc's PDF path through `--pdf-engine=xelatex`, with TOC and
numbered sections. It sets `Cambria`, `SimSun`, 3 cm margins, 1.2 line stretch,
11 pt font, and title/author/date metadata.

## Versions and environment

Observed locally: Pandoc 3.12.1, XeLaTeX from MiKTeX, Windows PowerShell host.
The README instead documents a private Docker image
`192.168.22.78:3000/polymaker/docs-pdf:1.0.0`. The image digest, Pandoc,
XeLaTeX, TeX package and font versions are not pinned in repository files.

No `.gitea/` or `.github/` workflow is present in the checked-out repository,
although README claims a Gitea release workflow. CI execution is therefore
NOT VERIFIED.

## Recommended insertion point

For P1, keep source assembly and the existing reader configuration as the
boundary, then perform extraction/reconstruction on the Pandoc JSON AST before
the PDF writer. This preserves headings, tables, figures and math as typed
nodes. Translation must not be inserted into the raw concatenated Markdown,
because that makes placeholder protection and cross-file structure ambiguous.

The source-root mismatch has been corrected in `scripts/build-pdf.sh` and
`sop/pdf-order.txt`. Before official use, make a deterministic build environment
available. No AI or translation service is required by the
current build and none should be added to the official path.
