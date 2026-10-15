"""Semantic AST validation: structure/protected fields versus translatable text."""

from __future__ import annotations

from typing import Any

from .models import Issue, Segment, ValidationReport


def _under(path: tuple[Any, ...], roots: set[tuple[Any, ...]]) -> bool:
    return any(path[: len(root)] == root for root in roots)


def _allowed_view(value: Any) -> Any:
    """Normalize translatable text runs while retaining formatting/protected nodes."""
    if isinstance(value, list):
        result: list[Any] = []
        for item in value:
            viewed = _allowed_view(item)
            if viewed == ("text",) and result and result[-1] == ("text",):
                continue
            result.append(viewed)
        return result
    if isinstance(value, dict):
        node_type = value.get("t")
        if node_type in {"Str", "Space", "SoftBreak", "LineBreak"}:
            return ("text",)
        if node_type in {"Math", "Code", "RawInline", "RawBlock", "CodeBlock"}:
            return value
        if node_type == "Link":
            content = value.get("c", [[], [], ["", ""]])
            attr, label, target = content[0], content[1], content[2]
            return {"t": "Link", "attr": attr, "target": target, "label": _allowed_view(label)}
        if node_type == "Image":
            content = value.get("c", [[], [], ["", ""]])
            attr, alt, target = content[0], content[1], content[2]
            return {"t": "Image", "attr": attr, "target": target, "alt": _allowed_view(alt)}
        if node_type == "Quoted":
            quote_type, children = value.get("c", [None, []])
            return {"t": node_type, "quote_type": quote_type, "c": _allowed_view(children)}
        if node_type in {"Strong", "Emph", "Underline", "Strikeout", "Superscript", "Subscript", "SmallCaps"}:
            return {"t": node_type, "c": _allowed_view(value.get("c", []))}
        if node_type == "Span":
            attr, children = value.get("c", [[], []])
            return {"t": node_type, "attr": attr, "c": _allowed_view(children)}
    return value


def _view(value: Any, path: tuple[Any, ...], allowed: set[tuple[Any, ...]]) -> Any:
    if path in allowed:
        return _allowed_view(value)
    if isinstance(value, list):
        return [_view(item, path + (index,), allowed) for index, item in enumerate(value)]
    if isinstance(value, dict):
        node_type = value.get("t")
        if node_type == "Str" and _under(path, allowed):
            return {"t": "Str", "c": "<translated>"}
        if node_type == "Space" and _under(path, allowed):
            return {"t": "Space"}
        if node_type in {"SoftBreak", "LineBreak"} and _under(path, allowed):
            return {"t": node_type}
        if node_type in {"Math", "Code", "RawInline", "RawBlock", "CodeBlock"}:
            return value
        return {key: _view(child, path + (key,), allowed) for key, child in value.items()}
    return value


def validate_translation(original_ast: dict[str, Any], translated_ast: dict[str, Any], segments: list[Segment]) -> ValidationReport:
    allowed = {
        segment.ast_path + (("c", 2) if segment.node_type == "Header" else ("c",))
        for segment in segments
    }
    issues: list[Issue] = []
    if _view(original_ast, (), allowed) != _view(translated_ast, (), allowed):
        issues.append(Issue("STRUCTURE_CHANGED", "error", "Immutable AST structure or protected content changed"))
    for segment in segments:
        try:
            original_node = original_ast
            translated_node = translated_ast
            for item in segment.ast_path:
                original_node = original_node[item]
                translated_node = translated_node[item]
            if original_node.get("t") != translated_node.get("t"):
                issues.append(Issue("NODE_TYPE_CHANGED", "error", "Segment node type changed", segment.ast_path, segment.segment_id))
        except (KeyError, IndexError, TypeError):
            issues.append(Issue("SEGMENT_PATH_MISSING", "error", "Segment AST path is missing", segment.ast_path, segment.segment_id))
    return ValidationReport(tuple(issues))
