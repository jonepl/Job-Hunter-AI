"""OpenAI GPT-4o evaluator adapter — scores resume-to-job match."""

import json
import logging

from openai import APIError, AsyncOpenAI, NotFoundError
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.adapters.evaluator.prompts import SYSTEM_PROMPT, USER_PROMPT
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult, ScoreBreakdown, ScoreCategory
from src.core.domain.resume import Resume
from src.core.domain.work_type import WorkType
from src.core.exceptions import ModelNotFoundError
from src.core.ports.evaluator_port import EvaluatorPort

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o"

_VALID_HIRE_RECOMMENDATIONS = frozenset({"Strong Yes", "Yes", "Borderline", "No"})


class _EvaluationResponse(BaseModel):
    """Internal Pydantic model to validate GPT-4o JSON responses."""

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


class OpenAIEvaluator(EvaluatorPort):
    """Evaluates job listings against a resume using OpenAI GPT-4o."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Initialise the evaluator with an OpenAI API key.

        Args:
            api_key: OpenAI API key loaded from environment.
            model: Optional model name override. Falls back to the default
                (gpt-4o) when None.
        """
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model or _MODEL

    async def evaluate(
        self,
        resume: Resume,
        job: Job,
        work_types: list[WorkType] | None = None,
    ) -> tuple[MatchResult, int, int]:
        """Evaluate a job listing against a resume using GPT-4o.

        Sends the resume text and job description to GPT-4o and parses the
        structured JSON response into a MatchResult. Returns a default
        low-score result on any API or validation failure.

        Args:
            resume: The parsed candidate resume.
            job: The job listing to evaluate.
            work_types: Optional work type filter context (unused in scoring).

        Returns:
            Tuple of (MatchResult, input_tokens, output_tokens).
            On failure returns (default_result, 0, 0).
        """
        logger.info("OpenAI — evaluating %r @ %s", job.title, job.company)

        prompt = USER_PROMPT.format(
            resume_text=resume.raw_text,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "evaluation_response",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "integer"},
                                "seniority_level": {"type": "string"},
                                "years_experience_detected": {
                                    "anyOf": [{"type": "integer"}, {"type": "null"}]
                                },
                                "score_breakdown": {
                                    "type": "object",
                                    "properties": {
                                        "role_alignment": {"$ref": "#/$defs/ScoreCategory"},
                                        "technical_stack_match": {"$ref": "#/$defs/ScoreCategory"},
                                        "system_design_architecture": {
                                            "$ref": "#/$defs/ScoreCategory"
                                        },
                                        "impact_and_metrics": {"$ref": "#/$defs/ScoreCategory"},
                                        "domain_industry_experience": {
                                            "$ref": "#/$defs/ScoreCategory"
                                        },
                                        "problem_space_relevance": {
                                            "$ref": "#/$defs/ScoreCategory"
                                        },
                                        "ownership_and_leadership": {
                                            "$ref": "#/$defs/ScoreCategory"
                                        },
                                        "resume_signal_quality": {"$ref": "#/$defs/ScoreCategory"},
                                        "career_trajectory": {"$ref": "#/$defs/ScoreCategory"},
                                    },
                                    "required": [
                                        "role_alignment",
                                        "technical_stack_match",
                                        "system_design_architecture",
                                        "impact_and_metrics",
                                        "domain_industry_experience",
                                        "problem_space_relevance",
                                        "ownership_and_leadership",
                                        "resume_signal_quality",
                                        "career_trajectory",
                                    ],
                                    "additionalProperties": False,
                                },
                                "matched_skills": {"type": "array", "items": {"type": "string"}},
                                "missing_skills": {"type": "array", "items": {"type": "string"}},
                                "summary": {"type": "string"},
                                "hire_recommendation": {
                                    "type": "string",
                                    "enum": ["Strong Yes", "Yes", "Borderline", "No"],
                                },
                            },
                            "required": [
                                "score",
                                "seniority_level",
                                "years_experience_detected",
                                "score_breakdown",
                                "matched_skills",
                                "missing_skills",
                                "summary",
                                "hire_recommendation",
                            ],
                            "additionalProperties": False,
                            "$defs": {
                                "ScoreCategory": {
                                    "type": "object",
                                    "properties": {
                                        "max": {"type": "integer"},
                                        "earned": {"type": "integer"},
                                        "reasoning": {"type": "string"},
                                    },
                                    "required": ["max", "earned", "reasoning"],
                                    "additionalProperties": False,
                                }
                            },
                        },
                    },
                },
                temperature=0.2,
            )

            raw = response.choices[0].message.content or ""
            data = json.loads(raw)
            evaluated = _EvaluationResponse(**data)

            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            return (
                MatchResult(
                    job=job,
                    score=evaluated.score,
                    seniority_level=evaluated.seniority_level,
                    years_experience_detected=evaluated.years_experience_detected,
                    score_breakdown=evaluated.score_breakdown,
                    matched_skills=evaluated.matched_skills,
                    missing_skills=evaluated.missing_skills,
                    summary=evaluated.summary,
                    hire_recommendation=evaluated.hire_recommendation,
                ),
                input_tokens,
                output_tokens,
            )

        except NotFoundError as exc:
            raise ModelNotFoundError(
                f"OpenAI model {self._model!r} not found. Check EVALUATOR_MODEL "
                f"(or --evaluator-model), or unset it to use the default."
            ) from exc
        except APIError as exc:
            logger.error("OpenAI API error evaluating %r: %s", job.title, exc)
            return _default_result(job), 0, 0
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Invalid GPT-4o response for %r: %s", job.title, exc)
            return _default_result(job), 0, 0
        except Exception as exc:
            logger.error("Unexpected error evaluating %r: %s", job.title, exc)
            return _default_result(job), 0, 0
