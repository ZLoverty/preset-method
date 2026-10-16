from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sop_i18n.canonical import source_key
from sop_i18n.candidates import TranslationCandidate, candidates_payload
from sop_i18n.jobs import TranslationJob, jobs_payload
from sop_i18n.memory import TranslationMemory
from sop_i18n.models import Segment
from sop_i18n.review_ui import ReviewApp


class ReviewUITests(unittest.TestCase):
    def test_existing_approved_source_is_hidden_from_candidate_filter_and_approval_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segment = Segment("seg-2", "Repeated source", "", (), "Para", {})
            key = source_key(segment)
            job = TranslationJob("job-2", "zh-CN", key, segment.segment_id, segment.source_text, {}, [], [], [segment.segment_id])
            candidate = TranslationCandidate(job.job_id, key, "zh-CN", "重复译文", {"provider": "test"})
            memory = TranslationMemory.empty()
            approved = memory.create_draft(source_key=key, source=segment.source_text, target="已有译文", occurrence_id="seg-1")
            approved.status = "approved"
            memory.save(root / "memory.json")
            (root / "jobs.json").write_text(json.dumps(jobs_payload([job]), ensure_ascii=False), encoding="utf-8")
            (root / "candidates.json").write_text(json.dumps(candidates_payload([candidate]), ensure_ascii=False), encoding="utf-8")
            (root / "glossary.json").write_text('{"schema_version": 1, "language": "zh-CN", "terms": []}\n', encoding="utf-8")

            app = ReviewApp(root / "jobs.json", root / "candidates.json", root / "memory.json", root / "glossary.json")
            self.assertEqual(app.state()["items"][0]["status"], "duplicate")
            result = app.update(job.job_id, candidate.target, "approve", "tester")
            self.assertIn("跳过重复候选", result["message"])
            self.assertEqual(TranslationMemory.load(root / "memory.json").find(approved.record_id).target, "已有译文")


if __name__ == "__main__":
    unittest.main()
