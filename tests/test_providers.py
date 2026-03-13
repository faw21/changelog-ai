"""Tests for providers module."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from changelog_ai.providers import create_provider, ClaudeProvider, OpenAIProvider, OllamaProvider


class TestCreateProvider:
    def test_creates_claude_provider(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        p = create_provider("claude")
        assert isinstance(p, ClaudeProvider)

    def test_creates_openai_provider(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake")
        p = create_provider("openai")
        assert isinstance(p, OpenAIProvider)

    def test_creates_ollama_provider(self):
        p = create_provider("ollama")
        assert isinstance(p, OllamaProvider)

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("invalid")

    def test_missing_anthropic_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(KeyError):
            create_provider("claude")

    def test_missing_openai_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(KeyError):
            create_provider("openai")

    def test_custom_model_passed(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        p = create_provider("claude", "claude-opus-4-6")
        assert p._model == "claude-opus-4-6"
