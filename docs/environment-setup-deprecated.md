# Skill: Environment Setup

---
name: environment-setup
description: >
  Bootstrap a new agentic job search project in VS Code. Use this skill
  to set up the full project environment including Python virtual environment,
  project structure, Agent Control System (rules, commands, skills), .env file,
  .gitignore, and all core dependencies. Trigger this skill at the start of any
  new agentic Python project, or when a developer says "set up my project",
  "initialize my environment", or "bootstrap this project".
---

## Goal

Set up a fully configured local development environment for the job search agent project. This includes verifying system prerequisites, creating the project structure, configuring the Agent Control System, installing dependencies, and validating the setup is complete.

---

## Prerequisites

Before executing any steps, verify the following are installed by running each command in the terminal. If any fail, stop and notify the user with the missing dependency and installation instructions.

```bash
python --version        # Required: 3.10+
node --version          # Required: 18+ (for Claude Code)
git --version           # Required: any recent version
pip --version           # Required: any recent version
```

---

## Steps

### Step 1 — Create Python Virtual Environment

Create and activate an isolated Python environment.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

**Validation:** Run `which python` (macOS/Linux) or `where python` (Windows). The path should point inside `.venv/`.

---

### Step 2 — Scaffold Project Structure

Create the full directory and file structure for the project.

```bash
mkdir -p ai/skills
mkdir -p docs
mkdir -p src/scraper
mkdir -p src/evaluator
mkdir -p src/tools
mkdir -p tests
```

Create the following empty placeholder files:

```bash
touch ai/rules.md
touch ai/commands.md
touch ai/skills/feature-development.md
touch ai/skills/debugging.md
touch ai/skills/testing.md
touch docs/prd.md
touch docs/architecture.md
touch src/__init__.py
touch src/scraper/__init__.py
touch src/evaluator/__init__.py
touch src/tools/__init__.py
touch tests/__init__.py
touch README.md
```

**Expected structure after this step:**

```
job-search-agent/
│
├── ai/
│   ├── rules.md
│   ├── commands.md
│   └── skills/
│       ├── feature-development.md
│       ├── debugging.md
│       └── testing.md
│
├── docs/
│   ├── prd.md
│   └── architecture.md
│
├── src/
│   ├── __init__.py
│   ├── scraper/
│   │   └── __init__.py
│   ├── evaluator/
│   │   └── __init__.py
│   └── tools/
│       └── __init__.py
│
├── tests/
│   └── __init__.py
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

**Validation:** Confirm all directories and files exist using `ls -R` or `tree` if available.

---

### Step 3 — Create `.gitignore`

Create a `.gitignore` file to prevent sensitive files and build artifacts from being committed.

```bash
cat > .gitignore << 'EOF'
# Environment
.env
.venv/
__pycache__/
*.pyc
*.pyo

# VS Code
.vscode/

# OS
.DS_Store
Thumbs.db

# Python packaging
*.egg-info/
dist/
build/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# Playwright
playwright-report/
test-results/
EOF
```

**Validation:** Confirm `.gitignore` exists and contains `.env` on its own line.

---

### Step 4 — Create `.env` File

Create a `.env` file to store API keys securely. Populate with placeholder values — the user will replace these with real keys.

```bash
cat > .env << 'EOF'
# LLM Provider
OPENAI_API_KEY=your_openai_api_key_here

# Claude Code (Anthropic)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Job Search APIs
JSEARCH_API_KEY=your_jsearch_api_key_here
EOF
```

**Validation:** Confirm `.env` exists and is listed in `.gitignore`. Never commit this file.

---

### Step 5 — Create `requirements.txt` and Install Dependencies

Create the `requirements.txt` file:

```bash
cat > requirements.txt << 'EOF'
# LLM Provider
openai

# Environment variable management
python-dotenv

# Web scraping
playwright
beautifulsoup4
requests

# Resume parsing
pypdf2

# Testing
pytest
pytest-asyncio

# Utilities
lxml
EOF
```

Install all dependencies:

```bash
pip install -r requirements.txt
```

Install Playwright browser binaries:

```bash
playwright install
```

**Validation:** Run `pip list` and confirm all packages from `requirements.txt` appear. Run `playwright --version` to confirm browser binaries installed.

---

### Step 6 — Populate Agent Control System

Populate the core Agent Control System files so Claude Code has project context for all future tasks.

#### `ai/rules.md`

```bash
cat > ai/rules.md << 'EOF'
# Project Rules

These rules must be followed at all times when working on this project.

## Language & Runtime
- Use Python 3.10+
- All code must run inside the .venv virtual environment

## API & Secret Management
- Use python-dotenv to load all API keys from .env
- Never hardcode API keys, URLs, or credentials in source code
- All configurable values must be stored in .env or a config file

## LLM Provider
- Use OpenAI GPT-4o as the primary LLM provider
- Use the openai Python SDK for all LLM calls

## Web Scraping
- Use Playwright for JavaScript-rendered pages (e.g. LinkedIn)
- Use BeautifulSoup + requests for static HTML pages (e.g. Indeed RSS)
- Use JSearch API (RapidAPI) as the primary job listing data source

## Code Standards
- All tool functions must return structured JSON
- All functions must include type hints
- Write a pytest test for every tool function
- Follow PEP 8 style conventions

## Project Structure
- Scrapers go in src/scraper/
- Evaluation logic goes in src/evaluator/
- Reusable tool functions go in src/tools/
- All tests go in tests/
EOF
```

#### `ai/commands.md`

```bash
cat > ai/commands.md << 'EOF'
# Commands

Reusable task shortcuts for common development operations.

## /add-job-source
Scaffold a new job platform scraper.
- Create a new file in src/scraper/
- Implement a fetch_jobs(query: str) -> list[dict] function
- Return structured JSON with keys: title, company, location, url, description
- Write a corresponding test in tests/

## /evaluate-jd
Build or update the JD evaluation logic.
- Read the resume from docs/resume.pdf or docs/resume.txt
- Compare resume skills against the job description
- Return a match score (0-100) and a list of matching/missing skills

## /run-tests
Run the full test suite and fix any failures.
- Run: pytest tests/ -v
- Identify failing tests
- Fix the root cause in source code
- Re-run until all tests pass

## /add-tool
Add a new tool function to src/tools/.
- Define the function with clear input/output types
- Return structured JSON
- Write a unit test in tests/

## /debug
Debug a failing component.
- Follow the skill in ai/skills/debugging.md
EOF
```

#### `ai/skills/feature-development.md`

```bash
cat > ai/skills/feature-development.md << 'EOF'
# Skill: Feature Development

## Goal
Implement a new feature in the job search agent following project conventions.

## Steps
1. Understand the feature requirement clearly before writing any code
2. Identify which module the feature belongs to (scraper, evaluator, tools)
3. Locate relevant existing files to understand patterns already in use
4. Implement the feature in the appropriate src/ directory
5. Ensure the function returns structured JSON
6. Write a pytest test in tests/ covering the happy path and at least one edge case
7. Run pytest to confirm all tests pass
8. Update README.md if the feature changes how the project is used
EOF
```

#### `ai/skills/debugging.md`

```bash
cat > ai/skills/debugging.md << 'EOF'
# Skill: Debugging

## Goal
Identify and resolve a bug or failure in the project.

## Steps
1. Reproduce the failing behavior — run the code and capture the exact error message
2. Identify the file and line number where the failure originates
3. Trace the code path that leads to the failure
4. Form a hypothesis about the root cause
5. Implement the smallest possible fix
6. Run the relevant pytest tests to confirm the fix works
7. Run the full test suite to confirm no regressions were introduced
EOF
```

#### `ai/skills/testing.md`

```bash
cat > ai/skills/testing.md << 'EOF'
# Skill: Testing

## Goal
Write and maintain tests for project components.

## Steps
1. Identify the function or module to be tested
2. Create a test file in tests/ named test_<module>.py if it does not exist
3. Write a test for the happy path (expected inputs, expected outputs)
4. Write a test for at least one edge case (empty input, missing field, API failure)
5. Use pytest fixtures for any shared setup
6. Run pytest tests/ -v to confirm all tests pass
EOF
```

**Validation:** Confirm all four files are non-empty using `cat ai/rules.md`.

---

### Step 7 — Initialize Git Repository

Initialize version control for the project.

```bash
git init
git add .
git commit -m "Initial project setup — environment bootstrap complete"
```

**Validation:** Run `git log --oneline` and confirm one commit appears.

---

### Step 8 — Validate Full Setup

Run this final checklist to confirm the environment is complete:

```bash
# 1. Virtual environment active
which python

# 2. Dependencies installed
pip list

# 3. Playwright ready
playwright --version

# 4. Project structure present
ls -R

# 5. Git initialized
git log --oneline

# 6. .env exists and is git-ignored
git status
```

**Expected outcome:** `.env` should appear as untracked/ignored and NOT in the staged files.

---

## Error Handling

| Error | Action |
|---|---|
| `python --version` shows < 3.10 | Stop. Ask user to install Python 3.10+ from python.org |
| `node --version` fails | Stop. Ask user to install Node.js 18+ from nodejs.org |
| `pip install` fails | Check virtual environment is activated. Retry. |
| `playwright install` fails | Run `playwright install --with-deps` to include system dependencies |
| `.env` appears in `git status` staged files | Stop immediately. Run `git reset HEAD .env` and verify `.gitignore` contains `.env` |

---

## Completion

When all steps and validations pass, notify the user:

> ✅ Environment setup complete. Your project is ready for Phase 1 development.
> Next step: Add your real API keys to the `.env` file, then begin building the scraper in `src/scraper/`.