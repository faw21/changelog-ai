"""LLM provider adapters for changelog-ai."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        ...


class ClaudeProvider(LLMProvider):
    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic
        import os
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise KeyError("ANTHROPIC_API_KEY")
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model

    def complete(self, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        import openai
        import os
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise KeyError("OPENAI_API_KEY")
        self._client = openai.OpenAI(api_key=key)
        self._model = model

    def complete(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=2048,
        )
        return resp.choices[0].message.content.strip()


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.2") -> None:
        import openai
        self._client = openai.OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
        self._model = model

    def complete(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=2048,
        )
        return resp.choices[0].message.content.strip()


def create_provider(provider: str, model: str | None = None) -> LLMProvider:
    if provider == "claude":
        return ClaudeProvider(model or "claude-haiku-4-5-20251001")
    if provider == "openai":
        return OpenAIProvider(model or "gpt-4o-mini")
    if provider == "ollama":
        return OllamaProvider(model or "llama3.2")
    raise ValueError(f"Unknown provider: {provider!r}. Choose: claude, openai, ollama")
