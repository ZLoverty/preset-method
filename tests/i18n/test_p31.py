from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sop_i18n.extract import extract_segments
from sop_i18n.glossary import Glossary
from sop_i18n.jobs import plan_jobs
from sop_i18n.memory import TranslationMemory
from sop_i18n.providers.openai import OpenAIProvider
from sop_i18n.providers.run import partition_jobs, run_resumable


class FakeResponse:
    status = 200
    def __init__(self, value: dict) -> None:
        self.value = value
    def read(self) -> bytes:
        return json.dumps(self.value).encode("utf-8")


class P31Tests(unittest.TestCase):
    def test_openai_provider_uses_structured_response_and_usage(self) -> None:
        ast = {"blocks": [{"t": "Para", "c": [{"t": "Str", "c": "Set 220 °C."}]}]}
        jobs = plan_jobs(extract_segments(ast), TranslationMemory.empty(), Glossary("zh-CN", []))
        calls = []
        def transport(request, timeout):
            calls.append((request, timeout))
            return FakeResponse({"status": "completed", "output_text": json.dumps({"schema_version": 1, "translations": [{"job_id": jobs[0].job_id, "target": "设置 220 °C。"}]}), "usage": {"input_tokens": 10, "output_tokens": 8, "total_tokens": 18}})
        provider = OpenAIProvider(model="test-model", api_key="test", prompt_path=Path("i18n/prompts/zh-CN-v1.txt"), transport=transport, max_retries=0)
        candidates = provider.translate(jobs)
        self.assertEqual(candidates[0].provenance["provider"], "openai")
        self.assertEqual(provider.usage.total_tokens, 18)
        request_body = json.loads(calls[0][0].data.decode("utf-8"))
        self.assertEqual(request_body["text"]["format"]["type"], "json_schema")

    def test_chat_completions_endpoint_uses_chat_schema(self) -> None:
        ast = {"blocks": [{"t": "Para", "c": [{"t": "Str", "c": "Set 220 C."}]}]}
        jobs = plan_jobs(extract_segments(ast), TranslationMemory.empty(), Glossary("zh-CN", []))
        calls = []
        def transport(request, timeout):
            calls.append(json.loads(request.data.decode("utf-8")))
            return FakeResponse({"choices": [{"message": {"content": json.dumps({"schema_version": 1, "translations": [{"job_id": jobs[0].job_id, "translated_text": "设置 220 C。", "source_key": "model-added-metadata"}]})}}], "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}})
        provider = OpenAIProvider(model="deepseek-chat", api_key="test", endpoint="https://api.deepseek.com/v1/chat/completions", prompt_path=Path("i18n/prompts/zh-CN-v1.txt"), transport=transport, max_retries=0)
        candidates = provider.translate(jobs)
        self.assertEqual(candidates[0].target, "设置 220 C。")
        self.assertIn("messages", calls[0])
        self.assertEqual(calls[0]["response_format"]["type"], "json_object")

    def test_partition_and_resume_skip_completed_batch(self) -> None:
        ast = {"blocks": [{"t": "Para", "c": [{"t": "Str", "c": "Set 220 °C."}]}]}
        jobs = plan_jobs(extract_segments(ast), TranslationMemory.empty(), Glossary("zh-CN", []))
        self.assertEqual(len(partition_jobs(jobs, max_jobs=1)), 1)
        response = {"status": "completed", "output_text": json.dumps({"schema_version": 1, "translations": [{"job_id": jobs[0].job_id, "target": "设置 220 °C。"}]})}
        with tempfile.TemporaryDirectory() as directory:
            provider = OpenAIProvider(model="test-model", api_key="test", transport=lambda request, timeout: FakeResponse(response), max_retries=0)
            first = run_resumable(provider, jobs, run_dir=Path(directory), glossary=Glossary("zh-CN", []), max_jobs=1)
            self.assertEqual(first["candidates"], 1)
            def should_not_call(request, timeout):
                raise AssertionError("completed batch was not reused")
            resumed = OpenAIProvider(model="test-model", api_key="test", transport=should_not_call, max_retries=0)
            second = run_resumable(resumed, jobs, run_dir=Path(directory), glossary=Glossary("zh-CN", []), max_jobs=1)
            self.assertEqual(second["batches_reused"], 1)

    def test_provider_reads_dotenv_without_executing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("API_KEY='dotenv-test-key'\nBROKEN=$(echo should-not-run)\n", encoding="utf-8")
            provider = OpenAIProvider(model="test-model", dotenv_path=env_file, transport=lambda request, timeout: None)
            self.assertEqual(provider.api_key, "dotenv-test-key")


if __name__ == "__main__":
    unittest.main()
