# Project Rules

These rules apply to all contributors — human and AI alike.
Read this file before making any changes to the project.

---

## Project Overview

This is a Dockerized Python backend service that scrapes job listings
from LinkedIn, Indeed, Glassdoor, and ZipRecruiter, evaluates them
against a candidate resume using GPT-4o, and delivers ranked matches
via email and CSV file output.

---

## Architecture — Hexagonal (Ports and Adapters)

- Core domain logic must never import from adapters
- All dependencies point inward — adapters depend on ports,
  ports define the domain contract
- New platforms are added as new adapters only — never modify core
- Reference docs/architecture.md for the full architecture diagram

---

## Language & Runtime

- Python 3.10+
- All code runs inside the .venv virtual environment
- Activate with: source .venv/bin/activate
- All scraper and service methods must use async/await
- Use asyncio.gather for all concurrent scraping operations

---

## Domain Entities

- All domain entities must be defined as Pydantic models
- Entities live in src/core/domain/
- Valid entities: Job, Resume, MatchResult
- Never use plain dataclasses or dicts as domain entities
- All Pydantic models must include field type hints

---

## Port Interfaces

- All ports must be defined as Abstract Base Classes (ABC)
- Ports live in src/core/ports/
- Valid ports: ScraperPort, EvaluatorPort, OutputPort
- Every adapter must explicitly subclass its corresponding port
- Missing abstract method implementations raise errors at instantiation

---

## LLM Provider

- Use OpenAI GPT-4o as the primary LLM
- Model name: gpt-4o
- Use the openai Python SDK for all LLM calls
- All LLM responses must be validated as Pydantic models
- Handle API errors gracefully — return default low-score
  MatchResult on failure

---

## Secret & Configuration Management

- All secrets and config values live in .env
- Load with python-dotenv — never hardcode values
- .env is git-ignored and must never be committed
- All new environment variables must be documented in docs/env.md
- Reference docs/env.md for the full variable list

---

## Project Structure Rules

- Domain entities → src/core/domain/
- Port interfaces → src/core/ports/
- Service orchestration → src/core/services/
- Scraper adapters → src/adapters/scrapers/ (one file per platform)
- Evaluator adapter → src/adapters/evaluator/
- Output adapters → src/adapters/output/
- Unit tests → tests/unit/ (mirrors src/ structure exactly)
- Integration tests → tests/integration/ (mirrors src/ structure exactly)
- Shared fixtures → tests/conftest.py
- Static test data → tests/fixtures/
- Resume input → docs/resume/resume.pdf
- CSV output → output/results_<timestamp>.csv
- Log files → logs/agent_<timestamp>.log

---

## Scraping Rules

- LinkedIn → Playwright (JavaScript-rendered, direct)
- Indeed, Glassdoor, ZipRecruiter → JSearch API (RapidAPI) — bot detection makes direct scraping non-viable for all three platforms
- Minimum 2 second delay between requests on all platforms
- Maximum 25 results per platform per run
- Always handle HTTP errors, timeouts, and empty responses
- All scraped data must be validated as Job Pydantic models

---

## Output Rules

- Results delivered via Gmail SMTP using Python smtplib
- Results saved as CSV to output/results_<timestamp>.csv
- CSV and logs are persisted via Docker volume mounts
- Only return top 10 matches above the configured score threshold
- Score threshold is configurable via SCORE_THRESHOLD in .env

---

## Code Standards

- All functions must include type hints
- All functions must include a docstring
- All tool functions must return structured JSON or Pydantic models
- Follow PEP 8 style conventions
- Maximum line length: 100 characters
- No unused imports

---

## Testing Rules

- Every module must have a unit test and an integration test
- Test files mirror src/ structure in both unit/ and integration/
- Unit tests mock all external calls — no real APIs or network
- Integration tests use saved HTML fixtures — no live network calls
- Shared fixtures defined in tests/conftest.py
- Static test data stored in tests/fixtures/
- Every test file named test_<module>.py
- Every test function named test_<function>_<scenario>()
- Run pytest tests/ -v before committing any code

---

## Docker Rules

- Single container — all-in-one
- Managed via docker-compose
- Playwright browser binaries installed inside the container
- Resume input injected via Docker volume mount
- CSV output persisted via Docker volume mount
- Log files persisted via Docker volume mount
- Secrets injected at runtime via env_file — never baked into image
- Reference ai/skills/docker.md for Docker task instructions

---

## Git Rules

- Never commit .env
- Commit message format: <type>: <short description>
- Types: feat, fix, test, docs, refactor, chore
- Example: feat: add LinkedIn scraper
- One feature or fix per commit
- Always run pytest tests/ -v before committing
