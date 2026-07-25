# Job Search Automation Agent

A Dockerized Python backend service that collects job listings from LinkedIn (scraped directly via Playwright) and from Indeed, Glassdoor, and ZipRecruiter (via the JSearch API), evaluates each listing against a candidate resume using an LLM (OpenAI GPT-4o or Anthropic Claude), and delivers the top ranked matches via email and CSV file.

---

## How It Works

1. Collects job listings concurrently from all four platforms (LinkedIn via Playwright; Indeed, Glassdoor, and ZipRecruiter via the JSearch API)
2. *(Optional)* Runs a cheap **Gemini pre-filter** to flag obvious junk postings before any paid evaluation — off by default, resume never seen ([details](#pre-filter-gemini-optional))
3. Parses your resume PDF and sends each job + resume to the configured LLM for scoring
4. Filters results below a configurable score threshold (default: 75)
5. Returns all qualifying matches ranked by relevance (or top N when TOP_RESULTS is set)
6. Always delivers a report via email and CSV — even when zero jobs qualify

---

## Architecture

Built on **Hexagonal Architecture (Ports and Adapters)**. Core domain logic is fully isolated from scrapers, the LLM, and output delivery. Each platform is a separate adapter — swapping or adding a platform never touches the core.

```
src/
├── main.py            ← thin CLI entrypoint (python -m src.main)
├── orchestration/     ← composition + run layer (assembles the hexagon)
│   ├── bootstrap.py       ← profile loading
│   ├── runner.py          ← immediate run logic
│   ├── scheduler.py       ← APScheduler scheduled mode
│   ├── service_factory.py ← composition root
│   ├── mark_runner.py     ← mark CLI backend
│   ├── resume_runner.py   ← resume CLI backend
│   └── generation_runner.py ← generate CLI backend
├── api/               ← FastAPI driving adapter (serves API + SPA)
├── cli/               ← argparse definitions and CLI overrides
├── infra/             ← logging configuration
├── core/
│   ├── domain/        ← Pydantic entities: Job, Resume, MatchResult, EnrichmentResult, EnrichmentSummary
│   ├── ports/         ← Abstract interfaces: ScraperPort, EvaluatorPort, OutputPort, JobEnrichmentPort
│   └── services/      ← JobSearchService (pipeline orchestration)
└── adapters/
    ├── scrapers/       ← linkedin.py, jsearch.py
    ├── evaluator/      ← openai_evaluator.py, anthropic_evaluator.py
    ├── enrichment/     ← gemini_enrichment.py (optional pre-filter)
    └── output/         ← email_output.py, file_output.py
```

See [docs/architecture.md](docs/architecture.md) for the full architecture document.

---

## Evaluator Providers

This app supports two evaluation providers. Configure via `EVALUATOR_PROVIDER` in `.env`.

**OpenAI GPT-4o:**
```env
EVALUATOR_PROVIDER=openai
```
Requires: `OPENAI_API_KEY`
Uses structured output enforcement via `response_format` json_schema strict mode.

**Anthropic Claude (claude-sonnet-4-5):**
```env
EVALUATOR_PROVIDER=anthropic
```
Requires: `ANTHROPIC_API_KEY`
Uses prompt-based JSON enforcement.

Switching providers requires only a `.env` change — no code changes needed.

---

## Requirements

- Docker + Docker Compose
- An OpenAI API key (GPT-4o access) or Anthropic API key (claude-sonnet-4-5 access)
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
SCORE_THRESHOLD=75

# Optional — remove to return all qualifying results
# TOP_RESULTS=10

# Optional — JSearch pages per API call (1-10, each page = 10 jobs, default: 2)
# JSEARCH_MAX_PAGES=2
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

**Remote jobs (location optional — defaults to "United States"):**
```bash
python -m src.main --query "Senior Software Engineer" --work-type remote
```

**Remote jobs with explicit location:**
```bash
python -m src.main --query "Senior Software Engineer" --location "United States" --work-type remote
```

**Hybrid jobs (location required):**
```bash
python -m src.main --query "Senior Software Engineer" --location "New York" --work-type hybrid
```

**On-site jobs (location required):**
```bash
python -m src.main --query "Senior Software Engineer" --location "Miami, FL" --work-type onsite
```

**All types, specific location:**
```bash
python -m src.main --query "Senior Software Engineer" --location "Remote"
```

**Location Rules:**

| `--work-type`       | `--location`     | Behavior                                  |
|---------------------|------------------|-------------------------------------------|
| `remote` (only)     | omitted          | defaults to `"United States"`             |
| `remote` (only)     | provided         | use provided value                        |
| `hybrid`            | omitted          | error — location required                 |
| `onsite`            | omitted          | error — location required                 |
| mixed (e.g. remote hybrid) | omitted   | error — location required                 |
| not specified       | provided         | use provided value (existing behavior)    |
| not specified       | omitted          | error — location required                 |

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

## Scheduled Docker Execution

Set `SCHEDULE_ENABLED=true` in `.env` to run on a schedule inside Docker:

```env
SCHEDULE_ENABLED=true
SCHEDULE_CRON=0 8 * * 1-5
SCHEDULE_TIMEZONE=America/New_York
```

Start the container:

```bash
docker-compose up -d
```

The container runs indefinitely and executes all profiles on the cron schedule.
Results delivered via email and CSV after each run.

To stop:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f agent
```

Immediate run (no scheduler):
```bash
# Set SCHEDULE_ENABLED=false in .env, then:
docker-compose run agent
# or
python -m src.main
```

---

## Multiple Search Profiles

Define multiple searches in `.env`:

```env
PROFILE_COUNT=2

PROFILE_1_QUERY=Senior Software Engineer
PROFILE_1_WORK_TYPE=remote
PROFILE_1_SCORE_THRESHOLD=75

PROFILE_2_QUERY=Full Stack Engineer
PROFILE_2_LOCATION=New York
PROFILE_2_WORK_TYPE=hybrid
PROFILE_2_SCORE_THRESHOLD=80
```

Each profile runs independently and delivers its own email and CSV report.

Profile fields:

| Variable | Required |
|---|---|
| `PROFILE_N_QUERY` | Yes |
| `PROFILE_N_LOCATION` | Required unless work type is remote only |
| `PROFILE_N_WORK_TYPE` | Optional |
| `PROFILE_N_DATE_POSTED` | Optional (default: `3days`) |
| `PROFILE_N_SCRAPERS` | Optional (default: all four) |
| `PROFILE_N_SCORE_THRESHOLD` | Optional (default: `75`) |
| `PROFILE_N_TOP_RESULTS` | Optional (default: all qualifying) |

---

## Scraper Configuration

Control which platforms are scraped via `.env`:

```env
ACTIVE_SCRAPERS=linkedin,indeed,glassdoor,ziprecruiter
```

**Common configurations:**

LinkedIn only (fastest — no JSearch API quota used):
```env
ACTIVE_SCRAPERS=linkedin
```

JSearch platforms only (saves LinkedIn Playwright overhead):
```env
ACTIVE_SCRAPERS=indeed,glassdoor,ziprecruiter
```

LinkedIn + Indeed only:
```env
ACTIVE_SCRAPERS=linkedin,indeed
```

**Override per run via CLI** (does not change `.env`):
```bash
python -m src.main \
  --query "Senior Software Engineer" \
  --work-type remote \
  --scrapers linkedin

python -m src.main \
  --query "Senior Software Engineer" \
  --work-type remote \
  --scrapers linkedin,indeed
```

CLI `--scrapers` overrides `ACTIVE_SCRAPERS` in `.env` for that run only.

**JSearch result volume** (`JSEARCH_MAX_PAGES`, default: `2`)
Controls how many pages are fetched per JSearch API call. Each page returns up to 10 jobs.
Multiple pages are bundled into a single API request — increasing this does not consume
additional free-tier quota. Valid range: `1`–`10`. Values outside this range are clamped automatically.
Add to `.env` to override:
```env
JSEARCH_MAX_PAGES=5   # 50 jobs per JSearch platform per run
```

---

## Pre-filter (Gemini, optional)

An optional stage sits **between scraping and evaluation** and uses a cheap Gemini
model to flag obviously irrelevant postings before the expensive, resume-aware LLM
evaluation runs. It is **disabled by default** with zero overhead.

**Privacy is structural.** The pre-filter port (`JobEnrichmentPort.enrich(job)`)
accepts only a `Job` and never a `Resume` — your resume can never reach Gemini,
enforced by the interface signature (see [ADR-022](docs/adr.md)), not by convention.

**Enable it:**
```env
ENRICHMENT_ENABLED=true
ENRICHMENT_MODE=shadow          # shadow (default) | enforce
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash   # optional override
ENRICHMENT_MAX_CONCURRENT=2     # lower to 1 on a free-tier key
ENRICHMENT_DELAY_SECONDS=1.0    # raise under a tight per-minute quota
```

**Two modes — measure first, then trust:**

| Mode | Behavior |
|---|---|
| `shadow` (default) | Evaluates **every** job anyway, but records what it *would* have skipped. Lets you measure the pre-filter's **false-skip rate** against real scores before relying on it. |
| `enforce` | Actually withholds flagged jobs from the paid evaluator — this is where you save money. |

Each run report (logs + email) shows a **Pre-filter Summary**: how many jobs were
flagged, the false-skip rate, estimated savings, and how many calls errored.
**Graduate to `enforce`** once the false-skip rate is `0` across ≥50 evaluated jobs
with no errors.

**Resilient by design:**
- **Fail-open** — any pre-filter error lets the job proceed to normal evaluation; a failure never drops a real job.
- **Circuit breaker** — quota exhaustion (`429`) or an unavailable model (`404`) trips a per-run breaker that skips the stage for the rest of the run, logged once. A bad `GEMINI_MODEL` disables the pre-filter for the run (it is *not* fatal) and is reported in the summary.
- **Throttled** — calls run under their own concurrency limit + delay so a large scrape can't blow the provider's per-minute quota.

> **Free-tier note:** Gemini's free tier has a low request-per-minute quota. Use
> `ENRICHMENT_MAX_CONCURRENT=1` and a larger `ENRICHMENT_DELAY_SECONDS` (e.g. `6`),
> and expect the stage to add noticeable latency. The pre-filter pays off most on
> noisy, broad, or staffing-heavy searches; narrow senior-role searches tend to
> contain little obvious junk to skip.

---

## LLM Cost Tracking

Enable cost visibility by setting `SHOW_COST_ESTIMATE=true` in `.env`.

**Before each run — startup estimate:**
```
════════════════════════════════════
Cost Estimate — Profile 1
Max jobs to evaluate : 85
Est. cost range      : $0.0042 - $0.0106
════════════════════════════════════
```

**During evaluation — per job:**
```
Evaluated 'Sr SWE' @ 'Disney' score=92 | tokens=3241/412 | $0.0122
```

**After evaluation — run total:**
```
════════════════════════════════════
Actual LLM Cost — Profile 1
Jobs evaluated  : 18
Total tokens    : 58,241 in / 7,476 out
Actual LLM cost : $0.2209
════════════════════════════════════
```

Email footer includes a cost summary section. CSV includes cost columns per row.

**Configuration:**
```env
SHOW_COST_ESTIMATE=true
OPENAI_INPUT_COST_PER_1M=2.50
OPENAI_OUTPUT_COST_PER_1M=10.00
ANTHROPIC_INPUT_COST_PER_1M=3.00
ANTHROPIC_OUTPUT_COST_PER_1M=15.00
```

Update rates when providers adjust pricing — no code change needed.

---

## Rate Limiting

The app controls LLM API concurrency to prevent TPM rate limit errors.

**Configure in `.env`:**
```env
MAX_CONCURRENT_EVALUATIONS=2
EVALUATION_DELAY_SECONDS=1.0
```

**Recommended values by OpenAI tier:**

| Tier | MAX_CONCURRENT_EVALUATIONS | EVALUATION_DELAY_SECONDS |
|---|---|---|
| Free tier | `1` | `2.0` |
| Tier 1 | `2` | `1.0` |
| Tier 2 | `5` | `0.5` |

If you see `429 TPM` errors: lower `MAX_CONCURRENT_EVALUATIONS` or increase `EVALUATION_DELAY_SECONDS`.

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

Follow the skill in [.claude/skills/add-job-source/SKILL.md](.claude/skills/add-job-source/SKILL.md) or run `/add-job-source [platform]` in Claude Code.

The short version:
1. Create `src/adapters/scrapers/<platform>.py` implementing `ScraperPort`
2. Register the scraper in `src/adapters/scrapers/scraper_factory.py`
3. Write unit tests in `tests/unit/adapters/scrapers/test_<platform>.py`

---

## Project Docs

| Document | Description |
|---|---|
| [docs/prd.md](docs/prd.md) | Product requirements |
| [docs/architecture.md](docs/architecture.md) | Architecture decisions and diagrams |
| [docs/env.md](docs/env.md) | Environment variable reference |
| [docs/adr.md](docs/adr.md) | Architecture Decision Records (living log) |
| [CLAUDE.md](CLAUDE.md) | Agent guide — auto-loaded by Claude Code every session |
| [.claude/rules/](.claude/rules/) | Coding conventions by topic — read before making changes |
| [.claude/commands/](.claude/commands/) | Claude Code slash commands |

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM | OpenAI GPT-4o OR Claude Sonnet-4-5 |
| Pre-filter (optional) | Google Gemini via google-genai |
| Browser scraping | Playwright (LinkedIn) |
| Job aggregator API | JSearch (RapidAPI) via requests (Indeed, Glassdoor, ZipRecruiter) |
| Resume parsing | PyPDF2 |
| Config management | python-dotenv |
| Containerization | Docker + docker-compose |
| Email delivery | Gmail SMTP (smtplib) |
| Testing | pytest + pytest-asyncio |
