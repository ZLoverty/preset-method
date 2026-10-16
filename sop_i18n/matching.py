"""Deterministic TM synchronization and strict translation resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import source_key
from .memory import TranslationMemory, TranslationRecord
from .models import Issue, Segment
from .placeholders import rebind_translation, validate_placeholder_tokens


STATUSES = {"MATCHED", "DRAFT", "MISSING", "CHANGED", "AMBIGUOUS", "OBSOLETE"}


@dataclass(frozen=True)
class OccurrenceMatch:
    segment_id: str
    source_key: str
    status: str
    record_ids: tuple[str, ...] = ()
    reference_record_id: str | None = None


@dataclass(frozen=True)
class SyncReport:
    occurrences: tuple[OccurrenceMatch, ...]
    obsolete_record_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"occurrences": [item.__dict__ for item in self.occurrences], "obsolete_record_ids": list(self.obsolete_record_ids)}


def synchronize(segments: list[Segment], memory: TranslationMemory) -> SyncReport:
    current_keys = {source_key(segment) for segment in segments}
    occurrences: list[OccurrenceMatch] = []
    referenced: set[str] = set()
    for segment in segments:
        key = source_key(segment)
        candidates = memory.candidates(key, segment.context, memory.language)
        if len(candidates) > 1:
            status = "AMBIGUOUS"
        elif candidates:
            status = "MATCHED" if candidates[0].status == "approved" and candidates[0].target else "DRAFT"
        else:
            changed = [record for record in memory.records if record.occurrence_id == segment.segment_id and record.source_key != key]
            status = "CHANGED" if changed else "MISSING"
            candidates = changed
        referenced.update(record.record_id for record in candidates)
        occurrences.append(OccurrenceMatch(segment.segment_id, key, status, tuple(record.record_id for record in candidates), candidates[0].record_id if len(candidates) == 1 else None))
    obsolete = tuple(sorted(record.record_id for record in memory.records if record.record_id not in referenced and record.source_key not in current_keys))
    return SyncReport(tuple(occurrences), obsolete)


def resolve(segments: list[Segment], memory: TranslationMemory, *, strict: bool = True) -> tuple[dict[str, str], list[Issue]]:
    translations: dict[str, str] = {}
    issues: list[Issue] = []
    for segment in segments:
        key = source_key(segment)
        candidates = memory.candidates(key, segment.context, memory.language)
        # Occurrence-specific records take precedence. Repeated source text
        # may legitimately have two approved records with different targets;
        # that is only ambiguous when there is no exact occurrence match.
        exact = [record for record in candidates if record.occurrence_id == segment.segment_id]
        pool = exact or candidates
        approved = [record for record in pool if record.status == "approved" and record.target]
        if len(approved) != 1:
            code = "MISSING_TRANSLATION" if not approved else "AMBIGUOUS_TRANSLATION"
            issues.append(Issue(code, "error", f"Expected one approved translation, found {len(approved)}", segment.ast_path, segment.segment_id))
            if not strict and not approved:
                translations[segment.segment_id] = segment.source_text
            continue
        record = approved[0]
        rebound_target, rebinding_issues = rebind_translation(
            record.target, record.source_placeholders, segment.placeholders
        )
        if rebinding_issues:
            issues.extend(Issue(item.code, "error", item.message, segment.ast_path, segment.segment_id) for item in rebinding_issues)
            continue
        placeholder_issues = validate_placeholder_tokens(rebound_target, segment.placeholders)
        if placeholder_issues:
            issues.extend(Issue(item.code, "error", item.message, segment.ast_path, segment.segment_id) for item in placeholder_issues)
            continue
        translations[segment.segment_id] = rebound_target
    return translations, issues
