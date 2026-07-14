"""Gemini pre-filter adapter — flags obvious junk before paid evaluation."""

import json
import logging

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from src.adapters.enrichment.prompts import SYSTEM_PROMPT, USER_PROMPT
from src.core.domain.enrichment_result import EnrichmentResult
from src.core.domain.job import Job
from src.core.ports.job_enrichment_port import JobEnrichmentPort

logger = logging.getLogger(__name__)

_MODEL = "gemini-3.5-flash"

# HTTP status returned by the Gemini API when a quota is exhausted.
_QUOTA_STATUS = 429

# HTTP status returned when the configured model does not exist for this key.
_MODEL_NOT_FOUND_STATUS = 404


class _PreFilterResponse(BaseModel):
    """Internal Pydantic model validating the Gemini JSON response."""

    should_skip: bool
    reason: str


class GeminiEnrichment(JobEnrichmentPort):
    """Pre-filters jobs with Gemini.

    Fail-open on any error (the job proceeds to normal evaluation). Two failures
    that would repeat identically for every job trip a circuit breaker that
    short-circuits the stage for the remainder of the run — a quota exhaustion
    (HTTP 429) and an unavailable model (HTTP 404) — so a single depleted key or a
    misconfigured model does not stall every subsequent job on a doomed API call,
    and the error is logged once rather than once per job.
    """

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Initialise the pre-filter with a Gemini API key.

        Args:
            api_key: Gemini API key loaded from environment.
            model: Optional model name override. Falls back to the default
                (gemini-3.5-flash) when None.
        """
        self._client = genai.Client(api_key=api_key)
        self._model = model or _MODEL
        self._quota_exhausted = False
        self._model_unavailable = False

    @property
    def circuit_broken(self) -> bool:
        """True once a circuit breaker (quota or unavailable model) has tripped."""
        return self._quota_exhausted or self._model_unavailable

    async def enrich(self, job: Job) -> EnrichmentResult:
        """Judge whether a job is obvious junk. Fail-open on any error.

        Args:
            job: The scraped job to inspect. No resume is passed — the port
                signature is the privacy boundary.

        Returns:
            An EnrichmentResult. On any error (or once the quota breaker has
            tripped) returns should_skip=False so the job is never dropped.
        """
        if self._quota_exhausted:
            return _fail_open("pre-filter disabled — Gemini quota exhausted this run")
        if self._model_unavailable:
            return _fail_open(f"pre-filter disabled — model {self._model!r} unavailable")

        prompt = USER_PROMPT.format(
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=_PreFilterResponse,
                ),
            )

            raw = (response.text or "").strip()
            if not raw:
                raise ValueError("Gemini returned empty response content")
            parsed = _PreFilterResponse(**json.loads(raw))

            if parsed.should_skip:
                logger.info(
                    "Pre-filter flagged %r @ %s to skip — %s",
                    job.title,
                    job.company,
                    parsed.reason,
                )
            return EnrichmentResult(should_skip=parsed.should_skip, reason=parsed.reason)

        except errors.APIError as exc:
            if exc.code == _QUOTA_STATUS:
                if not self._quota_exhausted:
                    self._quota_exhausted = True
                    logger.warning(
                        "Gemini quota exhausted — pre-filter circuit breaker tripped; "
                        "remaining jobs proceed to evaluation."
                    )
                return _fail_open("pre-filter skipped — Gemini quota exhausted")
            if exc.code == _MODEL_NOT_FOUND_STATUS:
                if not self._model_unavailable:
                    self._model_unavailable = True
                    logger.error(
                        "Gemini model %r unavailable (404) — set GEMINI_MODEL to a "
                        "supported model. Pre-filter disabled for the rest of this run.",
                        self._model,
                    )
                return _fail_open(f"pre-filter unavailable — model {self._model!r} not found")
            logger.error("Gemini API error pre-filtering %r: %s", job.title, exc)
            return _fail_open(f"pre-filter error — {exc}")
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            logger.error("Invalid Gemini pre-filter response for %r: %s", job.title, exc)
            return _fail_open(f"pre-filter invalid response — {exc}")
        except Exception as exc:
            logger.error("Unexpected pre-filter error for %r: %s", job.title, exc)
            return _fail_open(f"pre-filter unexpected error — {exc}")


def _fail_open(reason: str) -> EnrichmentResult:
    """Return a keep-the-job verdict used whenever the pre-filter cannot decide.

    Args:
        reason: Why the pre-filter failed open.

    Returns:
        An EnrichmentResult with should_skip=False and errored=True.
    """
    return EnrichmentResult(should_skip=False, reason=reason, errored=True)
