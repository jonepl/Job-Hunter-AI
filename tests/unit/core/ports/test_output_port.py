"""Unit tests for the OutputPort abstract interface."""

import pytest

from src.core.domain.match_result import MatchResult
from src.core.ports.output_port import OutputPort


class ConcreteOutputPort(OutputPort):
    """Minimal concrete implementation of OutputPort for testing."""

    async def deliver(
        self,
        results: list[MatchResult],
    ) -> None:
        """No-op delivery — implementation for testing only."""
        pass


class IncompleteOutputPort(OutputPort):
    """Concrete subclass that omits the required abstract method."""

    pass


def test_output_port_concrete_implementation_instantiates():
    """Happy path — a complete implementation of OutputPort can be instantiated."""
    output = ConcreteOutputPort()
    assert isinstance(output, OutputPort)


def test_output_port_missing_implementation_raises_type_error():
    """Validation failure — subclass missing deliver raises TypeError."""
    with pytest.raises(TypeError):
        IncompleteOutputPort()


def test_output_port_deliver_signature_matches_contract():
    """Happy path — deliver accepts a list of MatchResult and returns None."""
    import inspect
    sig = inspect.signature(OutputPort.deliver)
    params = list(sig.parameters.keys())
    assert "results" in params
    assert sig.return_annotation is None
