# 05 AST round-trip feasibility

## Test method

On a temporary combined input representing the intended 10-document PDF order:

```text
Markdown --reader extensions--> Pandoc JSON AST
JSON AST --> Markdown --> same reader --> Pandoc JSON AST
```

The source files and repository build configuration were not changed. The
first Markdown-to-JSON operation exited 0 and produced an AST containing 187
top-level blocks.

## Result

The second parse also contained 187 top-level blocks, but the JSON objects were
not exactly equal. Pandoc's Markdown writer normalized table layout,
whitespace and other serialization details. Therefore:

- typed structure survived this basic test;
- object/byte equality did not;
- rendered-document equivalence was **NOT VERIFIED** because XeLaTeX failed
  during MiKTeX initialization;
- filter-dependent behavior is not applicable to the current repository: no
  custom Lua or external filters were found.

## Compatibility assessment

The AST is suitable for a controlled translator if it operates on typed blocks
and inlines. It is not safe to translate raw Markdown by regex or to translate
each `Str` independently. Tables, figures, math, raw TeX, links and inline
code require protected-field checks.

## Recommended strategy

1. Resolve the source-root and build reproducibility blockers.
2. Assemble the exact production source set.
3. Parse once with the production reader flags.
4. Extract logical segments from supported block types, recording a path to each
   AST node and an immutable structural fingerprint.
5. Reconstruct only translated inline text and captions, preserving all
   protected nodes.
6. Validate structure and protected fingerprints before invoking Pandoc's PDF
   writer.

Do not claim final PDF equivalence until a fixed XeLaTeX/font environment can
render both baseline and reconstructed documents.
