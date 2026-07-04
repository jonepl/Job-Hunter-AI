Switch the active LLM evaluator provider.

Argument: `[provider]` — `openai` or `anthropic`.

- Update `EVALUATOR_PROVIDER` in `.env`.
- Ensure the matching API key is set (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).
- Confirm the correct evaluator initializes on the next run (built by
  `src/adapters/evaluator/factory.py`). Both providers return the identical
  `MatchResult` shape — no code changes are needed to switch.
