"""Unit tests for the EvaluatorPort abstract interface."""

import pytest

from src.core.domain.job import Job
from src.core.domain.match_result import MatchResult
from src.core.domain.resume import Resume
from src.core.ports.evaluator_port import EvaluatorPort


class ConcreteEvaluatorPort(EvaluatorPort):
    """Minimal concrete implementation of EvaluatorPort for testing."""

    async def evaluate(
        self,
        resume: Resume,
        job: Job,
    ) -> MatchResult:
        """Return a stub MatchResult — implementation for testing only."""
        return MatchResult(
            job=job,
            score=0,
            matched_skills=[],
            missing_skills=[],
            summary="stub",
        )


class IncompleteEvaluatorPort(EvaluatorPort):
    """Concrete subclass that omits the required abstract method."""

    pass


def test_evaluator_port_concrete_implementation_instantiates():
    """Happy path — a complete implementation of EvaluatorPort can be instantiated."""
    evaluator = ConcreteEvaluatorPort()
    assert isinstance(evaluator, EvaluatorPort)


def test_evaluator_port_missing_implementation_raises_type_error():
    """Validation failure — subclass missing evaluate raises TypeError."""
    with pytest.raises(TypeError):
        IncompleteEvaluatorPort()


def test_evaluator_port_evaluate_signature_matches_contract():
    """Happy path — evaluate accepts resume and job parameters."""
    import inspect

    sig = inspect.signature(EvaluatorPort.evaluate)
    params = list(sig.parameters.keys())
    assert "resume" in params
    assert "job" in params
