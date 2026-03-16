---
name: environment-setup
description: >
  Reference document describing the project environment for this job search
  agent. Read this skill to understand the project structure, conventions,
  dependencies, and setup decisions before performing any development task.
  Trigger when a developer asks about project structure, how the environment
  works, or when onboarding to this codebase for the first time. If the
  environment has not been set up yet, instruct the user to run setup.sh
  rather than executing setup steps manually.
---

# Skill: Environment Setup

## Purpose

This document is a **reference skill** — not an execution skill. The environment
is set up by running the shell script:

```bash
chmod +x setup.sh
./setup.sh
```

This skill exists so Claude Code understands the project structure, conventions,
and decisions made during setup. Read this before performing any development task.

---

## Why a Script Handles Setup (Not an Agent)

Environment setup is **deterministic** — the same steps run the same way every
time with no reasoning or judgment required. Scripts are the correct tool for
deterministic tasks because they are:

- Free (no token cost)
- Fast (no LLM inference)
- Reliable (no hallucination risk)
- Repeatable (idempotent by design)

Agents are reserved for tasks requiring **reasoning, judgment, or adaptability**
such as writing code, debugging failures, or evaluating job descriptions.

**Agent-Script Boundary:** If a task can be expressed as a fixed sequence of
shell commands, it belongs in a script. If it requires decision-making based on
context, it belongs with the agent.

---

## What setup.sh Does

| Step | Action |
|---|---|
| 1 | Verifies Python 3.10+, Node.js 18+, Git, pip |
| 2 | Creates and activates Python virtual environment at `.venv/` |
| 3 | Scaffolds full project directory and placeholder files |
| 4 | Creates `.gitignore` |
| 5 | Creates `.env` with placeholder API keys |
| 6 | Creates `requirements.txt` |
| 7 | Installs all Python dependencies |
| 8 | Installs Playwright browser binaries |
| 9 | Initializes Git repository with initial commit |
| 10 | Runs final validation checks |

---

## Project Structure

```
job-search-agent/
│
├── ai/                             ← Agent Control System
│   ├── rules.md                    ← Permanent project conventions
│   ├── commands.md                 ← Reusable task shortcuts
│   └── skills/
│       ├── environment-setup.md    ← This file (reference)
│       ├── feature-development.md  ← How to add new features
│       ├── debugging.md            ← How to debug failures
│       └── testing.md              ← How to write and run tests
│
├── docs/
│   ├── prd.md                      ← Product Requirements Document
│   └── architecture.md             ← System architecture decisions
│
├── src/
│   ├── scraper/                    ← Job listing scrapers per platform
│   ├── evaluator/                  ← Resume vs JD evaluation logic
│   └── tools/                      ← Reusable tool functions
│
├── tests/                          ← pytest test suite
│
├── setup.sh                        ← One-command environment bootstrap
├── .env                            ← API keys (never commit this)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `openai` | GPT-4o LLM provider |
| `python-dotenv` | Load API keys from `.env` |
| `playwright` | Browser automation for JS-rendered pages (LinkedIn) |
| `beautifulsoup4` | HTML parsing for static pages (Indeed RSS) |
| `requests` | HTTP requests for third-party job APIs |
| `pypdf2` | Extract text from resume PDF |
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `lxml` | XML/HTML parsing utility |

---

## Environment Variables

All secrets are stored in `.env` and loaded via `python-dotenv`. Never hardcode
keys in source code. The `.env` file is git-ignored and must never be committed.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | GPT-4o API access |
| `ANTHROPIC_API_KEY` | Claude Code authentication |
| `JSEARCH_API_KEY` | JSearch job listings API (RapidAPI) |

---

## Key Conventions

These are enforced by `ai/rules.md` and apply to all code in this project:

- All tool functions return **structured JSON**
- All functions include **type hints**
- Every tool function has a corresponding **pytest test**
- Playwright is used for **JS-rendered pages** (e.g. LinkedIn)
- BeautifulSoup is used for **static HTML pages** (e.g. Indeed RSS)
- All API keys loaded from `.env` via `python-dotenv`
- PEP 8 style conventions apply throughout

---

## Agent-Script Hybrid Pattern

This project uses an **agent-script hybrid** approach:

```
Claude Code (reasoning layer)
        │
        ▼
Decides what needs to be done
        │
        ▼
Calls a script or tool (execution layer)
        │
        ▼
Script runs deterministically — free, fast
        │
        ▼
Claude Code reads result and decides next step
```

This pattern minimizes token usage while preserving the agent's reasoning
capability for tasks that actually require it.

---

## Onboarding Checklist for Claude Code

When starting a new session on this project, verify:

- [ ] Virtual environment is active (`source .venv/bin/activate`)
- [ ] `.env` contains real API keys (not placeholders)
- [ ] `ai/rules.md` has been read and conventions are understood
- [ ] Relevant skill file has been read before starting the task
