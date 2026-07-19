"""ResumeTailorPort — abstract interface for tailoring a resume to one job (F).

An implementation sends the master resume corpus (ADR-028) and one job description
to an LLM and returns a structured ``TailoredResume`` (not a text blob — ADR-029).
Generation ports hard-allowlist ``openai|anthropic`` and fail at startup on any
other provider (CLAUDE.md #1); that allowlist is enforced in the factory, so the
port itself stays provider-agnostic. The core sees only this port.
"""

from abc import ABC, abstractmethod

from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.domain.tailored_resume import TailoredResume


class ResumeTailorPort(ABC):
    """Abstract base class defining the resume-tailoring contract."""

    @abstractmethod
    async def tailor(
        self,
        resume: Resume,
        job: Job,
        feedback: str | None = None,
    ) -> TailoredResume:
        """Tailor ``resume`` to ``job``, returning structured content to render.

        Args:
            resume: The candidate's master resume corpus.
            job: The job the resume is being tailored to.
            feedback: Optional formatter-violation summary fed back on the single
                corrective retry (ADR-029); None on the first attempt.

        Returns:
            A structured TailoredResume.
        """
        ...
