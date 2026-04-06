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
│   ├── main.py                          ← thin CLI entrypoint
│   ├── bootstrap.py                     ← profile loading
│   ├── runner.py                        ← immediate run logic
│   ├── scheduler.py                     ← APScheduler — cron-based multi-profile runner
│   ├── service_factory.py               ← Builds JobSearchService from SearchProfile
│   │
│   ├── api/                             ← future FastAPI entrypoint
│   │   └── __init__.py
│   │
│   ├── cli/                             ← CLI concerns
│   │   ├── __init__.py
│   │   ├── args.py                      ← argparse definition
│   │   └── overrides.py                 ← CLI override logic
│   │
│   ├── infra/                           ← infrastructure
│   │   ├── __init__.py
│   │   ├── logging.py                   ← logging config
│   │   ├── cost_tracker.py              ← Accumulates LLM token usage per run
│   │   └── cost_estimator.py            ← Pre-run static cost estimate
│   │
│   ├── core/
│   │   ├── domain/                      ← Pydantic entities
│   │   │   ├── __init__.py
│   │   │   ├── date_posted.py           ← DatePosted enum
│   │   │   ├── job.py                   ← Job entity
│   │   │   ├── resume.py                ← Resume entity
│   │   │   ├── match_result.py          ← MatchResult entity
│   │   │   ├── run_report.py            ← RunReport entity
│   │   │   ├── cost_estimate.py         ← CostEstimate — pre-run cost prediction
│   │   │   ├── run_cost.py              ← RunCost + EvaluationCost — actual run cost
│   │   │   ├── scraper_name.py          ← ScraperName enum
│   │   │   └── search_profile.py        ← SearchProfile — per-profile config model
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
│       │   ├── jsearch.py
│       │   └── scraper_factory.py       ← Builds active scraper instances
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
│   ├── test_bootstrap.py                    ← tests for load_profiles()
│   ├── test_runner.py                       ← tests for run_immediate()
│   ├── test_scheduler.py                    ← tests for run_all_profiles()
│   ├── cli/
│   │   ├── test_args.py                     ← tests for parse_args()
│   │   └── test_overrides.py               ← tests for apply_cli_overrides()
│   ├── infra/
│   │   ├── test_logging.py                 ← tests for configure_logging()
│   │   ├── test_cost_tracker.py            ← tests for CostTracker
│   │   └── test_cost_estimator.py          ← tests for estimate_run_cost()
│   ├── core/
│   │   ├── domain/
│   │   │   ├── test_date_posted.py          ← tests for DatePosted enum
│   │   │   ├── test_job.py                  ← tests for Job entity
│   │   │   ├── test_resume.py               ← tests for Resume entity
│   │   │   ├── test_match_result.py         ← tests for MatchResult entity
│   │   │   ├── test_run_report.py           ← tests for RunReport entity
│   │   │   ├── test_cost_estimate.py        ← tests for CostEstimate entity
│   │   │   ├── test_run_cost.py             ← tests for RunCost / EvaluationCost entities
│   │   │   ├── test_scraper_name.py         ← tests for ScraperName enum
│   │   │   └── test_search_profile.py       ← tests for SearchProfile model
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
│       │   ├── test_jsearch.py
│       │   └── test_scraper_factory.py
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

### `ScraperName`
Enumeration of all supported job platform scrapers. Used to control which platforms are active at runtime via `ACTIVE_SCRAPERS` in `.env` or `--scrapers` CLI argument.

```python
class ScraperName(str, Enum):
    LINKEDIN     = "linkedin"
    INDEED       = "indeed"
    GLASSDOOR    = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"

    @classmethod
    def from_string(cls, value: str) -> "ScraperName": ...
    # Case-insensitive parse; raises ValueError on unknown name

    @classmethod
    def parse_list(cls, value: str) -> list["ScraperName"]: ...
    # Parses comma-separated string, e.g. "linkedin,indeed"

    @classmethod
    def all(cls) -> list["ScraperName"]: ...
    # Returns all four ScraperName values
```

### `CostEstimate`
Represents a pre-run static cost estimate calculated from config before any API calls are made. Predicts the cost range based on maximum possible evaluations.

```python
class CostEstimate(BaseModel):
    max_jobs: int
    est_min_cost_usd: float
    est_max_cost_usd: float
    provider: str
    input_cost_per_1m: float
    output_cost_per_1m: float

    @property
    def formatted_range(self) -> str: ...
    # Returns "$0.1234 - $0.5678"
```

### `EvaluationCost`
Represents the token usage and cost for a single job evaluation.

```python
class EvaluationCost(BaseModel):
    job_title: str
    company: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
```

### `RunCost`
Represents the accumulated LLM cost across an entire pipeline run. Built from a list of `EvaluationCost` instances after all evaluations complete.

```python
class RunCost(BaseModel):
    evaluations: list[EvaluationCost]
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    provider: str
    jobs_evaluated: int

    @property
    def formatted_total(self) -> str: ...
    # Returns "$0.2134"

    @classmethod
    def from_evaluations(
        cls,
        evaluations: list[EvaluationCost],
        provider: str
    ) -> "RunCost": ...
```

### `RunReport`
Represents the full summary of a single pipeline run. Always produced regardless of whether any jobs passed the score threshold.

```python
class RunReport(BaseModel):
    qualifying_results: list[MatchResult]  # Jobs that passed threshold + TOP_RESULTS cap
    near_miss_results: list[MatchResult]   # Top 5 below threshold — only when qualifying is empty
    total_evaluated: int                   # Total jobs sent to LLM evaluator
    score_threshold: int                   # Threshold used this run
    top_results: int | None                # TOP_RESULTS cap used; None when not set
    active_scrapers: list[ScraperName]     # Scrapers active this run
    query: str                             # Search query used this run
    location: str                          # Location used this run
    run_at: datetime                       # Timestamp of run completion

    cost_estimate: CostEstimate | None   # None when SHOW_COST_ESTIMATE=false
    run_cost: RunCost | None             # None when SHOW_COST_ESTIMATE=false

    @property
    def has_qualifying_results(self) -> bool: ...
    # Returns True when qualifying_results is non-empty

    @property
    def suggested_threshold(self) -> int | None: ...
    # Floors the lowest near-miss score to nearest 5; None when near_miss_results empty
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
        job: Job,
        work_types: list[WorkType] | None = None,
    ) -> tuple[MatchResult, int, int]:
        """Evaluate a job listing against a resume.

        Returns a tuple of (MatchResult, input_tokens, output_tokens).
        Token counts are extracted from the API response metadata at
        no extra cost and made available for cost tracking.
        """
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
Scheduler (if SCHEDULE_ENABLED=true)
    → On cron trigger
    → For each SearchProfile
    → build_service(profile)
    → service.run(profile params)
    → RunReport delivered per profile

Immediate mode (SCHEDULE_ENABLED=false)
    → Load all profiles
    → For each SearchProfile
    → build_service(profile)
    → service.run(profile params)
    → RunReport delivered per profile
    → Exit

JobSearchService.run(query, location, threshold, top_results)
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
        │       ├── Semaphore limits concurrent calls to MAX_CONCURRENT_EVALUATIONS
        │       ├── EVALUATION_DELAY_SECONDS applied after each evaluation
        │       ├── Token usage extracted from API response metadata
        │       ├── CostTracker.record() called per job when SHOW_COST_ESTIMATE=true
        │       └── OpenAIEvaluatorAdapter.evaluate() → tuple[MatchResult, int, int]
        │
        ├── 4. Sort all evaluated by score descending
        │
        ├── 5. Filter qualifying — above score threshold
        │
        ├── 6. Apply TOP_RESULTS cap if set
        │
        ├── 7. If zero qualifying — collect top 5 near-misses below threshold
        │
        ├── 8. Build RunReport
        │
        ├── 9. Deliver RunReport to all output adapters
        │       ├── EmailOutputAdapter.deliver(report)
        │       └── FileOutputAdapter.deliver(report)
        │
        └── 10. Return RunReport
```

**Technical Terms:** `Dependency Injection`, `Async Pipeline`, `Score Threshold Filtering`

---

## 7. Adapters

### Scraper Adapters

| Adapter | Platform | Method | Notes |
|---|---|---|---|
| `LinkedInScraper` | LinkedIn | Playwright | JavaScript-rendered page. Supports `f_TPR` date posted filter and `f_WT` work type filter. |
| `JSearchScraper` | Indeed, Glassdoor, ZipRecruiter | JSearch API (RapidAPI) | Bot detection makes direct scraping non-viable for all three platforms. Supports `date_posted` param. `remote_jobs_only` for work type. |

All scraper adapters:
- Implement `ScraperPort`
- Apply a minimum 2 second delay between requests
- Handle HTTP errors, timeouts, and malformed responses gracefully
- Return validated `Job` Pydantic models

Active scrapers are controlled via `ACTIVE_SCRAPERS` in `.env` or the `--scrapers` CLI argument. `ScraperFactory` (`src/adapters/scrapers/scraper_factory.py`) builds the active scraper instances at startup — scrapers are never instantiated directly in `main.py`.

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

The agent supports two trigger modes:

| Mode | Mechanism | How To Use |
|---|---|---|
| **Immediate** | Run once and exit | `python -m src.main` (SCHEDULE_ENABLED=false or not set) |
| **Scheduled** | APScheduler inside container runs indefinitely | `docker-compose up` (SCHEDULE_ENABLED=true) |

Immediate mode is used for local testing and manual runs. Scheduled mode is
used for Docker-based automated execution — APScheduler runs on SCHEDULE_CRON
indefinitely inside the container with no host cron dependency.

**Technical Terms:** `Immediate Mode`, `APScheduler`, `BlockingScheduler`, `CronTrigger`

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
| `SCORE_THRESHOLD` | Yes | Minimum match score (default: 70). When no jobs meet this threshold a zero results report is delivered with top 5 near-miss jobs and a suggested lower threshold value. |
| `TOP_RESULTS` | No | When set caps qualifying results delivered after score filtering. When not set all jobs above SCORE_THRESHOLD are returned. |
| `JSEARCH_API_KEY` | Optional | Fallback job listings API |
| `EVALUATOR_PROVIDER` | Optional | Selects evaluator: `openai` or `anthropic` (default: `openai`) |
| `MAX_CONCURRENT_EVALUATIONS` | No | Max concurrent LLM evaluation requests (default: `2`) |
| `EVALUATION_DELAY_SECONDS` | No | Seconds delay between evaluations to manage TPM rate limits (default: `1.0`) |
| `SHOW_COST_ESTIMATE` | No | Enable cost tracking and visibility (default: `false`) |
| `OPENAI_INPUT_COST_PER_1M` | No | GPT-4o input token rate per million tokens in USD (default: `2.50`) |
| `OPENAI_OUTPUT_COST_PER_1M` | No | GPT-4o output token rate per million tokens in USD (default: `10.00`) |
| `ANTHROPIC_INPUT_COST_PER_1M` | No | claude-sonnet-4-5 input token rate per million tokens in USD (default: `3.00`) |
| `ANTHROPIC_OUTPUT_COST_PER_1M` | No | claude-sonnet-4-5 output token rate per million tokens in USD (default: `15.00`) |

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
- Immediate mode and APScheduler scheduled mode both supported. SCHEDULE_ENABLED controls which mode runs.
- Multi-profile search via PROFILE_N_ variables in .env
- CSV file + Gmail SMTP output per profile
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
| Trigger | Immediate mode + APScheduler scheduled mode | Both modes supported. SCHEDULE_ENABLED in .env controls which runs. |
| Test structure | Mirror `src/` in both `unit/` and `integration/` | Easy module location, clear coverage mapping per module |
| Shared test fixtures | `conftest.py` + `fixtures/` directory | Eliminates repeated setup, ensures consistent test data |
| Scraping method — LinkedIn | Playwright | JavaScript-rendered page — requires real browser execution |
| Scraping method — Indeed, Glassdoor, ZipRecruiter | JSearch API (RapidAPI) | Bot detection makes direct scraping non-viable for all three platforms (TLS fingerprinting, Cloudflare, JS cookie challenge) |
| Consolidated Indeed/Glassdoor/ZipRecruiter into JSearchScraper | Single JSearchScraper with platform parameter | All three platforms block direct scraping. JSearch is the permanent reliable source. Separate adapters were YAGNI — speculative generality with no practical benefit for a personal tool |
| Dual evaluator provider support | OpenAI GPT-4o (default) + Anthropic claude-sonnet-4-5 (alternative) | Hexagonal Architecture makes adding a second evaluator adapter trivial. Dual provider support enables cost comparison, fallback on API outage, and provider flexibility with zero core logic changes |
| Always deliver a run report | RunReport delivered on every run including zero-result runs | Silent zero-result runs gave users no feedback when thresholds were aggressive. Always delivering a report with near-miss results and threshold suggestions closes the feedback loop without requiring users to read logs. |
| TOP_RESULTS is optional | None when not set — all qualifying results returned | TOP_RESULTS is an optional delivery convenience. The app is fully functional without it. Forcing a default cap would silently hide qualifying results from users who never set the variable. |
| Date posted filter configured via .env with CLI override | `DATE_POSTED=3days` default, `--date-posted` CLI argument overrides | A persistent default prevents stale listings appearing on every run without requiring the user to pass the flag each time. The CLI override allows per-run flexibility without changing `.env`. Default of `3days` balances freshness with coverage. |
| Scraper selection via ACTIVE_SCRAPERS .env variable and --scrapers CLI override | `ScraperName` enum + `ScraperFactory` pattern | Hardcoded scraper instantiation gave no runtime control. `ScraperName` enum centralises valid scraper names preventing typos. `ScraperFactory` isolates instantiation logic from `main.py` keeping startup code clean. CLI override enables per-run flexibility without `.env` edits. |
| APScheduler for in-process scheduling | BlockingScheduler with CronTrigger | Keeps scheduling inside the container with no host cron dependency. Cron syntax is more expressive than interval-based scheduling. Timezone support handles daylight saving correctly. |
| Multiple search profiles via PROFILE_N_ prefix pattern | Numbered env var prefix with PROFILE_COUNT | Enables multiple independent searches per run without code changes. Each profile delivers its own report making results easy to distinguish. Numbered prefix is readable and extensible. |
| SCHEDULE_ENABLED controls mode — not a CLI flag | .env variable only | Scheduled Docker containers have no interactive CLI. .env is the correct configuration surface for containerized workloads. |
| main.py refactored into focused single-responsibility modules | cli/, infra/, bootstrap.py, runner.py as extracted modules | main.py had grown to ~170 lines handling logging, arg parsing, CLI overrides, profile loading, immediate run, and result logging. Extracting into focused modules enables reuse by a future API entrypoint, improves testability, and makes each concern independently maintainable. bootstrap.py and runner.py have no CLI dependency so they can be called from both CLI and API entrypoints. |
| api/ module created as placeholder | src/api/__init__.py only — no implementation yet | Reserving the module structure now ensures future API development follows the established pattern and does not require structural changes to existing code. |
| Cost tracking via CostTracker accumulating EvaluatorPort token usage | Tuple return from evaluate() carrying MatchResult + token counts | OpenAI and Anthropic both return token usage in API responses at no extra cost. Extracting it at the evaluator level keeps cost tracking out of core domain logic. CostTracker in infra/ owns accumulation and calculation. SHOW_COST_ESTIMATE=false has zero performance impact — all tracking is bypassed entirely. |
| Cost tracking disabled by default via SHOW_COST_ESTIMATE=false | Opt-in via .env flag | Zero overhead when disabled. Users who do not need cost visibility pay no performance penalty. All tracking code is bypassed entirely when flag is false. |
| Token rates configurable via .env variables | OPENAI_INPUT_COST_PER_1M, OPENAI_OUTPUT_COST_PER_1M, ANTHROPIC_INPUT_COST_PER_1M, ANTHROPIC_OUTPUT_COST_PER_1M | LLM providers adjust pricing frequently. Configurable rates mean no code change is needed when pricing changes — just update .env. |
| Evaluation concurrency and delay configurable via .env | MAX_CONCURRENT_EVALUATIONS=2 and EVALUATION_DELAY_SECONDS=1.0 as defaults | TPM rate limits are tier-dependent. A fixed concurrency value would be wrong for many users. Configurable defaults allow tuning without code changes as API tier improves. |
