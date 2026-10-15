from __future__ import annotations

import unittest

from sop_i18n.candidates import parse_response
from sop_i18n.glossary import Glossary
from sop_i18n.importer import import_drafts
from sop_i18n.jobs import jobs_payload, load_jobs, plan_jobs
from sop_i18n.memory import TranslationMemory
from sop_i18n.extract import extract_segments
from sop_i18n.qa import validate_candidate


class P3Tests(unittest.TestCase):
    def test_offline_plan_response_qa_and_draft_import(self) -> None:
        ast = {"blocks": [{"t": "Para", "c": [{"t": "Str", "c": "Set 220 °C."}]}]}
        segments = extract_segments(ast)
        memory = TranslationMemory.empty()
        glossary = Glossary("zh-CN", [])
        jobs = plan_jobs(segments, memory, glossary)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(load_jobs(jobs_payload(jobs))[0].job_id, jobs[0].job_id)
        candidates = parse_response({"schema_version": 1, "translations": [{"job_id": jobs[0].job_id, "target": "设置 220 °C。"}]}, jobs)
        self.assertFalse(validate_candidate(candidates[0], jobs[0], glossary))
        result = import_drafts(memory, jobs, candidates, glossary)
        self.assertEqual(len(result.imported), 1)
        self.assertEqual(memory.records[0].status, "draft")
        self.assertEqual(memory.records[0].target, "设置 220 °C。")

    def test_response_rejects_missing_duplicate_and_unknown_ids(self) -> None:
        ast = {"blocks": [{"t": "Para", "c": [{"t": "Str", "c": "One"}]}]}
        jobs = plan_jobs(extract_segments(ast), TranslationMemory.empty(), Glossary("zh-CN", []))
        with self.assertRaises(ValueError):
            parse_response({"schema_version": 1, "translations": []}, jobs)
        with self.assertRaises(ValueError):
            parse_response({"schema_version": 1, "translations": [{"job_id": "unknown", "target": "x"}]}, jobs)


if __name__ == "__main__":
    unittest.main()
