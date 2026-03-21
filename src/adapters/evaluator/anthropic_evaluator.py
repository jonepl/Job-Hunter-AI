"""Anthropic Claude evaluator adapter — scores resume-to-job match."""

import json
import logging

import anthropic
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.adapters.evaluator.prompts import SYSTEM_PROMPT, USER_PROMPT
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.resume import Resume
from src.core.ports.evaluator_port import EvaluatorPort

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-5"

_VALID_HIRE_RECOMMENDATIONS = frozenset({"Strong Yes", "Yes", "Borderline", "No"})

_RESCUE_FIELDS = frozenset({"matched_skills", "missing_skills", "summary", "hire_recommendation"})


class _EvaluationResponse(BaseModel):
    """Internal Pydantic model to validate Claude JSON responses."""

    score: int = Field(ge=0, le=100)
    seniority_level: str
    years_experience_detected: int | None
    score_breakdown: ScoreBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
    hire_recommendation: str

    @field_validator("hire_recommendation")
    @classmethod
    def validate_hire_recommendation(cls, v: str) -> str:
        """Validate hire_recommendation is one of the four expected values."""
        if v not in _VALID_HIRE_RECOMMENDATIONS:
            raise ValueError(
                f"hire_recommendation must be one of {_VALID_HIRE_RECOMMENDATIONS}, got {v!r}"
            )
        return v


def _zero_category(max_val: int) -> ScoreCategory:
    """Return a ScoreCategory with zero earned points for use in default results.

    Args:
        max_val: The maximum points for this category.

    Returns:
        A ScoreCategory with earned=0 and a failure reasoning message.
    """
    return ScoreCategory(max=max_val, earned=0, reasoning="Evaluation failed.")


def _default_result(job: Job) -> MatchResult:
    """Return a safe low-score MatchResult used when evaluation fails.

    Args:
        job: The job that could not be evaluated.

    Returns:
        A MatchResult with score 0 and safe default values for all fields.
    """
    return MatchResult(
        job=job,
        score=0,
        seniority_level="Unknown",
        years_experience_detected=None,
        hire_recommendation="No",
        score_breakdown=ScoreBreakdown(
            role_alignment=_zero_category(20),
            technical_stack_match=_zero_category(15),
            system_design_architecture=_zero_category(15),
            impact_and_metrics=_zero_category(15),
            domain_industry_experience=_zero_category(10),
            problem_space_relevance=_zero_category(10),
            ownership_and_leadership=_zero_category(10),
            resume_signal_quality=_zero_category(3),
            career_trajectory=_zero_category(2),
        ),
        matched_skills=[],
        missing_skills=[],
        summary="Evaluation failed — score set to 0.",
    )


def _rescue_misplaced_fields(data: dict) -> dict:
    """Rescue fields incorrectly nested inside score_breakdown.

    If matched_skills, missing_skills, summary, or hire_recommendation are
    absent at the top level but present inside score_breakdown, extract them
    to the top level before validation.

    Args:
        data: The raw parsed JSON dict from the LLM response.

    Returns:
        The data dict with misplaced fields moved to the top level.
    """
    breakdown = data.get("score_breakdown", {})
    for field in _RESCUE_FIELDS:
        if field not in data and field in breakdown:
            data[field] = breakdown.pop(field)
    return data


class ClaudeEvaluator(EvaluatorPort):
    """Evaluates job listings against a resume using Anthropic claude-sonnet-4-5."""

    def __init__(self, api_key: str) -> None:
        """Initialise the evaluator with an Anthropic API key.

        Args:
            api_key: Anthropic API key loaded from environment.
        """
        self._client = AsyncAnthropic(api_key=api_key)

    async def evaluate(
        self,
        resume: Resume,
        job: Job,
    ) -> MatchResult:
        """Evaluate a job listing against a resume using Claude.

        Sends the resume text and job description to claude-sonnet-4-5 and
        parses the JSON response into a MatchResult. Returns a default
        low-score result on any API or validation failure.

        Args:
            resume: The parsed candidate resume.
            job: The job listing to evaluate.

        Returns:
            A MatchResult containing score, breakdown, matched skills,
            missing skills, seniority level, and hire recommendation.
        """
        logger.info("Claude — evaluating %r", job.title)

        prompt = USER_PROMPT.format(
            resume_text=resume.raw_text,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
        )

        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            raw = response.content[0].text or ""
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            if not raw:
                raise ValueError("Claude returned empty response content")
            data = json.loads(raw)
            data = _rescue_misplaced_fields(data)
            logger.info("Claude raw response for %r: %s", job.title, data)
            evaluated = _EvaluationResponse(**data)

            return MatchResult(
                job=job,
                score=evaluated.score,
                seniority_level=evaluated.seniority_level,
                years_experience_detected=evaluated.years_experience_detected,
                score_breakdown=evaluated.score_breakdown,
                matched_skills=evaluated.matched_skills,
                missing_skills=evaluated.missing_skills,
                summary=evaluated.summary,
                hire_recommendation=evaluated.hire_recommendation,
            )

        except anthropic.APIError as exc:
            logger.error("Claude API error evaluating %r: %s", job.title, exc)
            return _default_result(job)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Invalid Claude response for %r: %s", job.title, exc)
            return _default_result(job)
        except Exception as exc:
            logger.error("Unexpected error evaluating %r: %s", job.title, exc)
            return _default_result(job)
