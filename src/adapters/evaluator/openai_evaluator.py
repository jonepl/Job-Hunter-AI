"""OpenAI GPT-4o evaluator adapter — scores resume-to-job match."""

import json
import logging

from openai import APIError, AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume
from src.core.ports.evaluator_port import EvaluatorPort

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o"

_SYSTEM_PROMPT = """You are an expert technical recruiter and resume evaluator.
Given a candidate resume and a job description, evaluate how well the candidate
matches the role. Respond only with valid JSON in the exact schema provided."""

_USER_PROMPT = """Evaluate the match between the following resume and job description.

RESUME:
{resume_text}

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION:
{job_description}

Respond with a JSON object using exactly this schema:
{{
    "score": <integer 0-100 representing overall match strength>,
    "matched_skills": [<list of skills/keywords present in both resume and job>],
    "missing_skills": [<list of skills required by job but absent from resume>],
    "summary": "<one to two sentence summary of the match>"
}}"""


class _EvaluationResponse(BaseModel):
    """Internal Pydantic model to validate GPT-4o JSON responses."""

    score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str


def _default_result(job: Job) -> MatchResult:
    """Return a safe low-score MatchResult used when evaluation fails.

    Args:
        job: The job that could not be evaluated.

    Returns:
        A MatchResult with score 0 and an error summary.
    """
    return MatchResult(
        job=job,
        score=0,
        matched_skills=[],
        missing_skills=[],
        summary="Evaluation failed — score set to 0.",
    )


class OpenAIEvaluator(EvaluatorPort):
    """Evaluates job listings against a resume using OpenAI GPT-4o."""

    def __init__(self, api_key: str) -> None:
        """Initialise the evaluator with an OpenAI API key.

        Args:
            api_key: OpenAI API key loaded from environment.
        """
        self._client = AsyncOpenAI(api_key=api_key)

    async def evaluate(
        self,
        resume: Resume,
        job: Job,
    ) -> MatchResult:
        """Evaluate a job listing against a resume using GPT-4o.

        Sends the resume text and job description to GPT-4o and parses the
        structured JSON response into a MatchResult. Returns a default
        low-score result on any API or validation failure.

        Args:
            resume: The parsed candidate resume.
            job: The job listing to evaluate.

        Returns:
            A MatchResult containing score, matched skills, missing skills,
            and a summary.
        """
        prompt = _USER_PROMPT.format(
            resume_text=resume.raw_text,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
        )

        try:
            response = await self._client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            raw = response.choices[0].message.content or ""
            data = json.loads(raw)
            evaluated = _EvaluationResponse(**data)

            return MatchResult(
                job=job,
                score=evaluated.score,
                matched_skills=evaluated.matched_skills,
                missing_skills=evaluated.missing_skills,
                summary=evaluated.summary,
            )

        except APIError as exc:
            logger.error("OpenAI API error evaluating %r: %s", job.title, exc)
            return _default_result(job)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Invalid GPT-4o response for %r: %s", job.title, exc)
            return _default_result(job)
        except Exception as exc:
            logger.error("Unexpected error evaluating %r: %s", job.title, exc)
            return _default_result(job)
