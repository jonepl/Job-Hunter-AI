# Commands

Invoke these commands by typing them in Claude Code.
Each command maps to a structured task the agent will execute.

---

## /setup
Set up the project environment for the first time.
- Instruct the user to run: `chmod +x setup.sh && ./setup.sh`
- Then read `ai/skills/environment-setup.md` for project context

## /add-job-source [platform]
Add a new job platform scraper.
- Follow the skill in `ai/skills/add-job-source.md`
- Replace [platform] with: linkedin, indeed, glassdoor, or ziprecruiter

## /evaluate-resume
Build or update the resume evaluation logic.
- Follow the skill in `ai/skills/resume-evaluation.md`

## /run-tests
Run the full test suite and fix any failures.
- Run: `pytest tests/ -v`
- Identify and fix all failing tests
- Re-run until all tests pass

## /debug [description]
Debug a failing component.
- Replace [description] with a short description of the failure
- Follow the skill in `ai/skills/debugging.md`

## /add-feature [description]
Implement a new feature.
- Replace [description] with what the feature should do
- Follow the skill in `ai/skills/feature-development.md`

## /refactor [file]
Refactor an existing file for clarity or performance.
- Read the target file first
- Apply changes without breaking existing tests
- Run `pytest tests/ -v` to confirm no regressions

## /document [file]
Add or update docstrings and inline comments in a file.
- Add a docstring to every function missing one
- Follow Google-style docstring format
- Do not change any logic