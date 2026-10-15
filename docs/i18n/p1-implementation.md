# P1 AST translation core

## Status

Implemented as a dependency-free Python package in `sop_i18n/`. It consumes
Pandoc JSON AST and uses the repository reader extensions when converting an
individual Markdown input through Pandoc.

P1 does not call AI services, persist translation memory, manage a glossary,
modify Markdown, generate Chinese PDF, or modify CI.

## Modules and public API

- `sop_i18n.models`: frozen serializable `Segment`, `Placeholder`, `Issue` and
  `ValidationReport` models.
- `sop_i18n.ast_io`: JSON I/O and Pandoc reader invocation.
- `sop_i18n.extract`: deterministic block-level extraction and unsupported-node
  diagnostics.
- `sop_i18n.placeholders`: structured inline encoding/decoding and integrity
  checks.
- `sop_i18n.reconstruct`: deep-copy, atomic translation application.
- `sop_i18n.validate`: semantic structure/protected-field comparison.
- `sop_i18n.cli`: `inspect`, `extract`, `rebuild` and `validate` commands.

The stable entry points are:

```python
extract_segments(ast: dict, *, source_file: str = "document") -> list[Segment]
apply_translations(ast: dict, segments: list[Segment], translations: Mapping[str, str]) -> dict
validate_translation(original_ast: dict, translated_ast: dict, segments: list[Segment]) -> ValidationReport
```

## Segment and placeholder model

Each segment has an occurrence-oriented ID derived from source file, node type
and AST path, plus a separate SHA-256 source hash. This keeps duplicate source
paragraphs distinct while leaving room for a future logical/TM ID.

The translation-facing text uses explicit tokens:

- `[[[p:N]]]`: opaque protected Pandoc inline, such as math or code.
- `[[[fmt:N]]]...[[[/fmt:N]]]`: formatting scope such as `Strong` or `Emph`.
- `[[[link:N]]]...[[[/link:N]]]`: translatable link label with immutable target.
- `[[[image:N]]]...[[[/image:N]]]`: translatable image alt text with immutable target.

The decoder parses balanced token scopes. It rejects missing, duplicated,
unknown or malformed tokens and preserves the original protected payload.

## Supported and unsupported AST

Supported current structures include `Header`, `Para`, `Plain`, nested list
content, `BlockQuote`, table cell content, inline formatting, links, images,
math, code and raw inline content. Table alignment/width nodes are recognized
as structural metadata. Unknown tagged nodes produce an error diagnostic;
they are not silently translated.

The implementation deliberately does not invent semantics for future custom
Pandoc nodes, citation rendering, or complex figure-caption schemas. Such
nodes must receive fixtures and explicit policy before production use.

## CLI

```text
python -m sop_i18n inspect --ast input.json
python -m sop_i18n extract --ast input.json --out segments.json
python -m sop_i18n inspect --order-file sop/pdf-order.txt
python -m sop_i18n rebuild --ast input.json --segments segments.json \
  --translations translations.json --out translated.json
python -m sop_i18n validate --original input.json --translated translated.json \
  --segments segments.json
```

`--markdown path.md` may replace `--ast` for `inspect` and `extract`. The CLI
uses Pandoc's production reader extension string and does not overwrite output
files unless `--force` is supplied. It never writes to `sop/` implicitly.

`translations.json` is a mapping from segment ID to translated token text.
P1 intentionally leaves review status and approval storage to P2.

## Validation invariants

The validator ignores text changes only under extracted segment roots. It still
checks node types, list/table structure, attributes, link/image destinations,
math/code/raw payloads and all non-approved text elsewhere. It permits changed
`Str`/`Space` counts and valid placeholder reordering.

All reconstruction is atomic: missing or invalid translations raise
`TranslationError`, and the caller's input AST is not mutated.

## Tests

Run:

```text
python -m unittest discover -s tests -p "test_*.py"
```

The test suite covers mixed formatting, links, math, code, images, placeholder
errors, atomicity, input immutability, protected link targets, tables,
unsupported nodes, a real `sop/entry.md` integration, and the complete
`sop/pdf-order.txt` assembly.

## Pandoc compatibility and limitations

The implementation was tested against Pandoc 3.12.1 and the reader string in
`scripts/build-pdf.sh`. Pandoc JSON schemas are versioned; P1 records the
observed behavior but does not claim compatibility with every Pandoc API
version. Future versions must run the integration suite and inspect any new
node types before adoption.

P1 does not provide persistent IDs across source moves, translation memory,
glossary enforcement, source-order assembly, PDF rendering comparison, or
Chinese typography validation. Those are P2/release-environment concerns.
