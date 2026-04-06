"""CostEstimate domain model — pre-run LLM cost prediction."""

from pydantic import BaseModel


class CostEstimate(BaseModel):
    """Represents a static pre-run cost estimate calculated from config.

    Produced before any API calls are made using scraper config and
    token rate settings to predict the cost range for a profile run.
    """

    max_jobs: int
    """Maximum number of jobs expected to be evaluated this run."""

    est_min_cost_usd: float
    """Estimated minimum cost in USD based on minimum token assumptions."""

    est_max_cost_usd: float
    """Estimated maximum cost in USD based on maximum token assumptions."""

    provider: str
    """LLM provider name (openai or anthropic)."""

    input_cost_per_1m: float
    """Input token cost per million tokens in USD."""

    output_cost_per_1m: float
    """Output token cost per million tokens in USD."""

    @property
    def formatted_range(self) -> str:
        """Return cost range as a formatted string.

        Returns:
            A string like "$0.1234 - $0.5678" showing the min/max cost range.

        Example:
            >>> CostEstimate(...).formatted_range
            "$0.1234 - $0.5678"
        """
        return f"${self.est_min_cost_usd:.4f} - ${self.est_max_cost_usd:.4f}"
