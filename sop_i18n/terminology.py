"""Deterministic English technical-term candidate extraction."""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from typing import Any
from .glossary import Glossary
from .jobs import TranslationJob
from .placeholders import TOKEN_RE

STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "can", "for", "from", "if", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "use", "with", "your"}
WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]*")

def extract_term_candidates(jobs: list[TranslationJob], glossary: Glossary, *, min_count: int = 2, max_words: int = 4, limit: int = 300) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter(); examples: defaultdict[str, list[str]] = defaultdict(list)
    existing = {term.source.casefold() for term in glossary.terms}
    for job in jobs:
        text = TOKEN_RE.sub(" ", job.source_text)
        words = WORD.findall(text)
        for size in range(1, max_words + 1):
            for index in range(len(words) - size + 1):
                phrase = " ".join(words[index:index + size])
                normalized = phrase.casefold()
                if normalized in existing or len(normalized) < 3 or all(word.casefold() in STOP for word in words[index:index + size]): continue
                if size == 1 and (phrase.casefold() in STOP or phrase.islower() and len(phrase) < 5): continue
                counts[normalized] += 1
                if len(examples[normalized]) < 3: examples[normalized].append(job.job_id)
    result = [{"source": phrase, "count": count, "job_ids": examples[phrase]} for phrase, count in counts.items() if count >= min_count]
    return sorted(result, key=lambda item: (-item["count"], -len(item["source"].split()), item["source"]))[:limit]
