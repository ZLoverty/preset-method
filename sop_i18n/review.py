"""Review lifecycle operations for translation memory records."""

from __future__ import annotations

from typing import Any

from .canonical import source_key
from .glossary import Glossary
from .memory import TranslationMemory
from .models import Issue, Segment
from .placeholders import decode_translation


def approve(memory: TranslationMemory, record_id: str, segment: Segment, *, reviewer: str, glossary: Glossary | None = None, comment: str | None = None) -> list[Issue]:
    record = memory.find(record_id)
    issues: list[Issue] = []
    if record.source_key != source_key(segment):
        issues.append(Issue("STALE_SOURCE_KEY", "error", "Translation record no longer matches the segment", segment.ast_path, segment.segment_id))
    if not record.target:
        issues.append(Issue("EMPTY_TRANSLATION", "error", "Cannot approve an empty translation", segment.ast_path, segment.segment_id))
    _, placeholder_issues = decode_translation(record.target, segment.placeholders)
    issues.extend(placeholder_issues)
    if glossary:
        issues.extend(glossary.check(segment, record.target))
    if any(issue.severity == "error" for issue in issues):
        return issues
    record.source_placeholders = [item.to_dict() for item in segment.placeholders]
    memory.transition(record_id, "approved", reviewer=reviewer, comment=comment)
    return issues


def reject(memory: TranslationMemory, record_id: str, *, reviewer: str, comment: str | None = None) -> None:
    memory.transition(record_id, "rejected", reviewer=reviewer, comment=comment)


def reopen(memory: TranslationMemory, record_id: str, *, reviewer: str, comment: str | None = None) -> None:
    memory.transition(record_id, "draft", reviewer=reviewer, comment=comment)
