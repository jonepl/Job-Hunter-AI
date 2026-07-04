---
name: resume-evaluation
description: >
  How resume-to-job scoring works in this repo and how to change it. Use when
  editing evaluator adapters, tuning the scoring rubric or prompts, or adding a
  new evaluator provider.
---

# Skill: Resume Evaluation

## Goal

Compare a candidate resume against a job listing and return a structured
`MatchResult` with a full scoring breakdown.

## How it works today

- The resume is parsed from `docs/resume/resume.pdf` (PyPDF2) into a `Resume`
  entity. (Note: it is currently re-parsed on every run — no cache layer yet.)
- `EvaluatorPort.evaluate(resume, job, work_types=None)` returns
  `tuple[MatchResult, int, int]` = `(result, input_tokens, output_tokens)`.
  Token counts come from the API response metadata for cost tracking.
- Two adapters implement it, selected by `EVALUATOR_PROVIDER` via
  `src/adapters/evaluator/factory.py`:
  - `OpenAIEvaluator` — `gpt-4o`, `response_format` strict JSON schema.
  - `AnthropicEvaluator` — `claude-sonnet-4-5`, prompt-based JSON enforcement.
- Prompts live in `src/adapters/evaluator/prompts.py`.

## `MatchResult` shape (must be produced in full)

`src/core/domain/match_result.py`:

- `job`, `score` (0–100), `seniority_level`, `years_experience_detected`,
  `matched_skills`, `missing_skills`, `summary`, `hire_recommendation`
- `score_breakdown` — a `ScoreBreakdown` of 9 `ScoreCategory` entries
  (`max`, `earned`, `reasoning`) covering: role alignment, technical stack match,
  system design/architecture, impact & metrics, domain/industry experience,
  problem-space relevance, ownership & leadership, resume signal quality, career
  trajectory.

## Rules when changing evaluation

- Both providers must return the **identical** `MatchResult` shape — keep the
  prompt, the JSON schema, and `match_result.py` in sync.
- Validate the LLM response into the Pydantic model; on API error return a
  default low-score `MatchResult` (never crash the run).
- Test with mocked LLM responses — never call a real API in tests.
