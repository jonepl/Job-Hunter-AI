"""OutputPort — abstract interface for result delivery adapters."""

from abc import ABC, abstractmethod

from src.core.domain.run_report import RunReport


class OutputPort(ABC):
    """Abstract base class defining the contract for output delivery adapters."""

    @abstractmethod
    async def deliver(
        self,
        report: RunReport,
    ) -> None:
        """Deliver a run report to the output destination.

        Args:
            report: RunReport containing qualifying results, near-miss results,
                    and run metadata. Always called regardless of result count.
        """
        ...
