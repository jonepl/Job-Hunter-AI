# Architecture Document
## Job Search Automation Agent

---

## 1. Overview

The Job Search Automation Agent is a Dockerized Python backend service that scrapes job listings from multiple platforms, evaluates each listing against a candidate resume using GPT-4o, and delivers ranked matches via email and CSV file output.

The system is designed using **Hexagonal Architecture (Ports and Adapters)** to ensure the core business logic is fully isolated from external dependencies such as job board scrapers, LLM providers, email services, and file output systems.

---

## 2. Architecture Pattern — Hexagonal Architecture

Hexagonal Architecture organizes the application into three distinct layers:

```
┌────────────────────────────────────────────────────────┐
│                    ADAPTERS (External)                 │
│                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │  Scrapers   │  │  Evaluator  │  │    Output      │  │
│  │  LinkedIn   │  │   OpenAI    │  │  Gmail SMTP    │  │
│  │  Indeed     │  │   GPT-4o    │  │  CSV File      │  │
│  │  Glassdoor  │  └──────┬──────┘  └───────┬────────┘  │
│  │  ZipRecruit │         │                 │           │
│  └──────┬──────┘         │                 │           │
│         │                │                 │           │
├─────────┼────────────────┼─────────────────┼───────────┤
│         │           PORTS (Interfaces)      │          │
│         ▼                ▼                 ▼           │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ ScraperPort │  │EvaluatorPort│  │  OutputPort    │  │
│  └──────┬──────┘  └──────┬──────┘  └───────┬────────┘  │
│         │                │                 │           │
├─────────┼────────────────┼─────────────────┼───────────┤
│         │            CORE DOMAIN            │          │
│         ▼                ▼                 ▼           │
│  ┌─────────────────────────────────────────────────┐   │
│  │              JobSearchService                   │   │
│  │         (Orchestration & Business Logic)        │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│         ┌────────────────┼────────────────┐            │
│         ▼                ▼                ▼            │
│      Job            Resume          MatchResult        │
│    (Entity)         (Entity)         (Entity)          │
└────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility |
|---|---|
| **Core Domain** | Business logic, domain entities, orchestration |
| **Ports** | Abstract interfaces defining contracts for external systems |
| **Adapters** | Concrete implementations of ports for each external system |

### Key Principle

No core domain code imports from adapters. All dependencies point inward — adapters depend on ports, ports define the domain contract, and the core domain has zero knowledge of external systems.

**This means:** swapping LinkedIn for a new job board, replacing GPT-4o with another LLM, or changing the email provider requires only a new adapter — the core logic is never touched.

---

## 3. Project Structure

```
job-search-agent/
│
├── ai/                                  ← Agent Control System
│   ├── rules.md
│   ├── commands.md
│   └── skills/
│       ├── environment-setup.md
│       ├── feature-development.md
│       ├── debugging.md
│       ├── testing.md
│       ├── add-job-source.md
│       └── resume-evaluation.md
│
├── docs/
│   ├── prd.md                           ← Product Requirements Document
│   ├── architecture.md                  ← This file
│   ├── env.md                           ← Environment variable reference
│   └── resume/
│       └── resume.pdf                   ← Candidate resume (volume mounted)
│
├── src/
│   ├── core/
│   │   ├── domain/                      ← Pydantic entities
│   │   │   ├── __init__.py
│   │   │   ├── job.py                   ← Job entity
│   │   │   ├── resume.py                ← Resume entity
│   │   │   └── match_result.py          ← MatchResult entity
│   │   │
│   │   ├── ports/                       ← Abstract Base Class interfaces
│   │   │   ├── __init__.py
│   │   │   ├── scraper_port.py          ← ScraperPort ABC
│   │   │   ├── evaluator_port.py        ← EvaluatorPort ABC
│   │   │   └── output_port.py           ← OutputPort ABC
│   │   │
│   │   └── services/                    ← Business logic orchestration
│   │       ├── __init__.py
│   │       └── job_search_service.py    ← JobSearchService
│   │
│   └── adapters/
│       ├── scrapers/                    ← One adapter per platform
│       │   ├── __init__.py
│       │   ├── linkedin.py
│       │   └── jsearch.py
│       │
│       ├── evaluator/                   ← LLM evaluation adapter
│       │   ├── __init__.py
│       │   └── openai_evaluator.py
│       │
│       └── output/                      ← Delivery adapters
│           ├── __init__.py
│           ├── email_output.py          ← Gmail SMTP adapter
│           └── file_output.py           ← CSV file adapter
│
tests/
│
├── unit/                                    ← mirrors src/ exactly
│   ├── core/
│   │   ├── domain/
│   │   │   ├── test_job.py                  ← tests for Job entity
│   │   │   ├── test_resume.py               ← tests for Resume entity
│   │   │   └── test_match_result.py         ← tests for MatchResult entity
│   │   │
│   │   ├── ports/
│   │   │   ├── test_scraper_port.py         ← tests for ScraperPort ABC
│   │   │   ├── test_evaluator_port.py       ← tests for EvaluatorPort ABC
│   │   │   └── test_output_port.py          ← tests for OutputPort ABC
│   │   │
│   │   └── services/
│   │       └── test_job_search_service.py   ← tests for orchestration logic
│   │
│   └── adapters/
│       ├── scrapers/
│       │   ├── test_linkedin.py
│       │   └── test_jsearch.py
│       ├── evaluator/
│       │   └── test_openai_evaluator.py
│       └── output/
│           ├── test_email_output.py
│           └── test_file_output.py
│
├── integration/                             ← mirrors src/ exactly
│   ├── core/
│   │   └── services/
│   │       └── test_job_search_service.py   ← full pipeline integration test
│   │
│   └── adapters/
│       ├── scrapers/
│       │   ├── test_linkedin.py
│       │   └── test_jsearch.py
│       ├── evaluator/
│       │   └── test_openai_evaluator.py
│       └── output/
│           ├── test_email_output.py
│           └── test_file_output.py
│
├── conftest.py                              ← shared fixtures for all tests
└── fixtures/                               ← static test data
│   ├── sample_resume.pdf                   ← test resume
│   ├── sample_job.json                     ← sample job listing
│   └── sample_match_result.json            ← sample evaluation result
│
├── logs/                                ← Persistent log output (volume mounted)
├── output/                              ← CSV results output (volume mounted)
├── Dockerfile
├── docker-compose.yml
├── setup.sh
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 4. Domain Entities

All domain entities are defined as **Pydantic models** for automatic validation, type enforcement, and JSON serialization. Pydantic is chosen because scraped and LLM-generated data is inherently unreliable — validation at the boundary prevents malformed data from propagating through the system.

### `Job`
Represents a single job listing scraped from a platform.

```python
class Job(BaseModel):
    title: str
    company: str
    location: str
    url: str
    description: str
    platform: str
    scraped_at: datetime
```

### `Resume`
Represents the parsed candidate resume.

```python
class Resume(BaseModel):
    raw_text: str
    parsed_at: datetime
```

### `MatchResult`
Represents the evaluated match between a resume and a job listing.

```python
class MatchResult(BaseModel):
    job: Job
    score: int                    # 0–100
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
```

---

## 5. Port Interfaces

Ports are defined as **Abstract Base Classes (ABC)** for explicit contract definition and runtime enforcement. Any adapter that fails to implement a required method raises an error immediately at instantiation — not silently at runtime.

### `ScraperPort`

```python
from abc import ABC, abstractmethod
from src.core.domain.job import Job

class ScraperPort(ABC):

    @abstractmethod
    async def fetch_jobs(
        self,
        query: str,
        location: str,
        limit: int = 25
    ) -> list[Job]:
        """Fetch job listings from a platform."""
        ...
```

### `EvaluatorPort`

```python
from abc import ABC, abstractmethod
from src.core.domain.resume import Resume
from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult

class EvaluatorPort(ABC):

    @abstractmethod
    async def evaluate(
        self,
        resume: Resume,
        job: Job
    ) -> MatchResult:
        """Evaluate a job listing against a resume."""
        ...
```

### `OutputPort`

```python
from abc import ABC, abstractmethod
from src.core.domain.match_result import MatchResult

class OutputPort(ABC):

    @abstractmethod
    async def deliver(
        self,
        results: list[MatchResult]
    ) -> None:
        """Deliver ranked match results."""
        ...
```

---

## 6. Core Service — `JobSearchService`

`JobSearchService` is the central orchestrator. It accepts port interfaces as constructor arguments (**dependency injection**) and coordinates the full pipeline.

```
JobSearchService.run(query, location, threshold)
        │
        ├── 1. Parse resume from PDF
        │
        ├── 2. Scrape all platforms asynchronously
        │       ├── LinkedInAdapter.fetch_jobs()
        │       ├── IndeedAdapter.fetch_jobs()
        │       ├── GlassdoorAdapter.fetch_jobs()
        │       └── ZipRecruiterAdapter.fetch_jobs()
        │
        ├── 3. Evaluate each job against resume (GPT-4o)
        │       └── OpenAIEvaluatorAdapter.evaluate()
        │
        ├── 4. Filter results above score threshold
        │
        ├── 5. Rank results by score — return top 10
        │
        ├── 6. Deliver results
        │       ├── EmailOutputAdapter.deliver()
        │       └── FileOutputAdapter.deliver()
        │
        └── 7. Log completion summary
```

**Technical Terms:** `Dependency Injection`, `Async Pipeline`, `Score Threshold Filtering`

---

## 7. Adapters

### Scraper Adapters

| Adapter | Platform | Method | Reason |
|---|---|---|---|
| `LinkedInScraper` | LinkedIn | Playwright | JavaScript-rendered page |
| `JSearchScraper` | Indeed, Glassdoor, ZipRecruiter | JSearch API (RapidAPI) | Bot detection makes direct scraping non-viable for all three platforms |

All scraper adapters:
- Implement `ScraperPort`
- Apply a minimum 2 second delay between requests
- Handle HTTP errors, timeouts, and malformed responses gracefully
- Return validated `Job` Pydantic models

### Evaluator Adapters

| Adapter | Provider | Model | Notes |
|---|---|---|---|
| `OpenAIEvaluator` | OpenAI API | gpt-4o | Default, uses `response_format` strict mode |
| `ClaudeEvaluator` | Anthropic API | claude-sonnet-4-5 | Alternative, uses prompt-based JSON enforcement |

Both adapters:
- Implement `EvaluatorPort`
- Send resume text and job description to the LLM for scoring
- Parse and validate LLM response as a `MatchResult` Pydantic model
- Handle API errors gracefully — return a default low-score result on failure
- Return identical `MatchResult` output structure
- Select via `EVALUATOR_PROVIDER` in `.env` (`openai` or `anthropic`)

### Output Adapters

| Adapter | Delivery Method | Format |
|---|---|---|
| `EmailOutputAdapter` | Gmail via SMTP (smtplib) | HTML email |
| `FileOutputAdapter` | Local filesystem | CSV file |

Both implement `OutputPort`. CSV output is written to `output/results_<timestamp>.csv` which is persisted via Docker volume mount.

---

## 8. Asynchronous Scraping

All four platform scrapers run **concurrently** using Python `asyncio`. This reduces total scraping time from sequential (sum of all platform times) to approximately the time of the slowest single platform.

```python
import asyncio

results = await asyncio.gather(
    linkedin.fetch_jobs(query, location),
    indeed.fetch_jobs(query, location),
    glassdoor.fetch_jobs(query, location),
    ziprecruiter.fetch_jobs(query, location)
)
```

**Technical Terms:** `asyncio`, `Concurrent Execution`, `asyncio.gather`, `Async/Await`

---

## 9. Trigger Mechanism

The agent supports two trigger modes in Phase 1:

| Mode | Mechanism | How To Use |
|---|---|---|
| **Manual** | Run docker-compose directly | `docker-compose run agent` |
| **Scheduled** | Cron job on host machine | `cron` triggers `docker-compose run agent` |

Phase 2 will introduce native scheduling inside the container or via a cloud scheduler.

**Technical Terms:** `Manual Trigger`, `Cron Job`, `Host Scheduler`

---

## 10. Logging

The application uses Python's built-in `logging` module with two handlers:

| Handler | Output | Format |
|---|---|---|
| `StreamHandler` | Console (stdout) | Human-readable |
| `FileHandler` | `logs/agent_<timestamp>.log` | Structured text |

Log files are persisted via Docker volume mount and survive container restarts.

**Log levels used:**
- `INFO` — pipeline start, platform scrape counts, evaluation scores, delivery confirmation
- `WARNING` — missing fields in scraped data, LLM response anomalies
- `ERROR` — scraper failures, API errors, email delivery failures

**Technical Terms:** `StreamHandler`, `FileHandler`, `Log Level`, `Structured Logging`

---

## 11. Containerization

### Single Container Architecture

The entire application runs in a **single Docker container** managed by `docker-compose`.

```
Docker Container
├── Python 3.10 runtime
├── Application source code
├── Playwright + browser binaries
└── All Python dependencies

Volume Mounts (persist outside container)
├── docs/resume/     ← Resume PDF input
├── output/          ← CSV results output
└── logs/            ← Application logs
```

### `Dockerfile` (outline)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y ...

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright browser binaries
RUN playwright install --with-deps

# Copy application source
COPY src/ ./src/

CMD ["python", "-m", "src.core.services.job_search_service"]
```

### `docker-compose.yml` (outline)

```yaml
version: "3.9"

services:
  agent:
    build: .
    env_file: .env
    volumes:
      - ./docs/resume:/app/docs/resume
      - ./output:/app/output
      - ./logs:/app/logs
```

**Technical Terms:** `Dockerfile`, `docker-compose`, `Volume Mount`, `env_file`, `Slim Base Image`

---

## 12. Environment Variables

All secrets and configuration values are injected at runtime via `.env`. See `docs/env.md` for the full reference.

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Yes | GPT-4o evaluation |
| `ANTHROPIC_API_KEY` | Yes | Claude Code authentication |
| `GMAIL_ADDRESS` | Yes | SMTP sender address |
| `GMAIL_APP_PASSWORD` | Yes | Gmail App Password for SMTP |
| `EMAIL_RECIPIENT` | Yes | Results delivery address |
| `SCORE_THRESHOLD` | Yes | Minimum match score (default: 70) |
| `JSEARCH_API_KEY` | Optional | Fallback job listings API |
| `EVALUATOR_PROVIDER` | Optional | Selects evaluator: `openai` or `anthropic` (default: `openai`) |

---

## 13. Testing Strategy

The test suite mirrors the `src/` directory structure exactly inside
both `unit/` and `integration/` directories. Every module has a
corresponding unit test and integration test.

### Test Type Responsibilities

| | Unit Test | Integration Test |
|---|---|---|
| **What it tests** | Module in complete isolation | Module interacting with its dependencies |
| **External calls** | All mocked — no real APIs or files | Real file I/O, real API response shapes |
| **Speed** | Very fast — milliseconds | Slower — seconds |
| **Scope** | One function or class | One adapter end-to-end |
| **Failures reveal** | Logic bugs in your code | Compatibility bugs with external systems |

### Example — LinkedInAdapter

**Unit test** (`tests/unit/adapters/scrapers/test_linkedin.py`):
- Mock Playwright browser entirely
- Test fetch_jobs() returns a list of validated Job Pydantic models
- Test fetch_jobs() handles a timeout gracefully
- Test fetch_jobs() handles malformed HTML gracefully
- Test that the 2 second rate limit delay is applied
- No real browser, no real network call

**Integration test** (`tests/integration/adapters/scrapers/test_linkedin.py`):
- Use a saved HTML fixture of a real LinkedIn results page
- Run fetch_jobs() against the fixture HTML
- Assert correct fields are extracted
- Assert Pydantic validation passes on real-world HTML structure
- No live network call — tests against real HTML shapes only

### Shared Fixtures — `conftest.py`

Shared test data is defined in `tests/conftest.py` and available
to all tests automatically via pytest fixture injection.
```python
# tests/conftest.py

import pytest
from src.core.domain.job import Job
from src.core.domain.resume import Resume
from src.core.domain.match_result import MatchResult
from datetime import datetime

@pytest.fixture
def sample_job():
    return Job(
        title="Senior Python Developer",
        company="Acme Corp",
        location="Remote",
        url="https://linkedin.com/jobs/123",
        description="We need a Python expert...",
        platform="linkedin",
        scraped_at=datetime.now()
    )

@pytest.fixture
def sample_resume():
    return Resume(
        raw_text="Experienced Python developer with 5 years...",
        parsed_at=datetime.now()
    )

@pytest.fixture
def sample_match_result(sample_job):
    return MatchResult(
        job=sample_job,
        score=85,
        matched_skills=["Python", "REST APIs"],
        missing_skills=["Kubernetes"],
        summary="Strong match with a gap in container orchestration."
    )
```

### Running Tests
```bash
# Run full test suite
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run tests for a specific module
pytest tests/unit/adapters/scrapers/test_linkedin.py -v
```

All tests must pass before committing any code. No test ever
calls a real external API.

---

## 14. Phase Roadmap

### Phase 1 — Local Docker (Current)
- Linear async Python pipeline
- Single Docker container
- Manual + cron-scheduled triggers
- CSV file + Gmail SMTP output
- All four platform scrapers

### Phase 2 — Cloud Deployment + Orchestration
- Migrate to cloud hosting (TBD provider)
- Introduce LangGraph for parallel scraping and conditional branching
- Native cloud scheduling replaces host cron
- Persistent database replaces CSV file output
- Monitoring and alerting

---

## 15. Architecture Decision Record (ADR)

| Decision | Choice | Rationale |
|---|---|---|
| Architecture pattern | Hexagonal (Ports & Adapters) | Isolates core logic from volatile external systems |
| Domain entities | Pydantic models | Validates unreliable scraped and LLM data at boundaries |
| Port interfaces | Abstract Base Classes | Explicit contracts with runtime enforcement |
| Scraping approach | Asynchronous (asyncio) | Reduces total scrape time to single slowest platform |
| LLM provider | OpenAI GPT-4o | Strong reasoning for resume-JD evaluation |
| Email delivery | Gmail SMTP (smtplib) | Free, no third-party dependency, built into Python |
| Output format | CSV | Simple, portable, human-readable |
| Containerization | Single Docker container | Simplicity for Phase 1 local development |
| Logging | Console + file | Full observability during development and scheduled runs |
| Trigger | Manual + cron | Flexible for Phase 1 without added infrastructure |
| Test structure | Mirror `src/` in both `unit/` and `integration/` | Easy module location, clear coverage mapping per module |
| Shared test fixtures | `conftest.py` + `fixtures/` directory | Eliminates repeated setup, ensures consistent test data |
| Scraping method — LinkedIn | Playwright | JavaScript-rendered page — requires real browser execution |
| Scraping method — Indeed, Glassdoor, ZipRecruiter | JSearch API (RapidAPI) | Bot detection makes direct scraping non-viable for all three platforms (TLS fingerprinting, Cloudflare, JS cookie challenge) |
| Consolidated Indeed/Glassdoor/ZipRecruiter into JSearchScraper | Single JSearchScraper with platform parameter | All three platforms block direct scraping. JSearch is the permanent reliable source. Separate adapters were YAGNI — speculative generality with no practical benefit for a personal tool |
| Dual evaluator provider support | OpenAI GPT-4o (default) + Anthropic claude-sonnet-4-5 (alternative) | Hexagonal Architecture makes adding a second evaluator adapter trivial. Dual provider support enables cost comparison, fallback on API outage, and provider flexibility with zero core logic changes |
