from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sop_i18n.canonical import source_key
from sop_i18n.ast_io import parse_ordered_markdown
from sop_i18n.glossary import Glossary, GlossaryTerm
from sop_i18n.matching import resolve, synchronize
from sop_i18n.memory import TranslationMemory
from sop_i18n.models import Placeholder, Segment
from sop_i18n.review import approve, reject, reopen
from sop_i18n.extract import extract_segments
from sop_i18n.placeholders import encode_inlines


def paragraph(text: str) -> dict:
    return {"t": "Para", "c": [{"t": "Str", "c": text}]}


class P2Tests(unittest.TestCase):
    def test_canonical_key_ignores_location_whitespace_and_placeholder_number(self) -> None:
        plain = extract_segments({"blocks": [paragraph("Record   the flow ratio.")]})[0]
        moved = extract_segments({"blocks": [paragraph("Record the flow ratio.")]})[0]
        self.assertEqual(source_key(plain), source_key(moved))
        source, placeholders = encode_inlines([{"t": "Code", "c": ["42", ""]}])
        altered_token = source.replace("p:0", "p:9")
        altered_placeholders = (Placeholder("[[[p:9]]]", placeholders[0].kind, placeholders[0].payload_hash, placeholders[0].payload),)
        protected = Segment("original", source, "different", ("blocks", 0), "Para", placeholders=placeholders)
        altered = Segment("other", altered_token, "different", ("blocks", 9), "Para", placeholders=altered_placeholders)
        self.assertEqual(source_key(protected), source_key(altered))

    def test_review_lifecycle_and_strict_resolution(self) -> None:
        segment = extract_segments({"blocks": [paragraph("Flow Ratio")]})[0]
        memory = TranslationMemory.empty()
        record = memory.create_draft(source_key=source_key(segment), source=segment.source_text, occurrence_id=segment.segment_id)
        self.assertEqual(synchronize([segment], memory).occurrences[0].status, "DRAFT")
        translations, issues = resolve([segment], memory)
        self.assertFalse(translations)
        self.assertTrue(issues)
        memory.update_target(record.record_id, "流量比")
        glossary = Glossary("zh-CN", [GlossaryTerm("flow", "Flow Ratio", "流量比", severity="error")])
        self.assertFalse(approve(memory, record.record_id, segment, reviewer="tester", glossary=glossary))
        self.assertEqual(memory.find(record.record_id).status, "approved")
        translations, issues = resolve([segment], memory)
        self.assertEqual(translations[segment.segment_id], "流量比")
        self.assertFalse(issues)
        memory.update_target(record.record_id, "修订流量比")
        reject(memory, record.record_id, reviewer="tester")
        self.assertEqual(memory.find(record.record_id).status, "rejected")
        reopen(memory, record.record_id, reviewer="tester")
        self.assertEqual(memory.find(record.record_id).status, "draft")

    def test_ambiguous_changed_and_obsolete_matching(self) -> None:
        original = extract_segments({"blocks": [paragraph("Original")]})[0]
        memory = TranslationMemory.empty()
        first = memory.create_draft(source_key=source_key(original), source=original.source_text, target="甲", context=original.context)
        second = memory.create_draft(source_key=source_key(original), source=original.source_text, target="乙", context=original.context)
        first.status = second.status = "approved"
        report = synchronize([original], memory)
        self.assertEqual(report.occurrences[0].status, "AMBIGUOUS")
        changed = extract_segments({"blocks": [paragraph("Changed")]})[0]
        previous = memory.create_draft(source_key=source_key(original), source=original.source_text, occurrence_id=changed.segment_id)
        self.assertEqual(synchronize([changed], memory).occurrences[0].status, "CHANGED")
        obsolete = memory.create_draft(source_key="sha256:obsolete", source="obsolete")
        report = synchronize([original], memory)
        self.assertIn(obsolete.record_id, report.obsolete_record_ids)

    def test_resolver_prefers_exact_occurrence_for_repeated_source(self) -> None:
        first = extract_segments({"blocks": [paragraph("Notes"), paragraph("Notes")]})[0]
        second = extract_segments({"blocks": [paragraph("Notes"), paragraph("Notes")]})[1]
        memory = TranslationMemory.empty()
        first_record = memory.create_draft(source_key=source_key(first), source=first.source_text, target="第一处", occurrence_id=first.segment_id)
        second_record = memory.create_draft(source_key=source_key(second), source=second.source_text, target="第二处", occurrence_id=second.segment_id)
        first_record.status = second_record.status = "approved"
        translations, issues = resolve([first, second], memory)
        self.assertFalse(issues)
        self.assertEqual(translations[first.segment_id], "第一处")
        self.assertEqual(translations[second.segment_id], "第二处")

    def test_atomic_json_storage_and_idempotent_drafts(self) -> None:
        segment = extract_segments({"blocks": [paragraph("New")]})[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.json"
            memory = TranslationMemory.empty()
            memory.create_draft(source_key=source_key(segment), source=segment.source_text, occurrence_id=segment.segment_id)
            memory.save(path)
            loaded = TranslationMemory.load(path)
            loaded.create_draft(source_key=source_key(segment), source=segment.source_text, occurrence_id=segment.segment_id)
            loaded.save(path)
            reloaded = TranslationMemory.load(path)
            self.assertEqual(len(reloaded.records), 1)
            self.assertEqual(reloaded.to_dict(), loaded.to_dict())

    def test_glossary_excludes_protected_tokens(self) -> None:
        source, placeholders = encode_inlines([{"t": "Str", "c": "Use"}, {"t": "Space"}, {"t": "Code", "c": ["Flow Ratio", ""]}])
        segment = Segment("s", source, "h", (), "Para", placeholders=placeholders)
        glossary = Glossary("zh-CN", [GlossaryTerm("flow", "Flow Ratio", "流量比", severity="error")])
        self.assertFalse(glossary.check(segment, source))

    def test_resolver_rebinds_placeholder_numbers_from_tm_metadata(self) -> None:
        payload = {"t": "Code", "c": ["220", ""]}
        old_placeholder = Placeholder("[[[p:1]]]", "p", "code-220", payload)
        current_placeholder = Placeholder("[[[p:3]]]", "p", "code-220", payload)
        old = Segment("old", "Set [[[p:1]]] to 220 °C.", "h1", (), "Para", placeholders=(old_placeholder,))
        current = Segment("current", "Set [[[p:3]]] to 220 °C.", "h2", (), "Para", placeholders=(current_placeholder,))
        memory = TranslationMemory.empty()
        record = memory.create_draft(
            source_key=source_key(old),
            source=old.source_text,
            target="设为 [[[p:1]]]。",
            source_placeholders=[item.to_dict() for item in old.placeholders],
        )
        record.status = "approved"
        translations, issues = resolve([current], memory)
        self.assertFalse(issues)
        self.assertEqual(translations[current.segment_id], "设为 [[[p:3]]]。")

    def test_resolver_fails_closed_for_legacy_protected_record_without_metadata(self) -> None:
        placeholder = Placeholder("[[[p:3]]]", "p", "code-220", {"t": "Code", "c": ["220", ""]})
        segment = Segment("s", "Value [[[p:3]]].", "h", (), "Para", placeholders=(
            placeholder,
        ))
        memory = TranslationMemory.empty()
        record = memory.create_draft(source_key=source_key(segment), source=segment.source_text, target="值 [[[p:3]]].")
        record.status = "approved"
        translations, issues = resolve([segment], memory)
        self.assertFalse(translations)
        self.assertTrue(any(item.code == "PLACEHOLDER_REBINDING_UNAVAILABLE" for item in issues))

    def test_real_sop_sync_is_incremental_and_does_not_touch_production_memory(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        ast = parse_ordered_markdown(repo / "sop" / "pdf-order.txt")
        segments = extract_segments(ast, source_file="sop/pdf-order.txt")
        memory = TranslationMemory.empty()
        first = synchronize(segments, memory)
        self.assertEqual(len(first.occurrences), len(segments))
        self.assertTrue(all(item.status == "MISSING" for item in first.occurrences))
        for item in segments:
            memory.create_draft(source_key=source_key(item), source=item.source_text, occurrence_id=item.segment_id)
        second = synchronize(segments, memory)
        self.assertTrue(all(item.status == "DRAFT" for item in second.occurrences))
        count = len(memory.records)
        for item in segments:
            memory.create_draft(source_key=source_key(item), source=item.source_text, occurrence_id=item.segment_id)
        self.assertEqual(len(memory.records), count)


if __name__ == "__main__":
    unittest.main()
