"""Unit tests for the EnrichmentResult domain entity."""

import pytest
from pydantic import ValidationError

from src.core.domain.enrichment_result import EnrichmentResult


def test_enrichment_result_holds_verdict_and_reason():
    """EnrichmentResult stores the skip verdict and its reason."""
    result = EnrichmentResult(should_skip=True, reason="empty description")

    assert result.should_skip is True
    assert result.reason == "empty description"


def test_enrichment_result_keep_verdict():
    """EnrichmentResult supports a keep (should_skip=False) verdict."""
    result = EnrichmentResult(should_skip=False, reason="looks legitimate")

    assert result.should_skip is False


def test_enrichment_result_errored_defaults_false():
    """A normal verdict is not an error."""
    result = EnrichmentResult(should_skip=False, reason="ok")

    assert result.errored is False


def test_enrichment_result_can_flag_errored():
    """A fail-open fallback marks errored=True."""
    result = EnrichmentResult(should_skip=False, reason="api error", errored=True)

    assert result.errored is True


def test_enrichment_result_requires_reason():
    """reason is mandatory — a flag is never applied without a justification."""
    with pytest.raises(ValidationError):
        EnrichmentResult(should_skip=True)
