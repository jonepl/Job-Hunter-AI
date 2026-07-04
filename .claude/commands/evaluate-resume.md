Build or update the resume-to-job evaluation logic.

Follow `.claude/skills/resume-evaluation/SKILL.md`. Changes to scoring live in
the evaluator adapters (`src/adapters/evaluator/`) and their prompts
(`prompts.py`) — the output must stay a valid `MatchResult` (including the
9-category `score_breakdown`). Test with mocked LLM responses; never call a real
API in tests.
