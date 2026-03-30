"""ScraperPort — abstract interface for all job platform scrapers."""

from abc import ABC, abstractmethod

from src.core.domain.date_posted import DatePosted
from src.core.domain.job import Job
from src.core.domain.work_type import WorkType


class ScraperPort(ABC):
    """Abstract base class defining the contract for platform scraper adapters."""

    @abstractmethod
    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
        work_types: list[WorkType] | None = None,
        date_posted: DatePosted | None = None,
    ) -> list[Job]:
        """Fetch job listings from a platform.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.
            work_types: Optional list of WorkType values to filter results by
                        work arrangement. When None all types are returned.
            date_posted: Optional recency filter. When None no date filter is applied.

        Returns:
            A list of validated Job domain entities.
        """
        ...
