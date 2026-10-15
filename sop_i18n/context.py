"""Bounded, read-only context extraction for translation jobs."""
from __future__ import annotations

from typing import Any

from .models import Segment


def _inline_text(items: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for item in items:
        if item.get("t") == "Str":
            out.append(str(item.get("c", "")))
        elif item.get("t") in {"Space", "SoftBreak", "LineBreak"}:
            out.append(" ")
        elif isinstance(item.get("c"), list) and item.get("t") not in {"Code", "Math", "RawInline"}:
            nested = item["c"][-1] if item["t"] == "Span" and item["c"] else item["c"]
            if isinstance(nested, list):
                out.append(_inline_text(nested))
    return "".join(out).strip()


def extract_context(ast: dict[str, Any], segments: list[Segment], *, max_neighbor_chars: int = 500) -> dict[str, dict[str, Any]]:
    """Return context keyed by segment ID, without reading outside ``ast``."""
    by_path = {segment.ast_path: segment for segment in segments}
    ordered: list[tuple[Segment, str, list[str]]] = []
    headings: list[str] = []

    def walk(value: Any, path: tuple[Any, ...]) -> None:
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, path + (index,))
            return
        if not isinstance(value, dict):
            return
        node = value.get("t")
        if node == "Header":
            level = int(value.get("c", [1])[0]) if value.get("c") else 1
            title = _inline_text(value.get("c", [None, None, []])[2])
            headings[:] = headings[: max(0, level - 1)]
            headings.append(title)
            segment = by_path.get(path)
            if segment:
                ordered.append((segment, segment.source_text, list(headings[:-1])))
            return
        if node in {"Para", "Plain"}:
            segment = by_path.get(path)
            if segment:
                ordered.append((segment, segment.source_text, list(headings)))
            return
        if "blocks" in value and isinstance(value["blocks"], list):
            walk(value["blocks"], path + ("blocks",))
        elif isinstance(value.get("c"), (list, dict)):
            walk(value["c"], path + ("c",))

    walk(ast, ())
    result: dict[str, dict[str, Any]] = {}
    paragraph_positions = [i for i, item in enumerate(ordered) if item[0].node_type in {"Para", "Plain"}]
    for index, (segment, source, heading_path) in enumerate(ordered):
        previous = next((ordered[i][1] for i in range(index - 1, -1, -1) if ordered[i][0].node_type in {"Para", "Plain"}), None)
        following = next((ordered[i][1] for i in range(index + 1, len(ordered)) if ordered[i][0].node_type in {"Para", "Plain"}), None)
        result[segment.segment_id] = {
            "document": "ast",
            "headings": heading_path,
            "previous_text": previous[:max_neighbor_chars] if previous else None,
            "next_text": following[:max_neighbor_chars] if following else None,
        }
    return result
