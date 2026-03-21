"""Unit tests for the Anthropic Claude evaluator adapter."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from src.adapters.evaluator.anthropic_evaluator import ClaudeEvaluator
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


def _full_payload(
    score: int = 85,
    years_experience_detected: int | None = 7,
) -> dict:
    """Build a complete mock Claude response payload with all required fields."""
    return {
        "score": score,
        "seniority_level": "Senior/Staff",
        "years_experience_detected": years_experience_detected,
        "score_breakdown": {
            "role_alignment": {"max": 20, "earned": 18, "reasoning": "Strong alignment."},
            "technical_stack_match": {"max": 15, "earned": 13, "reasoning": "Good stack."},
            "system_design_architecture": {"max": 15, "earned": 11, "reasoning": "Solid design."},
            "impact_and_metrics": {"max": 15, "earned": 12, "reasoning": "Clear impact."},
            "domain_industry_experience": {"max": 10, "earned": 8, "reasoning": "Relevant."},
            "problem_space_relevance": {"max": 10, "earned": 7, "reasoning": "On point."},
            "ownership_and_leadership": {"max": 10, "earned": 9, "reasoning": "Strong ownership."},
            "resume_signal_quality": {"max": 3, "earned": 3, "reasoning": "Clean resume."},
            "career_trajectory": {"max": 2, "earned": 2, "reasoning": "Upward."},
        },
        "matched_skills": ["Python", "REST APIs"],
        "missing_skills": ["Kubernetes"],
        "summary": "Strong match with a gap in container orchestration.",
        "hire_recommendation": "Strong Yes",
    }


def make_mock_anthropic_response(payload: dict) -> MagicMock:
    """Build a mock Anthropic messages response."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [content_block]
    return response


@pytest.mark.asyncio
async def test_evaluate_returns_valid_match_result(sample_resume, sample_job):
    """Happy path — evaluate returns a validated MatchResult from Claude."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=make_mock_anthropic_response(_full_payload())
    )

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert isinstance(result, MatchResult)
    assert result.score == 85
    assert result.seniority_level == "Senior/Staff"
    assert result.years_experience_detected == 7
    assert result.hire_recommendation == "Strong Yes"
    assert result.score_breakdown.role_alignment.earned == 18
    assert result.score_breakdown.career_trajectory.max == 2
    assert "Python" in result.matched_skills
    assert "Kubernetes" in result.missing_skills
    assert result.job == sample_job


@pytest.mark.asyncio
async def test_evaluate_returns_default_on_api_error(sample_resume, sample_job):
    """Error handling — returns score 0 MatchResult when Anthropic API raises APIError."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        side_effect=anthropic.APIStatusError(
            "API unavailable",
            response=MagicMock(),
            body=None,
        )
    )

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0
    assert result.matched_skills == []
    assert result.missing_skills == []
    assert "failed" in result.summary.lower()


@pytest.mark.asyncio
async def test_evaluate_returns_default_on_invalid_json(sample_resume, sample_job):
    """Error handling — returns score 0 MatchResult when Claude returns malformed JSON."""
    content_block = MagicMock()
    content_block.text = "This is not JSON at all"
    response = MagicMock()
    response.content = [content_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=response)

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0


@pytest.mark.asyncio
async def test_evaluate_returns_default_on_validation_error(sample_resume, sample_job):
    """Error handling — returns score 0 when Claude JSON fails Pydantic validation."""
    payload = {"score": 999, "matched_skills": [], "missing_skills": [], "summary": "bad score"}

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=make_mock_anthropic_response(payload)
    )

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0


@pytest.mark.asyncio
async def test_rescue_fields_misplaced_in_score_breakdown(sample_resume, sample_job):
    """Rescue — fields nested inside score_breakdown are moved to top level."""
    payload = {
        "score": 75,
        "seniority_level": "Mid-Level",
        "years_experience_detected": 4,
        "score_breakdown": {
            "role_alignment": {"max": 20, "earned": 15, "reasoning": "Good."},
            "technical_stack_match": {"max": 15, "earned": 10, "reasoning": "Fine."},
            "system_design_architecture": {"max": 15, "earned": 10, "reasoning": "Ok."},
            "impact_and_metrics": {"max": 15, "earned": 10, "reasoning": "Good."},
            "domain_industry_experience": {"max": 10, "earned": 8, "reasoning": "Relevant."},
            "problem_space_relevance": {"max": 10, "earned": 7, "reasoning": "On point."},
            "ownership_and_leadership": {"max": 10, "earned": 9, "reasoning": "Solid."},
            "resume_signal_quality": {"max": 3, "earned": 3, "reasoning": "Clean."},
            "career_trajectory": {"max": 2, "earned": 2, "reasoning": "Upward."},
            # Misplaced — should be at top level
            "matched_skills": ["Python"],
            "missing_skills": ["Docker"],
            "summary": "Good match.",
            "hire_recommendation": "Yes",
        },
    }

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=make_mock_anthropic_response(payload)
    )

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert isinstance(result, MatchResult)
    assert result.score == 75
    assert "Python" in result.matched_skills
    assert "Docker" in result.missing_skills
    assert result.summary == "Good match."
    assert result.hire_recommendation == "Yes"


@pytest.mark.asyncio
async def test_strips_markdown_json_code_fence_from_response(sample_resume, sample_job):
    """Fence stripping — evaluate handles response wrapped in ```json...``` fences."""
    payload = _full_payload()
    content_block = MagicMock()
    content_block.text = f"```json\n{json.dumps(payload)}\n```"
    response = MagicMock()
    response.content = [content_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=response)

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert isinstance(result, MatchResult)
    assert result.score == 85
    assert result.score != 0


@pytest.mark.asyncio
async def test_strips_plain_code_fence_from_response(sample_resume, sample_job):
    """Fence stripping — evaluate handles response wrapped in plain ```...``` fences."""
    payload = _full_payload()
    content_block = MagicMock()
    content_block.text = f"```\n{json.dumps(payload)}\n```"
    response = MagicMock()
    response.content = [content_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=response)

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert isinstance(result, MatchResult)
    assert result.score == 85
    assert result.score != 0


@pytest.mark.asyncio
async def test_returns_default_on_empty_response(sample_resume, sample_job, caplog):
    """Error handling — returns score 0 MatchResult when response text is empty string."""
    import logging

    content_block = MagicMock()
    content_block.text = ""
    response = MagicMock()
    response.content = [content_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=response)

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    with caplog.at_level(logging.ERROR):
        result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0
    assert "failed" in result.summary.lower()
    assert any("error" in r.levelname.lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_returns_default_on_none_response(sample_resume, sample_job):
    """Error handling — returns score 0 MatchResult when response text is None."""
    content_block = MagicMock()
    content_block.text = None
    response = MagicMock()
    response.content = [content_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=response)

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    result = await evaluator.evaluate(resume=sample_resume, job=sample_job)

    assert result.score == 0
    assert result.matched_skills == []


@pytest.mark.asyncio
async def test_evaluate_uses_correct_model(sample_resume, sample_job):
    """Config — evaluate passes claude-sonnet-4-5 as the model."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=make_mock_anthropic_response(_full_payload())
    )

    evaluator = ClaudeEvaluator(api_key="test-key")
    evaluator._client = mock_client

    await evaluator.evaluate(resume=sample_resume, job=sample_job)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-5"
