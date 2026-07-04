Refactor an existing file for clarity or performance.

Argument: `[file]`

- Read the target file first.
- Preserve behavior — apply changes without breaking existing tests.
- Do not change public signatures or the hexagonal dependency direction unless
  explicitly asked.
- Run `pytest tests/unit/ -v` to confirm no regressions.
