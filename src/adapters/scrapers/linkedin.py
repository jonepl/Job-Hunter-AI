"""LinkedIn scraper adapter — uses Playwright for JavaScript-rendered pages."""

import asyncio
import logging
from datetime import datetime
from urllib.parse import quote_plus

from playwright.async_api import Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.core.domain.date_posted import DatePosted
from src.core.domain.job import Job
from src.core.domain.work_type import WorkType
from src.core.ports.scraper_port import ScraperPort

logger = logging.getLogger(__name__)

_RATE_LIMIT_SECONDS = 2


class LinkedInScraper(ScraperPort):
    """Scrapes job listings from LinkedIn using Playwright."""

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
        work_types: list[WorkType] | None = None,
        date_posted: DatePosted | None = None,
    ) -> list[Job]:
        """Fetch job listings from LinkedIn.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.
            work_types: Optional list of WorkType values to filter by work
                        arrangement. When None all types are returned.
            date_posted: Optional recency filter. When None no date filter is applied.

        Returns:
            A list of validated Job domain entities.
        """
        encoded_query = quote_plus(query)
        encoded_location = quote_plus(location)
        work_type_param = WorkType.to_linkedin_param(work_types or [])
        date_posted_param = f"&f_TPR={date_posted.linkedin_param}" if date_posted else ""
        url = (
            f"https://www.linkedin.com/jobs/search/?"
            f"keywords={encoded_query}"
            f"&location={encoded_location}"
            f"{work_type_param}"
            f"{date_posted_param}"
        )

        if work_types:
            logger.info("LinkedIn — work type filter: %s", [wt.value for wt in work_types])
        else:
            logger.info("LinkedIn — no work type filter (all types returned)")

        if date_posted:
            logger.info("LinkedIn — date posted filter: %s", date_posted.value)
        else:
            logger.info("LinkedIn — no date posted filter (all dates returned)")

        jobs: list[Job] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.set_extra_http_headers(
                    {
                        "User-Agent": (
                            "Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        )
                    }
                )

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

                # Pass 1 — extract all card data while the search results DOM is intact.
                # Navigating away later (to fetch descriptions) destroys element handles,
                # so all fields must be read before any page.goto call.
                card_data: list[dict] = []
                for card in cards[:limit]:
                    try:
                        title_el = await card.query_selector(".base-search-card__title")
                        company_el = await card.query_selector(".base-search-card__subtitle")
                        location_el = await card.query_selector(".base-search-card__metadata")
                        link_el = await card.query_selector("a.base-card__full-link")
                        # Posting age lives in the metadata's <time datetime="…">.
                        # Salary and employment type are only on the detail page,
                        # which we deliberately do not fetch (rate-limit rule) — they
                        # stay None for LinkedIn jobs.
                        time_el = await card.query_selector(".base-search-card__metadata time")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        location_text = (
                            (await location_el.inner_text()).strip() if location_el else ""
                        )
                        url_href = await link_el.get_attribute("href") if link_el else ""
                        posted_attr = await time_el.get_attribute("datetime") if time_el else None

                        if not title or not url_href:
                            continue

                        card_data.append(
                            {
                                "title": title,
                                "company": company,
                                "location": location_text,
                                "url": url_href,
                                "posted_at": posted_attr,
                            }
                        )
                    except Exception as exc:
                        logger.warning("LinkedIn — failed to parse card: %s", exc)
                        continue

                # Pass 2 — fetch descriptions. Element handles are no longer used here,
                # so page navigation cannot produce stale-handle errors.
                for data in card_data:
                    description = await self._fetch_description(page, data["url"])
                    await asyncio.sleep(_RATE_LIMIT_SECONDS)

                    posted_at = None
                    if data["posted_at"]:
                        try:
                            posted_at = datetime.fromisoformat(data["posted_at"])
                        except Exception:
                            posted_at = None

                    jobs.append(
                        Job(
                            title=data["title"],
                            company=data["company"],
                            location=data["location"],
                            url=data["url"],
                            description=description,
                            platform="linkedin",
                            scraped_at=datetime.now(),
                            posted_at=posted_at,
                        )
                    )

                await browser.close()

        except PlaywrightTimeoutError:
            logger.error("LinkedIn — page load timed out")
        except Exception as exc:
            logger.error("LinkedIn — unexpected error: %s", exc)

        logger.info("LinkedIn — returning %d jobs", len(jobs))
        return jobs

    async def _fetch_description(self, page: Page, url: str) -> str:
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
