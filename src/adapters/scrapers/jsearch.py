"""JSearch scraper adapter — fetches job listings via the JSearch API (RapidAPI).

Used for Indeed, Glassdoor, and ZipRecruiter. Direct scraping for all three
platforms is non-viable due to bot detection (TLS fingerprinting, Cloudflare,
and JS cookie challenges respectively). JSearch is the permanent primary source.
"""

import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from src.core.domain.date_posted import DatePosted
from src.core.domain.job import Job
from src.core.domain.work_type import WorkType
from src.core.ports.scraper_port import ScraperPort

load_dotenv()

logger = logging.getLogger(__name__)

_JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
_REQUEST_TIMEOUT = 30


class JSearchScraper(ScraperPort):
    """Fetches job listings via the JSearch API for a given platform."""

    def __init__(self, platform: str) -> None:
        """Initialise the scraper for the specified platform.

        Args:
            platform: Platform label stamped on each Job (e.g. "indeed",
                "glassdoor", "ziprecruiter").
        """
        self.platform = platform

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
        work_types: list[WorkType] | None = None,
        date_posted: DatePosted | None = None,
    ) -> list[Job]:
        """Fetch job listings via the JSearch API.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.
            work_types: Optional list of WorkType values to filter results by
                        work arrangement. When None all types are returned.
            date_posted: Optional recency filter. When None no date filter is applied.

        Returns:
            A list of validated Job domain entities, or an empty list on any
            HTTP error, timeout, or unexpected exception.
        """
        headers = {
            "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY", ""),
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        params = {
            "query": f"{query} in {location}",
            "page": "1",
            "num_pages": "1",
            "country": "US"
        }

        if work_types is None:
            pass  # no filter — all types returned
        elif work_types == [WorkType.REMOTE]:
            params["remote_jobs_only"] = "true"
            logger.info("%s — work type filter: remote only", self.platform)
        elif work_types == [WorkType.ONSITE]:
            params["remote_jobs_only"] = "false"
            logger.info("%s — work type filter: onsite only", self.platform)
        elif work_types == [WorkType.HYBRID]:
            logger.warning(
                "%s — hybrid work type filter not natively supported by JSearch. "
                "Results may include non-hybrid roles.",
                self.platform,
            )
        else:
            logger.info(
                "%s — multiple work types requested (%s). JSearch does not support "
                "multi-type filtering — all work types will be returned.",
                self.platform,
                [wt.value for wt in work_types],
            )

        if date_posted:
            params["date_posted"] = date_posted.jsearch_param
            logger.info("%s — date posted filter: %s", self.platform, date_posted.value)
        else:
            logger.info(
                "%s — no date posted filter (all dates returned)",
                self.platform,
            )

        jobs: list[Job] = []

        try:
            logger.info("%s — querying JSearch API", self.platform)
            response = requests.get(
                _JSEARCH_URL, headers=headers, params=params, timeout=_REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json().get("data", [])

            for item in data[:limit]:
                try:
                    city = item.get("job_city", "")
                    state = item.get("job_state", "")
                    location_text = ", ".join(filter(None, [city, state])) or location

                    try:
                        scraped_at = datetime.fromisoformat(
                            item["job_posted_at_datetime_utc"].replace("Z", "+00:00")
                        )
                    except Exception:
                        scraped_at = datetime.now()

                    jobs.append(Job(
                        title=item.get("job_title", ""),
                        company=item.get("employer_name", ""),
                        location=location_text,
                        url=item.get("job_apply_link", ""),
                        description=item.get("job_description", ""),
                        platform=self.platform,
                        scraped_at=scraped_at,
                    ))
                except Exception as exc:
                    logger.warning("%s — failed to parse job item: %s", self.platform, exc)
                    continue

        except requests.HTTPError as exc:
            logger.error("%s — HTTP error: %s", self.platform, exc)
        except requests.Timeout:
            logger.error("%s — request timed out", self.platform)
        except Exception as exc:
            logger.error("%s — unexpected error: %s", self.platform, exc)

        logger.info("%s — returning %d jobs", self.platform, len(jobs))
        return jobs
