"""Deterministic translation job planning and serialization."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .canonical import source_key
from .glossary import Glossary
from .matching import synchronize
from .memory import TranslationMemory
from .models import Segment

SCHEMA_VERSION = 1
POLICY_VERSION = "p3-zh-CN-v1"


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class TranslationJob:
    job_id: str
    language: str
    source_key: str
    segment_id: str
    source_text: str
    context: dict[str, Any]
    glossary: list[dict[str, Any]]
    source_placeholders: list[dict[str, Any]]
    occurrence_ids: list[str] = field(default_factory=list)
    previous_translation: str | None = None
    prompt_version: str = POLICY_VERSION
    node_type: str = "Para"

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, **self.__dict__}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TranslationJob":
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported translation job schema version")
        allowed = {"job_id", "language", "source_key", "segment_id", "source_text", "context", "glossary", "source_placeholders", "occurrence_ids", "previous_translation", "prompt_version", "node_type"}
        if set(value) - ({"schema_version"} | allowed):
            raise ValueError("Unknown translation job fields")
        return cls(**{key: value[key] for key in allowed if key in value})


def _terms(glossary: Glossary, source: str) -> list[dict[str, Any]]:
    natural = glossary._natural_text(source).casefold()
    return [{"id": term.term_id, "source": term.source, "target": term.target, "alternatives": list(term.alternatives), "severity": term.severity} for term in glossary.terms if term.source.casefold() in natural]


def plan_jobs(segments: list[Segment], memory: TranslationMemory, glossary: Glossary, *, contexts: dict[str, dict[str, Any]] | None = None) -> list[TranslationJob]:
    contexts = contexts or {}
    report = synchronize(segments, memory)
    by_id = {segment.segment_id: segment for segment in segments}
    groups: dict[str, TranslationJob] = {}
    for occurrence in report.occurrences:
        if occurrence.status not in {"MISSING", "CHANGED"}:
            continue
        segment = by_id[occurrence.segment_id]
        context = contexts.get(segment.segment_id, segment.context)
        relevant = _terms(glossary, segment.source_text)
        identity = {"language": memory.language, "source_key": occurrence.source_key, "context": context, "glossary": relevant, "policy": POLICY_VERSION}
        job_id = "job_" + _hash(identity).split(":", 1)[1][:20]
        if job_id in groups:
            groups[job_id].occurrence_ids.append(segment.segment_id)
            continue
        candidates = memory.candidates(occurrence.source_key, segment.context, memory.language)
        previous = next((item.target for item in candidates if item.status == "approved" and item.target), None)
        groups[job_id] = TranslationJob(job_id, memory.language, occurrence.source_key, segment.segment_id, segment.source_text, context, relevant, [item.to_dict() for item in segment.placeholders], [segment.segment_id], previous, node_type=segment.node_type)
    return [groups[key] for key in sorted(groups)]


def jobs_payload(jobs: list[TranslationJob]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "language": jobs[0].language if jobs else "zh-CN", "policy_version": POLICY_VERSION, "jobs": [job.to_dict() for job in jobs]}


def load_jobs(payload: dict[str, Any]) -> list[TranslationJob]:
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("jobs"), list):
        raise ValueError("Invalid translation jobs artifact")
    return [TranslationJob.from_dict(item) for item in payload["jobs"]]
