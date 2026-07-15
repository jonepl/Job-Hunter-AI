"""Unit tests for build_enrichment() — the pre-filter factory."""

from unittest.mock import patch

from src.adapters.enrichment.factory import build_enrichment
from src.adapters.enrichment.gemini_enrichment import GeminiEnrichment


def test_returns_none_when_disabled(monkeypatch):
    """The pre-filter is off by default (ENRICHMENT_ENABLED not 'true')."""
    monkeypatch.delenv("ENRICHMENT_ENABLED", raising=False)

    assert build_enrichment() is None


def test_returns_none_when_enabled_but_no_key(monkeypatch):
    """Enabled but missing GEMINI_API_KEY degrades to disabled, not a crash."""
    monkeypatch.setenv("ENRICHMENT_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert build_enrichment() is None


def test_builds_adapter_when_enabled_with_key(monkeypatch):
    """Enabled with a key returns a GeminiEnrichment adapter."""
    monkeypatch.setenv("ENRICHMENT_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    with patch("src.adapters.enrichment.gemini_enrichment.genai.Client"):
        adapter = build_enrichment()

    assert isinstance(adapter, GeminiEnrichment)


def test_applies_model_override(monkeypatch):
    """GEMINI_MODEL overrides the adapter's default model."""
    monkeypatch.setenv("ENRICHMENT_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")

    with patch("src.adapters.enrichment.gemini_enrichment.genai.Client"):
        adapter = build_enrichment()

    assert adapter._model == "gemini-2.5-flash"


def test_enabled_is_case_insensitive(monkeypatch):
    """ENRICHMENT_ENABLED accepts 'TRUE' as truthy."""
    monkeypatch.setenv("ENRICHMENT_ENABLED", "TRUE")
    monkeypatch.setenv("GEMINI_API_KEY", "secret")

    with patch("src.adapters.enrichment.gemini_enrichment.genai.Client"):
        adapter = build_enrichment()

    assert isinstance(adapter, GeminiEnrichment)
