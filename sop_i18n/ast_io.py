"""Pandoc JSON and Markdown I/O using the repository's production reader flags."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

READER = "markdown+pipe_tables+strikeout+task_lists+autolink_bare_uris+tex_math_dollars+raw_tex+raw_attribute+link_attributes+header_attributes-smart"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def parse_markdown(path: Path, pandoc: str = "pandoc") -> dict[str, Any]:
    command = [pandoc, str(path), "--from", READER, "--resource-path", str(path.parent), "--to", "json"]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or f"Pandoc exited with {completed.returncode}")
    return json.loads(completed.stdout)


def parse_ordered_markdown(order_file: Path, pandoc: str = "pandoc") -> dict[str, Any]:
    """Assemble the repository manifest without changing any source file."""
    root = order_file.parent.parent if order_file.parent.name == "sop" else order_file.parent
    documents = []
    for raw in order_file.read_text(encoding="utf-8").splitlines():
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        path = root / entry
        if not path.is_file():
            raise FileNotFoundError(f"Document listed in {order_file} does not exist: {entry}")
        documents.append(path)
    with tempfile.TemporaryDirectory(prefix="sop-i18n-") as directory:
        combined = Path(directory) / "combined.md"
        with combined.open("w", encoding="utf-8", newline="\n") as handle:
            for document in documents:
                text = document.read_text(encoding="utf-8")
                lines = [line for line in text.splitlines() if line.strip() != "---"]
                handle.write("\n".join(lines) + "\n\n")
        return parse_markdown(combined, pandoc=pandoc)
