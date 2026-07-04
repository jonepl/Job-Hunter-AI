Implement a new feature.

Argument: `[description]` — what the feature should do.

Follow `.claude/skills/feature-development/SKILL.md`. Read the relevant
`.claude/rules/` topic files first, respect the hexagonal boundaries (new
behavior goes in a new adapter or a service method — never break the core's
inward dependency direction), add unit tests under `tests/unit/`, and run
`pytest tests/unit/ -v` before finishing.
