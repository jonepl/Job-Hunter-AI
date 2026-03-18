"""Indeed scraper adapter — uses BeautifulSoup + requests for static HTML."""

import asyncio
import logging
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from src.core.domain.job import Job
from src.core.ports.scraper_port import ScraperPort

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.indeed.com/jobs?q={query}&l={location}&sort=date"
_JOB_URL = "https://www.indeed.com/viewjob?jk={job_key}"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_RATE_LIMIT_SECONDS = 2
_REQUEST_TIMEOUT = 10


class IndeedScraper(ScraperPort):
    """Scrapes job listings from Indeed using BeautifulSoup + requests."""

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
    ) -> list[Job]:
        """Fetch job listings from Indeed.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.

        Returns:
            A list of validated Job domain entities.
        """
        url = _SEARCH_URL.format(
            query=quote_plus(query),
            location=quote_plus(location),
        )
        jobs: list[Job] = []

        try:
            logger.info("Indeed — fetching search page")
            response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            await asyncio.sleep(_RATE_LIMIT_SECONDS)

            soup = BeautifulSoup(response.text, "lxml")
            cards = soup.select("[data-jk]")
            logger.info("Indeed — found %d cards", len(cards))

            for card in cards[:limit]:
                try:
                    job_key = card.get("data-jk", "")
                    title_el = card.select_one("[data-testid='jobTitle'] span")
                    company_el = card.select_one("[data-testid='company-name']")
                    location_el = card.select_one("[data-testid='text-location']")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location_text = location_el.get_text(strip=True) if location_el else location
                    job_url = _JOB_URL.format(job_key=job_key) if job_key else ""

                    if not title or not job_url:
                        continue

                    description = self._fetch_description(job_url)
                    await asyncio.sleep(_RATE_LIMIT_SECONDS)

                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location_text,
                        url=job_url,
                        description=description,
                        platform="indeed",
                        scraped_at=datetime.now(),
                    ))
                except Exception as exc:
                    logger.warning("Indeed — failed to parse card: %s", exc)
                    continue

        except requests.Timeout:
            logger.error("Indeed — request timed out")
        except requests.HTTPError as exc:
            logger.error("Indeed — HTTP error: %s", exc)
        except Exception as exc:
            logger.error("Indeed — unexpected error: %s", exc)

        logger.info("Indeed — returning %d jobs", len(jobs))
        return jobs

    def _fetch_description(self, url: str) -> str:
        """Fetch and extract the job description from a detail page.

        Args:
            url: URL of the Indeed job detail page.

        Returns:
            The extracted job description text, or empty string on failure.
        """
        try:
            response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            el = soup.select_one("#jobDescriptionText")
            return el.get_text(separator="\n", strip=True) if el else ""
        except Exception as exc:
            logger.warning("Indeed — failed to fetch description from %s: %s", url, exc)
            return ""
