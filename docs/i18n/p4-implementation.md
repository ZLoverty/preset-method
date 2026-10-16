# P4 Chinese PDF Build

## Status

P4 build orchestration is implemented as a deterministic, no-AI path. The
default policy is `partial`: approved translations are used when available and
unresolved prose remains in English. This makes incremental delivery and TM
maintenance practical while keeping terminology and protected content under
review.

`strict` remains available for a release gate that requires every segment to
have an approved translation. It is an opt-in policy, not the normal workflow.

## Compatibility with the English build

The existing `scripts/build-pdf.sh` assembles the files listed by
`sop/pdf-order.txt`, removes separator lines containing only `---`, parses the
combined Markdown with Pandoc, and renders with:

- reader extensions `pipe_tables`, `strikeout`, `task_lists`,
  `autolink_bare_uris`, `tex_math_dollars`, `raw_tex`, `raw_attribute`,
  `header_attributes`, and `smart`;
- `--resource-path=sop`;
- XeLaTeX, TOC, numbered sections, 3 cm margins, 1.2 line stretch, 11 pt;
- Cambria as the main font and configurable CJK font (the existing English
  command uses `SimSun`);
- title, author and release-date metadata.

For the Chinese build, the title is `Polymaker 耗材预设调校指南`, the table of
contents heading is `目录`, and the document language metadata is `zh-CN`.

P4 uses the same ordered assembly function and reader configuration. The
translated AST is rendered as Pandoc JSON with equivalent metadata and
resource path. No second Markdown source or Chinese Markdown file is created.

Language-independent settings are ordering, separator removal, reader
extensions, resource path, TOC/section numbering, geometry, line stretch,
font size, images, tables, links, math and raw/code payloads. Chinese-specific
settings are the `zh-CN` language contract and configurable `CJKmainfont` /
`CJKsansfont`. No filter is applied twice; this repository's production script
does not define a Lua filter or custom template.

## Build stages and translation policy

`build_chinese` executes:

```text
source_assembly -> ast_extraction -> translation_resolution
 -> ast_reconstruction -> structural_validation -> pandoc_rendering
 -> pdf_validation
```

P2 resolution is the only translation source. It accepts approved candidates,
performs placeholder rebinding, and never mutates TM. Under `partial`, missing
or ambiguous segments use their English source text as a visible fallback;
they are reported as warnings and never silently treated as translated.
Malformed translations, placeholder/protected-content errors and structural
validation failures remain blocking in both policies. P1 reconstruction and
semantic validation run before Pandoc. A failed stage never replaces the
requested PDF.

The policy is intentionally asymmetric: terminology should be reasonably
stable, while full sentence uniqueness is not required. Glossary terms and
approved TM entries should therefore be reviewed, but the entire TM does not
need to be approved before a build can start.

Reports include coverage counts, stage, error code, message and segment ID:

```json
{
  "schema_version": 1,
  "language": "zh-CN",
  "status": "passed_with_warnings",
  "translation_policy": "partial",
  "stage": "translation_resolution",
  "segments_total": 397,
  "segments_resolved": 397,
  "segments_untranslated": 236,
  "coverage": {"MATCHED": 0, "DRAFT": 0, "MISSING": 397},
  "issues": []
}
```

## CLI

Check-only mode is safe and mandatory for CI/manual preflight:

```text
python -m sop_i18n build --check-only \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --report dist/i18n/zh-CN-report.json
```

The default partial check reports `passed_with_warnings` when fallback
segments remain. To require complete approved coverage, add:

```text
python -m sop_i18n build --check-only \
  --translation-policy strict \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --report dist/i18n/zh-CN-strict-report.json
```

Rendering an incremental build:

```text
python -m sop_i18n build \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --output dist/sop-zh-CN.pdf \
  --report dist/i18n/zh-CN-report.json \
  --cjk-mainfont SimSun
```

The generated report lists `untranslated_segment_ids` and emits one warning
per English fallback. Reviewers can approve important records progressively;
future builds automatically consume the approved TM entries.

The Chinese build reads `PDF_VERSION` from `.env` and writes it into the
release metadata and build report. Use `--env-file PATH` for another dotenv
file, or `--version VALUE` to override it for a one-off build.

Use `--cjk-mainfont` and optionally `--cjk-sansfont` to select installed
fonts. Windows may use SimSun or an installed Noto/Source Han CJK font; Linux
installations should provide an explicitly installed Noto Serif/Sans CJK SC or
Source Han font. Font binaries are not bundled. XeLaTeX reports unavailable
fonts during rendering and the build fails.

## Verification and limitations

Minimum PDF verification checks existence, nonzero size and `%PDF-` signature.
Manual visual QA remains required for Chinese glyphs, headings, tables,
figures, equations, page breaks, captions, references and mixed
Chinese/English typography. PDF bytes are not promised reproducible across
different TeX installations; translated AST content is deterministic for the
same source, approved TM, configuration and tool versions.

The current order-file assembly cannot attach original per-file document names
inside the combined Pandoc AST; diagnostics identify the order file and stable
segment IDs. This does not change document structure or resource resolution.
