# 06 Proposed translation architecture

## Boundary

```text
English sop/*.md
  -> deterministic order manifest / assembly
  -> Pandoc reader with current extensions
  -> JSON AST
  -> segment extraction + protected placeholders
  -> approved translation input (P1 interface only)
  -> AST reconstruction
  -> structural/protected-content validation
  -> existing Pandoc/XeLaTeX build
  -> Chinese PDF
```

The translation layer belongs between AST parsing and the existing writer. It
must not be called by the official build; the official build consumes only
approved translations or a prevalidated translated AST.

## Granularity

Use one segment for each heading, paragraph/Plain block, list item, table cell,
block quote, image caption/alt text and future footnote body. Preserve inline
formatting as placeholders or nested token records. A sentence may move a
link/math/code placeholder, but the placeholder itself must remain unchanged.

## Protection

Protect math payloads, code, raw TeX, image targets, link URLs/titles, header
IDs, classes/attributes, filenames, model/parameter identifiers, numeric values
and units. Use stable tokens such as `⟦P0007⟧` in the translation-facing text,
with a typed map and original AST digest. Validation rejects token loss,
duplication, mutation, or unexpected tokens.

## Identity and approval

P1 should expose a segment identity containing source file, AST path, block
kind, logical heading context, canonical source-text hash and protected-content
hash. Later TM storage can reuse a translation when the canonical source hash
matches even if the paragraph moves; a changed source or protected payload
invalidates the approval. Approval state must be separate from source content.

## Validation

Require: same block/node kinds where supported, same table dimensions and
attributes, same image/link targets, same math/code/raw payloads, complete
placeholder coverage, no untranslated required segment, valid local asset
references, and stable heading/reference policy. Report unsupported nodes as
errors rather than silently passing them through.

## Build reproducibility

Keep translation generation/review outside the official build. Pin the
Pandoc/XeLaTeX/font environment in a container or runner, use a checked-in
manifest, and run a deterministic validation-only build in CI. The current
repository lacks a verifiable workflow and must resolve that before this design
can become release infrastructure.
