"""Inline placeholder encoding and reconstruction.

The token format is deliberately explicit and parsed structurally. Tokens are
not replaced with a regular-expression substitution after translation.
"""

from __future__ import annotations

import hashlib
import json
import re
import copy
from collections import Counter
from typing import Any

from .models import Issue, Placeholder

TOKEN_RE = re.compile(r"\[\[\[(/?)(fmt|link|image|span):(\d+)\]\]\]|\[\[\[p:(\d+)\]\]\]")
FORMATTING_TYPES = {"Strong", "Emph", "Underline", "Strikeout", "Superscript", "Subscript", "SmallCaps", "Quoted", "Span"}
OPAQUE_TYPES = {"Math", "Code", "RawInline", "Cite", "Note", "LineBreak", "SoftBreak", "Space"}


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _token(kind: str, index: int, closing: bool = False) -> str:
    return f"[[[{ '/' if closing else ''}{kind}:{index}]]]"


def _text_to_inlines(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for part in re.split(r"(\s+)", text):
        if not part:
            continue
        if part.isspace():
            result.append({"t": "Space"})
        else:
            result.append({"t": "Str", "c": part})
    return result


class InlineEncoder:
    def __init__(self) -> None:
        self.placeholders: list[Placeholder] = []

    def encode(self, inlines: list[dict[str, Any]]) -> str:
        return self._encode_children(inlines)

    def _add(self, kind: str, payload: Any) -> str:
        index = len(self.placeholders)
        token = _token(kind, index)
        self.placeholders.append(Placeholder(token, kind, _digest(payload), payload))
        return token

    def _encode_children(self, children: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for inline in children:
            node_type = inline.get("t")
            if node_type == "Str":
                parts.append(str(inline.get("c", "")))
            elif node_type == "Space":
                parts.append(" ")
            elif node_type == "SoftBreak":
                parts.append("\n")
            elif node_type == "LineBreak":
                parts.append("\n")
            elif node_type in FORMATTING_TYPES:
                children_value = inline.get("c", [])
                if node_type == "Quoted":
                    quote_type, children_value = children_value
                    payload = {"t": node_type, "quote_type": quote_type}
                elif node_type == "Span":
                    attr, children_value = children_value
                    payload = {"t": node_type, "attr": attr}
                else:
                    payload = {"t": node_type}
                index = len(self.placeholders)
                self.placeholders.append(Placeholder(_token("fmt", index), "format", _digest(payload), payload))
                parts.append(_token("fmt", index))
                parts.append(self._encode_children(children_value))
                parts.append(_token("fmt", index, closing=True))
            elif node_type == "Link":
                attr, label, target = inline.get("c", [[], [], ["", ""]])
                payload = {"t": "Link", "attr": attr, "target": target}
                index = len(self.placeholders)
                self.placeholders.append(Placeholder(_token("link", index), "link", _digest(payload), payload))
                parts.extend([_token("link", index), self._encode_children(label), _token("link", index, closing=True)])
            elif node_type == "Image":
                attr, alt, target = inline.get("c", [[], [], ["", ""]])
                payload = {"t": "Image", "attr": attr, "target": target}
                index = len(self.placeholders)
                self.placeholders.append(Placeholder(_token("image", index), "image", _digest(payload), payload))
                parts.extend([_token("image", index), self._encode_children(alt), _token("image", index, closing=True)])
            else:
                parts.append(self._add("p", inline))
        return "".join(parts)


def encode_inlines(inlines: list[dict[str, Any]]) -> tuple[str, tuple[Placeholder, ...]]:
    encoder = InlineEncoder()
    return encoder.encode(inlines), tuple(encoder.placeholders)


def _placeholder_map(placeholders: tuple[Placeholder, ...]) -> dict[str, Placeholder]:
    return {item.token: item for item in placeholders}


def validate_placeholder_tokens(text: str, placeholders: tuple[Placeholder, ...]) -> list[Issue]:
    expected = _placeholder_map(placeholders)
    found = TOKEN_RE.findall(text)
    tokens: list[str] = []
    for closing, kind, index, opaque_index in found:
        tokens.append(_token("p", int(opaque_index)) if opaque_index else _token(kind, int(index), bool(closing)))
    issues: list[Issue] = []
    counts = Counter(tokens)
    allowed_tokens: set[str] = set()
    for token, placeholder in expected.items():
        allowed_tokens.add(token)
        if placeholder.kind in {"format", "link", "image"}:
            match = re.fullmatch(r"\[\[\[(?:fmt|link|image):(\d+)\]\]\]", token)
            if match:
                kind = token[3:].split(":", 1)[0]
                allowed_tokens.add(_token(kind, int(match.group(1)), closing=True))
    for token in sorted(expected):
        required_tokens = [token]
        if expected[token].kind in {"format", "link", "image"}:
            match = re.fullmatch(r"\[\[\[(?:fmt|link|image):(\d+)\]\]\]", token)
            assert match is not None
            kind = token[3:].split(":", 1)[0]
            required_tokens.append(_token(kind, int(match.group(1)), closing=True))
        for required_token in required_tokens:
            if counts[required_token] != 1:
                issues.append(Issue("PLACEHOLDER_COUNT", "error", f"Expected one occurrence of {required_token}, found {counts[required_token]}"))
    for token in sorted(set(tokens) - allowed_tokens):
        issues.append(Issue("UNKNOWN_PLACEHOLDER", "error", f"Unknown placeholder {token}"))
    return issues


def rebind_translation(
    text: str,
    source_placeholders: list[dict[str, Any]] | None,
    current_placeholders: tuple[Placeholder, ...],
) -> tuple[str, list[Issue]]:
    """Rebind TM placeholder numbers to the current segment's numbers.

    Placeholder numbers are an encoding detail, so identity is matched by
    kind and payload hash, with occurrence order disambiguating duplicates.
    The operation fails closed when the source metadata is absent or the
    protected structure changed.
    """
    if not current_placeholders:
        return text, []
    if not source_placeholders:
        return text, [Issue(
            "PLACEHOLDER_REBINDING_UNAVAILABLE",
            "error",
            "Approved translation has no source placeholder metadata",
        )]

    try:
        old = tuple(Placeholder.from_dict(item) for item in source_placeholders)
    except (KeyError, TypeError) as exc:
        return text, [Issue("PLACEHOLDER_METADATA_INVALID", "error", str(exc))]

    old_identity = [(item.kind, item.payload_hash) for item in old]
    current_identity = [(item.kind, item.payload_hash) for item in current_placeholders]
    if old_identity != current_identity:
        return text, [Issue(
            "PLACEHOLDER_IDENTITY_MISMATCH",
            "error",
            "Source and current placeholder identities or nesting order differ",
        )]

    # The sequence equality above also ensures that duplicate identities are
    # paired deterministically by occurrence order.
    token_map: dict[str, str] = {}
    try:
        for previous, current in zip(old, current_placeholders):
            previous_open = _opening_token(previous.token)
            current_open = _opening_token(current.token)
            token_map[previous_open] = current_open
            if previous.kind in {"format", "link", "image"}:
                token_map[_closing_token(previous_open)] = _closing_token(current_open)
    except ValueError as exc:
        return text, [Issue("PLACEHOLDER_METADATA_INVALID", "error", str(exc))]

    issues: list[Issue] = []

    def replace(match: re.Match[str]) -> str:
        closing, kind, index_text, opaque_index = match.groups()
        old_token = _token("p", int(opaque_index)) if opaque_index else _token(kind, int(index_text), bool(closing))
        replacement = token_map.get(old_token)
        if replacement is None:
            issues.append(Issue("PLACEHOLDER_TOKEN_UNMAPPED", "error", f"No current placeholder mapping for {old_token}"))
            return match.group(0)
        return replacement

    rebound = TOKEN_RE.sub(replace, text)
    return rebound, issues


def _opening_token(token: str) -> str:
    match = re.fullmatch(r"\[\[\[/?(fmt|link|image):(\d+)\]\]\]|\[\[\[p:(\d+)\]\]\]", token)
    if not match:
        raise ValueError(f"Invalid placeholder token: {token}")
    if match.group(3):
        return _token("p", int(match.group(3)))
    return _token(match.group(1), int(match.group(2)))


def _closing_token(opening: str) -> str:
    match = re.fullmatch(r"\[\[\[(fmt|link|image):(\d+)\]\]\]", opening)
    if not match:
        raise ValueError(f"Not a scoped placeholder: {opening}")
    return _token(match.group(1), int(match.group(2)), closing=True)


def decode_translation(text: str, placeholders: tuple[Placeholder, ...]) -> tuple[list[dict[str, Any]] | None, list[Issue]]:
    issues = validate_placeholder_tokens(text, placeholders)
    if issues:
        return None, issues
    by_token = _placeholder_map(placeholders)
    root: list[dict[str, Any]] = []
    containers: list[list[dict[str, Any]]] = [root]
    stacks: list[tuple[str, dict[str, Any]]] = []
    cursor = 0
    for match in TOKEN_RE.finditer(text):
        containers[-1].extend(_text_to_inlines(text[cursor:match.start()]))
        closing, kind, index_text, opaque_index = match.groups()
        if opaque_index:
            placeholder = by_token.get(_token("p", int(opaque_index)))
            if placeholder is None:
                return None, [Issue("UNKNOWN_PLACEHOLDER", "error", "Unknown opaque placeholder")]
            containers[-1].append(copy.deepcopy(placeholder.payload))
        else:
            index = int(index_text)
            opening = _token(kind, index)
            closing_token = _token(kind, index, closing=True)
            if not closing:
                placeholder = by_token.get(opening)
                if placeholder is None:
                    return None, [Issue("UNKNOWN_PLACEHOLDER", "error", f"Unknown placeholder {opening}")]
                payload = placeholder.payload
                if kind == "fmt":
                    node_type = payload["t"]
                    if node_type == "Quoted":
                        node = {"t": node_type, "c": [payload["quote_type"], []]}
                    elif node_type == "Span":
                        node = {"t": node_type, "c": [copy.deepcopy(payload["attr"]), []]}
                    else:
                        node = {"t": node_type, "c": []}
                elif kind == "link":
                    node = {"t": "Link", "c": [copy.deepcopy(payload["attr"]), [], copy.deepcopy(payload["target"])]}
                else:
                    node = {"t": "Image", "c": [copy.deepcopy(payload["attr"]), [], copy.deepcopy(payload["target"])]}
                stacks.append((closing_token, node))
                containers.append(node["c"][1] if node["t"] in {"Quoted", "Link", "Image"} else node["c"])
            else:
                if not stacks or stacks[-1][0] != closing_token:
                    return None, [Issue("PLACEHOLDER_NESTING", "error", f"Unexpected closing placeholder {closing_token}")]
                _, node = stacks.pop()
                containers.pop()
                containers[-1].append(node)
        cursor = match.end()
    containers[-1].extend(_text_to_inlines(text[cursor:]))
    if stacks:
        return None, [Issue("PLACEHOLDER_NESTING", "error", "Unclosed placeholder scope")]
    return root, []
