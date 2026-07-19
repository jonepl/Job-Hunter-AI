"""Unit tests for the CoverLetterPort abstract contract."""

import inspect

import pytest

from src.core.ports.cover_letter_port import CoverLetterPort


def test_cannot_instantiate_abstract_port():
    """The port is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        CoverLetterPort()  # type: ignore[abstract]


def test_incomplete_subclass_fails_at_instantiation():
    """A subclass missing generate raises at instantiation, not runtime."""

    class Partial(CoverLetterPort):
        pass  # deliberately omits generate

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_port_declares_the_expected_methods():
    """The contract exposes exactly the generation operation."""
    methods = {
        name
        for name, _ in inspect.getmembers(CoverLetterPort, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert methods == {"generate"}
