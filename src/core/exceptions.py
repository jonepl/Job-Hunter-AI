"""Core domain exceptions shared across services and adapters.

These represent fatal configuration errors that should abort a run rather than
degrade gracefully — distinct from transient runtime failures (a flaky API
call, a malformed response) which evaluators handle by returning a default
low-score result.
"""


class ModelNotFoundError(Exception):
    """Raised when the configured evaluator model does not exist for the provider.

    A misspelled or nonexistent EVALUATOR_MODEL would otherwise fail every
    evaluation identically, producing a misleading zero-results run. Raising
    this lets the entrypoint fail fast with an actionable message instead.
    """


class GenerationError(Exception):
    """Raised when a document generation cannot start for a user-fixable reason.

    Distinct from an LLM/network failure: this signals a precondition the user
    controls — no master resume stored, or an unknown job id (F). The CLI reports
    the message and exits non-zero without writing a generation record.
    """
