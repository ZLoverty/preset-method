"""Canonical source identities independent of AST location and token numbering."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any

from .models import Placeholder, Segment
from .placeholders import TOKEN_RE

CANONICALIZATION_VERSION = 1


def _canonical_payload(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_inline_text(source_text: str, placeholders: tuple[Placeholder, ...]) -> str:
    """Replace numbered tokens with payload-based symbols, then normalize prose whitespace."""
    by_token = {item.token: item for item in placeholders}
    normalized: list[str] = []
    cursor = 0
    for match in TOKEN_RE.finditer(source_text):
        prose = unicodedata.normalize("NFC", source_text[cursor : match.start()])
        normalized.append(re.sub(r"\s+", " ", prose))
        closing, kind, index_text, opaque_index = match.groups()
        if opaque_index:
            item = by_token.get(f"[[[p:{opaque_index}]]]")
            payload_hash = item.payload_hash if item else "unknown"
            normalized.append(f"<protected:{item.kind if item else 'unknown'}:{payload_hash}>")
        else:
            index = int(index_text)
            item = by_token.get(f"[[[{kind}:{index}]]]")
            payload_hash = item.payload_hash if item else "unknown"
            normalized.append(f"</{kind}:{payload_hash}>" if closing else f"<{kind}:{payload_hash}>")
        cursor = match.end()
    normalized.append(re.sub(r"\s+", " ", unicodedata.normalize("NFC", source_text[cursor:])))
    return "".join(normalized).strip()


def canonical_representation(segment: Segment, version: int = CANONICALIZATION_VERSION) -> dict[str, Any]:
    if version != CANONICALIZATION_VERSION:
        raise ValueError(f"Unsupported canonicalization version: {version}")
    return {
        "canonicalization_version": version,
        "node_type": segment.node_type,
        "source_text": canonical_inline_text(segment.source_text, segment.placeholders),
    }


def source_key(segment: Segment, version: int = CANONICALIZATION_VERSION) -> str:
    encoded = _canonical_payload(canonical_representation(segment, version))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
