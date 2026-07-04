---
name: testing
description: >
  How to write and run tests in this repo. Use when adding or fixing tests, or
  when verifying a change before committing.
---

# Skill: Testing

## Goal

Write and maintain unit tests that mirror `src/` and never touch real external
systems.

## Layout

- Unit tests live in `tests/unit/` and mirror `src/` exactly (e.g.
  `src/core/services/job_search_service.py` →
  `tests/unit/core/services/test_job_search_service.py`).
- There is **no `tests/integration/` suite and no `tests/fixtures/` directory**
  today — do not assume they exist.
- Shared fixtures are in `tests/conftest.py` (injected automatically).

## Steps

1. Identify the function or module to test; create/locate the mirrored test file.
2. Write a happy-path test (expected inputs → expected output).
3. Write at least one failure-case test: empty input, missing field, or an API
   timeout / HTTP error.
4. Mock all external calls with `unittest.mock` (`patch`, `MagicMock`). Async
   functions use `@pytest.mark.asyncio` (pytest-asyncio).
5. Run `pytest tests/unit/ -v`. All tests must pass; none may call a real API.

## Naming

- Test files: `test_<module>.py`
- Test functions: `test_<function>_<scenario>()`
  (e.g. `test_fetch_jobs_returns_list_of_job_models`)
