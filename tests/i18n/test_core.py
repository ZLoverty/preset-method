from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from sop_i18n.extract import extract_segments, extract_with_diagnostics
from sop_i18n.ast_io import parse_ordered_markdown
from sop_i18n.placeholders import decode_translation, encode_inlines
from sop_i18n.reconstruct import TranslationError, apply_translations
from sop_i18n.validate import validate_translation


def ast_with_blocks(*blocks: dict) -> dict:
    return {"pandoc-api-version": [1, 23], "meta": {}, "blocks": list(blocks)}


class CoreTests(unittest.TestCase):
    def test_mixed_inline_extraction_and_protection(self) -> None:
        ast = ast_with_blocks({
            "t": "Para",
            "c": [
                {"t": "Str", "c": "Set"}, {"t": "Space"},
                {"t": "Strong", "c": [{"t": "Str", "c": "Flow Ratio"}]},
                {"t": "Space"}, {"t": "Code", "c": ["0.95", ""]},
                {"t": "Space"}, {"t": "Link", "c": [[], [{"t": "Str", "c": "guide"}], ["calibration.md", ""]]},
                {"t": "Space"}, {"t": "Math", "c": [{"t": "InlineMath"}, "x^2"]},
            ],
        })
        segments = extract_segments(ast)
        self.assertEqual(len(segments), 1)
        text = segments[0].source_text
        self.assertIn("Flow Ratio", text)
        self.assertIn("[[[p:", text)
        self.assertEqual({item.kind for item in segments[0].placeholders}, {"format", "link", "p"})
        self.assertEqual(segments[0].placeholders[-1].payload["c"][1], "x^2")

    def test_placeholder_reordering_and_invalid_tokens(self) -> None:
        source, placeholders = encode_inlines([
            {"t": "Str", "c": "A"}, {"t": "Space"},
            {"t": "Code", "c": ["X", ""]}, {"t": "Space"},
            {"t": "Strong", "c": [{"t": "Str", "c": "B"}]},
        ])
        self.assertIn("A", source)
        protected = next(item.token for item in placeholders if item.kind == "p")
        fmt = next(item.token for item in placeholders if item.kind == "format")
        closing = fmt.replace("[[[", "[[[/", 1)
        reordered = f"{protected} {fmt}译文{closing}"
        decoded, issues = decode_translation(reordered, placeholders)
        self.assertFalse(issues)
        self.assertTrue(decoded)
        missing, issues = decode_translation(reordered.replace(protected, ""), placeholders)
        self.assertIsNone(missing)
        self.assertTrue(any(issue.code == "PLACEHOLDER_COUNT" for issue in issues))

    def test_reconstruction_is_atomic_and_input_is_unchanged(self) -> None:
        ast = ast_with_blocks({"t": "Para", "c": [{"t": "Str", "c": "Hello"}]})
        original = copy.deepcopy(ast)
        segments = extract_segments(ast)
        translated = apply_translations(ast, segments, {segments[0].segment_id: "你好"})
        self.assertEqual(ast, original)
        self.assertNotEqual(translated, ast)
        with self.assertRaises(TranslationError):
            apply_translations(ast, segments, {segments[0].segment_id: "bad [[[p:999]]]"})
        self.assertEqual(ast, original)

    def test_validation_preserves_link_target_and_detects_mutation(self) -> None:
        ast = ast_with_blocks({"t": "Para", "c": [{"t": "Link", "c": [[], [{"t": "Str", "c": "guide"}], ["guide.md", ""]]}]})
        segments = extract_segments(ast)
        translated = apply_translations(ast, segments, {segments[0].segment_id: segments[0].source_text.replace("guide", "指南")})
        self.assertTrue(validate_translation(ast, translated, segments).ok)
        translated["blocks"][0]["c"][0]["c"][2][0] = "evil.md"
        report = validate_translation(ast, translated, segments)
        self.assertFalse(report.ok)
        self.assertTrue(any(issue.code == "STRUCTURE_CHANGED" for issue in report.issues))

    def test_table_geometry_and_unknown_nodes(self) -> None:
        cell = [["", [], []], {"t": "AlignDefault"}, 1, 1, [{"t": "Plain", "c": [{"t": "Str", "c": "Cell"}]}]]
        table = {"t": "Table", "c": [["", [], []], [None, []], [[{"t": "AlignDefault"}, {"t": "ColWidth", "c": 0.5}]], [["", [], []], [[cell]]], [["", 0, []]], [["", [], []], []]]}
        segments, diagnostics = extract_with_diagnostics(ast_with_blocks(table, {"t": "Mystery", "c": "visible"}))
        self.assertEqual(len(segments), 1)
        self.assertTrue(any(issue.code == "UNSUPPORTED_NODE" for issue in diagnostics))

    def test_duplicate_occurrences_and_image_math_protection(self) -> None:
        ast = ast_with_blocks(
            {"t": "Para", "c": [{"t": "Str", "c": "same"}]},
            {"t": "Para", "c": [{"t": "Str", "c": "same"}]},
            {"t": "Para", "c": [{"t": "Image", "c": [["", [], []], [{"t": "Str", "c": "caption"}], ["assets/a.png", ""]]}, {"t": "Space"}, {"t": "Math", "c": [{"t": "DisplayMath"}, "x+y"]}]},
        )
        segments = extract_segments(ast)
        self.assertEqual(len(segments), 3)
        self.assertNotEqual(segments[0].segment_id, segments[1].segment_id)
        self.assertEqual(segments[0].source_hash, segments[1].source_hash)
        translated = apply_translations(ast, segments, {item.segment_id: item.source_text.replace("caption", "说明") for item in segments})
        self.assertTrue(validate_translation(ast, translated, segments).ok)
        self.assertEqual(translated["blocks"][2]["c"][0]["c"][2][0], "assets/a.png")

    def test_unauthorized_text_change_is_rejected(self) -> None:
        ast = ast_with_blocks({"t": "Para", "c": [{"t": "Str", "c": "approved"}]}, {"t": "RawBlock", "c": ["latex", "\\text{outside}"]})
        segments = extract_segments(ast)
        translated = apply_translations(ast, segments, {item.segment_id: item.source_text for item in segments})
        translated["blocks"][1]["c"][1] = "\\text{unauthorized}"
        report = validate_translation(ast, translated, segments)
        self.assertFalse(report.ok)

    def test_duplicate_unknown_and_malformed_placeholders_fail(self) -> None:
        _, placeholders = encode_inlines([{"t": "Code", "c": ["42", ""]}])
        token = placeholders[0].token
        for candidate in (f"{token}{token}", "[[[p:999]]]", "[[[fmt:0]]]text"):
            decoded, issues = decode_translation(candidate, placeholders)
            self.assertIsNone(decoded)
            self.assertTrue(issues)

    def test_real_entry_pandoc_integration(self) -> None:
        if shutil.which("pandoc") is None:
            self.skipTest("pandoc is not installed")
        repo = Path(__file__).resolve().parents[2]
        source = repo / "sop" / "entry.md"
        reader = "markdown+pipe_tables+strikeout+task_lists+autolink_bare_uris+tex_math_dollars+raw_tex+raw_attribute+header_attributes-smart"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "entry.json"
            completed = subprocess.run(["pandoc", str(source), "--from", reader, "--resource-path", str(repo / "sop"), "--to", "json", "--output", str(output)], check=False)
            self.assertEqual(completed.returncode, 0)
            ast = json.loads(output.read_text(encoding="utf-8"))
        segments, diagnostics = extract_with_diagnostics(ast, source_file="sop/entry.md")
        self.assertGreater(len(segments), 0)
        self.assertFalse([item for item in diagnostics if item.severity == "error"])
        identity = apply_translations(ast, segments, {item.segment_id: item.source_text for item in segments})
        self.assertTrue(validate_translation(ast, identity, segments).ok)

    def test_real_sop_order_integration(self) -> None:
        if shutil.which("pandoc") is None:
            self.skipTest("pandoc is not installed")
        repo = Path(__file__).resolve().parents[2]
        ast = parse_ordered_markdown(repo / "sop" / "pdf-order.txt")
        segments, diagnostics = extract_with_diagnostics(ast, source_file="sop/pdf-order.txt")
        self.assertGreater(len(segments), 300)
        self.assertFalse([item for item in diagnostics if item.severity == "error"])
        identity = apply_translations(ast, segments, {item.segment_id: item.source_text for item in segments})
        self.assertTrue(validate_translation(ast, identity, segments).ok)
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "translated.json"
            candidate.write_text(json.dumps(identity, ensure_ascii=False), encoding="utf-8")
            accepted = subprocess.run(["pandoc", str(candidate), "--from", "json", "--to", "json", "--output", str(Path(directory) / "accepted.json")], check=False)
            self.assertEqual(accepted.returncode, 0)


if __name__ == "__main__":
    unittest.main()
