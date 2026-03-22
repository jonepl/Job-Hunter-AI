# Product Requirements Document

## Job Search Automation Agent

**Version:** 1.1
**Date:** 2026-03-16
**Status:** Draft

---

## 1. Overview

The Job Search Automation Agent is a Dockerized Python backend service that automates the end-to-end process of finding relevant job listings. It scrapes job postings from multiple platforms, evaluates each listing against a candidate resume using OpenAI GPT-4o, ranks the results by relevance score, and delivers the top matches via email — all without manual intervention.

The service is built on Hexagonal Architecture (Ports and Adapters), keeping core domain logic fully isolated from external dependencies. Each platform scraper, the LLM evaluator, and the output delivery mechanism are all independent adapters that can be swapped or extended without touching the core.

---

## 2. Problem Statement

Manually searching for jobs across multiple platforms is time-consuming and repetitive. A candidate must:

- Visit LinkedIn, Indeed, Glassdoor, and ZipRecruiter separately
- Read each job description individually
- Manually assess whether each role aligns with their experience and resume

This process is inefficient, inconsistent, and does not scale. There is no single tool that aggregates, filters, and ranks results intelligently against a specific candidate profile.

---

## 3. Goals

- Automatically scrape job listings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter
- Parse and extract text from a candidate's PDF resume
- Evaluate each job description against the resume using GPT-4o
- Score and rank results by relevance
- Return only jobs that meet a configurable relevance threshold (default: 70)
- Deliver results via SMTP email to the configured recipient
- Save results to a structured output file that persists after the container stops
- Run end-to-end without manual intervention once started

---

## 4. Target User

A single job seeker running the service locally via Docker. The user mounts their resume and output directory as volumes, sets environment variables, and triggers the service manually. They receive a curated ranked list of job matches by email.

---

## 5. Architecture Overview

The service follows **Hexagonal Architecture** (Ports and Adapters). Core domain logic is fully isolated from all external integrations. Adapters implement defined port interfaces and are injected at runtime.

### Dependency Direction

```
Adapters → Ports ← Core Domain
```

Core domain code never imports from adapters. All dependencies point inward.

### Project Structure

```
src/
├── core/
│   ├── domain/          # Entities: Job, Resume, MatchResult
│   ├── ports/           # Interfaces: ScraperPort, EvaluatorPort, OutputPort
│   └── services/        # JobSearchService — orchestrates the pipeline
└── adapters/
    ├── scrapers/         # linkedin.py, jsearch.py
    ├── evaluator/        # openai_evaluator.py
    └── output/           # email_output.py, file_output.py
```

### Ports

| Port | Responsibility |
|---|---|
| `ScraperPort` | Defines the interface each platform scraper must implement |
| `EvaluatorPort` | Defines the interface for resume-to-job evaluation and scoring |
| `OutputPort` | Defines the interface for result delivery (email, file) |

### Adapters

| Adapter | Port | Notes |
|---|---|---|
| `LinkedInScraper` | `ScraperPort` | Playwright — JS-rendered |
| `JSearchScraper` | `ScraperPort` | JSearch API (RapidAPI) — Indeed, Glassdoor, ZipRecruiter |
| `OpenAIEvaluator` | `EvaluatorPort` | GPT-4o via OpenAI SDK (default) |
| `ClaudeEvaluator` | `EvaluatorPort` | claude-sonnet-4-5 via Anthropic SDK (alternative) |
| `EmailOutput` | `OutputPort` | SMTP delivery |
| `FileOutput` | `OutputPort` | Structured file — persisted via volume mount |

---

## 6. Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM | OpenAI GPT-4o (default evaluator) or Anthropic claude-sonnet-4-5 (alternative evaluator) — provider switchable via `EVALUATOR_PROVIDER` in `.env` |
| JS-rendered scraping | Playwright (LinkedIn) |
| API-based scraping | JSearch API (RapidAPI) for Indeed, Glassdoor, ZipRecruiter |
| Resume parsing | PyPDF2 |
| Secret management | python-dotenv |
| Containerization | Docker + docker-compose |
| Email delivery | SMTP |
| Orchestration (Phase 2) | LangGraph |

---

## 7. Features

### Inputs

| Input | Description |
|---|---|
| Resume | PDF file injected via Docker volume mount at `docs/resume/resume.pdf` |
| Search query | e.g. `"Senior Python Developer"` |
| Location | e.g. `"Remote"` or `"Miami, FL"` |
| Score threshold | Configurable minimum match score (default: `70`) |

### Scraping

- Scrape job listings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter
- Use Playwright for LinkedIn (JavaScript-rendered, direct scraping)
- Use JSearch API (RapidAPI) for Indeed, Glassdoor, and ZipRecruiter — bot detection makes direct scraping non-viable for all three platforms
- Enforce a minimum 2-second delay between requests
- Cap results at 50 listings per platform per run
- Handle HTTP errors, timeouts, and empty responses gracefully

### Resume Evaluation

- Parse the candidate's PDF resume using PyPDF2
- Cache extracted resume text — do not re-parse on every run
- Send each job description and resume to GPT-4o for relevance scoring
- Each result includes: title, company, location, URL, score, matched skills, missing skills, and a summary

### Ranking & Filtering

- Rank all evaluated jobs by relevance score (descending)
- Filter out any jobs below the configured score threshold
- Returns top TOP_RESULTS ranked job matches above SCORE_THRESHOLD when TOP_RESULTS is set. Returns all qualifying matches when TOP_RESULTS is not set.

### Always-On Run Report

- A report is always delivered after every run regardless of results
- Qualifying results: full ranked results with score breakdowns
- Zero qualifying results: zero results report with top 5 near-miss jobs, explanation, and threshold suggestion
- Near-miss results shown in condensed format — no score breakdown table
- TOP_RESULTS is optional — when not set all qualifying results are returned

### Output

- Save ranked results to a structured output file persisted via Docker volume mount
- Deliver results via SMTP email to the configured recipient

---

## 8. Success Criteria

- Agent completes a full run end-to-end without manual intervention
- Returns top TOP_RESULTS ranked job matches above SCORE_THRESHOLD when TOP_RESULTS is set. Returns all qualifying matches when TOP_RESULTS is not set.
- Only returns matches scoring above the configurable threshold
- A report is always delivered — email and CSV written on every run including zero-result runs
- Delivers results via email to the configured recipient
- Saves results to an output file that persists after the container stops
- Core domain logic is fully testable without real scrapers or APIs
- All LLM calls handle API errors gracefully with try/except

---

## 9. Constraints

- Must be free or low-cost to run
- Minimize paid API usage — use open-source libraries where possible
- Playwright browser binaries must run inside the Docker container
- Resume and output files are managed via Docker volume mounts — not baked into the image
- No cloud infrastructure costs in Phase 1
- No more than 50 results scraped per platform per run

---

## 10. Project Phases

### Phase 1 — Local Docker (Current)

A sequential linear pipeline deployed locally via docker-compose:

1. Accept inputs: query, location, resume path, score threshold
2. Scrape job listings from all four platforms
3. Parse resume text from PDF
4. Evaluate each job against the resume via GPT-4o
5. Score, filter, and rank results
6. Save results to output file
7. Deliver results via email

Execution is manual — no scheduling or automation.

### Phase 2 — Cloud Deployment + Orchestration

- Migrate to cloud hosting
- Introduce LangGraph for parallel scraping across platforms and conditional branching (e.g. fallback on scrape failure)
- Add scheduling for automated runs

---

## 11. Out of Scope (Phase 1)

- No web UI or dashboard
- No database — file output only
- No user authentication
- No scheduled or automated runs
- No Kubernetes or cloud infrastructure
- No LangGraph orchestration
