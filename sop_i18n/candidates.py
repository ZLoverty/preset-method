"""Strict provider response and candidate artifacts."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from typing import Any
from .jobs import TranslationJob, SCHEMA_VERSION

@dataclass
class TranslationCandidate:
    job_id: str
    source_key: str
    language: str
    target: str
    provenance: dict[str, Any]
    validation: dict[str, Any] | None = None
    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "job_id": self.job_id, "source_key": self.source_key, "language": self.language, "target": self.target, "provenance": self.provenance, "validation": self.validation or {"status": "pending", "issues": []}}

def parse_response(payload: dict[str, Any], jobs: list[TranslationJob], *, provider="offline", model=None, prompt_version="zh-CN-v1", glossary_hash="") -> list[TranslationCandidate]:
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("translations"), list):
        raise ValueError("Invalid translation response schema")
    by_id = {job.job_id: job for job in jobs}; seen: set[str] = set(); result = []
    for item in payload["translations"]:
        if set(item) != {"job_id", "target"} or not isinstance(item["target"], str):
            raise ValueError("Translation responses require exactly job_id and target")
        job_id = item["job_id"]
        if job_id not in by_id: raise ValueError(f"Unknown job ID: {job_id}")
        if job_id in seen: raise ValueError(f"Duplicate job ID: {job_id}")
        seen.add(job_id); job = by_id[job_id]
        result.append(TranslationCandidate(job_id, job.source_key, job.language, item["target"], {"provider": provider, "model": model, "prompt_version": prompt_version, "glossary_hash": glossary_hash}))
    missing = sorted(set(by_id) - seen)
    if missing: raise ValueError("Missing translation responses: " + ", ".join(missing))
    return sorted(result, key=lambda item: item.job_id)

def candidates_payload(candidates: list[TranslationCandidate]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "candidates": [item.to_dict() for item in candidates]}

def load_candidates(payload: dict[str, Any]) -> list[TranslationCandidate]:
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("candidates"), list): raise ValueError("Invalid candidate artifact")
    result=[]
    for item in payload["candidates"]:
        if item.get("schema_version") != SCHEMA_VERSION: raise ValueError("Unsupported candidate schema version")
        result.append(TranslationCandidate(item["job_id"], item["source_key"], item["language"], item["target"], item["provenance"], item.get("validation")))
    return result
