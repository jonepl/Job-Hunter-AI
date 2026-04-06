"""RunCost domain models — actual LLM token usage accumulated during a run."""

from pydantic import BaseModel


class EvaluationCost(BaseModel):
    """Represents the token usage and cost for a single job evaluation."""

    job_title: str
    """Title of the evaluated job."""

    company: str
    """Company of the evaluated job."""

    input_tokens: int
    """Number of input tokens consumed by this evaluation."""

    output_tokens: int
    """Number of output tokens consumed by this evaluation."""

    cost_usd: float
    """Total cost in USD for this evaluation."""


class RunCost(BaseModel):
    """Represents the accumulated LLM cost for an entire pipeline run.

    Built from a list of EvaluationCost instances after all evaluations
    are complete. Tracks total token usage and cost across the run.
    """

    evaluations: list[EvaluationCost]
    """One EvaluationCost entry per job evaluated this run."""

    total_input_tokens: int
    """Sum of input tokens across all evaluations."""

    total_output_tokens: int
    """Sum of output tokens across all evaluations."""

    total_cost_usd: float
    """Sum of costs across all evaluations in USD."""

    provider: str
    """LLM provider used this run (openai or anthropic)."""

    jobs_evaluated: int
    """Total number of jobs evaluated this run."""

    @property
    def formatted_total(self) -> str:
        """Return total cost as a formatted string.

        Returns:
            A string like "$0.2134" showing the total cost to four decimal places.

        Example:
            >>> RunCost(...).formatted_total
            "$0.2134"
        """
        return f"${self.total_cost_usd:.4f}"

    @classmethod
    def from_evaluations(
        cls,
        evaluations: list[EvaluationCost],
        provider: str,
    ) -> "RunCost":
        """Build a RunCost summary from a list of EvaluationCost records.

        Args:
            evaluations: List of per-job EvaluationCost instances.
            provider: LLM provider name (openai or anthropic).

        Returns:
            A RunCost aggregating all token usage and cost totals.
        """
        total_input = sum(e.input_tokens for e in evaluations)
        total_output = sum(e.output_tokens for e in evaluations)
        total_cost = sum(e.cost_usd for e in evaluations)
        return cls(
            evaluations=evaluations,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost_usd=total_cost,
            provider=provider,
            jobs_evaluated=len(evaluations),
        )
