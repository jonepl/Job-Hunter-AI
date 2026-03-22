# Job Search Automation Agent

A Dockerized Python backend service that scrapes job listings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter, evaluates each listing against a candidate resume using OpenAI GPT-4o, and delivers the top ranked matches via email and CSV file.

---

## How It Works

1. Scrapes job listings concurrently from all four platforms
2. Parses your resume PDF and sends each job + resume to GPT-4o for scoring
3. Filters results below a configurable score threshold (default: 70)
4. Returns all qualifying matches ranked by relevance (or top N when TOP_RESULTS is set)
5. Always delivers a report via email and CSV — even when zero jobs qualify

---

## Architecture

Built on **Hexagonal Architecture (Ports and Adapters)**. Core domain logic is fully isolated from scrapers, the LLM, and output delivery. Each platform is a separate adapter — swapping or adding a platform never touches the core.

```
src/
├── core/
│   ├── domain/        ← Pydantic entities: Job, Resume, MatchResult
│   ├── ports/         ← Abstract interfaces: ScraperPort, EvaluatorPort, OutputPort
│   └── services/      ← JobSearchService (pipeline orchestration)
└── adapters/
    ├── scrapers/       ← linkedin.py, indeed.py, glassdoor.py, ziprecruiter.py
    ├── evaluator/      ← openai_evaluator.py, anthropic_evaluator.py
    └── output/         ← email_output.py, file_output.py
```

See [docs/architecture.md](docs/architecture.md) for the full architecture document.

---

## Evaluator Providers

This app supports two evaluation providers. Configure via `EVALUATOR_PROVIDER` in `.env`.

**OpenAI GPT-4o (default):**
```env
EVALUATOR_PROVIDER=openai
```
Requires: `OPENAI_API_KEY`
Uses structured output enforcement via `response_format` json_schema strict mode.

**Anthropic Claude (claude-sonnet-4-6):**
```env
EVALUATOR_PROVIDER=anthropic
```
Requires: `ANTHROPIC_API_KEY`
Uses prompt-based JSON enforcement.

Switching providers requires only a `.env` change — no code changes needed.

---

## Requirements

- Docker + Docker Compose
- An OpenAI API key (GPT-4o access) or Anthropic API key (claude-sonnet-4-6 access)
- A Gmail account with an App Password configured
- Your resume as a PDF file

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd job-search-automation
```

### 2. Run the setup script

```bash
chmod +x setup.sh && ./setup.sh
```

This creates the `.venv` virtual environment and installs all dependencies.

### 3. Configure environment variables

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` and set the following:

```env
# LLM
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_claude_api_key

# Job Search API
JSEARCH_API_KEY=your_jsearch_key

# Email delivery
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
EMAIL_RECIPIENT=recipient@example.com

# Scoring
SCORE_THRESHOLD=70

# Optional — remove to return all qualifying results
# TOP_RESULTS=10
```

See [docs/env.md](docs/env.md) for descriptions of every variable and how to generate a Gmail App Password.

### 4. Add your resume

Place your resume PDF at:

```
docs/resume/resume.pdf
```

### 5. Build the Docker container

```bash
docker compose build
```

---

## Running the Agent

Run directly with arguments:

```bash
python -m src.main --query "Job Title" --location "Location"
```

```bash
docker compose run agent
```

Or pass them inline without editing `.env`:

```bash
docker compose run -e QUERY="Senior Python Developer" -e LOCATION="Remote" agent
```

Results are delivered to your configured email address and saved to:

```
output/results_<timestamp>.csv
```

Logs are written to:

```
logs/agent_<timestamp>.log
```

Both directories are persisted via Docker volume mounts and survive container restarts.

---

## Result Filtering

**SCORE_THRESHOLD** (default: 75)
Jobs scoring below this are excluded from qualifying results.
When no jobs meet the threshold a zero results report is still delivered with top 5 near-miss jobs and a suggested lower threshold.

**TOP_RESULTS** (optional — not set by default)
When set caps the number of qualifying results delivered after score filtering.
When not set all qualifying results above SCORE_THRESHOLD are returned.
Add to `.env` to enable:
```env
TOP_RESULTS=10
```

**Zero Results Behavior:**
If no jobs meet SCORE_THRESHOLD the app still delivers a report containing:
- Explanation of what happened
- Top 5 near-miss jobs below threshold
- Suggested lower threshold value
- Total jobs evaluated this run

You always receive an email and CSV after every run — no silent failures.

---

## Development

### Activate the virtual environment

```bash
source .venv/bin/activate
```

### Run the full test suite

```bash
pytest tests/unit/ -v
```

### Run tests for a specific layer

```bash
pytest tests/unit/core/domain/ -v
pytest tests/unit/core/ports/ -v
pytest tests/unit/core/services/ -v
pytest tests/unit/adapters/ -v
```

All tests mock external dependencies — no real API calls, no live network, no real files required.

---

## Adding a New Job Platform

Follow the skill in [ai/skills/add-job-source.md](ai/skills/add-job-source.md) or run `/add-job-source [platform]` in Claude Code.

The short version:
1. Create `src/adapters/scrapers/<platform>.py` implementing `ScraperPort`
2. Add the scraper to the `scrapers` list in `src/main.py`
3. Write unit tests in `tests/unit/adapters/scrapers/test_<platform>.py`

---

## Project Docs

| Document | Description |
|---|---|
| [docs/prd.md](docs/prd.md) | Product requirements |
| [docs/architecture.md](docs/architecture.md) | Architecture decisions and diagrams |
| [docs/env.md](docs/env.md) | Environment variable reference |
| [ai/rules.md](ai/rules.md) | Coding conventions — read before making changes |
| [ai/commands.md](ai/commands.md) | Claude Code command shortcuts |

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM | OpenAI GPT-4o OR Claude Sonnet-4-6 |
| JS-rendered scraping | Playwright (LinkedIn, Glassdoor) |
| Static scraping | BeautifulSoup + requests (Indeed, ZipRecruiter) |
| Resume parsing | PyPDF2 |
| Config management | python-dotenv |
| Containerization | Docker + docker-compose |
| Email delivery | Gmail SMTP (smtplib) |
| Testing | pytest + pytest-asyncio |
