"""JobEnrichmentPort — abstract interface for the pre-filter stage.

The signature is the privacy boundary. `enrich` accepts only a `Job` and never a
`Resume`: personal data is structurally prevented from reaching the pre-filter
adapter (ADR-022). Do not add a `Resume` parameter to this contract.
"""

from abc import ABC, abstractmethod

from src.core.domain.enrichment_result import EnrichmentResult
from src.core.domain.job import Job


class JobEnrichmentPort(ABC):
    """Abstract base class defining the contract for pre-filter adapters."""

    @abstractmethod
    async def enrich(self, job: Job) -> EnrichmentResult:
        """Judge whether a job is obviously irrelevant before paid evaluation.

        Implementations must be **fail-open**: any error returns a verdict of
        ``should_skip=False`` so a pre-filter failure never drops a real job.

        Args:
            job: The scraped job listing to inspect. No resume or other personal
                data is passed — this is the structural privacy boundary.

        Returns:
            An EnrichmentResult carrying the skip verdict and its reason.
        """
        ...
