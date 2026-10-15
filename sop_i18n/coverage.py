"""Coverage and review-state summaries."""

from __future__ import annotations

from collections import Counter

from .matching import SyncReport


def coverage(report: SyncReport) -> dict[str, int]:
    counts = Counter(item.status for item in report.occurrences)
    return {key: counts.get(key, 0) for key in ("MATCHED", "DRAFT", "MISSING", "CHANGED", "AMBIGUOUS", "OBSOLETE")}
