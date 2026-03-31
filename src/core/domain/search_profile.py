"""SearchProfile domain model — represents a single job search configuration."""

import os

from pydantic import BaseModel

from src.core.domain.date_posted import DatePosted
from src.core.domain.scraper_name import ScraperName
from src.core.domain.work_type import WorkType


class SearchProfile(BaseModel):
    """Represents a single job search configuration loaded from environment variables.

    Each profile defines an independent search with its own query, location,
    filters, and delivery preferences. Multiple profiles can run in sequence
    on each scheduled trigger.
    """

    profile_id: int
    """Profile number (1, 2, 3...)."""

    query: str
    """Job search query string."""

    location: str
    """Job search location."""

    work_types: list[WorkType] | None = None
    """Work type filter. None means no filter applied."""

    date_posted: DatePosted | None = None
    """Recency filter. None means no filter — default 3days applied at load time."""

    active_scrapers: list[ScraperName]
    """Scraper platforms to query. Default: all four."""

    score_threshold: int = 75
    """Minimum match score to include in results."""

    top_results: int | None = None
    """Cap on qualifying results delivered. None means all qualifying results."""

    @classmethod
    def from_env(cls, n: int) -> "SearchProfile":
        """Load profile N from environment variables using PROFILE_N_ prefix.

        Args:
            n: Profile number to load.

        Returns:
            A fully populated SearchProfile.

        Raises:
            ValueError: If PROFILE_N_QUERY is not set or location cannot be resolved.
        """
        prefix = f"PROFILE_{n}_"

        query = os.getenv(f"{prefix}QUERY")
        if not query:
            raise ValueError(
                f"PROFILE_{n}_QUERY is required but not set in .env"
            )

        work_type_raw = os.getenv(f"{prefix}WORK_TYPE")
        work_types = (
            [WorkType(w.strip().lower()) for w in work_type_raw.split(",")]
            if work_type_raw else None
        )

        date_posted_raw = os.getenv(f"{prefix}DATE_POSTED", "3days")
        date_posted = DatePosted.from_string(date_posted_raw)

        scrapers_raw = os.getenv(
            f"{prefix}SCRAPERS",
            "linkedin,indeed,glassdoor,ziprecruiter"
        )
        active_scrapers = ScraperName.parse_list(scrapers_raw)

        score_threshold = int(
            os.getenv(f"{prefix}SCORE_THRESHOLD", "75")
        )

        top_results_raw = os.getenv(f"{prefix}TOP_RESULTS")
        top_results = int(top_results_raw) if top_results_raw else None

        # Resolve location
        location_raw = os.getenv(f"{prefix}LOCATION")
        if not location_raw:
            if work_types and work_types == [WorkType.REMOTE]:
                location_raw = "United States"
            else:
                raise ValueError(
                    f"PROFILE_{n}_LOCATION is required when work type is not remote only"
                )

        return cls(
            profile_id=n,
            query=query,
            location=location_raw,
            work_types=work_types,
            date_posted=date_posted,
            active_scrapers=active_scrapers,
            score_threshold=score_threshold,
            top_results=top_results,
        )

    @classmethod
    def load_all(cls) -> list["SearchProfile"]:
        """Load all profiles from .env using PROFILE_COUNT to determine how many exist.

        Falls back to legacy single search mode if PROFILE_COUNT is not set.

        Returns:
            List of SearchProfile instances.

        Raises:
            ValueError: If neither PROFILE_COUNT nor SEARCH_QUERY is set.
        """
        profile_count_raw = os.getenv("PROFILE_COUNT")

        if profile_count_raw:
            count = int(profile_count_raw)
            return [cls.from_env(n) for n in range(1, count + 1)]

        # Legacy single search fallback
        query = os.getenv("SEARCH_QUERY")
        if not query:
            raise ValueError(
                "Either PROFILE_COUNT with PROFILE_N_QUERY variables or "
                "SEARCH_QUERY must be set in .env"
            )

        work_type_raw = os.getenv("WORK_TYPE")
        work_types = (
            [WorkType(w.strip().lower()) for w in work_type_raw.split(",")]
            if work_type_raw else None
        )

        date_posted_raw = os.getenv("DATE_POSTED", "3days")
        date_posted = DatePosted.from_string(date_posted_raw)

        scrapers_raw = os.getenv(
            "ACTIVE_SCRAPERS",
            "linkedin,indeed,glassdoor,ziprecruiter"
        )
        active_scrapers = ScraperName.parse_list(scrapers_raw)

        score_threshold = int(os.getenv("SCORE_THRESHOLD", "75"))

        top_results_raw = os.getenv("TOP_RESULTS")
        top_results = int(top_results_raw) if top_results_raw else None

        location_raw = os.getenv("SEARCH_LOCATION")
        if not location_raw:
            if work_types and work_types == [WorkType.REMOTE]:
                location_raw = "United States"
            else:
                raise ValueError(
                    "SEARCH_LOCATION is required when WORK_TYPE is not remote"
                )

        return [SearchProfile(
            profile_id=1,
            query=query,
            location=location_raw,
            work_types=work_types,
            date_posted=date_posted,
            active_scrapers=active_scrapers,
            score_threshold=score_threshold,
            top_results=top_results,
        )]
