# Rules — Testing

- The unit suite lives in `tests/unit/` and **mirrors `src/` exactly** (e.g.
  `src/adapters/scrapers/jsearch.py` → `tests/unit/adapters/scrapers/test_jsearch.py`).
- There is **no `tests/integration/` suite and no `tests/fixtures/` directory**
  today. Do not reference them or write commands that assume they exist. If an
  integration suite is added later, update this rule and `docs/architecture.md`.
- Unit tests mock all external calls — no real APIs, no live network, no real
  files. Use `unittest.mock` (`patch`, `MagicMock`). Async tests use
  `@pytest.mark.asyncio` (pytest-asyncio).
- Shared fixtures are defined in `tests/conftest.py` and injected automatically.
- Naming:
  - Test files: `test_<module>.py`
  - Test functions: `test_<function>_<scenario>()` (e.g.
    `test_fetch_jobs_returns_list_of_job_models`)
- Every module should have a corresponding unit test.
- Run `pytest tests/unit/ -v` before committing. All tests must pass and none
  may call a real external API.
