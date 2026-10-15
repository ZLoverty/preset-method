"""Deterministic extraction of natural-language AST segments."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import Issue, Segment
from .placeholders import encode_inlines

INLINE_BLOCKS = {"Header", "Para", "Plain"}
SUPPORTED_STRUCTURAL = {"Pandoc", "Meta", "BlockQuote", "BulletList", "OrderedList", "DefinitionList", "Table", "Figure", "Div", "CodeBlock", "RawBlock"}
KNOWN_NODES = INLINE_BLOCKS | SUPPORTED_STRUCTURAL | {"Str", "Space", "SoftBreak", "LineBreak", "Strong", "Emph", "Underline", "Strikeout", "Superscript", "Subscript", "SmallCaps", "Quoted", "Span", "Link", "Image", "Math", "Code", "RawInline", "Cite", "Note", "Caption", "TableHead", "TableBody", "TableFoot", "Row", "Cell", "AlignDefault", "AlignLeft", "AlignRight", "AlignCenter", "ColWidth", "ColWidthDefault", "Decimal", "Period"}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _inline_content(node: dict[str, Any]) -> list[dict[str, Any]] | None:
    if node.get("t") == "Header":
        content = node.get("c", [])
        return content[2] if len(content) > 2 and isinstance(content[2], list) else []
    if node.get("t") in {"Para", "Plain"}:
        return node.get("c", [])
    return None


def extract_segments(ast: dict[str, Any], *, source_file: str = "document") -> list[Segment]:
    segments, _ = extract_with_diagnostics(ast, source_file=source_file)
    return segments


def extract_with_diagnostics(ast: dict[str, Any], *, source_file: str = "document") -> tuple[list[Segment], list[Issue]]:
    segments: list[Segment] = []
    issues: list[Issue] = []
    current_context: list[str] = []

    def walk(value: Any, path: tuple[Any, ...]) -> None:
        nonlocal current_context
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, path + (index,))
            return
        if not isinstance(value, dict):
            return
        node_type = value.get("t")
        if node_type not in KNOWN_NODES and node_type:
            issues.append(Issue("UNSUPPORTED_NODE", "error", f"Unsupported AST node {node_type}", path))
            return
        if node_type == "Header":
            content = _inline_content(value) or []
            source_text, placeholders = encode_inlines(content)
            header_text = "".join(item.get("c", "") for item in content if item.get("t") == "Str")
            context = {"headings": list(current_context)}
            current_context.append(header_text)
            segments.append(_make_segment(source_file, path, node_type, source_text, context, placeholders))
            current_context.pop()
            return
        if node_type in {"Para", "Plain"}:
            content = _inline_content(value) or []
            source_text, placeholders = encode_inlines(content)
            if source_text.strip():
                segments.append(_make_segment(source_file, path, node_type, source_text, {"headings": list(current_context)}, placeholders))
            return
        if node_type in {"Math", "Code", "RawInline", "Cite", "Note"}:
            return
        if node_type in {"Str", "Space", "SoftBreak", "LineBreak", "Strong", "Emph", "Underline", "Strikeout", "Superscript", "Subscript", "SmallCaps", "Quoted", "Span", "Link", "Image"}:
            return
        if "blocks" in value and isinstance(value["blocks"], list):
            walk(value["blocks"], path + ("blocks",))
            return
        if isinstance(value.get("c"), (list, dict)):
            walk(value["c"], path + ("c",))

    walk(ast, ())
    return segments, issues


def _make_segment(source_file: str, path: tuple[Any, ...], node_type: str, source_text: str, context: dict[str, Any], placeholders: tuple[Any, ...]) -> Segment:
    occurrence = f"{source_file}:{node_type}:{'/'.join(map(str, path))}"
    return Segment(
        segment_id=f"seg-{_hash(occurrence)[:20]}",
        source_text=source_text,
        source_hash=_hash(source_text),
        ast_path=path,
        node_type=node_type,
        context=context,
        placeholders=placeholders,
    )


def segments_to_json(segments: list[Segment], diagnostics: list[Issue] | None = None) -> dict[str, Any]:
    return {"segments": [item.to_dict() for item in segments], "diagnostics": [item.to_dict() for item in diagnostics or []]}
