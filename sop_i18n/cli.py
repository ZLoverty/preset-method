"""Command-line interface for inspection, extraction, reconstruction and validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ast_io import load_json, parse_markdown, parse_ordered_markdown, save_json
from .canonical import source_key
from .coverage import coverage
from .glossary import Glossary
from .extract import extract_with_diagnostics, segments_to_json
from .matching import resolve, synchronize
from .memory import TranslationMemory
from .models import Segment
from .reconstruct import TranslationError, apply_translations
from .review import approve as approve_record
from .review import reject as reject_record
from .review import reopen as reopen_record
from .validate import validate_translation
from .context import extract_context
from .jobs import jobs_payload, load_jobs, plan_jobs
from .candidates import candidates_payload, load_candidates, parse_response
from .qa import validate_candidate
from .importer import import_drafts
from .build import build_chinese
from .providers.openai import OpenAIProvider, ProviderError
from .providers.run import run_resumable
from .review_ui import serve as serve_review_ui
from .terminology import extract_term_candidates


def _ast_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ast", type=Path)
    group.add_argument("--markdown", type=Path)
    group.add_argument("--order-file", type=Path)


def _load(args: argparse.Namespace) -> dict[str, Any]:
    if args.ast:
        return load_json(args.ast)
    if args.markdown:
        return parse_markdown(args.markdown)
    return parse_ordered_markdown(args.order_file)


def _extract(args: argparse.Namespace) -> int:
    ast = _load(args)
    segments, diagnostics = extract_with_diagnostics(ast, source_file=str(args.ast or args.markdown or args.order_file))
    payload = segments_to_json(segments, diagnostics)
    if args.out:
        if args.out.exists() and not args.force:
            raise RuntimeError(f"Refusing to overwrite existing file: {args.out}")
        save_json(args.out, payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def _inspect(args: argparse.Namespace) -> int:
    ast = _load(args)
    segments, diagnostics = extract_with_diagnostics(ast, source_file=str(args.ast or args.markdown or args.order_file))
    counts: dict[str, int] = {}
    protected = 0
    for segment in segments:
        counts[segment.node_type] = counts.get(segment.node_type, 0) + 1
        protected += len(segment.placeholders)
    print(json.dumps({"segments": counts, "total_segments": len(segments), "protected_elements": protected, "diagnostics": [item.to_dict() for item in diagnostics]}, ensure_ascii=False, indent=2))
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def _rebuild(args: argparse.Namespace) -> int:
    ast = load_json(args.ast)
    payload = load_json(args.segments)
    segments = [Segment.from_dict(item) for item in payload["segments"]]
    translations = load_json(args.translations)
    try:
        rebuilt = apply_translations(ast, segments, translations)
    except TranslationError as error:
        print(json.dumps({"ok": False, "issues": [item.to_dict() for item in error.issues]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    if args.out.exists() and not args.force:
        print(f"Refusing to overwrite existing file: {args.out}", file=sys.stderr)
        return 2
    save_json(args.out, rebuilt)
    return 0


def _validate(args: argparse.Namespace) -> int:
    original = load_json(args.original)
    translated = load_json(args.translated)
    payload = load_json(args.segments)
    segments = [Segment.from_dict(item) for item in payload["segments"]]
    report = validate_translation(original, translated, segments)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


def _segments_from_source(args: argparse.Namespace) -> tuple[dict[str, Any], list[Segment]]:
    ast = _load(args)
    segments, diagnostics = extract_with_diagnostics(ast, source_file=str(args.ast or args.markdown or args.order_file))
    errors = [item for item in diagnostics if item.severity == "error"]
    if errors:
        raise RuntimeError("Source extraction failed: " + "; ".join(item.message for item in errors[:5]))
    return ast, segments


def _tm_status(args: argparse.Namespace) -> int:
    _, segments = _segments_from_source(args)
    memory = TranslationMemory.load(args.memory)
    report = synchronize(segments, memory)
    payload = coverage(report)
    payload["obsolete_records"] = len(report.obsolete_record_ids)
    payload["total_segments"] = len(segments)
    payload["records"] = len(memory.records)
    print(json.dumps(payload if not args.json else {**payload, "report": report.to_dict()}, ensure_ascii=False, indent=2))
    return 0


def _tm_sync(args: argparse.Namespace) -> int:
    _, segments = _segments_from_source(args)
    memory = TranslationMemory.load(args.memory)
    report = synchronize(segments, memory)
    if args.create_drafts:
        by_id = {item.segment_id: item for item in segments}
        for occurrence in report.occurrences:
            if occurrence.status in {"MISSING", "CHANGED"}:
                segment = by_id[occurrence.segment_id]
                memory.create_draft(source_key=occurrence.source_key, source=segment.source_text, context=segment.context, occurrence_id=segment.segment_id, source_placeholders=[item.to_dict() for item in segment.placeholders])
        memory.save(args.memory)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _tm_resolve(args: argparse.Namespace) -> int:
    _, segments = _segments_from_source(args)
    memory = TranslationMemory.load(args.memory)
    translations, issues = resolve(segments, memory, strict=not args.preview)
    payload = {"ok": not issues, "translations": translations, "issues": [item.to_dict() for item in issues]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.out and (not issues or args.preview):
        if args.out.exists() and not args.force:
            raise RuntimeError(f"Refusing to overwrite existing file: {args.out}")
        save_json(args.out, translations)
    return 0 if not issues else 1


def _find_segment(args: argparse.Namespace, record_id: str) -> Segment:
    _, segments = _segments_from_source(args)
    memory = TranslationMemory.load(args.memory)
    record = memory.find(record_id)
    for segment in segments:
        if segment.segment_id == record.occurrence_id or source_key(segment) == record.source_key:
            return segment
    raise RuntimeError(f"No current segment found for record {record_id}")


def _tm_review(args: argparse.Namespace, operation: str) -> int:
    memory = TranslationMemory.load(args.memory)
    if operation == "update":
        memory.update_target(args.record_id, args.target)
    else:
        segment = _find_segment(args, args.record_id)
        if operation == "approve":
            glossary = Glossary.load(args.glossary) if args.glossary else None
            issues = approve_record(memory, args.record_id, segment, reviewer=args.reviewer, glossary=glossary, comment=args.comment)
            if any(item.severity == "error" for item in issues):
                print(json.dumps({"ok": False, "issues": [item.to_dict() for item in issues]}, ensure_ascii=False, indent=2))
                return 1
        elif operation == "reject":
            reject_record(memory, args.record_id, reviewer=args.reviewer, comment=args.comment)
        else:
            reopen_record(memory, args.record_id, reviewer=args.reviewer, comment=args.comment)
    memory.save(args.memory)
    return 0


def _glossary_check(args: argparse.Namespace) -> int:
    _, segments = _segments_from_source(args)
    glossary = Glossary.load(args.glossary)
    translations = load_json(args.translations)
    issues = []
    for segment in segments:
        target = translations.get(segment.segment_id)
        if target is not None:
            issues.extend(glossary.check(segment, target))
    print(json.dumps({"ok": not any(item.severity == "error" for item in issues), "issues": [item.to_dict() for item in issues]}, ensure_ascii=False, indent=2))
    return 0 if not any(item.severity == "error" for item in issues) else 1


def _translate_plan(args: argparse.Namespace) -> int:
    ast, segments = _segments_from_source(args)
    memory = TranslationMemory.load(args.memory)
    glossary = Glossary.load(args.glossary)
    jobs = plan_jobs(segments, memory, glossary, contexts=extract_context(ast, segments, max_neighbor_chars=args.max_neighbor_chars))
    if args.out.exists() and not args.force: raise RuntimeError(f"Refusing to overwrite existing file: {args.out}")
    save_json(args.out, jobs_payload(jobs))
    print(json.dumps({"jobs": len(jobs), "occurrences": sum(len(item.occurrence_ids) for item in jobs)}, ensure_ascii=False, indent=2))
    return 0


def _translate_import_response(args: argparse.Namespace) -> int:
    jobs = load_jobs(load_json(args.jobs)); response = load_json(args.response)
    candidates = parse_response(response, jobs, provider=args.provider, model=args.model, prompt_version=args.prompt_version)
    if args.out.exists() and not args.force: raise RuntimeError(f"Refusing to overwrite existing file: {args.out}")
    save_json(args.out, candidates_payload(candidates)); print(json.dumps({"candidates": len(candidates)}, ensure_ascii=False, indent=2)); return 0


def _translate_check(args: argparse.Namespace) -> int:
    jobs = load_jobs(load_json(args.jobs)); candidates = load_candidates(load_json(args.candidates)); glossary = Glossary.load(args.glossary)
    by_id = {job.job_id: job for job in jobs}; errors = []
    for candidate in candidates:
        issues = validate_candidate(candidate, by_id.get(candidate.job_id), glossary) if candidate.job_id in by_id else []
        candidate.validation = {"status": "pass" if not any(item.severity == "error" for item in issues) else "fail", "issues": [item.to_dict() for item in issues]}
        errors.extend(candidate.validation["issues"])
    if args.out:
        if args.out.exists() and not args.force: raise RuntimeError(f"Refusing to overwrite existing file: {args.out}")
        save_json(args.out, candidates_payload(candidates))
    print(json.dumps({"ok": not any(item.get("severity") == "error" for item in errors), "issues": errors}, ensure_ascii=False, indent=2))
    return 0 if not any(item.get("severity") == "error" for item in errors) else 1


def _translate_import_drafts(args: argparse.Namespace) -> int:
    jobs = load_jobs(load_json(args.jobs)); candidates = load_candidates(load_json(args.candidates)); memory = TranslationMemory.load(args.memory); glossary = Glossary.load(args.glossary)
    if args.only_passing:
        candidates = [item for item in candidates if item.validation and item.validation.get("status") == "pass"]
    result = import_drafts(memory, jobs, candidates, glossary)
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    if result.issues or result.conflicts: return 1
    memory.save(args.memory); return 0


def _translate_run(args: argparse.Namespace) -> int:
    try:
        from .jobs import load_jobs
        jobs = load_jobs(load_json(args.jobs))
        glossary = Glossary.load(args.glossary)
        pricing = load_json(args.pricing) if args.pricing else None
        provider = OpenAIProvider(model=args.model, endpoint=args.endpoint, prompt_path=args.prompt, prompt_version=args.prompt_version, timeout=args.timeout, max_retries=args.retries, initial_backoff=args.initial_backoff, max_backoff=args.max_backoff, dotenv_path=args.env_file)
        report = run_resumable(provider, jobs, run_dir=args.run_dir, glossary=glossary, max_jobs=args.max_jobs, max_request_bytes=args.max_request_bytes, pricing=pricing, max_cost=args.max_cost, resume=not args.no_resume)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ProviderError, ValueError, OSError) as exc:
        print(json.dumps({"status": "failed", "stage": "provider", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


def _build(args: argparse.Namespace) -> int:
    report = build_chinese(order_file=args.order_file, memory_path=args.memory, output=args.output, report_path=args.report, emit_ast=args.emit_ast, check_only=args.check_only, keep_intermediate=args.keep_intermediate, cjk_mainfont=args.cjk_mainfont, cjk_sansfont=args.cjk_sansfont, version=args.version, env_file=args.env_file, translation_policy=args.translation_policy)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") in {"passed", "passed_with_warnings"} else 1


def _review(args: argparse.Namespace) -> int:
    serve_review_ui(args.jobs, args.candidates, args.memory, args.glossary, args.host, args.port)
    return 0


def _glossary_extract(args: argparse.Namespace) -> int:
    from .jobs import load_jobs
    jobs = load_jobs(load_json(args.jobs)); glossary = Glossary.load(args.glossary)
    payload = {"schema_version": 1, "language": "zh-CN", "candidates": extract_term_candidates(jobs, glossary, min_count=args.min_count, max_words=args.max_words, limit=args.limit)}
    if args.out:
        if args.out.exists() and not args.force: raise RuntimeError(f"Refusing to overwrite existing file: {args.out}")
        save_json(args.out, payload)
    else: print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m sop_i18n")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="summarize AST structures and extracted segments")
    _ast_args(inspect)
    inspect.set_defaults(func=_inspect)
    extract = sub.add_parser("extract", help="extract translation segments as JSON")
    _ast_args(extract)
    extract.add_argument("--out", type=Path)
    extract.add_argument("--force", action="store_true")
    extract.set_defaults(func=_extract)
    rebuild = sub.add_parser("rebuild", help="apply translations to an AST")
    rebuild.add_argument("--ast", type=Path, required=True)
    rebuild.add_argument("--segments", type=Path, required=True)
    rebuild.add_argument("--translations", type=Path, required=True)
    rebuild.add_argument("--out", type=Path, required=True)
    rebuild.add_argument("--force", action="store_true")
    rebuild.set_defaults(func=_rebuild)
    validate = sub.add_parser("validate", help="validate structural and protected invariants")
    validate.add_argument("--original", type=Path, required=True)
    validate.add_argument("--translated", type=Path, required=True)
    validate.add_argument("--segments", type=Path, required=True)
    validate.set_defaults(func=_validate)

    build = sub.add_parser("build", help="strictly build the reviewed Chinese PDF")
    build.add_argument("--language", default="zh-CN", choices=["zh-CN"])
    build.add_argument("--order-file", type=Path, default=Path("sop/pdf-order.txt"))
    build.add_argument("--memory", type=Path, default=Path("i18n/memory/zh-CN.json"))
    build.add_argument("--output", type=Path, default=Path("dist/sop-zh-CN.pdf"))
    build.add_argument("--report", type=Path)
    build.add_argument("--emit-ast", type=Path)
    build.add_argument("--check-only", action="store_true")
    build.add_argument("--keep-intermediate", action="store_true")
    build.add_argument("--cjk-mainfont", default="SimSun")
    build.add_argument("--cjk-sansfont")
    build.add_argument("--version", help="override PDF_VERSION from .env")
    build.add_argument("--env-file", type=Path, default=Path(".env"), help="dotenv file containing PDF_VERSION")
    build.add_argument("--translation-policy", choices=["partial", "strict"], default="partial", help="partial keeps unresolved prose in English; strict requires every segment approved")
    build.set_defaults(func=_build)

    review = sub.add_parser("review", help="open the local browser translation review UI")
    review.add_argument("--jobs", type=Path, required=True)
    review.add_argument("--candidates", type=Path, required=True)
    review.add_argument("--memory", type=Path, default=Path("i18n/memory/zh-CN.json"))
    review.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json"))
    review.add_argument("--host", default="127.0.0.1")
    review.add_argument("--port", type=int, default=8765)
    review.set_defaults(func=_review)

    tm = sub.add_parser("tm", help="translation memory and review operations")
    tm_sub = tm.add_subparsers(dest="tm_command", required=True)
    for name, function, help_text in (("status", _tm_status, "show incremental translation coverage"), ("sync", _tm_sync, "synchronize source occurrences with TM"), ("resolve", _tm_resolve, "resolve approved translations")):
        command = tm_sub.add_parser(name, help=help_text)
        _ast_args(command)
        command.add_argument("--memory", type=Path, default=Path("i18n/memory/zh-CN.json"))
        if name == "status":
            command.add_argument("--json", action="store_true")
        elif name == "sync":
            command.add_argument("--create-drafts", action="store_true")
        else:
            command.add_argument("--out", type=Path)
            command.add_argument("--preview", action="store_true")
            command.add_argument("--force", action="store_true")
        command.set_defaults(func=function)

    for name, function, help_text in (("approve", "approve", "approve a validated draft"), ("reject", "reject", "reject a draft"), ("reopen", "reopen", "reopen a rejected translation"), ("update", "update", "update a draft target")):
        command = tm_sub.add_parser(name, help=help_text)
        command.add_argument("--memory", type=Path, default=Path("i18n/memory/zh-CN.json"))
        command.add_argument("--record-id", required=True)
        command.add_argument("--reviewer", default="local")
        command.add_argument("--comment")
        if name in {"approve", "reject", "reopen"}:
            _ast_args(command)
        if name == "approve":
            command.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json"))
        if name == "update":
            command.add_argument("--target", required=True)
        command.set_defaults(func=lambda args, operation=name: _tm_review(args, operation))

    glossary = sub.add_parser("glossary", help="terminology review operations")
    glossary_sub = glossary.add_subparsers(dest="glossary_command", required=True)
    check = glossary_sub.add_parser("check", help="check translations against the glossary")
    _ast_args(check)
    check.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json"))
    check.add_argument("--translations", type=Path, required=True)
    check.set_defaults(func=_glossary_check)
    extract_terms = glossary_sub.add_parser("extract", help="extract technical term candidates without modifying glossary")
    extract_terms.add_argument("--jobs", type=Path, required=True)
    extract_terms.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json"))
    extract_terms.add_argument("--out", type=Path)
    extract_terms.add_argument("--min-count", type=int, default=2)
    extract_terms.add_argument("--max-words", type=int, default=4)
    extract_terms.add_argument("--limit", type=int, default=300)
    extract_terms.add_argument("--force", action="store_true")
    extract_terms.set_defaults(func=_glossary_extract)

    translate = sub.add_parser("translate", help="offline translation planning and candidate workflow")
    translate_sub = translate.add_subparsers(dest="translate_command", required=True)
    plan = translate_sub.add_parser("plan", help="generate deterministic translation jobs")
    _ast_args(plan); plan.add_argument("--memory", type=Path, default=Path("i18n/memory/zh-CN.json")); plan.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json")); plan.add_argument("--out", type=Path, required=True); plan.add_argument("--max-neighbor-chars", type=int, default=500); plan.add_argument("--force", action="store_true"); plan.set_defaults(func=_translate_plan)
    response = translate_sub.add_parser("import-response", help="parse a strict provider response")
    response.add_argument("--jobs", type=Path, required=True); response.add_argument("--response", type=Path, required=True); response.add_argument("--out", type=Path, required=True); response.add_argument("--provider", default="offline"); response.add_argument("--model"); response.add_argument("--prompt-version", default="zh-CN-v1"); response.add_argument("--force", action="store_true"); response.set_defaults(func=_translate_import_response)
    quality = translate_sub.add_parser("check", help="locally validate candidate translations")
    quality.add_argument("--jobs", type=Path, required=True); quality.add_argument("--candidates", type=Path, required=True); quality.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json")); quality.add_argument("--out", type=Path); quality.add_argument("--force", action="store_true"); quality.set_defaults(func=_translate_check)
    drafts = translate_sub.add_parser("import-drafts", help="atomically import validated candidates as drafts")
    drafts.add_argument("--jobs", type=Path, required=True); drafts.add_argument("--candidates", type=Path, required=True); drafts.add_argument("--memory", type=Path, default=Path("i18n/memory/zh-CN.json")); drafts.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json")); drafts.add_argument("--only-passing", action="store_true", help="import only candidates already marked QA pass"); drafts.set_defaults(func=_translate_import_drafts)
    run = translate_sub.add_parser("run", help="run the opt-in OpenAI provider with resumable batches")
    run.add_argument("--jobs", type=Path, required=True); run.add_argument("--run-dir", type=Path, required=True); run.add_argument("--model", required=True); run.add_argument("--endpoint", default="https://api.openai.com/v1/responses"); run.add_argument("--prompt", type=Path, default=Path("i18n/prompts/zh-CN-v1.txt")); run.add_argument("--prompt-version", default="zh-CN-v1"); run.add_argument("--env-file", type=Path, default=Path(".env")); run.add_argument("--glossary", type=Path, default=Path("i18n/glossary.json")); run.add_argument("--max-jobs", type=int, default=20); run.add_argument("--max-request-bytes", type=int, default=100000); run.add_argument("--timeout", type=float, default=120.0); run.add_argument("--retries", type=int, default=3); run.add_argument("--initial-backoff", type=float, default=1.0); run.add_argument("--max-backoff", type=float, default=30.0); run.add_argument("--pricing", type=Path); run.add_argument("--max-cost", type=float); run.add_argument("--no-resume", action="store_true"); run.set_defaults(func=_translate_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
