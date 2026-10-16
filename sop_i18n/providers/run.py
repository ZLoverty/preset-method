"""Resumable sequential OpenAI batch execution."""
from __future__ import annotations
import hashlib, json, os, tempfile, time
from pathlib import Path
from typing import Any
from ..candidates import candidates_payload, load_candidates
from ..jobs import TranslationJob, jobs_payload
from ..qa import validate_candidate
from ..glossary import Glossary
from .openai import OpenAIProvider, ProviderError

def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def partition_jobs(jobs: list[TranslationJob], *, max_jobs: int = 20, max_request_bytes: int = 100_000) -> list[list[TranslationJob]]:
    if max_jobs < 1 or max_request_bytes < 1: raise ValueError("batch limits must be positive")
    result=[]; current=[]; size=2
    for job in jobs:
        encoded=len(json.dumps(job.to_dict(), ensure_ascii=False).encode("utf-8"))
        if encoded + 2 > max_request_bytes: raise ProviderError(f"Job {job.job_id} exceeds request-size limit", retryable=False)
        if current and (len(current) >= max_jobs or size + encoded > max_request_bytes): result.append(current); current=[]; size=2
        current.append(job); size += encoded + 1
    if current: result.append(current)
    return result

def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle: json.dump(value, handle, ensure_ascii=False, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)

def estimate_cost(usage: dict[str, Any], pricing: dict[str, float] | None) -> float | None:
    if not pricing: return None
    return usage.get("input_tokens", 0) / 1_000_000 * pricing.get("input_per_million_tokens_usd", 0.0) + usage.get("output_tokens", 0) / 1_000_000 * pricing.get("output_per_million_tokens_usd", 0.0)

def run_resumable(provider: OpenAIProvider, jobs: list[TranslationJob], *, run_dir: Path, glossary: Glossary, max_jobs: int = 20, max_request_bytes: int = 100_000, pricing: dict[str, float] | None = None, max_cost: float | None = None, resume: bool = True) -> dict[str, Any]:
    batches = partition_jobs(jobs, max_jobs=max_jobs, max_request_bytes=max_request_bytes)
    prompt_hash = _hash(provider.prompt_path.read_text(encoding="utf-8")); manifest = {"schema_version": 1, "provider": provider.name, "model": provider.model, "prompt_version": provider.prompt_version, "prompt_hash": prompt_hash, "policy_version": "p3-zh-CN-v1", "jobs_hash": _hash(jobs_payload(jobs)), "max_jobs": max_jobs, "max_request_bytes": max_request_bytes}
    manifest_path = run_dir / "manifest.json"
    if resume and manifest_path.exists() and json.loads(manifest_path.read_text(encoding="utf-8")) != manifest: raise ProviderError("Resume configuration does not match existing run", retryable=False)
    _atomic_json(manifest_path, manifest)
    batch_dir = run_dir / "batches"; all_candidates=[]; skipped=0
    for index, batch in enumerate(batches, 1):
        path = batch_dir / f"batch-{index:04d}.json"
        expected = {job.job_id for job in batch}
        if resume and path.exists():
            saved = load_candidates(json.loads(path.read_text(encoding="utf-8")))
            if {item.job_id for item in saved} == expected:
                all_candidates.extend(saved); skipped += 1; continue
        estimated = estimate_cost(provider.usage.to_dict(), pricing)
        if max_cost is not None and estimated is not None and estimated >= max_cost: raise ProviderError("Configured translation budget would be exceeded", retryable=False)
        candidates = provider.translate(batch)
        for candidate in candidates:
            issues = validate_candidate(candidate, next(job for job in batch if job.job_id == candidate.job_id), glossary)
            candidate.validation = {"status": "pass" if not any(item.severity == "error" for item in issues) else "fail", "issues": [item.to_dict() for item in issues]}
        _atomic_json(path, candidates_payload(candidates)); all_candidates.extend(candidates)
    all_candidates.sort(key=lambda item: item.job_id)
    _atomic_json(run_dir / "candidates.json", candidates_payload(all_candidates))
    usage = provider.usage.to_dict(); report = {"status": "completed", "batches": len(batches), "batches_reused": skipped, "candidates": len(all_candidates), "usage": usage, "estimated_cost_usd": estimate_cost(usage, pricing)}
    _atomic_json(run_dir / "report.json", report)
    return report
