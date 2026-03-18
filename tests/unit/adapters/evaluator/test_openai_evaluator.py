"""Unit tests for the OpenAI GPT-4o evaluator adapter."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIError

from src.adapters.evaluator.openai_evaluator import OpenAIEvaluator
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume


@pytest.fixture
def sample_resume() -> Resume:
    """Return a valid Resume fixture."""
    return Resume(
        raw_text="Experienced Python developer with 5 years of backend experience.",
        parsed_at=datetime(2026, 3, 17, 9, 0, 0),
    )


@pytest.fixture
def sample_job() -> Job:
    """Return a valid Job fixture."""
    return Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="We need a Python expert with REST API experience.",
        platform="linkedin",
        scraped_at=datetime(2026, 3, 17, 9, 0, 0),
    )


def make_mock_openai_response(payload: dict) -> MagicMock:
    """Build a mock OpenAI chat completion response."""
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_evaluate_returns_valid_match_result(sample_resume, sample_job):
    """Happy path — evaluate returns a validated MatchResult from GPT-4o."""
    payload = {
        "score": 85,
        "matched_skills": ["Python", "REST APIs"],
        "missing_skills": ["Kubernetes"],
        "summary": "Strong match with a gap in container orchestration.",
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_mock_openai_response(payload)
    )

    evaluator = OpenAIEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert isinstance(result, MatchResult)
    assert result.score == 85
    assert "Python" in result.matched_skills
    assert "Kubernetes" in result.missing_skills
    assert result.job == sample_job


@pytest.mark.asyncio
async def test_evaluate_returns_default_result_on_api_error(sample_resume, sample_job):
    """Error handling — returns score 0 MatchResult when OpenAI API raises APIError."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=APIError("API unavailable", request=MagicMock(), body=None)
    )

    evaluator = OpenAIEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0
    assert result.matched_skills == []
    assert result.missing_skills == []
    assert "failed" in result.summary.lower()


@pytest.mark.asyncio
async def test_evaluate_returns_default_result_on_malformed_json(sample_resume, sample_job):
    """Error handling — returns score 0 MatchResult when GPT-4o returns invalid JSON."""
    message = MagicMock()
    message.content = "This is not JSON at all"
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=response)

    evaluator = OpenAIEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0


@pytest.mark.asyncio
async def test_evaluate_returns_default_result_on_invalid_schema(sample_resume, sample_job):
    """Error handling — returns score 0 when GPT-4o JSON fails Pydantic validation."""
    payload = {"score": 999, "matched_skills": [], "missing_skills": [], "summary": "bad score"}

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_mock_openai_response(payload)
    )

    evaluator = OpenAIEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0
