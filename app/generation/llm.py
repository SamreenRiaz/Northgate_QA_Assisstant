"""Talk to the language model. This is the only module that knows which LLM provider we use.

It speaks the OpenAI-compatible chat API, so Groq, Gemini, Ollama or OpenAI work by
changing .env only. A provider with its own API would get its own class here.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Protocol

from openai import OpenAI, RateLimitError

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_REASONING_EFFORT,
    USAGE_LOG_PATH,
)

Message = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


class LLMError(Exception):
    """The model could not produce an answer (missing key, rate limit, empty reply)."""


class LLM(Protocol):
    """What the rest of the app needs from any language model (the real one or a test fake)."""

    def complete(self, messages: list[Message]) -> str: ...


class OpenAICompatibleLLM:
    def __init__(
        self,
        client: OpenAI | None = None,
        model: str = LLM_MODEL,
        reasoning_effort: str = LLM_REASONING_EFFORT,
        max_tokens: int = LLM_MAX_TOKENS,
        usage_log: Path = USAGE_LOG_PATH,
    ) -> None:
        if client is None:
            if not LLM_API_KEY:
                raise LLMError("LLM_API_KEY is not set. Copy .env.example to .env and add your key.")
            # The SDK retries rate-limited and failed requests itself, waiting as the server asks.
            client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, max_retries=3)
        self._client = client
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._max_tokens = max_tokens
        self._usage_log = usage_log

    def complete(self, messages: list[Message]) -> str:
        """Send the conversation, return the model's answer text."""
        options = {"reasoning_effort": self._reasoning_effort} if self._reasoning_effort else {}
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_completion_tokens=self._max_tokens,
                **options,
            )
        except RateLimitError as error:
            raise LLMError(f"Rate limit reached for {self._model} (it may be the daily limit): {error}") from error

        self._log_usage(response.usage)
        choice = response.choices[0]
        if not choice.message.content:
            raise LLMError(f"The model returned no answer (finish_reason: {choice.finish_reason}).")
        return choice.message.content.strip()

    def _log_usage(self, usage) -> None:
        """Append this call's token counts to a JSON Lines log, to keep track of the daily budget."""
        if usage is None:
            return
        self._usage_log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "model": self._model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
        with open(self._usage_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
