# Skill: Add Job Source

## Goal
Add a new job platform scraper to the project.

## Supported Platforms
- LinkedIn (Playwright — JS-rendered)
- Indeed (BeautifulSoup — static HTML / RSS)
- Glassdoor (Playwright — JS-rendered)
- ZipRecruiter (BeautifulSoup — static HTML)

## Steps
1. Create `src/scraper/<platform>.py`
2. Implement the following function signature:

   def fetch_jobs(query: str, location: str, limit: int = 25) -> list[dict]:

3. Each job dict must include these keys:
   - `title` — job title
   - `company` — company name
   - `location` — job location
   - `url` — direct link to the job posting
   - `description` — full job description text
   - `platform` — source platform name (e.g. "linkedin")
   - `scraped_at` — ISO 8601 timestamp

4. Apply a minimum 2 second delay between requests
5. Handle these error cases gracefully:
   - HTTP errors (4xx, 5xx)
   - Timeout errors
   - Empty or malformed responses
   - Missing fields in the scraped data

6. Use Playwright for: LinkedIn, Glassdoor
7. Use BeautifulSoup + requests for: Indeed, ZipRecruiter

8. Create `tests/test_<platform>.py` with:
   - A mock test for `fetch_jobs()` using `unittest.mock.patch`
   - A test for empty results handling
   - A test for malformed response handling

9. Run `pytest tests/ -v` — all tests must pass
10. Register the new scraper in `src/scraper/__init__.py`