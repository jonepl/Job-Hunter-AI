---
name: environment-setup
description: >
  Reference for this repo's environment, structure, and setup conventions. Read
  it when onboarding to the codebase, or when asked about project structure, how
  the environment is bootstrapped, or where things live. Environment setup is
  deterministic — instruct the user to run setup.sh rather than performing the
  steps by hand.
---

# Skill: Environment Setup

## Purpose

A **reference** skill (not an execution skill). The environment is bootstrapped
by a shell script:

```bash
chmod +x setup.sh && ./setup.sh
source .venv/bin/activate
```

Setup is deterministic — scripts are free, fast, reliable, and idempotent.
Reserve the agent for tasks needing reasoning (writing code, debugging,
evaluating job descriptions). If a task is a fixed sequence of shell commands it
belongs in a script; if it needs judgment it belongs with the agent.

## What setup.sh does

Verifies prerequisites (Python 3.10+, pip, etc.), creates the `.venv` virtual
environment, installs Python dependencies from `requirements.txt`, installs
Playwright browser binaries, generates a `.env` with placeholders, and runs
validation checks.

## Project structure (as-built)

```
Job-Hunter-AI/
├── CLAUDE.md                       ← auto-loaded agent guide (start here)
├── .claude/
│   ├── rules/                      ← topic-scoped conventions
│   ├── commands/                   ← slash commands
│   └── skills/                     ← this skill lives here
├── docs/
│   ├── prd.md  architecture.md  adr.md  env.md
│   └── resume/resume.pdf           ← candidate resume (volume mounted)
├── src/
│   ├── main.py                     ← thin entrypoint (python -m src.main)
│   ├── orchestration/              ← bootstrap, runner, scheduler, service_factory, *_runner
│   ├── cli/                        ← argparse + overrides
│   ├── infra/                      ← logging, cost_tracker, cost_estimator
│   ├── core/
│   │   ├── domain/  ports/  services/
│   └── adapters/
│       ├── scrapers/   ← linkedin.py, jsearch.py, scraper_factory.py
│       ├── evaluator/  ← openai_evaluator.py, anthropic_evaluator.py, factory.py, prompts.py
│       └── output/     ← email_output.py, file_output.py
├── tests/unit/                     ← mirrors src/ exactly (no integration suite yet)
├── setup.sh  Dockerfile  docker-compose.yml  requirements.txt  .env
```

`src/api/`, `src/evaluator/`, `src/scraper/`, `src/tools/` are empty stubs —
real code lives under `src/adapters/`.

## Dependencies (requirements.txt)

`openai`, `anthropic` (LLM providers); `python-dotenv` (config); `playwright`
(LinkedIn browser automation); `requests` (JSearch API); `pypdf2` (resume
parsing); `pytest`, `pytest-asyncio` (tests); `apscheduler`, `pytz`
(scheduling); `beautifulsoup4`, `lxml` (present but currently unused — LinkedIn
uses Playwright selectors, not BeautifulSoup).

## Key environment variables

Full reference in `docs/env.md`. Secrets live in `.env` (git-ignored, never
committed), loaded via `python-dotenv`. Required: `EVALUATOR_PROVIDER`,
`OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY`, `GMAIL_ADDRESS`,
`GMAIL_APP_PASSWORD`, `EMAIL_RECIPIENT`, `JSEARCH_API_KEY`.

## Onboarding checklist

- [ ] `.venv` active (`source .venv/bin/activate`)
- [ ] `.env` contains real credentials (not placeholders)
- [ ] `CLAUDE.md` and the relevant `.claude/rules/` file read
- [ ] The task-specific skill read before starting
