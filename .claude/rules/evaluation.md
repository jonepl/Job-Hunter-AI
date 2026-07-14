# Rules — LLM Evaluation, Cost & Rate Limiting

## LLM provider

- `EVALUATOR_PROVIDER` (`.env`) selects the evaluator: `openai` (default) or
  `anthropic`. The evaluator is built by `src/adapters/evaluator/factory.py`.
- Models: OpenAI `gpt-4o` (`OpenAIEvaluator`, `response_format` strict mode) and
  Anthropic `claude-sonnet-4-5` (`AnthropicEvaluator`, prompt-based JSON
  enforcement). Both use their official Python SDKs.
- The default model can be overridden via `EVALUATOR_MODEL` (`.env`) or the
  `--evaluator-model` CLI flag (CLI writes the env var; the factory reads it).
  Each adapter takes an optional `model` arg, falling back to its `_MODEL`
  default. Never hardcode the model at a call site — pass it through the ctor.
- Both adapters return the **identical `MatchResult` shape** — including
  `seniority_level`, `years_experience_detected`, `hire_recommendation`, and the
  9-category `score_breakdown`. Keep prompts (`prompts.py`) and parsing in sync
  with `src/core/domain/match_result.py`.
- All LLM responses must be validated into Pydantic models.
- Handle **transient** API errors gracefully — flaky calls, timeouts, and
  malformed/invalid responses return a default low-score `MatchResult`; never
  crash the run over one bad evaluation.
- **Exception — configuration errors are fatal, not graceful.** A model-not-found
  error (`NotFoundError` from either SDK) means `EVALUATOR_MODEL` is wrong for the
  provider; it would fail *every* job identically and deliver a misleading
  zero-results run. Adapters re-raise it as `ModelNotFoundError`
  (`src/core/exceptions.py`); the service re-raises rather than swallowing it; the
  immediate runner exits non-zero and the scheduler aborts that trigger. Do not
  "fix" this back into a default low-score result — the distinction is deliberate.

## Cost tracking

- `SHOW_COST_ESTIMATE` controls all cost visibility — `false` by default, with
  **zero performance impact** when disabled (all tracking bypassed).
- `CostTracker` lives in `src/infra/cost_tracker.py`; `estimate_run_cost()` in
  `src/infra/cost_estimator.py`.
- `EvaluatorPort.evaluate()` returns `tuple[MatchResult, int, int]` —
  `(result, input_tokens, output_tokens)`. Token counts come from the API
  response metadata at no extra cost.
- Token rates are configurable via `.env` (`OPENAI_INPUT_COST_PER_1M`,
  `OPENAI_OUTPUT_COST_PER_1M`, `ANTHROPIC_INPUT_COST_PER_1M`,
  `ANTHROPIC_OUTPUT_COST_PER_1M`) — **never hardcode pricing**.
- CSV always includes cost columns (empty string when tracking disabled). The
  email cost section appears only when `report.run_cost` is not None.

## Rate limiting

- `MAX_CONCURRENT_EVALUATIONS` controls the evaluation semaphore size (default
  `2`); `EVALUATION_DELAY_SECONDS` is applied after each evaluation inside the
  semaphore (default `1.0`).
- Both load from `.env` — never hardcoded. Log both values at pipeline start.
