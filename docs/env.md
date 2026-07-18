# Environment Variables

All variables are stored in .env and loaded via python-dotenv.
Secrets are injected into the Docker container at runtime via
env_file in docker-compose.yml.

Never commit .env to Git. Copy .env.example to .env and replace
all placeholder values with real credentials before running.

---

## Required Variables

| Variable | Description | Where To Get It |
|---|---|---|
| EVALUATOR_PROVIDER | Selects which LLM evaluator to use — `openai` or `anthropic` | Choose between the app defined values |
| OPENAI_API_KEY | GPT-4o API access for resume evaluation | platform.openai.com |
| ANTHROPIC_API_KEY | Claude Code authentication and ClaudeEvaluator API access | console.anthropic.com |
| GMAIL_ADDRESS | Gmail address used as SMTP sender | Your Gmail account |
| GMAIL_APP_PASSWORD | Gmail App Password for SMTP auth | Google Account → Security → App Passwords |
| EMAIL_RECIPIENT | Email address to receive ranked results | Your preferred email |
| JSEARCH_API_KEY | Job listings API | rapidapi.com/JSearch |


## Optional Variables

| Variable | Description | Default |
|---|---|---|
| EVALUATOR_MODEL | LLM model name for the evaluator. Overrides the provider's built-in default. Must be valid for the active `EVALUATOR_PROVIDER` (e.g. `gpt-4o` / `gpt-4o-mini` for openai, `claude-sonnet-4-5` for anthropic). The `--evaluator-model` CLI flag overrides this for a single run. An invalid model name fails the run fast with a clear error rather than scoring every job 0. | provider default (`gpt-4o` / `claude-sonnet-4-5`) |
| SCORE_THRESHOLD | Minimum match score to include in results (0-100). Used in legacy single search mode. | `75` |
| TOP_RESULTS | When set caps the number of qualifying results delivered after score filtering. | not set — all qualifying results returned |
| DATE_POSTED | Default recency filter for job listings. Values: `24h`, `3days`, `week`, `month`. Used in legacy single search mode. | `3days` |
| ACTIVE_SCRAPERS | Comma-separated list of scrapers. Used in legacy single search mode. Supported: `linkedin`, `indeed`, `glassdoor`, `ziprecruiter`. | all four |
| JSEARCH_MAX_PAGES | Number of result pages fetched per JSearch API call. Each page contains up to 10 job listings. Multiple pages are bundled into a single API request and do not increase free tier quota consumption. Valid range: 1–10. Values outside this range are clamped automatically. Examples: 1 → 10 jobs, 2 → 20 jobs (default), 5 → 50 jobs, 10 → 100 jobs. | `2` |
| MAX_CONCURRENT_EVALUATIONS | Maximum number of LLM evaluation calls running at the same time. Reduce if hitting provider concurrency limits. | `2` |
| EVALUATION_DELAY_SECONDS | Seconds to wait after each evaluation call before releasing the semaphore slot. Spreads token consumption over time to stay within TPM rate limits. | `1.0` |
| ENRICHMENT_ENABLED | Enables the Gemini pre-filter stage that flags obvious junk postings before paid evaluation (ADR-022). When not `true` the stage is skipped entirely with zero overhead. Requires `GEMINI_API_KEY`; a missing key degrades to disabled rather than failing the run. | `false` |
| ENRICHMENT_MODE | Pre-filter behavior. `shadow` evaluates every job and only *measures* what would have been skipped, reporting the false-skip rate so precision can be verified before it is trusted. `enforce` actually withholds flagged jobs from the paid evaluator. Start in `shadow`; graduate to `enforce` once the false-skip rate is 0 across ≥50 evaluated jobs. Ignored when `ENRICHMENT_ENABLED` is not `true`. | `shadow` |
| GEMINI_API_KEY | Google Gemini API key for the pre-filter. Only read when `ENRICHMENT_ENABLED=true`. | aistudio.google.com/app/apikey |
| GEMINI_MODEL | Gemini model name for the pre-filter. Must be available to your API key — a 404 disables the pre-filter for the run (fail-open) and is reported in the run summary. Override to trade cost for capability. | `gemini-3.5-flash` |
| ENRICHMENT_MAX_CONCURRENT | Maximum concurrent pre-filter calls. Kept low so a large scrape does not exceed the provider's per-minute request quota (the circuit breaker cannot undo requests already in flight). Free-tier keys should use `1`. | `2` |
| ENRICHMENT_DELAY_SECONDS | Seconds to wait after each pre-filter call before releasing the semaphore slot. Raise it to spread requests under a tight per-minute quota. | `1.0` |

---

## Persistence Settings

Job memory and deduplication (ADR-023/024/033/034). Persistence is always on — a
seen job is not re-scored, and its cross-provider sightings are remembered.

| Variable | Description | Default |
| --- | --- | --- |
| DB_PATH | Path to the SQLite database file. Created (with its parent directory) on first run. Persists across runs via the `./data` volume mount. | `data/agent.db` |
| DB_BUSY_TIMEOUT_MS | `PRAGMA busy_timeout` in milliseconds — how long a write waits for a competing write before erroring. Handles contention between a scheduled run and a browser mutation once the web server lands (ADR-034 §1). | `5000` |
| NEAR_MISS_BAND | Fixed-width offset below the score threshold that defines the near-miss band (ADR-033). A job is *near-miss* when `threshold - NEAR_MISS_BAND ≤ score < threshold`, and the zero-results suggested threshold is this floor. Replaces the old floor-the-lowest-of-five rule. | `15` |

---

## Scheduler Settings

| Variable | Required | Default | Description |
|---|---|---|---|
| SCHEDULE_ENABLED | No | `false` | Set to `true` to enable APScheduler mode. App runs indefinitely on SCHEDULE_CRON schedule. Set to `false` for immediate run mode. |
| SCHEDULE_CRON | Only when SCHEDULE_ENABLED=true | `0 8 * * 1-5` | Cron expression for schedule. Default runs weekdays at 8am. Standard cron format: `minute hour day month weekday`. |
| SCHEDULE_TIMEZONE | No | `America/New_York` | Timezone for scheduler. Uses IANA timezone names. |

### SCHEDULE_CRON Examples

| Expression | Meaning |
|---|---|
| `0 8 * * 1-5` | Weekdays at 8am |
| `0 */6 * * *` | Every 6 hours |
| `0 9,17 * * *` | 9am and 5pm daily |

### SCHEDULE_TIMEZONE Examples

```
America/New_York
America/Chicago
America/Los_Angeles
America/Denver
```

---

## Search Profile Settings

Profiles allow multiple independent searches to run per trigger. Each profile
delivers its own RunReport email and CSV.

| Variable | Required | Default | Description |
|---|---|---|---|
| PROFILE_COUNT | No | not set — falls back to legacy SEARCH_QUERY mode | Number of search profiles defined in .env. When set the app loads PROFILE_1_ through PROFILE_N_ variables. |

### Per-Profile Variables (replace N with profile number)

| Variable | Required | Default |
|---|---|---|
| PROFILE_N_QUERY | Yes | — |
| PROFILE_N_LOCATION | Required unless work type is remote only | `United States` when remote only |
| PROFILE_N_WORK_TYPE | No | None (all types) |
| PROFILE_N_DATE_POSTED | No | `3days` |
| PROFILE_N_SCRAPERS | No | all four platforms |
| PROFILE_N_SCORE_THRESHOLD | No | `75` |
| PROFILE_N_TOP_RESULTS | No | not set (all qualifying results) |


### PROFILE_N_WORK_TYPE Examples

```
remote
hybrid
onsite
```

## Legacy Single Search Settings

Used when PROFILE_COUNT is not set. Configure a single search directly.

| Variable | Required | Default |
|---|---|---|
| SEARCH_QUERY | Yes | — |
| SEARCH_LOCATION | Required unless WORK_TYPE=remote | `United States` when remote only |
| WORK_TYPE | No | None (all types) |
| DATE_POSTED | No | `3days` |
| ACTIVE_SCRAPERS | No | all four platforms |
| SCORE_THRESHOLD | No | `75` |
| TOP_RESULTS | No | not set (all qualifying results) |

---

## Gmail App Password Setup

A Gmail App Password is a 16-character code that allows the agent
to send email via SMTP without using your main Gmail password.

Steps to generate:
1. Go to myaccount.google.com
2. Navigate to Security
3. Enable 2-Step Verification if not already enabled
4. Search for App Passwords
5. Select Mail as the app and generate
6. Copy the 16-character password into GMAIL_APP_PASSWORD in .env

---

## .env.example

Copy this file to .env and replace all placeholder values:

```
# ── Scheduler ─────────────────────────────────────────────────────────────────
SCHEDULE_ENABLED=false
SCHEDULE_CRON=0 8 * * 1-5
SCHEDULE_TIMEZONE=America/New_York

# ── Search Profiles ───────────────────────────────────────────────────────────
PROFILE_COUNT=2

# Profile 1 — Senior remote roles
PROFILE_1_QUERY=Senior Software Engineer
PROFILE_1_WORK_TYPE=remote
PROFILE_1_DATE_POSTED=3days
PROFILE_1_SCRAPERS=linkedin,indeed,glassdoor,ziprecruiter
PROFILE_1_SCORE_THRESHOLD=75

# Profile 2 — Full stack hybrid NYC
PROFILE_2_QUERY=Full Stack Engineer
PROFILE_2_LOCATION=New York
PROFILE_2_WORK_TYPE=hybrid
PROFILE_2_DATE_POSTED=week
PROFILE_2_SCRAPERS=linkedin,glassdoor
PROFILE_2_SCORE_THRESHOLD=80
PROFILE_2_TOP_RESULTS=5

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
JSEARCH_API_KEY=your_jsearch_api_key_here

# ── Email ─────────────────────────────────────────────────────────────────────
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
EMAIL_RECIPIENT=your@email.com

# ── Evaluator ─────────────────────────────────────────────────────────────────
EVALUATOR_PROVIDER=openai
MAX_CONCURRENT_EVALUATIONS=2
EVALUATION_DELAY_SECONDS=1.0

# ── Pre-filter (Gemini, optional) ─────────────────────────────────────────────
# Flags obvious junk before paid evaluation. Start in shadow (measure only);
# flip to enforce once the false-skip rate is 0 across >= 50 evaluated jobs.
# Keep concurrency low (1 on free tier) so a large scrape does not blow the quota.
ENRICHMENT_ENABLED=false
ENRICHMENT_MODE=shadow
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
ENRICHMENT_MAX_CONCURRENT=2
ENRICHMENT_DELAY_SECONDS=1.0

# ── Persistence (job memory + dedup) ──────────────────────────────────────────
# SQLite job store. A seen job is not re-scored; NEAR_MISS_BAND defines the
# amber near-miss band below the threshold (ADR-023/024/033/034).
DB_PATH=data/agent.db
DB_BUSY_TIMEOUT_MS=5000
NEAR_MISS_BAND=15

# ── JSearch (Default to us) ───────────────────────────────────────────────────────────────────
JSEARCH_COUNTRY=us

# JSearch result pages per API call
# Each page = 10 jobs, 1 API request
# Valid range: 1-10 (default: 2)
JSEARCH_MAX_PAGES=2

# ── Cost Tracking ─────────────────────────────────────────────────────────────
SHOW_COST_ESTIMATE=false

# Token pricing — update when providers adjust rates (USD per 1M tokens)
OPENAI_INPUT_COST_PER_1M=2.50
OPENAI_OUTPUT_COST_PER_1M=10.00
ANTHROPIC_INPUT_COST_PER_1M=3.00
ANTHROPIC_OUTPUT_COST_PER_1M=15.00
```

---

---

## Cost Tracking

| Variable | Required | Default | Description |
|---|---|---|---|
| SHOW_COST_ESTIMATE | No | `false` | When `true` shows a pre-run cost estimate at startup and tracks actual token usage and cost per evaluation. Results included in logs, email footer, and CSV output. Set to `false` for zero performance overhead. |
| OPENAI_INPUT_COST_PER_1M | No | `2.50` | OpenAI input token cost per million tokens in USD. Update when OpenAI adjusts pricing. |
| OPENAI_OUTPUT_COST_PER_1M | No | `10.00` | OpenAI output token cost per million tokens in USD. |
| ANTHROPIC_INPUT_COST_PER_1M | No | `3.00` | Anthropic input token cost per million tokens in USD. |
| ANTHROPIC_OUTPUT_COST_PER_1M | No | `15.00` | Anthropic output token cost per million tokens in USD. |

---

## Notes

- SCORE_THRESHOLD accepts integer values between 0 and 100
- TOP_RESULTS is optional — omit it entirely to return all qualifying results
- EMAIL_RECIPIENT can be the same as GMAIL_ADDRESS
- Never share or commit any of these values to Git
- Rotate API keys immediately if accidentally exposed
