"""Git-friendly JSON translation memory with atomic persistence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
STATUSES = {"draft", "approved", "rejected"}
TRANSITIONS = {
    "draft": {"approved", "rejected"},
    "approved": {"draft"},
    "rejected": {"draft"},
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_id(language: str, source_key: str, context: dict[str, Any], target: str) -> str:
    raw = json.dumps([language, source_key, context, target], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "tm_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


@dataclass
class TranslationRecord:
    record_id: str
    language: str
    source_key: str
    source: str
    target: str
    status: str
    context: dict[str, Any]
    canonicalization_version: int = 1
    source_schema_version: int = 1
    occurrence_id: str | None = None
    source_placeholders: list[dict[str, Any]] | None = None
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)
    reviewed_at: str | None = None
    reviewer: str | None = None
    review_comment: str | None = None

    def validate(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"Invalid translation status: {self.status}")
        if not self.record_id or not self.language or not self.source_key:
            raise ValueError("record_id, language and source_key are required")
        if not isinstance(self.context, dict):
            raise ValueError("context must be an object")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "record_id": self.record_id,
            "language": self.language,
            "source_key": self.source_key,
            "source": self.source,
            "target": self.target,
            "status": self.status,
            "context": self.context,
            "canonicalization_version": self.canonicalization_version,
            "source_schema_version": self.source_schema_version,
            "occurrence_id": self.occurrence_id,
            "source_placeholders": self.source_placeholders,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reviewed_at": self.reviewed_at,
            "reviewer": self.reviewer,
            "review_comment": self.review_comment,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TranslationRecord":
        record = cls(**{key: value[key] for key in ("record_id", "language", "source_key", "source", "target", "status", "context")},
            canonicalization_version=value.get("canonicalization_version", 1),
            source_schema_version=value.get("source_schema_version", 1),
            occurrence_id=value.get("occurrence_id"), created_at=value.get("created_at", now_utc()),
            updated_at=value.get("updated_at", now_utc()), reviewed_at=value.get("reviewed_at"),
            reviewer=value.get("reviewer"), review_comment=value.get("review_comment"),
            source_placeholders=value.get("source_placeholders"))
        record.validate()
        return record


class TranslationMemory:
    def __init__(self, language: str = "zh-CN", records: Iterable[TranslationRecord] = ()) -> None:
        self.language = language
        self.records = list(records)
        for record in self.records:
            record.validate()

    @classmethod
    def empty(cls, language: str = "zh-CN") -> "TranslationMemory":
        return cls(language)

    @classmethod
    def load(cls, path: Path) -> "TranslationMemory":
        if not path.exists():
            return cls.empty()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Unsupported TM schema version: {payload.get('schema_version')}")
        language = payload.get("language", "zh-CN")
        records = [TranslationRecord.from_dict(item) for item in payload.get("records", [])]
        return cls(language, records)

    def to_dict(self) -> dict[str, Any]:
        records = sorted((record.to_dict() for record in self.records), key=lambda item: item["record_id"])
        return {"schema_version": SCHEMA_VERSION, "language": self.language, "records": records}

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add(self, record: TranslationRecord) -> TranslationRecord:
        record.validate()
        if any(item.record_id == record.record_id for item in self.records):
            raise ValueError(f"Record already exists: {record.record_id}")
        self.records.append(record)
        return record

    def find(self, record_id: str) -> TranslationRecord:
        for record in self.records:
            if record.record_id == record_id:
                return record
        raise KeyError(record_id)

    def candidates(self, source_key: str, context: dict[str, Any] | None = None, language: str | None = None) -> list[TranslationRecord]:
        context = context or {}
        return [record for record in self.records if record.source_key == source_key and (language is None or record.language == language) and (record.context == context or not record.context)]

    def transition(self, record_id: str, status: str, *, reviewer: str | None = None, comment: str | None = None) -> TranslationRecord:
        record = self.find(record_id)
        if status not in TRANSITIONS.get(record.status, set()):
            raise ValueError(f"Illegal translation status transition: {record.status} -> {status}")
        record.status = status
        record.updated_at = now_utc()
        record.reviewed_at = now_utc() if status in {"approved", "rejected"} else None
        record.reviewer = reviewer
        record.review_comment = comment
        return record

    def update_target(self, record_id: str, target: str) -> TranslationRecord:
        record = self.find(record_id)
        record.target = target
        record.updated_at = now_utc()
        if record.status == "approved":
            record.status = "draft"
            record.reviewed_at = None
            record.reviewer = None
        return record

    def create_draft(self, *, source_key: str, source: str, target: str = "", context: dict[str, Any] | None = None, occurrence_id: str | None = None, source_placeholders: list[dict[str, Any]] | None = None, language: str | None = None, canonicalization_version: int = 1) -> TranslationRecord:
        context = context or {}
        language = language or self.language
        record = TranslationRecord(_stable_id(language, source_key, context, target), language, source_key, source, target, "draft", copy.deepcopy(context), canonicalization_version=canonicalization_version, occurrence_id=occurrence_id, source_placeholders=copy.deepcopy(source_placeholders))
        existing = next((item for item in self.records if item.record_id == record.record_id), None)
        return existing or self.add(record)
