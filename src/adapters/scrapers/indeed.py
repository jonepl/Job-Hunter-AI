"""Indeed scraper adapter — fetches job listings via the JSearch API."""

import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from src.core.domain.job import Job
from src.core.ports.scraper_port import ScraperPort

load_dotenv()

logger = logging.getLogger(__name__)

_JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
_REQUEST_TIMEOUT = 10


class IndeedScraper(ScraperPort):
    """Fetches Indeed job listings via the JSearch API."""

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
    ) -> list[Job]:
        """Fetch job listings from Indeed via JSearch API.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.

        Returns:
            A list of validated Job domain entities.
        """
        headers = {
            "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY", ""),
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        params = {
            "query": f"{query} in {location}",
            "page": "1",
            "num_pages": "1",
        }
        jobs: list[Job] = []

        try:
            logger.info("Indeed — querying JSearch API")
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
                        platform="indeed",
                        scraped_at=scraped_at,
                    ))
                except Exception as exc:
                    logger.warning("Indeed — failed to parse job item: %s", exc)
                    continue

        except requests.HTTPError as exc:
            logger.error("Indeed — HTTP error: %s", exc)
        except requests.Timeout:
            logger.error("Indeed — request timed out")
        except Exception as exc:
            logger.error("Indeed — unexpected error: %s", exc)

        logger.info("Indeed — returning %d jobs", len(jobs))
        return jobs
