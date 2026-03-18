"""OutputPort — abstract interface for result delivery adapters."""

from abc import ABC, abstractmethod

from src.core.domain.match_result import MatchResult


class OutputPort(ABC):
    """Abstract base class defining the contract for output delivery adapters."""

    @abstractmethod
    async def deliver(
        self,
        results: list[MatchResult],
    ) -> None:
        """Deliver ranked match results.

        Args:
            results: Ordered list of MatchResult entities to deliver.
        """
        ...
