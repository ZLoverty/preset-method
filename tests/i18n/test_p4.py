from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sop_i18n.build import CHINESE_TITLE, CHINESE_TOC_TITLE, _metadata, build_chinese, resolve_pdf_version


class P4Tests(unittest.TestCase):
    def test_chinese_metadata_uses_chinese_title_and_toc(self) -> None:
        metadata = _metadata({"meta": {}}, "local")["meta"]
        self.assertEqual(metadata["title"]["c"][0]["c"], CHINESE_TITLE)
        self.assertEqual(metadata["toc-title"]["c"][0]["c"], CHINESE_TOC_TITLE)
        self.assertEqual(metadata["lang"]["c"][0]["c"], "zh-CN")

    def test_pdf_version_is_read_from_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("PDF_VERSION=v2026.10\nBROKEN=$(do-not-execute)\n", encoding="utf-8")
            self.assertEqual(resolve_pdf_version(env_file), "v2026.10")

    def test_partial_policy_allows_english_fallback(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "zh-CN.pdf"
            report_path = root / "report.json"
            memory_path = root / "memory.json"
            memory_path.write_text('{"schema_version": 1, "language": "zh-CN", "records": []}\n', encoding="utf-8")
            report = build_chinese(order_file=repo / "sop" / "pdf-order.txt", memory_path=memory_path, output=output, report_path=report_path, check_only=True)
            self.assertEqual(report["status"], "passed_with_warnings")
            self.assertEqual(report["segments_untranslated"], 397)
            self.assertFalse(output.exists())
            persisted = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "passed_with_warnings")
            self.assertEqual(persisted["coverage"]["MISSING"], 397)

    def test_strict_policy_still_fails_without_approved_translation(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_path = root / "memory.json"
            memory_path.write_text('{"schema_version": 1, "language": "zh-CN", "records": []}\n', encoding="utf-8")
            report = build_chinese(order_file=repo / "sop" / "pdf-order.txt", memory_path=memory_path, output=root / "zh-CN.pdf", check_only=True, translation_policy="strict")
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["stage"], "translation_resolution")


if __name__ == "__main__":
    unittest.main()
