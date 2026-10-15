"""Atomic, conflict-safe import of validated P3 candidates into P2 drafts."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .candidates import TranslationCandidate
from .jobs import TranslationJob
from .memory import TranslationMemory
from .qa import validate_candidate
from .glossary import Glossary

@dataclass(frozen=True)
class ImportResult:
    imported: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    issues: tuple[dict[str, Any], ...] = ()

def import_drafts(memory: TranslationMemory, jobs: list[TranslationJob], candidates: list[TranslationCandidate], glossary: Glossary | None = None) -> ImportResult:
    by_job = {job.job_id: job for job in jobs}; selected = {candidate.job_id: candidate for candidate in candidates}
    problems: list[dict[str, Any]] = []
    for job_id, candidate in selected.items():
        job = by_job.get(job_id)
        if job is None: problems.append({"code": "UNKNOWN_JOB", "job_id": job_id}); continue
        problems.extend({**issue.to_dict(), "job_id": job_id} for issue in validate_candidate(candidate, job, glossary) if issue.severity == "error")
    if problems: return ImportResult(issues=tuple(problems))
    imported=[]; unchanged=[]; conflicts=[]; skipped=[]
    actions: list[tuple[str, TranslationJob, TranslationCandidate, Any | None]] = []
    for job_id in sorted(selected):
        job, candidate = by_job[job_id], selected[job_id]
        records = [item for item in memory.records if item.source_key == job.source_key and item.language == memory.language]
        record = next((item for item in records if item.occurrence_id in job.occurrence_ids), None) or next(iter(records), None)
        if record is None:
            actions.append(("create", job, candidate, None)); continue
        if record.status in {"approved", "rejected"}: skipped.append(record.record_id); continue
        if not record.target or record.target == candidate.target:
            actions.append(("update" if not record.target else "unchanged", job, candidate, record)); continue
        conflicts.append(record.record_id)
    if conflicts: return ImportResult(conflicts=tuple(conflicts), issues=({"code": "DRAFT_CONFLICT", "record_ids": list(conflicts)},))
    for action, job, candidate, record in actions:
        if action == "create":
            created = memory.create_draft(source_key=job.source_key, source=job.source_text, target=candidate.target, context={}, source_placeholders=job.source_placeholders, occurrence_id=job.segment_id)
            imported.append(created.record_id)
        elif action == "update":
            record.target = candidate.target; record.source_placeholders = job.source_placeholders; imported.append(record.record_id)
        else:
            unchanged.append(record.record_id)
    return ImportResult(tuple(imported), tuple(unchanged), tuple(conflicts), tuple(skipped), ())
