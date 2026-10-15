"""Serializable data models used by the AST translation core."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Placeholder:
    token: str
    kind: str
    payload_hash: str
    payload: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "kind": self.kind,
            "payload_hash": self.payload_hash,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Placeholder":
        return cls(
            token=value["token"],
            kind=value["kind"],
            payload_hash=value["payload_hash"],
            payload=value.get("payload"),
        )


@dataclass(frozen=True)
class Segment:
    segment_id: str
    source_text: str
    source_hash: str
    ast_path: tuple[Any, ...]
    node_type: str
    context: dict[str, Any] = field(default_factory=dict)
    placeholders: tuple[Placeholder, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "source_text": self.source_text,
            "source_hash": self.source_hash,
            "ast_path": list(self.ast_path),
            "node_type": self.node_type,
            "context": self.context,
            "placeholders": [item.to_dict() for item in self.placeholders],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Segment":
        return cls(
            segment_id=value["segment_id"],
            source_text=value["source_text"],
            source_hash=value["source_hash"],
            ast_path=tuple(value["ast_path"]),
            node_type=value["node_type"],
            context=dict(value.get("context", {})),
            placeholders=tuple(
                Placeholder.from_dict(item) for item in value.get("placeholders", [])
            ),
        )


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    ast_path: tuple[Any, ...] = ()
    segment_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "ast_path": list(self.ast_path),
            "segment_id": self.segment_id,
        }


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[Issue, ...] = ()

    @property
    def ok(self) -> bool:
        return not any(issue.severity in {"error", "fatal"} for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "issues": [issue.to_dict() for issue in self.issues]}
