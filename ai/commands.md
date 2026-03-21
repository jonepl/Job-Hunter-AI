# Commands

Invoke these by typing them in Claude Code.
Each command maps to a structured task the agent will execute.
Always read ai/rules.md before executing any command.

---

## Environment

/setup
Set up the project environment for the first time.
- Instruct the user to run: chmod +x setup.sh && ./setup.sh
- Then read ai/skills/environment-setup.md for project context

/build-docker
Build the Docker container.
- Follow the skill in ai/skills/docker.md
- Run: docker-compose build
- Confirm the build completes without errors

/run-agent [query] [location]
Trigger a manual agent run inside Docker.
- Replace [query] with job search query e.g. "Senior Python Developer"
- Replace [location] with location e.g. "Remote" or "Miami, FL"
- Run: docker-compose run agent

---

## Development

/add-job-source [platform]
Add a new job platform scraper.
- Follow the skill in ai/skills/add-job-source.md
- Replace [platform] with: linkedin, indeed, glassdoor, ziprecruiter

/add-feature [description]
Implement a new feature.
- Replace [description] with what the feature should do
- Follow the skill in ai/skills/feature-development.md

/refactor [file]
Refactor an existing file for clarity or performance.
- Read the target file first
- Apply changes without breaking existing tests
- Run pytest tests/ -v to confirm no regressions

/document [file]
Add or update docstrings and inline comments in a file.
- Add a docstring to every function missing one
- Follow Google-style docstring format
- Do not change any logic

---

## Testing

/run-tests
Run the full test suite.
- Run: pytest tests/ -v
- Fix all failures before confirming complete

/run-tests-unit
Run unit tests only.
- Run: pytest tests/unit/ -v
- Fix all failures before confirming complete

/run-tests-integration
Run integration tests only.
- Run: pytest tests/integration/ -v
- Fix all failures before confirming complete

---

## Evaluator

/switch-evaluator [provider]
Switch the active LLM evaluator provider.
- Replace [provider] with: openai or anthropic
- Update EVALUATOR_PROVIDER in .env
- Confirm the correct evaluator initializes on next run

---

## Debugging

/debug [description]
Debug a failing component.
- Replace [description] with a short description of the failure
- Follow the skill in ai/skills/debugging.md

/evaluate-resume
Build or update the resume evaluation logic.
- Follow the skill in ai/skills/resume-evaluation.md
