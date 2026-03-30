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
| OPENAI_API_KEY | GPT-4o API access for resume evaluation | platform.openai.com |
| ANTHROPIC_API_KEY | Claude Code authentication and ClaudeEvaluator API access | console.anthropic.com |
| GMAIL_ADDRESS | Gmail address used as SMTP sender | Your Gmail account |
| GMAIL_APP_PASSWORD | Gmail App Password for SMTP auth | Google Account → Security → App Passwords |
| EMAIL_RECIPIENT | Email address to receive ranked results | Your preferred email |
| SCORE_THRESHOLD | Minimum match score to include in results (0-100). When no jobs meet this threshold a zero results report is still delivered containing top 5 near-miss jobs and a suggested lower threshold value. | Set to 70 as default |
| JSEARCH_API_KEY | Job listings API | rapidapi.com/JSearch |
| EVALUATOR_PROVIDER | Selects which LLM evaluator to use — `openai` or `anthropic` (default: `openai`). Required only when using ClaudeEvaluator. | Set to `openai` or `anthropic` |

## Optional Variables

| Variable | Description | Where To Get It |
|---|---|---|
| TOP_RESULTS | When set caps the number of qualifying results delivered after score filtering. When not set all jobs above SCORE_THRESHOLD are returned. Default: not set — all qualifying results returned when not configured. | Set to any positive integer (e.g. `10`) |
| DATE_POSTED | Default recency filter for job listings. Controls how far back the app searches for job postings. Can be overridden per run via `--date-posted` CLI argument. Values: `24h` (past 24 hours), `3days` (past 3 days), `week` (past 7 days), `month` (past 30 days). Default: `3days`. | Set to `24h`, `3days`, `week`, or `month` |

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
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
JSEARCH_API_KEY=your_jsearch_api_key_here

GMAIL_ADDRESS=your_gmail_address@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
EMAIL_RECIPIENT=your_recipient_email@example.com

SCORE_THRESHOLD=70
EVALUATOR_PROVIDER=openai

# Default date posted filter (24h/3days/week/month)
DATE_POSTED=3days
```

---

## Notes

- SCORE_THRESHOLD accepts integer values between 0 and 100
- TOP_RESULTS is optional — omit it entirely to return all qualifying results
- EMAIL_RECIPIENT can be the same as GMAIL_ADDRESS
- Never share or commit any of these values to Git
- Rotate API keys immediately if accidentally exposed
