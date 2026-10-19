"""Strict Chinese AST/PDF build orchestration for P4."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .ast_io import parse_ordered_markdown, save_json
from .extract import extract_with_diagnostics
from .matching import resolve, synchronize
from .memory import TranslationMemory
from .models import Issue
from .reconstruct import TranslationError, apply_translations
from .validate import validate_translation

READER = "markdown+pipe_tables+strikeout+task_lists+autolink_bare_uris+tex_math_dollars+raw_tex+raw_attribute+link_attributes+header_attributes-smart"
CHINESE_TITLE = "Polymaker 耗材预设调校指南"
CHINESE_TOC_TITLE = "目录"


def _dotenv_value(path: Path, name: str) -> str | None:
    """Read one simple KEY=value entry without executing the dotenv file."""
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value
    return None


def resolve_pdf_version(env_file: Path = Path(".env")) -> str:
    return os.environ.get("PDF_VERSION") or _dotenv_value(env_file, "PDF_VERSION") or "local"


def _issue(code: str, message: str, stage: str, *, segment_id: str | None = None, severity: str = "error") -> dict[str, Any]:
    return {"stage": stage, "code": code, "message": message, "severity": severity, "segment_id": segment_id}


def _write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _metadata(ast: dict[str, Any], version: str) -> dict[str, Any]:
    result = dict(ast)
    meta = dict(result.get("meta", {}))
    result["meta"] = meta
    # Build-only metadata mirrors the production English invocation.
    meta.setdefault("title", {"t": "MetaInlines", "c": [{"t": "Str", "c": CHINESE_TITLE}]})
    meta.setdefault("author", {"t": "MetaInlines", "c": [{"t": "Str", "c": "Polymaker"}]})
    meta["date"] = {"t": "MetaInlines", "c": [{"t": "Str", "c": f"Release {version}"}]}
    meta["lang"] = {"t": "MetaInlines", "c": [{"t": "Str", "c": "zh-CN"}]}
    meta["toc-title"] = {"t": "MetaInlines", "c": [{"t": "Str", "c": CHINESE_TOC_TITLE}]}
    return result


def build_chinese(*, order_file: Path, memory_path: Path, output: Path, report_path: Path | None = None, emit_ast: Path | None = None, check_only: bool = False, keep_intermediate: bool = False, cjk_mainfont: str = "SimSun", cjk_sansfont: str | None = None, version: str | None = None, env_file: Path = Path(".env"), translation_policy: str = "partial") -> dict[str, Any]:
    if translation_policy not in {"partial", "strict"}: raise ValueError("translation_policy must be partial or strict")
    version = version or resolve_pdf_version(env_file)
    report: dict[str, Any] = {"schema_version": 1, "language": "zh-CN", "version": version, "translation_policy": translation_policy, "status": "failed", "stage": "source_assembly", "segments_total": 0, "segments_resolved": 0, "segments_untranslated": 0, "untranslated_segment_ids": [], "issues": []}
    temporary_paths: list[Path] = []
    try:
        try:
            source_ast = parse_ordered_markdown(order_file)
        except Exception as exc:
            report["issues"].append(_issue("SOURCE_ASSEMBLY_FAILED", str(exc), "source_assembly")); return report
        report["stage"] = "ast_extraction"
        segments, diagnostics = extract_with_diagnostics(source_ast, source_file=str(order_file))
        report["segments_total"] = len(segments)
        report["issues"].extend(_issue(item.code, item.message, "ast_extraction") for item in diagnostics)
        if any(item.severity == "error" for item in diagnostics): return report

        report["stage"] = "translation_resolution"
        memory = TranslationMemory.load(memory_path)
        sync = synchronize(segments, memory)
        report.update({"coverage": {status: sum(item.status == status for item in sync.occurrences) for status in ("MATCHED", "DRAFT", "MISSING", "CHANGED", "AMBIGUOUS")}})
        translations, resolution_issues = resolve(segments, memory, strict=translation_policy == "strict")
        report["segments_resolved"] = len(translations)
        fallback_codes = {"MISSING_TRANSLATION", "AMBIGUOUS_TRANSLATION"}
        fallback_ids = [item.segment_id for item in resolution_issues if item.code in fallback_codes and item.segment_id]
        if translation_policy == "partial":
            by_id = {segment.segment_id: segment for segment in segments}
            for segment_id in fallback_ids:
                translations[segment_id] = by_id[segment_id].source_text
            report["segments_untranslated"] = len(fallback_ids)
            report["untranslated_segment_ids"] = fallback_ids
            report["issues"].extend(_issue(item.code, item.message + "; using English source fallback under partial policy", "translation_resolution", segment_id=item.segment_id, severity="warning") for item in resolution_issues if item.code in fallback_codes)
            blocking = [item for item in resolution_issues if item.code not in fallback_codes]
            report["issues"].extend(_issue(item.code, item.message, "translation_resolution", segment_id=item.segment_id) for item in blocking)
            if blocking: return report
        else:
            report["issues"].extend(_issue(item.code, item.message, "translation_resolution", segment_id=item.segment_id) for item in resolution_issues)
            if resolution_issues: return report

        report["stage"] = "ast_reconstruction"
        try:
            translated_ast = apply_translations(source_ast, segments, translations)
        except TranslationError as exc:
            report["issues"].extend(_issue(item.code, item.message, "ast_reconstruction", segment_id=item.segment_id) for item in exc.issues); return report
        report["stage"] = "structural_validation"
        validation = validate_translation(source_ast, translated_ast, segments)
        report["issues"].extend(_issue(item.code, item.message, "structural_validation", segment_id=item.segment_id) for item in validation.issues)
        if not validation.ok: return report
        translated_ast = _metadata(translated_ast, version)
        if emit_ast:
            emit_ast.parent.mkdir(parents=True, exist_ok=True); save_json(emit_ast, translated_ast)
        if check_only:
            report["status"] = "passed_with_warnings" if report["segments_untranslated"] else "passed"; report["stage"] = "structural_validation"; return report

        report["stage"] = "pandoc_rendering"
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="sop-zh-CN-", suffix=".json", dir=output.parent, delete=False) as handle:
            ast_path = Path(handle.name); save_json(ast_path, translated_ast); temporary_paths.append(ast_path)
        with tempfile.NamedTemporaryFile(prefix="sop-zh-CN-", suffix=".pdf", dir=output.parent, delete=False) as handle:
            pdf_path = Path(handle.name); temporary_paths.append(pdf_path)
        command = ["pandoc", str(ast_path), "--from=json", "--resource-path=sop", "--pdf-engine=xelatex", "--toc", "--number-sections", "--metadata", f"title={CHINESE_TITLE}", "--metadata", "author=Polymaker", "--metadata", f"date=Release {version}", "--metadata", f"toc-title={CHINESE_TOC_TITLE}", "--metadata", "lang=zh-CN", "--variable", "mainfont=Cambria", "--variable", f"CJKmainfont={cjk_mainfont}", "--variable", "geometry:margin=3cm", "--variable", "linestretch=1.2", "--variable", "fontsize=11pt", "--output", str(pdf_path)]
        if cjk_sansfont: command.extend(["--variable", f"CJKsansfont={cjk_sansfont}"])
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        if completed.returncode:
            report["issues"].append(_issue("PANDOC_RENDER_FAILED", (completed.stderr or completed.stdout).strip()[-4000:], "pandoc_rendering")); return report

        report["stage"] = "pdf_validation"
        if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            report["issues"].append(_issue("PDF_EMPTY", "Pandoc produced no PDF", "pdf_validation")); return report
        if pdf_path.read_bytes()[:5] != b"%PDF-":
            report["issues"].append(_issue("PDF_SIGNATURE_INVALID", "Output is not a PDF", "pdf_validation")); return report
        os.replace(pdf_path, output)
        report["status"] = "passed_with_warnings" if report["segments_untranslated"] else "passed"; report["stage"] = "pdf_validation"; report["output"] = str(output)
        return report
    finally:
        if not keep_intermediate:
            for path in temporary_paths:
                try: path.unlink(missing_ok=True)
                except OSError: pass
        _write_report(report_path, report)
