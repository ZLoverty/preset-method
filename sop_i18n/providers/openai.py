"""Small standard-library OpenAI Responses API adapter.

The adapter owns no TM state. It returns P3 candidates and usage metadata only.
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..candidates import TranslationCandidate, parse_response
from ..jobs import TranslationJob


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, status: int | None = None, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status = status
        self.retry_after = retry_after


@dataclass
class ProviderUsage:
    requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _dotenv_value(path: Path, names: tuple[str, ...]) -> str | None:
    """Read one simple KEY=value entry without executing the dotenv file."""
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() not in names:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value
    return None


RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "enum": [1]},
        "translations": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {"job_id": {"type": "string"}, "target": {"type": "string"}}, "required": ["job_id", "target"]}},
    },
    "required": ["schema_version", "translations"],
}


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, model: str, api_key: str | None = None, endpoint: str = "https://api.openai.com/v1/responses", prompt_path: Path = Path("i18n/prompts/zh-CN-v1.txt"), prompt_version: str = "zh-CN-v1", timeout: float = 120.0, max_retries: int = 3, initial_backoff: float = 1.0, max_backoff: float = 30.0, transport: Callable[..., Any] | None = None, dotenv_path: Path = Path(".env")) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY") or _dotenv_value(dotenv_path, ("OPENAI_API_KEY", "API_KEY"))
        if not self.api_key: raise ProviderError("OPENAI_API_KEY is not set")
        self.endpoint = endpoint
        self.prompt_path = prompt_path
        self.prompt_version = prompt_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.transport = transport or urllib.request.urlopen
        self.usage = ProviderUsage()

    def _request_body(self, jobs: list[TranslationJob]) -> dict[str, Any]:
        policy = self.prompt_path.read_text(encoding="utf-8")
        payload = [{"job_id": job.job_id, "source_key": job.source_key, "source_text": job.source_text, "source_placeholders": job.source_placeholders, "context": job.context, "glossary": job.glossary, "previous_translation": job.previous_translation} for job in jobs]
        return {"model": self.model, "instructions": policy, "input": json.dumps({"target_language": "zh-CN", "prompt_version": self.prompt_version, "jobs": payload}, ensure_ascii=False), "text": {"format": {"type": "json_schema", "name": "translation_response", "strict": True, "schema": RESPONSE_SCHEMA}}}

    def _call(self, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(self.endpoint, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            response = self.transport(request, timeout=self.timeout)
            raw = response.read()
            status = getattr(response, "status", 200)
            if status >= 400: raise ProviderError(f"OpenAI API HTTP {status}", retryable=status in {429, 500, 502, 503, 504}, status=status)
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            retryable = exc.code in {429, 500, 502, 503, 504}
            retry_after = None
            try: retry_after = float(exc.headers.get("Retry-After")) if exc.headers.get("Retry-After") else None
            except (TypeError, ValueError): pass
            raise ProviderError(f"OpenAI API HTTP {exc.code}", retryable=retryable, status=exc.code, retry_after=retry_after) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"OpenAI network error: {exc.reason}", retryable=True) from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("OpenAI returned invalid JSON", retryable=False) from exc

    @staticmethod
    def _output_text(response: dict[str, Any]) -> str:
        if isinstance(response.get("output_text"), str): return response["output_text"]
        chunks: list[str] = []
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str): chunks.append(content["text"])
        if not chunks: raise ProviderError("OpenAI response contained no output text")
        return "".join(chunks)

    def translate(self, jobs: list[TranslationJob]) -> list[TranslationCandidate]:
        if not jobs: return []
        body = self._request_body(jobs)
        started = time.monotonic(); last: ProviderError | None = None
        for attempt in range(self.max_retries + 1):
            self.usage.requests += 1
            try:
                response = self._call(body)
                if response.get("status") in {"failed", "cancelled", "incomplete"}: raise ProviderError("OpenAI response was incomplete", retryable=False)
                raw = json.loads(self._output_text(response))
                candidates = parse_response(raw, jobs, provider=self.name, model=self.model, prompt_version=self.prompt_version)
                usage = response.get("usage", {})
                self.usage.input_tokens += int(usage.get("input_tokens", 0) or 0); self.usage.output_tokens += int(usage.get("output_tokens", 0) or 0); self.usage.total_tokens += int(usage.get("total_tokens", 0) or 0)
                self.usage.successful_requests += 1; self.usage.elapsed_seconds += time.monotonic() - started
                return candidates
            except ProviderError as exc:
                last = exc; self.usage.failed_requests += 1
                if not exc.retryable or attempt >= self.max_retries: break
                self.usage.retries += 1
                delay = exc.retry_after if exc.retry_after is not None else min(self.max_backoff, self.initial_backoff * (2 ** attempt)) * (0.75 + random.random() * 0.5)
                time.sleep(delay)
        self.usage.elapsed_seconds += time.monotonic() - started
        raise last or ProviderError("OpenAI request failed")
