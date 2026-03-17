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
| ANTHROPIC_API_KEY | Claude Code authentication | console.anthropic.com |
| GMAIL_ADDRESS | Gmail address used as SMTP sender | Your Gmail account |
| GMAIL_APP_PASSWORD | Gmail App Password for SMTP auth | Google Account → Security → App Passwords |
| EMAIL_RECIPIENT | Email address to receive ranked results | Your preferred email |
| SCORE_THRESHOLD | Minimum match score to include in results (0-100) | Set to 70 as default |

## Optional Variables

| Variable | Description | Where To Get It |
|---|---|---|
| JSEARCH_API_KEY | Fallback job listings API | rapidapi.com/JSearch |

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

OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GMAIL_ADDRESS=your_gmail_address@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
EMAIL_RECIPIENT=your_recipient_email@example.com
SCORE_THRESHOLD=70
JSEARCH_API_KEY=your_jsearch_api_key_here

---

## Notes

- SCORE_THRESHOLD accepts integer values between 0 and 100
- EMAIL_RECIPIENT can be the same as GMAIL_ADDRESS
- Never share or commit any of these values to Git
- Rotate API keys immediately if accidentally exposed
