"""Unit tests for the generation factory — the hard provider allowlist (CLAUDE.md #1)."""

import pytest

from src.adapters.generation.anthropic_generation import ClaudeCoverLetter, ClaudeTailor
from src.adapters.generation.docx_writer import DocxWriter
from src.adapters.generation.factory import (
    build_cover_letter,
    build_docx_writer,
    build_resume_tailor,
)
from src.adapters.generation.openai_generation import OpenAICoverLetter, OpenAITailor


def test_openai_provider_builds_openai_adapters(monkeypatch):
    """TAILOR_PROVIDER=openai with a key builds the OpenAI adapters."""
    monkeypatch.setenv("TAILOR_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("TAILOR_MODEL", raising=False)

    assert isinstance(build_resume_tailor(), OpenAITailor)
    assert isinstance(build_cover_letter(), OpenAICoverLetter)


def test_anthropic_provider_builds_anthropic_adapters(monkeypatch):
    """TAILOR_PROVIDER=anthropic with a key builds the Claude adapters."""
    monkeypatch.setenv("TAILOR_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    assert isinstance(build_resume_tailor(), ClaudeTailor)
    assert isinstance(build_cover_letter(), ClaudeCoverLetter)


def test_model_override_is_applied(monkeypatch):
    """TAILOR_MODEL overrides the provider default on the built adapter."""
    monkeypatch.setenv("TAILOR_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("TAILOR_MODEL", "gpt-4o-mini")

    assert build_resume_tailor().model == "gpt-4o-mini"


def test_disallowed_provider_fails_at_startup(monkeypatch):
    """A provider outside the allowlist (e.g. gemini) exits at startup, not mid-run."""
    monkeypatch.setenv("TAILOR_PROVIDER", "gemini")
    with pytest.raises(SystemExit):
        build_resume_tailor()


def test_missing_api_key_fails_at_startup(monkeypatch):
    """An allowlisted provider with no API key exits at startup."""
    monkeypatch.setenv("TAILOR_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        build_cover_letter()


def test_build_docx_writer_returns_writer():
    """The docx writer is provider-independent and always builds."""
    assert isinstance(build_docx_writer(), DocxWriter)
