"""EvaluatorPort — abstract interface for resume-to-job evaluation adapters."""

from abc import ABC, abstractmethod

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume


class EvaluatorPort(ABC):
    """Abstract base class defining the contract for evaluation adapters."""

    @abstractmethod
    async def evaluate(
        self,
        resume: Resume,
        job: Job,
    ) -> MatchResult:
        """Evaluate a job listing against a resume.

        Args:
            resume: The parsed candidate resume.
            job: The job listing to evaluate.

        Returns:
            A MatchResult containing the score, matched skills,
            missing skills, and summary.
        """
        ...
