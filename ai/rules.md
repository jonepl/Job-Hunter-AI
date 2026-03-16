# Project Rules

These rules apply to all contributors — human and AI alike.
Read this file before making any changes to the project.

---

## Project Overview

This is an agentic job search assistant that scrapes job descriptions
from LinkedIn, Indeed, Glassdoor, and ZipRecruiter, evaluates them
against a candidate resume, and returns ranked matches.

---

## Language & Runtime

- Python 3.10+
- All code runs inside the `.venv` virtual environment
- Activate with: `source .venv/bin/activate`

---

## LLM Provider

- Use OpenAI GPT-4o as the primary LLM
- Use the `openai` Python SDK for all LLM calls
- Model name: `gpt-4o`
- All LLM calls must handle API errors gracefully with try/except

---

## Secret & Configuration Management

- All API keys and secrets live in `.env`
- Load secrets using `python-dotenv` — never hardcode them
- `.env` is git-ignored and must never be committed
- New environment variables must be documented in `docs/env.md`

---

## Project Structure Rules

- Scrapers go in `src/scraper/` — one file per platform
- Evaluation logic goes in `src/evaluator/`
- Shared reusable functions go in `src/tools/`
- All tests go in `tests/` — mirror the `src/` structure
- Resume files go in `docs/resume/`

---

## Code Standards

- All functions must include type hints
- All functions must include a docstring
- All tool functions must return structured JSON
- Follow PEP 8 style conventions
- Maximum line length: 100 characters
- No unused imports

---

## Scraping Rules

- Use Playwright for JavaScript-rendered pages: LinkedIn, Glassdoor
- Use BeautifulSoup + requests for static pages: Indeed, ZipRecruiter
- Use JSearch API (RapidAPI) as a fallback data source
- Always include rate limiting between requests (min 2s delay)
- Never scrape more than 50 results per platform per run
- Always handle HTTP errors, timeouts, and empty responses

---

## Resume Rules

- Resume must be in PDF format
- Resume file lives at `docs/resume/resume.pdf`
- Use `pypdf2` to extract text from the resume
- Extracted resume text is cached — do not re-parse on every run

---

## Testing Rules

- Write a pytest test for every tool function
- Tests live in `tests/` mirroring `src/` structure
- Every test file is named `test_<module>.py`
- Test the happy path and at least one failure/edge case
- Run `pytest tests/ -v` before committing any code

---

## Git Rules

- Never commit `.env`
- Write clear commit messages: `<type>: <short description>`
  - Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`
  - Example: `feat: add LinkedIn scraper`
- One feature or fix per commit
- Always run tests before committing