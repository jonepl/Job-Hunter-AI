"""ZipRecruiter scraper adapter — uses BeautifulSoup + requests for static HTML."""

import asyncio
import logging
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from src.core.domain.job import Job
from src.core.ports.scraper_port import ScraperPort

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.ziprecruiter.com/jobs-search?search={query}&location={location}"
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


class ZipRecruiterScraper(ScraperPort):
    """Scrapes job listings from ZipRecruiter using BeautifulSoup + requests."""

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
    ) -> list[Job]:
        """Fetch job listings from ZipRecruiter.

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
            logger.info("ZipRecruiter — fetching search page")
            response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            await asyncio.sleep(_RATE_LIMIT_SECONDS)

            soup = BeautifulSoup(response.text, "lxml")
            cards = soup.select("article[data-job-id]")
            logger.info("ZipRecruiter — found %d cards", len(cards))

            for card in cards[:limit]:
                try:
                    title_el = card.select_one("[class*='job_title']")
                    company_el = card.select_one("[class*='hiring_company_text']")
                    location_el = card.select_one("[class*='location']")
                    link_el = card.select_one("a[href]")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location_text = location_el.get_text(strip=True) if location_el else location
                    job_url = link_el["href"] if link_el else ""

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
                        platform="ziprecruiter",
                        scraped_at=datetime.now(),
                    ))
                except Exception as exc:
                    logger.warning("ZipRecruiter — failed to parse card: %s", exc)
                    continue

        except requests.Timeout:
            logger.error("ZipRecruiter — request timed out")
        except requests.HTTPError as exc:
            logger.error("ZipRecruiter — HTTP error: %s", exc)
        except Exception as exc:
            logger.error("ZipRecruiter — unexpected error: %s", exc)

        logger.info("ZipRecruiter — returning %d jobs", len(jobs))
        return jobs

    def _fetch_description(self, url: str) -> str:
        """Fetch and extract the job description from a detail page.

        Args:
            url: URL of the ZipRecruiter job detail page.

        Returns:
            The extracted job description text, or empty string on failure.
        """
        try:
            response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            el = soup.select_one("[class*='job_description']")
            return el.get_text(separator="\n", strip=True) if el else ""
        except Exception as exc:
            logger.warning("ZipRecruiter — failed to fetch description from %s: %s", url, exc)
            return ""
