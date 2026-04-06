"""EvaluatorPort — abstract interface for resume-to-job evaluation adapters."""

from abc import ABC, abstractmethod

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume
from src.core.domain.work_type import WorkType


class EvaluatorPort(ABC):
    """Abstract base class defining the contract for evaluation adapters."""

    @abstractmethod
    async def evaluate(
        self,
        resume: Resume,
        job: Job,
        work_types: list[WorkType] | None = None,
    ) -> tuple[MatchResult, int, int]:
        """Evaluate a job listing against a resume.

        Args:
            resume: The parsed candidate resume.
            job: The job listing to evaluate.
            work_types: Optional work type filter context. Not used in
                        scoring — passed for potential future use.

        Returns:
            Tuple of:
                MatchResult — the evaluation result with score and breakdown.
                int — number of input tokens consumed.
                int — number of output tokens consumed.
        """
        ...
