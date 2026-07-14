"""Unit tests for the Gemini pre-filter adapter."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors

from src.adapters.enrichment.gemini_enrichment import _MODEL, GeminiEnrichment
from src.core.domain.job import Job


def _mock_response(should_skip: bool, reason: str) -> MagicMock:
    """Return a fake generate_content response carrying JSON text."""
    resp = MagicMock()
    resp.text = json.dumps({"should_skip": should_skip, "reason": reason})
    return resp


def _build(model=None):
    """Build a GeminiEnrichment with a patched genai client.

    Returns the adapter and the AsyncMock standing in for generate_content.
    """
    with patch("src.adapters.enrichment.gemini_enrichment.genai.Client") as client_cls:
        client = MagicMock()
        generate = AsyncMock()
        client.aio.models.generate_content = generate
        client_cls.return_value = client
        adapter = GeminiEnrichment(api_key="k", model=model)
    return adapter, generate


def test_init_defaults_to_module_model():
    """The adapter defaults to the module _MODEL when no override is given."""
    adapter, _ = _build()
    assert adapter._model == _MODEL


def test_init_accepts_model_override():
    """The adapter uses an explicit model override."""
    adapter, _ = _build(model="gemini-2.5-flash")
    assert adapter._model == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_enrich_returns_skip_verdict(sample_job: Job):
    """A should_skip=true response maps to an EnrichmentResult flagged to skip."""
    adapter, generate = _build()
    generate.return_value = _mock_response(True, "empty placeholder listing")

    result = await adapter.enrich(sample_job)

    assert result.should_skip is True
    assert result.reason == "empty placeholder listing"


@pytest.mark.asyncio
async def test_enrich_returns_keep_verdict(sample_job: Job):
    """A should_skip=false response maps to a keep verdict."""
    adapter, generate = _build()
    generate.return_value = _mock_response(False, "legitimate role")

    result = await adapter.enrich(sample_job)

    assert result.should_skip is False
    # A successful assessment is not an error, even when it keeps the job.
    assert result.errored is False


@pytest.mark.asyncio
async def test_enrich_uses_configured_model(sample_job: Job):
    """enrich sends the configured model name to the API."""
    adapter, generate = _build(model="gemini-2.5-flash")
    generate.return_value = _mock_response(False, "ok")

    await adapter.enrich(sample_job)

    assert generate.await_args.kwargs["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_enrich_never_sends_resume_data(sample_job: Job):
    """The request carries only job fields — the privacy boundary at the wire."""
    adapter, generate = _build()
    generate.return_value = _mock_response(False, "ok")

    await adapter.enrich(sample_job)

    contents = generate.await_args.kwargs["contents"]
    assert sample_job.title in contents
    assert sample_job.description in contents
    assert "resume" not in contents.lower()


@pytest.mark.asyncio
async def test_enrich_fails_open_on_api_error(sample_job: Job):
    """A non-quota API error fails open (keep the job) and flags errored."""
    adapter, generate = _build()
    generate.side_effect = errors.APIError(500, {"error": {"message": "boom"}})

    result = await adapter.enrich(sample_job)

    assert result.should_skip is False
    assert result.errored is True
    assert adapter.circuit_broken is False


@pytest.mark.asyncio
async def test_model_not_found_trips_breaker_and_logs_once(sample_job: Job):
    """A 404 disables the pre-filter for the run without re-hitting the API."""
    adapter, generate = _build()
    generate.side_effect = errors.APIError(
        404, {"error": {"message": "model unavailable", "status": "NOT_FOUND"}}
    )

    first = await adapter.enrich(sample_job)

    assert first.should_skip is False
    assert first.errored is True
    assert adapter.circuit_broken is True
    assert generate.await_count == 1

    # A second job short-circuits — the model is known-bad, no further API calls.
    second = await adapter.enrich(sample_job)

    assert second.should_skip is False
    assert generate.await_count == 1


@pytest.mark.asyncio
async def test_enrich_fails_open_on_invalid_json(sample_job: Job):
    """A malformed response fails open rather than crashing the run."""
    adapter, generate = _build()
    bad = MagicMock()
    bad.text = "not json at all"
    generate.return_value = bad

    result = await adapter.enrich(sample_job)

    assert result.should_skip is False
    assert result.errored is True


@pytest.mark.asyncio
async def test_quota_error_trips_circuit_breaker(sample_job: Job):
    """A 429 trips the breaker and short-circuits later jobs without another call."""
    adapter, generate = _build()
    generate.side_effect = errors.APIError(
        429, {"error": {"message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}}
    )

    first = await adapter.enrich(sample_job)

    assert first.should_skip is False
    assert adapter.circuit_broken is True
    assert generate.await_count == 1

    # A second job must not hit the API again — the breaker is open.
    second = await adapter.enrich(sample_job)

    assert second.should_skip is False
    assert generate.await_count == 1
