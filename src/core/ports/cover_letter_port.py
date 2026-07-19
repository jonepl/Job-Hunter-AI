"""CoverLetterPort — abstract interface for generating a cover letter (F).

A sibling of ``ResumeTailorPort`` (ADR-029 keeps them separate — the two have
genuinely different validation rules). An implementation sends the master resume
corpus, one job, and a ``VoiceDescriptor`` (ADR-030) to an LLM and returns a
structured ``CoverLetter``. The ``openai|anthropic`` allowlist is enforced in the
factory (CLAUDE.md #1); the port stays provider-agnostic.
"""

from abc import ABC, abstractmethod

from src.core.domain.cover_letter import CoverLetter
from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.domain.voice_descriptor import VoiceDescriptor


class CoverLetterPort(ABC):
    """Abstract base class defining the cover-letter generation contract."""

    @abstractmethod
    async def generate(
        self,
        resume: Resume,
        job: Job,
        voice: VoiceDescriptor,
        feedback: str | None = None,
    ) -> CoverLetter:
        """Generate a cover letter for ``job`` in the candidate's voice.

        Args:
            resume: The candidate's master resume corpus.
            job: The job the letter is for.
            voice: The structured voice descriptor (tone, person, style notes).
            feedback: Optional formatter-violation summary fed back on the single
                corrective retry (ADR-029); None on the first attempt.

        Returns:
            A structured CoverLetter.
        """
        ...
