---
name: add-job-source
description: >
  How to add a new job platform scraper to this hexagonal codebase. Use when
  wiring up a new source of job listings behind the ScraperPort interface.
---

# Skill: Add Job Source

## Goal

Add a new job platform scraper as a `ScraperPort` adapter.

## Before you start

Indeed, Glassdoor, and ZipRecruiter are **already** served by the single
`JSearchScraper` (JSearch API, parameterized by platform) — direct scraping is
non-viable for them (bot detection). Only add a new adapter for a genuinely new
source. Direct browser scraping (LinkedIn-style) uses Playwright.

## Steps

1. Create `src/adapters/scrapers/<platform>.py` with a class that subclasses
   `ScraperPort` and implements:

   ```python
   async def fetch_jobs(
       self,
       query: str,
       location: str,
       limit: int = 25,
       work_types: list[WorkType] | None = None,
       date_posted: DatePosted | None = None,
   ) -> list[Job]:
       ...
   ```

2. Return validated `Job` Pydantic models (`src/core/domain/job.py`) — never raw
   dicts. Populate `title`, `company`, `location`, `url`, `description`,
   `platform`, `scraped_at`.
3. Apply a minimum 2-second delay between requests where the adapter issues
   multiple requests. Handle HTTP errors, timeouts, and empty/malformed
   responses gracefully (return `[]` rather than crashing the run).
4. Map `work_types` and `date_posted` to the platform's query params where
   supported.
5. Add the platform to the `ScraperName` enum
   (`src/core/domain/scraper_name.py`) if it's a new name.
6. Register the adapter in `build_scrapers()`
   (`src/adapters/scrapers/scraper_factory.py`) — never instantiate scrapers
   directly in `main.py`.
7. Add unit tests at `tests/unit/adapters/scrapers/test_<platform>.py`:
   - Happy path returns `list[Job]` (mock the network/browser).
   - Empty-results handling.
   - Malformed-response handling.
   Use `unittest.mock` and `@pytest.mark.asyncio`. No real network calls.
8. Run `pytest tests/unit/ -v` — all tests must pass.
