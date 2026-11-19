"""Tests for the LLM client, using a fake OpenAI client: no network, no tokens."""
import json
from types import SimpleNamespace

import httpx
import pytest
from openai import RateLimitError

import app.generation.llm as llm_module
from app.generation.llm import LLMError, OpenAICompatibleLLM

MESSAGES = [{"role": "user", "content": "How many VPN sessions can I have?"}]


class FakeClient:
    """Mimics client.chat.completions.create() and remembers what it was sent."""

    def __init__(self, content="  At most 2 sessions.  ", finish_reason="stop", error=None):
        self.sent = None
        self._content, self._finish_reason, self._error = content, finish_reason, error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.sent = kwargs
        if self._error:
            raise self._error
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason=self._finish_reason)],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120),
        )


def make_llm(client, tmp_path, **options):
    return OpenAICompatibleLLM(client=client, model="test-model", usage_log=tmp_path / "usage.jsonl", **options)


def test_returns_answer_text(tmp_path):
    assert make_llm(FakeClient(), tmp_path).complete(MESSAGES) == "At most 2 sessions."


def test_sends_model_messages_and_limits(tmp_path):
    client = FakeClient()
    make_llm(client, tmp_path, reasoning_effort="low", max_tokens=500).complete(MESSAGES)
    assert client.sent == {
        "model": "test-model",
        "messages": MESSAGES,
        "max_completion_tokens": 500,
        "reasoning_effort": "low",
    }


def test_no_reasoning_effort_when_empty(tmp_path):
    client = FakeClient()
    make_llm(client, tmp_path, reasoning_effort="").complete(MESSAGES)
    assert "reasoning_effort" not in client.sent


def test_logs_token_usage(tmp_path):
    make_llm(FakeClient(), tmp_path).complete(MESSAGES)
    [entry] = [json.loads(line) for line in (tmp_path / "usage.jsonl").read_text().splitlines()]
    assert entry["model"] == "test-model"
    assert entry["total_tokens"] == 120


def test_empty_answer_raises(tmp_path):
    # Reasoning models can spend the whole token budget thinking and return no text.
    with pytest.raises(LLMError, match="finish_reason: length"):
        make_llm(FakeClient(content=None, finish_reason="length"), tmp_path).complete(MESSAGES)


def test_rate_limit_raises_clear_error(tmp_path):
    response = httpx.Response(429, request=httpx.Request("POST", "https://example.test"))
    error = RateLimitError("Rate limit reached: tokens per day (TPD)", response=response, body=None)
    with pytest.raises(LLMError, match="Rate limit reached for test-model"):
        make_llm(FakeClient(error=error), tmp_path).complete(MESSAGES)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(llm_module, "LLM_API_KEY", "")
    with pytest.raises(LLMError, match="LLM_API_KEY is not set"):
        OpenAICompatibleLLM()
