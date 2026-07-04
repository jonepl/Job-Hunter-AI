Run the test suite.

- Run: `pytest tests/unit/ -v` (only a unit suite exists today).
- Fix all failures before confirming complete.
- Optionally scope to a layer or module, e.g.
  `pytest tests/unit/core/services/ -v` or
  `pytest tests/unit/adapters/scrapers/test_jsearch.py -v`.
