# 07 P1 implementation specification

P1 scope: AST-safe extraction, protected-content handling, reconstruction and
validation. Excluded: AI providers, persistent TM/glossary storage and CI
automation, except for interfaces needed by tests.

## Suggested modules

```text
src/preset_i18n/
  ast.py          Pandoc JSON models and traversal
  extract.py      supported-node segment extraction
  protect.py      placeholder creation and verification
  reconstruct.py  translated segment application
  validate.py     structural/resource/protection checks
  cli.py          extract/reconstruct/validate commands
```

Public interfaces:

```python
extract_segments(ast: dict, *, source_file: str) -> ExtractionResult
reconstruct(ast: dict, translations: Mapping[str, Translation]) -> dict
validate_ast(original: dict, rebuilt: dict, *, resource_root: Path) -> list[Issue]
```

Suggested models:

```python
Segment(id, source_file, ast_path, kind, context, source_text,
        protected_text, source_hash, protected_hash, placeholders)
Placeholder(token, kind, payload_hash, original_node)
Translation(segment_id, text, status="draft|approved")
Issue(severity, code, segment_id, message)
```

## Extraction rules

- Support Header, Para, Plain, list items, Table cells, BlockQuote, Image
  captions/alt text and Notes when encountered.
- Recursively tokenize inline children; emit text runs plus typed placeholders.
- Never translate Code, CodeBlock, Math, raw TeX, URL/title, image target,
  attributes, IDs or numeric/unit tokens marked protected.
- Reject or explicitly report unsupported Div, Cite, custom RawBlock and
  rowspan/colspan variants until fixtures define their policy.

## CLI contract

```text
preset-i18n extract  --ast input.json --out segments.json
preset-i18n rebuild  --ast input.json --translations translations.json --out translated.json
preset-i18n validate --original input.json --translated translated.json --resource-root sop
```

Commands must be deterministic, use UTF-8, return nonzero on errors, and never
call a network or AI service. `rebuild` should refuse missing translations for
segments declared required unless an explicit review status permits them.

## Tests and fixtures

Unit fixtures must cover mixed bold/link/math/code text, moved placeholders,
images with captions, nested lists, tables, raw `\\appendix`, headings/IDs,
empty segments, Unicode, duplicate/missing tokens and unsupported nodes.
Integration tests should parse the real 10-document temporary assembly, verify
all 14 assets and formulas, reconstruct an identity translation, and compare
protected fingerprints and block/table geometry.

## Definition of done

- Extraction is deterministic and produces stable IDs/fingerprints.
- Identity reconstruction passes validation for the real source assembly.
- Deliberately changed URL, math, code, image path, table shape or placeholder
  fails with a useful diagnostic.
- Mixed inline formatting and placeholder movement are covered by tests.
- Unsupported structures are reported explicitly.
- No AI/network dependency is introduced.
- A fixed build environment is documented before claiming PDF equivalence.
