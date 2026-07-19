"""Unit tests for the ResumeTailorPort abstract contract."""

import inspect

import pytest

from src.core.ports.resume_tailor_port import ResumeTailorPort


def test_cannot_instantiate_abstract_port():
    """The port is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ResumeTailorPort()  # type: ignore[abstract]


def test_incomplete_subclass_fails_at_instantiation():
    """A subclass missing tailor raises at instantiation, not runtime."""

    class Partial(ResumeTailorPort):
        pass  # deliberately omits tailor

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_port_declares_the_expected_methods():
    """The contract exposes exactly the tailoring operation."""
    methods = {
        name
        for name, _ in inspect.getmembers(ResumeTailorPort, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert methods == {"tailor"}
