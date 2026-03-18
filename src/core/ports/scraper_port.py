"""ScraperPort — abstract interface for all job platform scrapers."""

from abc import ABC, abstractmethod

from src.core.domain.job import Job


class ScraperPort(ABC):
    """Abstract base class defining the contract for platform scraper adapters."""

    @abstractmethod
    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
    ) -> list[Job]:
        """Fetch job listings from a platform.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.

        Returns:
            A list of validated Job domain entities.
        """
        ...
