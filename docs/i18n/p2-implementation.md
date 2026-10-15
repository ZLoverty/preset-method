# P2 Translation Memory, Glossary and Incremental Review

## Status

P2 is implemented without AI services, network calls, database services or
source Markdown rewriting. P1 public functions remain unchanged.

The persistent source of truth uses UTF-8, deterministic JSON files:

```text
i18n/
  glossary.json
  memory/zh-CN.json
sop_i18n/
  canonical.py
  memory.py
  matching.py
  glossary.py
  review.py
  coverage.py
```

JSON is used instead of YAML so the implementation has no new runtime
dependency. The schema is versioned and files are written through a temporary
file plus `os.replace`.

## Canonical source identity

`source_key(segment)` returns a `sha256:` key over a canonical representation:

```json
{
  "canonicalization_version": 1,
  "node_type": "Para",
  "source_text": "Record <protected:p:...> the flow ratio."
}
```

Canonicalization applies Unicode NFC and collapses prose whitespace. It removes
AST location and segment occurrence identity. Placeholder numbers are replaced
by the placeholder kind and protected payload hash, so renumbering does not
invalidate a reusable translation. Math, code, URLs, image paths and formatting
payloads remain part of the key; changing them changes the key.

The P1 `segment_id` remains an occurrence identity. It is not used as the TM
key, so a moved paragraph can reuse its translation.

## Translation memory schema

`i18n/memory/zh-CN.json` has the following top-level shape:

```json
{
  "schema_version": 1,
  "language": "zh-CN",
  "records": []
}
```

Each record contains `record_id`, `language`, `source_key`, `source`, `target`,
`status`, `context`, canonical/source schema versions, occurrence ID,
`source_placeholders` and review metadata (`created_at`, `updated_at`,
`reviewed_at`, `reviewer`, `review_comment`). The production memory is intentionally empty; test
translations live only in temporary files.

Supported states and transitions:

```text
draft -> approved
draft -> rejected
rejected -> draft
approved -> draft       # explicit revision; approval is cleared
```

Direct `approved -> rejected` is not allowed. Editing an approved target first
returns it to `draft`. Multiple records can share a source key when context or
target differs; strict resolution fails closed when more than one approved
candidate remains.

## Synchronization and matching

`synchronize(segments, memory)` reports `MATCHED`, `DRAFT`, `MISSING`,
`CHANGED`, `AMBIGUOUS` and preserves `OBSOLETE` record IDs. Matching uses exact
source key plus exact/empty context. A record with the same occurrence ID but a
new source key is reported as `CHANGED`; the old record is not overwritten.
Obsolete records are reported, never deleted.

`tm sync --create-drafts` creates empty draft records for missing/changed
occurrences. Repeating the command is idempotent because draft identity is
deterministically derived from language, source key, context and target.

## P2.1 placeholder rebinding

Canonicalization deliberately ignores placeholder numbers, but a saved target
may still contain the old numbers. Every newly created draft and every
approved record therefore carries the source placeholder descriptors
(`kind`, `payload_hash`, payload and token). Before strict resolution,
`rebind_translation` pairs old and current placeholders by canonical identity
and occurrence order, then rewrites both opening and closing tokens to the
current segment's numbers.

Rebinding is followed by the existing P1 token-count and nesting validation.
If identities differ, metadata is malformed, or an old record has protected
tokens but no `source_placeholders` metadata, resolution fails closed with an
error. Such legacy records must be reapproved or migrated; the resolver never
guesses a mapping. This protects opaque placeholders and nested format/link/
image scopes as well as ordinary text.

## Review and approval

Approval calls P1 placeholder validation before changing status. It also checks
that the record's canonical source key matches the current segment and runs the
configured glossary. Error-severity diagnostics block approval; warnings are
returned to the caller but do not block it. Draft and rejected records are never
selected by the strict resolver.

## Glossary

The checked-in glossary is `i18n/glossary.json`. It currently contains actual
SOP terminology including Flow Ratio, Pressure Advance, Preset and Max
Volumetric Speed. Terms support phrase/whole-word matching, case sensitivity,
allowed alternatives and `error`/`warning`/`info` severity.

Glossary matching removes P1 placeholder tokens before scanning. Therefore
technical code, math, URLs and image paths are excluded from natural-language
term checks. This remains a review aid, not a semantic translation evaluator.

## CLI reference

Existing P1 commands remain available. P2 adds:

```text
python -m sop_i18n tm status --order-file sop/pdf-order.txt --memory i18n/memory/zh-CN.json
python -m sop_i18n tm sync --order-file sop/pdf-order.txt --memory i18n/memory/zh-CN.json --create-drafts
python -m sop_i18n tm resolve --order-file sop/pdf-order.txt --memory i18n/memory/zh-CN.json --out translations.json
python -m sop_i18n tm approve --order-file sop/pdf-order.txt --memory i18n/memory/zh-CN.json --record-id TM_ID --reviewer name
python -m sop_i18n tm reject --order-file sop/pdf-order.txt --memory i18n/memory/zh-CN.json --record-id TM_ID --reviewer name
python -m sop_i18n tm reopen --order-file sop/pdf-order.txt --memory i18n/memory/zh-CN.json --record-id TM_ID --reviewer name
python -m sop_i18n tm update --memory i18n/memory/zh-CN.json --record-id TM_ID --target "新的译文"
python -m sop_i18n glossary check --order-file sop/pdf-order.txt --glossary i18n/glossary.json --translations translations.json
```

Strict `tm resolve` writes a complete P1-compatible mapping only when every
segment has exactly one valid approved translation. `--preview` may return
English source fallback mappings for inspection, but its result is explicitly
incomplete and must not be used for publication.

## End-to-end example

For a temporary one-paragraph AST, extract a segment, create a draft with its
canonical source key, manually set its target, approve it after placeholder and
glossary checks, then call `resolve`. The resulting mapping is directly usable:

```python
segments = extract_segments(ast)
memory = TranslationMemory.load(Path("i18n/memory/zh-CN.json"))
segment = segments[0]
record = memory.create_draft(
    source_key=source_key(segment),
    source=segment.source_text,
    occurrence_id=segment.segment_id,
)
memory.update_target(record.record_id, "流量比校准")
# review.approve(memory, record.record_id, segment, reviewer="alice", ...)
translations, issues = resolve(segments, memory)
translated_ast = apply_translations(ast, segments, translations)
report = validate_translation(ast, translated_ast, segments)
```

The integration tests execute this lifecycle with temporary memory and the real
`sop/pdf-order.txt` ordering, without adding artificial records to production
memory.

## Tests

```text
python -m unittest discover -s tests -p "test_*.py"
```

The suite covers canonicalization, placeholder-number independence, source
relocation, review transitions, duplicate/ambiguous records, changed and
obsolete sources, atomic persistence, idempotent drafts, glossary protection,
strict resolution, all existing P1 tests and full SOP integration.

## Known limitations and P3 interface

- Context compatibility is intentionally conservative: exact or empty context
  only; richer section/document policies belong in P3.
- Fuzzy matching is not automatic and is not used for approval.
- JSON schema migration tooling is not needed for version 1 but must reject
  unknown versions rather than silently reinterpret them.
- The production memory starts empty; no human-approved Chinese SOP exists yet.
- No PDF generation or GitHub Actions changes are part of P2.

P3 machine translation should receive extracted `Segment` objects and emit a
draft mapping or draft TM records only. It must never call `approve`, write an
`approved` record, or bypass `resolve`/P1 validation. The intended interface is
an offline import of `{segment_id: translated_token_text}` plus source key and
placeholder validation, followed by the existing local review lifecycle.
