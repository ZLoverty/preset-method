"""Provider-neutral offline translation orchestration helpers."""
from __future__ import annotations
from typing import Protocol
from .jobs import TranslationJob
from .candidates import TranslationCandidate

class TranslationProvider(Protocol):
    def translate(self, jobs: list[TranslationJob]) -> list[TranslationCandidate]: ...

class OfflineProvider:
    """Exports jobs; completed responses are parsed by ``candidates``."""
    name = "offline"
    def translate(self, jobs: list[TranslationJob]) -> list[TranslationCandidate]:
        raise RuntimeError("OfflineProvider does not call an AI service; submit a structured response artifact")

def batches(jobs: list[TranslationJob], max_jobs: int = 20) -> list[list[TranslationJob]]:
    if max_jobs < 1: raise ValueError("max_jobs must be positive")
    return [jobs[index:index + max_jobs] for index in range(0, len(jobs), max_jobs)]


def translate_batches(provider: TranslationProvider, jobs: list[TranslationJob], *, max_jobs: int = 20, retries: int = 0) -> list[TranslationCandidate]:
    """Run stable batches with bounded retries for provider failures.

    The provider owns no TM state. A caller can persist each returned batch as
    an artifact before proceeding, which makes interrupted runs resumable.
    Semantic candidate QA is deliberately outside this retry loop.
    """
    if retries < 0: raise ValueError("retries must be non-negative")
    result: list[TranslationCandidate] = []
    for batch in batches(jobs, max_jobs):
        last: Exception | None = None
        for _ in range(retries + 1):
            try:
                result.extend(provider.translate(batch))
                last = None
                break
            except Exception as exc:  # provider boundary: bounded and re-raised
                last = exc
        if last is not None:
            raise last
    return result
