---
name: debugging
description: >
  How to trace and fix a bug or failure in this codebase. Use when a component
  is throwing, returning wrong data, or a test is failing.
---

# Skill: Debugging

## Goal

Identify and resolve a bug or failure with the smallest safe change.

## Steps

1. Reproduce the failure — run the code (or the failing test) and capture the
   exact error and full stack trace before forming any hypothesis.
2. Identify the file, function, and line where the error originates.
3. Trace the code path that leads there. In this repo failures usually sit in an
   adapter (scraper/evaluator/output) or in `JobSearchService` orchestration —
   the core domain entities rarely fail on their own.
4. Form a single root-cause hypothesis.
5. Apply the **smallest** fix — do not refactor while debugging.
6. Run the targeted test, e.g.
   `pytest tests/unit/adapters/scrapers/test_jsearch.py -v`.
7. Run the full unit suite: `pytest tests/unit/ -v`. Confirm no regressions.
8. Commit: `fix: <short description>`.

## Common areas

- **Scraper returns nothing / errors** — check network mocking in tests, and the
  graceful-degradation paths (HTTP errors, timeouts, empty responses).
- **Evaluator parse errors** — the LLM response must validate into `MatchResult`
  (including all 9 `score_breakdown` categories). Check `prompts.py`.
- **429 / TPM rate-limit errors** — lower `MAX_CONCURRENT_EVALUATIONS` or raise
  `EVALUATION_DELAY_SECONDS` (both in `.env`).
- **Wrong/empty results delivered** — check `SCORE_THRESHOLD`, `TOP_RESULTS`, and
  the near-miss path in `JobSearchService` / `RunReport`.
