# Rules — Architecture

Hexagonal (Ports and Adapters). Read `docs/architecture.md` for the full
diagram and `docs/adr.md` for the reasoning behind these choices.

## Dependency direction

- Core domain logic must **never** import from adapters.
- All dependencies point inward — adapters depend on ports; ports define the
  domain contract; the core has zero knowledge of external systems.
- New platforms, evaluators, or output channels are added as **new adapters
  only** — never modify the core to accommodate them.

## Domain entities

- All domain entities are **Pydantic models** with field type hints — never
  plain dataclasses or dicts.
- Entities live in `src/core/domain/`.
- Current entities: `Job`, `Resume`, `MatchResult` (+ nested `ScoreBreakdown`,
  `ScoreCategory`), `RunReport`, `RunCost`, `EvaluationCost`, `CostEstimate`,
  `SearchProfile`, and the enums `ScraperName`, `WorkType`, `DatePosted`.
- Validation happens at the boundary — scraped and LLM-generated data is
  unreliable, so validate it into a model before it propagates.

## Port interfaces

- All ports are **Abstract Base Classes (ABC)** in `src/core/ports/`.
- Current ports: `ScraperPort`, `EvaluatorPort`, `OutputPort`.
- Every adapter explicitly subclasses its corresponding port. Missing abstract
  method implementations raise at instantiation, not silently at runtime.
- Port signatures (keep adapters in sync):
  - `ScraperPort.fetch_jobs(query, location, limit=25, work_types=None, date_posted=None) -> list[Job]`
  - `EvaluatorPort.evaluate(resume, job, work_types=None) -> tuple[MatchResult, int, int]`
  - `OutputPort.deliver(report) -> None`

## Entrypoint architecture

- `src/main.py` is a **thin entrypoint** — wires and dispatches only, no logic.
  Never add logic directly to `main.py`.
- CLI concerns → `src/cli/` (`args.py`, `overrides.py`).
- Logging config → `src/infra/logging.py`.
- Profile loading → `src/bootstrap.py`. Immediate run → `src/runner.py`.
- `bootstrap.py` and `runner.py` have **no CLI/argparse dependency** — they
  accept plain Python objects so a future API entrypoint can reuse them.
- `src/api/` is reserved for a future FastAPI entrypoint. `src/evaluator/`,
  `src/scraper/`, `src/tools/` are empty leftover stubs — real code is under
  `src/adapters/`.

## Project structure

- Domain entities → `src/core/domain/`
- Port interfaces → `src/core/ports/`
- Service orchestration → `src/core/services/`
- Scraper adapters → `src/adapters/scrapers/` (built via `scraper_factory.py`)
- Evaluator adapters → `src/adapters/evaluator/` (selected via `factory.py`)
- Output adapters → `src/adapters/output/`
- Unit tests → `tests/unit/` (mirrors `src/` exactly)
- Shared fixtures → `tests/conftest.py`
