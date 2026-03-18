"""LinkedIn scraper adapter — uses Playwright for JavaScript-rendered pages."""

import asyncio
import logging
from datetime import datetime
from urllib.parse import quote_plus

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from src.core.domain.job import Job
from src.core.ports.scraper_port import ScraperPort

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.linkedin.com/jobs/search/?keywords={query}&location={location}&f_TPR=r604800"
_RATE_LIMIT_SECONDS = 2


class LinkedInScraper(ScraperPort):
    """Scrapes job listings from LinkedIn using Playwright."""

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
    ) -> list[Job]:
        """Fetch job listings from LinkedIn.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.

        Returns:
            A list of validated Job domain entities.
        """
        url = _BASE_URL.format(
            query=quote_plus(query),
            location=quote_plus(location),
        )
        jobs: list[Job] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.set_extra_http_headers({
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                })

                logger.info("LinkedIn — navigating to search URL")
                await page.goto(url, timeout=30_000)
                await asyncio.sleep(_RATE_LIMIT_SECONDS)

                try:
                    await page.wait_for_selector(".base-search-card", timeout=10_000)
                except PlaywrightTimeoutError:
                    logger.warning("LinkedIn — no job cards found within timeout")
                    await browser.close()
                    return []

                cards = await page.query_selector_all(".base-search-card")
                logger.info("LinkedIn — found %d cards", len(cards))

                for card in cards[:limit]:
                    try:
                        title_el = await card.query_selector(".base-search-card__title")
                        company_el = await card.query_selector(".base-search-card__subtitle")
                        location_el = await card.query_selector(".base-search-card__metadata")
                        link_el = await card.query_selector("a.base-card__full-link")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        location_text = (await location_el.inner_text()).strip() if location_el else ""
                        url_href = await link_el.get_attribute("href") if link_el else ""

                        if not title or not url_href:
                            continue

                        description = await self._fetch_description(page, url_href)
                        await asyncio.sleep(_RATE_LIMIT_SECONDS)

                        jobs.append(Job(
                            title=title,
                            company=company,
                            location=location_text,
                            url=url_href,
                            description=description,
                            platform="linkedin",
                            scraped_at=datetime.now(),
                        ))
                    except Exception as exc:
                        logger.warning("LinkedIn — failed to parse card: %s", exc)
                        continue

                await browser.close()

        except PlaywrightTimeoutError:
            logger.error("LinkedIn — page load timed out")
        except Exception as exc:
            logger.error("LinkedIn — unexpected error: %s", exc)

        logger.info("LinkedIn — returning %d jobs", len(jobs))
        return jobs

    async def _fetch_description(self, page, url: str) -> str:
        """Navigate to a job detail page and extract the description.

        Args:
            page: The active Playwright page instance.
            url: URL of the job detail page.

        Returns:
            The extracted job description text, or empty string on failure.
        """
        try:
            await page.goto(url, timeout=20_000)
            await page.wait_for_selector(".description__text", timeout=8_000)
            el = await page.query_selector(".description__text")
            return (await el.inner_text()).strip() if el else ""
        except Exception as exc:
            logger.warning("LinkedIn — failed to fetch description from %s: %s", url, exc)
            return ""
