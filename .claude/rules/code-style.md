# Rules — Code Style, Config & Git

## Language & runtime

- Python 3.10+. All code runs inside the `.venv` virtual environment
  (`source .venv/bin/activate`).
- All scraper, evaluator, service, and output methods use `async`/`await`.
- Use `asyncio.gather` for concurrent scraping across platforms.

## Code standards

- Every function has type hints and a docstring.
- Follow PEP 8. Maximum line length: 100 characters. No unused imports.
- Domain data crossing a boundary is a Pydantic model — not a dict.

## Secrets & configuration

- All secrets and config live in `.env`, loaded via `python-dotenv` — never
  hardcode values.
- `.env` is git-ignored and must never be committed.
- Every new environment variable must be documented in `docs/env.md`. That file
  is the single source of truth for the variable list.

## Git

- Never commit `.env`.
- Commit message format: `<type>: <short description>`.
- Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.
  Example: `feat: add LinkedIn scraper`.
- One feature or fix per commit. Run `pytest tests/unit/ -v` before committing.
