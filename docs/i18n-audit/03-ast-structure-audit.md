# 03 Markdown and AST structure audit

The temporary audit input used the 10 documents named by `sop/pdf-order.txt`
with `docs/` changed to `sop/`, standalone separators removed as the script
does, and the script's reader extensions. Pandoc JSON generation exited 0.

## Node inventory

Observed node types and approximate counts in the combined AST:

| Node | Count | Translation treatment |
|---|---:|---|
| Header | 62 | Translate visible inlines; preserve level and identifier policy |
| Para / Plain | 78 / 229 | Segment at block level, not individual `Str` nodes |
| Strong / Emph | 183 / 1 | Preserve wrapper and child order while translating children |
| BulletList / OrderedList | 49 / 23 | Translate each item as a unit; preserve nesting and list attributes |
| Table | 1 | Translate cell content; preserve alignment, widths, headers and geometry |
| Image / Figure | 14 / 4 | Translate alt/caption only; protect source path and attributes |
| Link | 15 | Translate label; preserve URL, title and reference identity |
| InlineMath / DisplayMath | 67 / 4 | Opaque protected payload; do not translate LaTeX |
| Code | 16 | Opaque protected payload |
| RawBlock | 1 | Inspect and allow-list; `\\appendix` affects document structure |
| BlockQuote | 4 | Translate prose; preserve quote block structure |
| LineBreak / SoftBreak | 3 / 21 | Preserve unless reconstruction deliberately normalizes whitespace |

## Representative source structures

- `sop/max-volumetric-speed.md`: display formulas and inline math for area and
  volumetric flow.
- `sop/cooling.md`: inline variables such as `$Fan_{\\text{min}}$` and
  `$T_g \\approx 60^\\circ C$`.
- `sop/entry.md`: a Markdown table with links in cells.
- `sop/overview.md`, `sop/bed-temperature.md`, and other SOP files: image
  alt text/captions with `assets/...` targets.
- `sop/printer-calibration.md`: `\\appendix` raw TeX block.
- Many files use inline code for slicer commands and parameter names.

## Protected fields and safety

Immutable fields include header level/identifier, table shape and cell spans,
image target, link URL/title, code text, math type and payload, raw TeX,
numeric values and units where the glossary marks them as protected, and list
nesting. Visible labels, prose, captions and alt text are translatable.

Inline child ordering may change semantically in translation, so extraction
must preserve a placeholder sequence and allow placeholders to move only as
whole tokens. It must reject missing, duplicated or altered placeholders.

No citations, footnotes, Div/Span custom classes, explicit IDs, or rowspan /
colspan tables were observed in the tested inputs. This is an inventory result,
not permission to ignore those node types in generic P1 code; fixtures should
cover them as unsupported/forward-compatible cases.

## Risks

The current concatenation loses each source file's native location. Relative
links such as those in `entry.md` are therefore a separate validation target.
Images now resolve through the production `--resource-path=sop`; final rendered
link behavior still needs verification in the fixed PDF environment.
