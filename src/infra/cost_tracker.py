"""Cost tracking for LLM API usage.

Tracks token consumption and cost per evaluation. Builds RunCost
summary at end of pipeline run.
"""

from src.core.domain.run_cost import EvaluationCost, RunCost


class CostTracker:
    """Accumulates LLM token usage across a pipeline run.

    Records token counts per job evaluation and builds a RunCost
    summary at run completion. All tracking is bypassed when disabled
    so there is zero performance overhead when SHOW_COST_ESTIMATE=false.
    """

    def __init__(
        self,
        provider: str,
        input_cost_per_1m: float,
        output_cost_per_1m: float,
        enabled: bool = True,
    ) -> None:
        """Initialise the cost tracker.

        Args:
            provider: LLM provider name (openai or anthropic).
            input_cost_per_1m: Input token cost per million tokens in USD.
            output_cost_per_1m: Output token cost per million tokens in USD.
            enabled: When False all record() calls are no-ops and
                     build_run_cost() returns None. Defaults to True.
        """
        self.provider = provider
        self.input_cost_per_1m = input_cost_per_1m
        self.output_cost_per_1m = output_cost_per_1m
        self.enabled = enabled
        self._evaluations: list[EvaluationCost] = []

    def record(
        self,
        job_title: str,
        company: str,
        input_tokens: int,
        output_tokens: int,
    ) -> EvaluationCost | None:
        """Record token usage for one job evaluation.

        Calculates the cost from token counts and configured rates, appends
        the result to the internal evaluation list, and returns the
        EvaluationCost for immediate logging. Returns None when disabled.

        Args:
            job_title: Title of the evaluated job.
            company: Company of the evaluated job.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens consumed.

        Returns:
            EvaluationCost for this evaluation, or None when disabled.
        """
        if not self.enabled:
            return None

        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_1m

        cost = EvaluationCost(
            job_title=job_title,
            company=company,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=input_cost + output_cost,
        )
        self._evaluations.append(cost)
        return cost

    def build_run_cost(self) -> RunCost | None:
        """Build and return a RunCost summary from all recorded evaluations.

        Returns None when disabled or when no evaluations have been recorded.

        Returns:
            RunCost aggregating all accumulated token usage, or None.
        """
        if not self.enabled:
            return None
        if not self._evaluations:
            return None
        return RunCost.from_evaluations(self._evaluations, self.provider)
