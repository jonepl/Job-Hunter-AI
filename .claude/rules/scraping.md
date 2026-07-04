# Rules — Scraping & Scraper Configuration

## Scraping

- **LinkedIn** → Playwright (JavaScript-rendered, scraped directly). Supports
  `f_TPR` (date posted) and `f_WT` (work type) URL params.
- **Indeed, Glassdoor, ZipRecruiter** → the **JSearch API** (RapidAPI) via a
  single `JSearchScraper` parameterized by platform. Direct scraping is
  non-viable for all three (bot detection). Do not add direct scrapers for them.
- Minimum 2-second delay between requests where applicable (LinkedIn issues
  multiple requests; JSearch issues one batched request per platform).
- Maximum 25 results per platform per run (`limit=25` default on `fetch_jobs`).
- Always handle HTTP errors, timeouts, and empty/malformed responses gracefully.
- All scraped data must be validated into `Job` Pydantic models before leaving
  the adapter.

## Work type

- Valid work types: `remote`, `hybrid`, `onsite` — passed via `--work-type` CLI
  or `PROFILE_N_WORK_TYPE`.
- `--location` is optional **only** when `--work-type remote` is the sole work
  type; it then defaults to `"United States"`. Log INFO when defaulting.
- `--location` is required for hybrid, onsite, mixed work types, and when no
  work type is specified.
- Location resolution is an entrypoint concern — `JobSearchService.run()` always
  receives a resolved, non-null location string.

## Scraper configuration

- `ACTIVE_SCRAPERS` (`.env`) controls which scrapers run by default;
  `--scrapers` overrides it for a single run.
- `ScraperName` enum (`src/core/domain/scraper_name.py`) centralizes valid names.
- `build_scrapers()` (`src/adapters/scrapers/scraper_factory.py`) instantiates
  active scrapers. **Never instantiate scrapers directly in `main.py`** — always
  go through the factory.
- Validate scraper names at startup; exit with a clear error on an invalid name
  or an empty list. Log the active scrapers and whether the source was CLI or
  `.env`.
