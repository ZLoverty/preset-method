"""Local candidate QA; provider claims are never trusted."""
from __future__ import annotations
import re
from .models import Issue, Segment, Placeholder
from .placeholders import TOKEN_RE, decode_translation
from .glossary import Glossary
from .candidates import TranslationCandidate

NUMBER_RE = re.compile(
    r"(?<![A-Za-z])\d+(?:\.\d+)?\s*(?:%|°\s*[CF]|mm/s|mm|cm|kg|ms|分钟|minutes?|min|m|秒|seconds?|s|rpm|Hz|V|A)(?![A-Za-z])"
    r"|(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])",
    re.I,
)

def _numbers(text: str) -> list[str]:
    # Placeholder indices such as fmt:2 must never be treated as source
    # numbers or units (the P1 token syntax itself contains letters).
    natural = TOKEN_RE.sub(" ", text)
    values = []
    for item in NUMBER_RE.findall(natural):
        value = re.sub(r"\s+", "", item).casefold()
        value = value.replace("秒", "s").replace("分钟", "min").replace("seconds", "s").replace("second", "s").replace("minutes", "min").replace("minute", "min")
        values.append(value)
    return values

def validate_candidate(candidate: TranslationCandidate, job, glossary: Glossary | None = None) -> list[Issue]:
    segment = Segment(job.segment_id, job.source_text, "", (), "Para", job.context, tuple(Placeholder.from_dict(item) for item in job.source_placeholders))
    issues: list[Issue] = []
    if candidate.language != job.language: issues.append(Issue("LANGUAGE_MISMATCH", "error", "Candidate language does not match job"))
    if candidate.source_key != job.source_key: issues.append(Issue("SOURCE_KEY_MISMATCH", "error", "Candidate source key does not match job"))
    if not candidate.target.strip(): issues.append(Issue("EMPTY_TRANSLATION", "error", "Candidate target is empty"))
    _, structural = decode_translation(candidate.target, segment.placeholders); issues.extend(structural)
    source_numbers = _numbers(segment.source_text); target_numbers = _numbers(candidate.target)
    # Translation can legitimately reorder or repeat a quantity while keeping
    # the same numeric/unit facts (for example “100% or close to 100%”).
    if set(source_numbers) != set(target_numbers):
        issues.append(Issue("NUMBER_UNIT_MISMATCH", "error", f"Source numeric tokens {source_numbers} differ from target {target_numbers}"))
    if "```" in candidate.target or candidate.target.strip().lower().startswith(("translation:", "note:", "explanation:")):
        issues.append(Issue("OUTPUT_HYGIENE", "error", "Unexpected commentary or Markdown fence in candidate"))
    if glossary: issues.extend(glossary.check(segment, candidate.target))
    return issues
