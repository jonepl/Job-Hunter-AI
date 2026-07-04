Debug a failing component.

Argument: `[description]` — a short description of the failure.

Follow `.claude/skills/debugging/SKILL.md`: reproduce the failure and capture
the exact error, read the full stack trace, trace the code path, form a root-
cause hypothesis, apply the smallest fix (no refactoring while debugging), then
run `pytest tests/unit/ -v` to confirm no regressions.
