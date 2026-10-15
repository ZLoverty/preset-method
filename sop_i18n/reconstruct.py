"""Atomic application of translated segment strings to Pandoc ASTs."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .models import Issue, Segment
from .placeholders import decode_translation


class TranslationError(ValueError):
    """Raised when a translation cannot be safely reconstructed."""

    def __init__(self, issues: list[Issue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.message for issue in issues))


def _get(root: Any, path: tuple[Any, ...]) -> Any:
    value = root
    for item in path:
        value = value[item]
    return value


def _set(root: Any, path: tuple[Any, ...], value: Any) -> None:
    parent = _get(root, path[:-1])
    parent[path[-1]] = value


def apply_translations(ast: dict[str, Any], segments: list[Segment], translations: Mapping[str, str]) -> dict[str, Any]:
    expected = {segment.segment_id for segment in segments}
    supplied = set(translations)
    issues: list[Issue] = []
    for segment in segments:
        if segment.segment_id not in translations:
            issues.append(Issue("MISSING_TRANSLATION", "error", "Missing translation", segment.ast_path, segment.segment_id))
    for unknown in sorted(supplied - expected):
        issues.append(Issue("UNKNOWN_SEGMENT", "error", f"Unknown segment {unknown}"))
    prepared: list[tuple[tuple[Any, ...], list[dict[str, Any]]]] = []
    for segment in segments:
        if segment.segment_id not in translations:
            continue
        translated, decode_issues = decode_translation(translations[segment.segment_id], segment.placeholders)
        if decode_issues or translated is None:
            issues.extend(Issue(item.code, item.severity, item.message, segment.ast_path, segment.segment_id) for item in decode_issues)
        else:
            prepared.append((segment.ast_path + ("c", 2) if segment.node_type == "Header" else segment.ast_path + ("c",), translated))
    if issues:
        raise TranslationError(issues)
    result = copy.deepcopy(ast)
    for path, value in prepared:
        _set(result, path, value)
    return result
