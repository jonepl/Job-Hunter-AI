# Skill: Feature Development

## Goal
Implement a new feature following project conventions.

## Steps
1. Read `ai/rules.md` before writing any code
2. Clarify the feature requirement — ask if anything is ambiguous
3. Identify which module the feature belongs to:
   - New job platform → `src/scraper/`
   - Evaluation logic → `src/evaluator/`
   - Shared utility → `src/tools/`
4. Check existing files in the target module for patterns to follow
5. Implement the feature with type hints and a docstring
6. Ensure all tool functions return structured JSON
7. Write tests in `tests/` mirroring the source file location
8. Run `pytest tests/ -v` — fix all failures before proceeding
9. Commit with a clear message: `feat: <short description>`