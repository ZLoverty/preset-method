"""Review-aid glossary checks for source and translated segment text."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Issue, Segment
from .placeholders import TOKEN_RE


@dataclass(frozen=True)
class GlossaryTerm:
    term_id: str
    source: str
    target: str
    match_mode: str = "phrase"
    severity: str = "warning"
    case_sensitive: bool = False
    alternatives: tuple[str, ...] = ()


class Glossary:
    def __init__(self, language: str, terms: list[GlossaryTerm], schema_version: int = 1) -> None:
        self.language = language
        self.terms = terms
        self.schema_version = schema_version

    @classmethod
    def load(cls, path: Path) -> "Glossary":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError(f"Unsupported glossary schema version: {payload.get('schema_version')}")
        terms = []
        for item in payload.get("terms", []):
            if not item.get("id") or not item.get("source") or not item.get("target"):
                raise ValueError("Glossary terms require id, source and target")
            if item.get("severity", "warning") not in {"error", "warning", "info"}:
                raise ValueError(f"Invalid glossary severity: {item['severity']}")
            terms.append(GlossaryTerm(item["id"], item["source"], item["target"], item.get("match_mode", "phrase"), item.get("severity", "warning"), item.get("case_sensitive", False), tuple(item.get("alternatives", []))))
        return cls(payload.get("language", "zh-CN"), terms)

    @staticmethod
    def _natural_text(text: str) -> str:
        return TOKEN_RE.sub(" ", text)

    def check(self, segment: Segment, target: str) -> list[Issue]:
        source = self._natural_text(segment.source_text)
        translated = self._natural_text(target)
        issues: list[Issue] = []
        for term in self.terms:
            flags = 0 if term.case_sensitive else re.IGNORECASE
            boundary = r"\b" if term.match_mode == "whole_word" else ""
            pattern = boundary + re.escape(term.source) + boundary
            if not re.search(pattern, source, flags):
                continue
            allowed = (term.target,) + term.alternatives
            if not any(re.search(re.escape(candidate), translated, flags) for candidate in allowed):
                issues.append(Issue("GLOSSARY_MISMATCH", term.severity, f"Preferred translation for '{term.source}' is '{term.target}'", segment.ast_path, segment.segment_id))
        return issues
