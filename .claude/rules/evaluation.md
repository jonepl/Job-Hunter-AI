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

## Pre-filter (Gemini)

- The pre-filter is an **optional stage between scraping and evaluation** behind
  `JobEnrichmentPort` (`src/core/ports/job_enrichment_port.py`). Adapter:
  `GeminiEnrichment` (`src/adapters/enrichment/gemini_enrichment.py`), built by
  `build_enrichment()` and wired in `service_factory`.
- **The port signature is the privacy boundary.** `enrich(job: Job)` accepts only
  a `Job` and **never** a `Resume` — personal data is structurally prevented from
  reaching Gemini (ADR-022). Do not widen this contract.
- **Fail-open, always.** Any pre-filter error returns `should_skip=False` with
  `errored=True`; a failure never drops a real job. Two repeating-for-every-job
  failures trip a per-run circuit breaker that short-circuits the rest of the run
  and logs **once**: quota exhaustion (HTTP 429) and an unavailable model (HTTP
  404). A 404 is *not* fatal like the evaluator's `ModelNotFoundError` — a dead
  pre-filter just means "no pre-filtering," not a bogus zero-results run.
- **Throttle the stage.** Pre-filter calls run under their own semaphore + delay
  (`ENRICHMENT_MAX_CONCURRENT`, `ENRICHMENT_DELAY_SECONDS`) — never fire the whole
  batch at once, or a large scrape blows the provider's per-minute quota before the
  circuit breaker can trip. Both load from `.env`; never hardcode.
- **Don't let a broken pre-filter look healthy.** `EnrichmentSummary.error_count`
  counts fail-open jobs; when it equals `total_jobs` the run is fully degraded and
  flag counts are meaningless — the service warns and the email says so. Graduation
  requires `error_count == 0`.
- **Skip-but-log, never silent.** Every flag carries a `reason`. `ENRICHMENT_MODE`
  (`.env`, default `shadow`) selects behavior: `shadow` evaluates everything and
  only *measures* what would have been skipped; `enforce` withholds flagged jobs
  from the paid evaluator.
- **Graduation criterion (written).** The run report surfaces the **false-skip
  rate** (flagged jobs that nonetheless scored ≥ threshold, measurable only in
  shadow mode) plus estimated savings. Flip to `enforce` only once the false-skip
  rate is **0 across ≥50 evaluated jobs** (`GRADUATION_MIN_EVALS`). Do not remove
  this surface — without it, shadow becomes the permanent state.
- Never hardcode the Gemini model — it flows from `GEMINI_MODEL` through the ctor,
  same pattern as the evaluators.

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
