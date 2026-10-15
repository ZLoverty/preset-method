"""Command-line interface for inspection, extraction, reconstruction and validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ast_io import load_json, parse_markdown, parse_ordered_markdown, save_json
from .extract import extract_with_diagnostics, segments_to_json
from .models import Segment
from .reconstruct import TranslationError, apply_translations
from .validate import validate_translation


def _ast_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ast", type=Path)
    group.add_argument("--markdown", type=Path)
    group.add_argument("--order-file", type=Path)


def _load(args: argparse.Namespace) -> dict[str, Any]:
    if args.ast:
        return load_json(args.ast)
    if args.markdown:
        return parse_markdown(args.markdown)
    return parse_ordered_markdown(args.order_file)


def _extract(args: argparse.Namespace) -> int:
    ast = _load(args)
    segments, diagnostics = extract_with_diagnostics(ast, source_file=str(args.ast or args.markdown or args.order_file))
    payload = segments_to_json(segments, diagnostics)
    if args.out:
        if args.out.exists() and not args.force:
            raise RuntimeError(f"Refusing to overwrite existing file: {args.out}")
        save_json(args.out, payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def _inspect(args: argparse.Namespace) -> int:
    ast = _load(args)
    segments, diagnostics = extract_with_diagnostics(ast, source_file=str(args.ast or args.markdown or args.order_file))
    counts: dict[str, int] = {}
    protected = 0
    for segment in segments:
        counts[segment.node_type] = counts.get(segment.node_type, 0) + 1
        protected += len(segment.placeholders)
    print(json.dumps({"segments": counts, "total_segments": len(segments), "protected_elements": protected, "diagnostics": [item.to_dict() for item in diagnostics]}, ensure_ascii=False, indent=2))
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def _rebuild(args: argparse.Namespace) -> int:
    ast = load_json(args.ast)
    payload = load_json(args.segments)
    segments = [Segment.from_dict(item) for item in payload["segments"]]
    translations = load_json(args.translations)
    try:
        rebuilt = apply_translations(ast, segments, translations)
    except TranslationError as error:
        print(json.dumps({"ok": False, "issues": [item.to_dict() for item in error.issues]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    if args.out.exists() and not args.force:
        print(f"Refusing to overwrite existing file: {args.out}", file=sys.stderr)
        return 2
    save_json(args.out, rebuilt)
    return 0


def _validate(args: argparse.Namespace) -> int:
    original = load_json(args.original)
    translated = load_json(args.translated)
    payload = load_json(args.segments)
    segments = [Segment.from_dict(item) for item in payload["segments"]]
    report = validate_translation(original, translated, segments)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m sop_i18n")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="summarize AST structures and extracted segments")
    _ast_args(inspect)
    inspect.set_defaults(func=_inspect)
    extract = sub.add_parser("extract", help="extract translation segments as JSON")
    _ast_args(extract)
    extract.add_argument("--out", type=Path)
    extract.add_argument("--force", action="store_true")
    extract.set_defaults(func=_extract)
    rebuild = sub.add_parser("rebuild", help="apply translations to an AST")
    rebuild.add_argument("--ast", type=Path, required=True)
    rebuild.add_argument("--segments", type=Path, required=True)
    rebuild.add_argument("--translations", type=Path, required=True)
    rebuild.add_argument("--out", type=Path, required=True)
    rebuild.add_argument("--force", action="store_true")
    rebuild.set_defaults(func=_rebuild)
    validate = sub.add_parser("validate", help="validate structural and protected invariants")
    validate.add_argument("--original", type=Path, required=True)
    validate.add_argument("--translated", type=Path, required=True)
    validate.add_argument("--segments", type=Path, required=True)
    validate.set_defaults(func=_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
