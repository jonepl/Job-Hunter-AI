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
| SCORE_THRESHOLD | Minimum match score to include in results (0-100). Used in legacy single search mode. | `75` |
| TOP_RESULTS | When set caps the number of qualifying results delivered after score filtering. | not set — all qualifying results returned |
| DATE_POSTED | Default recency filter for job listings. Values: `24h`, `3days`, `week`, `month`. Used in legacy single search mode. | `3days` |
| ACTIVE_SCRAPERS | Comma-separated list of scrapers. Used in legacy single search mode. Supported: `linkedin`, `indeed`, `glassdoor`, `ziprecruiter`. | all four |

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
MAX_CONCURRENT_EVALUATIONS=3

# ── JSearch (Default to us) ───────────────────────────────────────────────────────────────────
JSEARCH_COUNTRY=us
```

---

## Notes

- SCORE_THRESHOLD accepts integer values between 0 and 100
- TOP_RESULTS is optional — omit it entirely to return all qualifying results
- EMAIL_RECIPIENT can be the same as GMAIL_ADDRESS
- Never share or commit any of these values to Git
- Rotate API keys immediately if accidentally exposed
