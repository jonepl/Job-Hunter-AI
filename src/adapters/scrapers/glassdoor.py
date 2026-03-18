"""Glassdoor scraper adapter — uses Playwright for JavaScript-rendered pages."""

import asyncio
import logging
from datetime import datetime
from urllib.parse import quote_plus

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from src.core.domain.job import Job
from src.core.ports.scraper_port import ScraperPort

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}&locT=N&locId=0"
_RATE_LIMIT_SECONDS = 2


class GlassdoorScraper(ScraperPort):
    """Scrapes job listings from Glassdoor using Playwright."""

    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25,
    ) -> list[Job]:
        """Fetch job listings from Glassdoor.

        Args:
            query: Job search query string (e.g. "Senior Python Developer").
            location: Location string (e.g. "Remote" or "Miami, FL").
            limit: Maximum number of results to return. Defaults to 25.

        Returns:
            A list of validated Job domain entities.
        """
        url = _BASE_URL.format(query=quote_plus(query))
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

                logger.info("Glassdoor — navigating to search URL")
                await page.goto(url, timeout=30_000)
                await asyncio.sleep(_RATE_LIMIT_SECONDS)

                # Dismiss sign-in modal if present
                try:
                    close_btn = await page.query_selector("[alt='Close']")
                    if close_btn:
                        await close_btn.click()
                        await asyncio.sleep(1)
                except Exception:
                    pass

                try:
                    await page.wait_for_selector("li.react-job-listing", timeout=10_000)
                except PlaywrightTimeoutError:
                    logger.warning("Glassdoor — no job cards found within timeout")
                    await browser.close()
                    return []

                cards = await page.query_selector_all("li.react-job-listing")
                logger.info("Glassdoor — found %d cards", len(cards))

                for card in cards[:limit]:
                    try:
                        title_el = await card.query_selector("[data-test='job-title']")
                        company_el = await card.query_selector("[data-test='employer-name']")
                        location_el = await card.query_selector("[data-test='emp-location']")
                        link_el = await card.query_selector("a[data-test='job-title']")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        location_text = (await location_el.inner_text()).strip() if location_el else location
                        href = await link_el.get_attribute("href") if link_el else ""
                        job_url = f"https://www.glassdoor.com{href}" if href.startswith("/") else href

                        if not title or not job_url:
                            continue

                        await card.click()
                        await asyncio.sleep(_RATE_LIMIT_SECONDS)
                        description = await self._extract_description(page)

                        jobs.append(Job(
                            title=title,
                            company=company,
                            location=location_text,
                            url=job_url,
                            description=description,
                            platform="glassdoor",
                            scraped_at=datetime.now(),
                        ))
                    except Exception as exc:
                        logger.warning("Glassdoor — failed to parse card: %s", exc)
                        continue

                await browser.close()

        except PlaywrightTimeoutError:
            logger.error("Glassdoor — page load timed out")
        except Exception as exc:
            logger.error("Glassdoor — unexpected error: %s", exc)

        logger.info("Glassdoor — returning %d jobs", len(jobs))
        return jobs

    async def _extract_description(self, page) -> str:
        """Extract the job description from the currently open detail panel.

        Args:
            page: The active Playwright page instance.

        Returns:
            The extracted job description text, or empty string on failure.
        """
        try:
            await page.wait_for_selector("[class*='JobDetails']", timeout=8_000)
            el = await page.query_selector("[class*='JobDetails']")
            return (await el.inner_text()).strip() if el else ""
        except Exception as exc:
            logger.warning("Glassdoor — failed to extract description: %s", exc)
            return ""
