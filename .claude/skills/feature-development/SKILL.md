---
name: feature-development
description: >
  How to add a feature to this hexagonal job-search agent without breaking the
  Ports & Adapters boundaries. Use when implementing new behavior — a new
  adapter, a new service capability, a new config-driven option, or a new domain
  field.
---

# Skill: Feature Development

## Goal

Implement a new feature following this repo's hexagonal conventions.

## Where features belong

- **New job platform** → a new adapter under `src/adapters/scrapers/` subclassing
  `ScraperPort`, registered in `scraper_factory.build_scrapers()`. See the
  `add-job-source` skill.
- **New evaluator / scoring change** → `src/adapters/evaluator/` (+ `prompts.py`).
  See the `resume-evaluation` skill.
- **New output channel** → a new adapter under `src/adapters/output/` subclassing
  `OutputPort`.
- **New pipeline behavior** → a method on `JobSearchService`
  (`src/core/services/job_search_service.py`).
- **New domain data** → a Pydantic entity/field under `src/core/domain/`.
- **New config surface** → a `.env` variable, loaded in
  `orchestration/bootstrap.py` / the relevant factory, documented in
  `docs/env.md`.

## Steps

1. Read `CLAUDE.md` and the relevant `.claude/rules/` topic file(s).
2. Clarify the requirement — ask if anything is ambiguous.
3. Respect the dependency direction: **core never imports from adapters.** Add
   an adapter or a service method rather than reaching outward from the core.
4. Follow existing patterns in the target module. Keep functions `async` where
   the surrounding code is async; add type hints and a docstring.
5. Domain data crossing a boundary must be a Pydantic model, not a dict.
6. Add unit tests under `tests/unit/`, mirroring the source path, mocking all
   external calls.
7. If you added a config variable, document it in `docs/env.md`. If you made a
   notable design decision, append an ADR to `docs/adr.md`.
8. Run `pytest tests/unit/ -v` — fix all failures.
9. Commit: `feat: <short description>`.
